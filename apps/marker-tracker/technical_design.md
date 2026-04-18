# Marker Tracker — 技术方案设计

> **版本**：v2.0 | **日期**：2026-04-19 | **状态**：Beta

---

## 一、系统架构

### 1.1 六段式流水线

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  DICOM/MP4  │───▶│  帧序列解码   │───▶│ 首帧 marker  │
│   输入层     │    │  + 时间轴     │    │   初始化     │
└─────────────┘    └──────────────┘    └──────┬───────┘
                                              │
┌─────────────┐    ┌──────────────┐    ┌──────▼───────┐
│  导出报告    │◀───│  距离曲线    │◀───│  逐帧跟踪    │
│  + 可视化    │    │  + 统计摘要  │    │ + 失追恢复   │
└─────────────┘    └──────────────┘    └──────────────┘
         ▲                                     │
         │         ┌──────────────┐             │
         └─────────│  质量门控    │◀────────────┘
                   └──────────────┘
```

流水线由 `MarkerTrackerPipeline` 类编排，支持两种执行模式：
- **一键执行**：`pipeline.run(input_path)` — 全自动完成所有阶段
- **分步执行**：`load_input()` → `initialize()` → `run_tracking()` → `evaluate_quality()` → `compute_metrics()` → `export_report()` — 每步可插入自定义逻辑

### 1.2 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置管理 | `src/config.py` | `PipelineConfig` dataclass + 3 种预设模板 + JSON 序列化/反序列化 + 参数校验 |
| 事件系统 | `src/events.py` | `EventBus` 事件总线 + `ProgressPrinter` / `DebugFrameSaver` / `EventLogger` 内置回调 |
| 输入解码 | `src/image_io.py` | DICOM/MP4 读取、按需帧提取、时间轴构建、元信息解析 |
| 首帧初始化 | `src/init_marker.py` | 自适应阈值检测 / 人工点选、ROI 建立、模板提取 |
| 逐帧跟踪 | `src/tracking.py` | 模板匹配 + 光流双路融合、三级失追恢复、模板动态更新 |
| 质量控制 | `src/quality_gate.py` | 失追段检测、帧间跳变告警、Marker ID 串换检测 |
| 距离度量 | `src/metrics.py` | 距离/运动指标计算、Savitzky-Golay 平滑、统计摘要、mm 换算 |
| 报告导出 | `src/report.py` | `ReportExporter` 统一管理：CSV/JSON/PNG/Chart/关键帧截图 |
| 主流程 | `src/pipeline.py` | `MarkerTrackerPipeline` 类 + 状态机 + EventBus + CLI 入口 |
| 合成数据 | `src/synthetic.py` | 7 种合成测试序列 + ground truth JSON |
| GUI | `src/gui/` | PySide6 桌面界面（4 个子模块） |

---

## 二、模块详细设计

### 2.0 配置管理 — `config.py`

#### PipelineConfig 层级结构

```python
@dataclass
class InitConfig:
    mode: str = "auto"                  # auto | manual | semi_auto
    marker_type: str = "dark"           # dark | bright
    roi_radius: int = 32                # ROI 搜索半径 (px)
    auto_threshold_method: str = "otsu" # otsu | adaptive | fixed
    auto_threshold_value: float = 0.0
    min_marker_area: int = 10
    max_marker_area: int = 500
    circularity_threshold: float = 0.5

@dataclass
class TrackingConfig:
    template_threshold: float = 0.5
    template_update_alpha: float = 0.0  # 0=不更新
    template_update_interval: int = 5
    template_update_score: float = 0.8
    search_radius: int = 32
    optflow_win_size: int = 31
    optflow_max_level: int = 3
    fusion_mode: str = "weighted"       # weighted | template_only | optflow_only

@dataclass
class QualityConfig:
    max_jump_px: float = 50.0
    max_consecutive_lost: int = 10
    swap_check: bool = True
    recovery_expand_factor: float = 2.0
    recovery_max_level: int = 3

@dataclass
class MetricConfig:
    pixel_spacing: float | None = None
    known_distance_mm: float | None = None
    smooth_window: int = 11
    smooth_order: int = 3

@dataclass
class ExportConfig:
    output_dir: str = "./output"
    formats: list[str] = field(default_factory=lambda: ["csv", "json", "png"])
    key_frame_count: int = 5
    dpi: int = 150
    curve_show_confidence: bool = True
    trajectory_overlay: bool = True

@dataclass
class PipelineConfig:
    init: InitConfig = field(default_factory=InitConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    metric: MetricConfig = field(default_factory=MetricConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    debug: bool = False
    debug_save_frames: bool = False
    debug_output_dir: str = "./debug_output"

    def validate(self) -> list[str]: ...
    def to_json(self, path: str) -> None: ...
    @classmethod
    def from_json(cls, path: str) -> "PipelineConfig": ...
```

#### 预设模板

| 预设名 | 适用场景 | 关键差异 |
|--------|----------|----------|
| `cardiac` | 心脏造影 | 高帧率、小搜索窗、低阈值 |
| `lung` | 肺部 | 大搜索窗、低阈值、允许更大跳变 |
| `video` | 通用视频 | 大搜索窗、光流权重更高、更大平滑窗口 |

---

### 2.1 事件系统 — `events.py`

#### EventBus

```python
class EventType(str, Enum):
    # 流水线生命周期
    PIPELINE_START / PIPELINE_COMPLETE / PIPELINE_ERROR
    # 各阶段
    STAGE_START / STAGE_PROGRESS / STAGE_COMPLETE / STAGE_ERROR
    # 帧级
    FRAME_TRACKED / FRAME_LOST / FRAME_RECOVERED
    # 质量告警
    QUALITY_WARNING / SWAP_DETECTED

@dataclass
class Event:
    type: EventType
    stage: str          # load / init / tracking / quality / metrics / export
    data: dict
    timestamp: float

class EventBus:
    def on(self, event_type: EventType, callback: EventCallback) -> None: ...
    def on_any(self, callback: EventCallback) -> None: ...
    def emit(self, event: Event) -> None: ...
    @property
    def history(self) -> list[Event]: ...
```

#### 内置回调

| 回调类 | 功能 |
|--------|------|
| `ProgressPrinter` | CLI 进度条，`[████████░░] 80.0% 跟踪中...` |
| `DebugFrameSaver` | 调试帧保存，缩略 + 采样，最多 500 帧 |
| `EventLogger` | 全量事件写入日志文件 |

---

### 2.2 输入解码 — `image_io.py`

#### 输入接口

```python
class SequenceReader:
    """统一 DICOM/MP4 帧序列读取接口"""

    def __init__(self, path: str):
        self.path = path

    @property
    def frame_count(self) -> int: ...

    @property
    def fps(self) -> float: ...

    @property
    def metadata(self) -> dict: ...

    def get_frame(self, idx: int) -> np.ndarray:
        """返回第 idx 帧灰度图 (按需加载)"""

    def get_time_axis(self) -> np.ndarray:
        """返回每帧对应的时间戳数组 (ms)
        优先级：DICOM Frame Time Vector > Frame Time > fps 换算 > frame index
        """

    def get_pixel_spacing(self) -> float | None:
        """返回 Pixel Spacing (mm/px)，无则返回 None"""
```

#### DICOMReader

```python
class DICOMReader(SequenceReader):
    def __init__(self, path: str):
        self.ds = pydicom.dcmread(path)
        self._parse_metadata()

    def _extract_frame(self, idx: int) -> np.ndarray:
        """单帧按需提取 + 归一化 + 灰度转换"""

    def _build_time_axis(self) -> np.ndarray:
        """构建时间轴（使用 frame_count 而非 len(frames)，避免全量加载）"""

    @property
    def frames(self) -> list[np.ndarray]:
        """全量帧序列（兼容旧接口，大序列慎用）"""
```

**关键优化**：`_build_time_axis()` 使用 `self.frame_count` 而非 `len(self.frames)`，避免为获取帧数而触发全量像素加载。

#### VideoReader

```python
class VideoReader(SequenceReader):
    def __init__(self, path: str):
        self.cap = cv2.VideoCapture(path)
        self._fps = self.cap.get(cv2.CAP_PROP_FPS)

    def get_time_axis(self) -> np.ndarray:
        """无 DICOM 元信息，按 fps 近似换算"""

    def get_pixel_spacing(self) -> None:
        """视频输入无空间标定信息，返回 None"""
```

#### 工厂函数

```python
def create_reader(path: str) -> SequenceReader:
    """根据文件扩展名自动创建 DICOMReader 或 VideoReader"""
```

---

### 2.3 首帧初始化 — `init_marker.py`

#### 初始化流程

```
首帧灰度图
  ├─ auto 模式：自适应阈值 + 轮廓检测 → 圆度筛选 → MarkerROI 列表
  └─ manual 模式：人工点选坐标 → 以各点为中心提取模板
  → 建立搜索窗 (search_radius)
  → 返回 InitializationResult
```

#### 数据结构

```python
@dataclass
class MarkerROI:
    """单个 Marker 的 ROI 信息"""
    marker_id: int
    cx: float               # Marker 中心 x (像素坐标)
    cy: float               # Marker 中心 y (像素坐标)
    radius: float           # Marker 半径 (px)
    template: np.ndarray    # 模板图像 patch
    search_radius: float = 0.0  # 搜索窗口半径

@dataclass
class InitializationResult:
    """首帧初始化结果"""
    frame_idx: int = 0
    frame_shape: tuple = (0, 0)
    markers: list[MarkerROI] = field(default_factory=list)
    line_ref_length_px: float = 0.0

    @property
    def marker_count(self) -> int: ...
```

#### FrameInitializer

```python
class FrameInitializer:
    def __init__(self, threshold_method="otsu", threshold_value=0.0,
                 marker_type="dark", circularity_threshold=0.5,
                 threshold_area_range=(10, 500)): ...

    def auto_detect(self, frame: np.ndarray, marker_type="dark"
                    ) -> list[MarkerROI]:
        """自适应阈值 + 轮廓检测自动定位 Marker"""

    def manual_select(self, frame: np.ndarray, points: list[tuple[float, float]],
                      radius: float | None = None) -> list[MarkerROI]:
        """基于人工点选坐标创建 Marker ROI"""

    def initialize(self, frame: np.ndarray, config: InitConfig,
                   manual_points: list | None = None) -> InitializationResult:
        """统一初始化入口，根据 config.mode 选择自动/手动"""
```

---

### 2.4 逐帧跟踪 — `tracking.py`

#### 双路融合策略

```
第 i 帧 (MarkerTracker.track_frame):
  1. 光流预测：用上一帧位置预测当前位置 (Lucas-Kanade)
  2. 模板匹配：在预测位置附近搜索 (Template Matching)
  3. 融合判定 (fusion_mode):
     - weighted: 两路加权融合，距离<3px 取模板匹配，否则取高置信路
     - template_only: 仅使用模板匹配
     - optflow_only: 仅使用光流预测
  4. 置信度评估：综合两路分数
  5. 失追检测：置信度低于阈值 → 尝试恢复
  6. 模板更新：连续 N 帧高分时用当前帧更新模板
```

#### 数据结构

```python
@dataclass
class TrackPoint:
    """单帧单 Marker 的跟踪结果"""
    frame_idx: int
    marker_id: int
    cx: float
    cy: float
    confidence: float       # 0~1 跟踪置信度
    method: str = "fusion"  # "template" / "flow" / "fusion"
    lost: bool = False      # 是否失追
```

#### MarkerTracker

```python
class MarkerTracker:
    def __init__(self, markers: list[MarkerROI], config: TrackingConfig): ...

    def track_frame(self, prev_frame: np.ndarray, curr_frame: np.ndarray
                    ) -> list[TrackPoint]:
        """跟踪单帧，返回每个 Marker 的 TrackPoint"""

    def _attempt_recovery(self, prev_frame, curr_frame, cx, cy,
                          template, marker, frame_idx, marker_id
                          ) -> TrackPoint:
        """三级失追恢复（内嵌于 MarkerTracker，无独立 RecoveryManager 类）：
        Level 1: 降低阈值 + 扩大搜索窗 (search_radius × expand_factor)
        Level 2: 提高金字塔层数重试光流
        Level 3: 标记为不可恢复 (lost=True)
        """
```

#### 模板更新策略

```python
def _maybe_update_template(self, marker_id: int, frame: np.ndarray,
                           score: float) -> None:
    """当连续 template_update_interval 帧匹配分数 > template_update_score 时，
    用当前帧更新模板，防止模板老化导致漂移。
    更新学习率由 template_update_alpha 控制（0=不更新）。"""
```

---

### 2.5 质量控制 — `quality_gate.py`

#### QualityReport

```python
@dataclass
class QualityReport:
    """质量门控报告"""
    total_frames: int
    total_markers: int
    lost_frames: list[dict]           # [{marker_id, start_frame, end_frame}]
    swap_warnings: list[dict]         # [{frame_idx, marker_a, marker_b, distance}]
    jump_warnings: list[dict]         # [{marker_id, frame_idx, jump_px}]
    overall_quality: float            # 0~1 综合评分
    flagged: bool                     # 是否需要人工复检
```

#### QualityGate

```python
class QualityGate:
    def __init__(self, max_jump_px: float = 50.0,
                 swap_check_enabled: bool = True,
                 lost_recover_max_gap: int = 3,
                 quality_threshold: float = 0.7): ...

    def evaluate(self, tracks: list[list[TrackPoint]],
                 time_axis: np.ndarray | None = None
                 ) -> QualityReport:
        """评估跟踪质量，生成全局报告"""
```

#### 检测规则明细

| 规则 | 条件 | 级别 |
|------|------|------|
| 失追段 | 连续 N 帧 lost=True | warning |
| 帧间跳变 | 位移 > max_jump_px | warning |
| 串 ID 嫌疑 | A/B 相对位置翻转 | critical |
| 综合评分 | 基于 complete_rate + low_conf_rate | info |
| 人工复检 | flagged=True（质量低于阈值） | critical |

---

### 2.6 距离度量 — `metrics.py`

#### 数据结构

```python
@dataclass
class DistanceMetrics:
    """单帧距离指标"""
    frame_idx: int
    time_ms: float
    distance_px: float
    distance_mm: float | None  # None 表示无 pixel spacing
    dx_px: float               # x 方向位移分量
    dy_px: float               # y 方向位移分量

@dataclass
class MotionMetrics:
    """单 Marker 运动指标"""
    frame_idx: int
    time_ms: float
    marker_id: int
    # ... 位移/速度分量

@dataclass
class SummaryStats:
    """统计摘要"""
    mean: float; std: float; min: float; max: float
    median: float; p5: float; p95: float; range: float

@dataclass
class MetricsResult:
    """完整的指标计算结果"""
    distance_series: list[DistanceMetrics]
    motion_series: list[list[MotionMetrics]]  # 每个 Marker 一组
    distance_stats: SummaryStats | None
    baseline_distance_px: float = 0.0
    baseline_distance_mm: float | None = None
```

#### MetricsCalculator

```python
class MetricsCalculator:
    def __init__(self, pixel_spacing: float | None = None,
                 known_distance_mm: float | None = None,
                 smooth_window: int = 11, smooth_order: int = 3): ...

    def compute(self, tracks: list[list[TrackPoint]],
                time_axis: np.ndarray | None = None
                ) -> MetricsResult:
        """
        1. 从 TrackPoint 列表计算每帧 Marker 间距离
        2. Savitzky-Golay 平滑 (window, order)
        3. 计算统计摘要 (mean/std/min/max/median/p5/p95/range)
        4. 如有 pixel_spacing，额外输出 mm 版本
        5. 如有 known_distance_mm，计算基线校准
        """
```

---

### 2.7 报告导出 — `report.py`

#### ReportExporter

```python
class ReportExporter:
    def __init__(self, output_dir: str, config: ExportConfig | None = None): ...

    def export_all(self, tracks, metrics, quality, frames_getter=None,
                   metadata=None) -> dict:
        """导出全部格式的报告，返回 {格式: 文件路径} 字典"""

    def export_csv(self, metrics: MetricsResult) -> str:
        """导出距离序列 CSV
        列：frame_idx, time_ms, distance_px, distance_mm, dx_px, dy_px
        """

    def export_json(self, tracks, metrics, quality, metadata) -> str:
        """导出完整 JSON 结果
        {metadata, statistics, quality, frames: [...], markers: [...]}
        """

    def export_visualization(self, tracks, metrics, frames_getter) -> str:
        """OpenCV 轨迹叠加 + 距离曲线图 → tracking_visualization.png"""

    def export_distance_chart(self, metrics, quality) -> str | None:
        """Matplotlib 高质量距离曲线图 → distance_chart.png
        原始曲线 + 平滑曲线 + 置信度条带 + d_max/d_min 标注
        """

    def export_key_frames(self, tracks, metrics, frames_getter,
                          key_frame_indices=None) -> str:
        """关键帧截图导出 → key_frames/ 目录
        自动选取：首帧、末帧、距离极值帧
        截图上叠加：轨迹线 + Marker 位置 + 帧号 + 距离标注
        """
```

---

### 2.8 主流程编排 — `pipeline.py`

#### PipelineState 状态机

```python
class PipelineState(str, Enum):
    IDLE → LOADING → INITIALIZING → TRACKING → EVALUATING → COMPUTING → EXPORTING → COMPLETED
                                                                         ↘ ERROR
                                                                         ↘ CANCELLED
```

#### MarkerTrackerPipeline

```python
class MarkerTrackerPipeline:
    def __init__(self, config: PipelineConfig | None = None,
                 event_bus: EventBus | None = None): ...

    # 一键执行
    def run(self, input_path: str, output_dir: str | None = None,
            manual_points: list | None = None) -> dict: ...

    # 分步执行
    def load_input(self, path: str) -> dict: ...
    def initialize(self, manual_points=None) -> InitializationResult: ...
    def run_tracking(self) -> list[list[TrackPoint]]: ...
    def evaluate_quality(self) -> QualityReport: ...
    def compute_metrics(self) -> MetricsResult: ...
    def export_report(self) -> dict: ...

    # 取消
    def cancel(self) -> None: ...

    # 状态
    state: PipelineState
    config: PipelineConfig
    events: EventBus
```

**关键特性**：
- **EventBus 集成**：每个阶段发射 STAGE_START/STAGE_PROGRESS/STAGE_COMPLETE 事件，GUI 可实时响应
- **取消机制**：跟踪循环中检查 `self.state == CANCELLED`，可随时中断
- **分步执行**：每步返回结果，用户可在步骤间插入自定义逻辑

---

### 2.9 合成数据 — `synthetic.py`

#### 测试序列

| 序列名 | 帧数 | 特点 | 用途 |
|--------|------|------|------|
| standard | 200 | 标准2个暗色Marker，正弦运动 | 基本功能验证 |
| minimal | 2 | 最小帧数 | 边界条件 B-01 |
| large | 1000 | 大帧数 | 边界条件 B-02 |
| high_noise | 200 | 高噪声 | 鲁棒性测试 |
| close_range | 200 | 近距离Marker | 边界条件 B-04 |
| large_motion | 200 | 大幅运动 | 跟踪极限测试 |
| bright_markers | 200 | 亮色Marker | 反向对比度测试 |

```python
class MarkerMotion:
    """定义 Marker 的运动模式"""

def generate_sequence(name: str, n_frames: int = 200, size: int = 512
                      ) -> tuple[list[np.ndarray], dict]:
    """生成合成序列 + ground truth"""

def generate_test_suite(output_dir: str) -> str:
    """生成全部 7 个测试序列到指定目录"""
```

---

### 2.10 GUI — `src/gui/`

#### 模块结构

| 模块 | 文件 | 职责 |
|------|------|------|
| 主窗口 | `main_window.py` | 窗口布局、菜单栏、PipelineWorker 线程 |
| 参数面板 | `panels.py` | `ParameterPanel`（参数配置）、`ResultPanel`（结果展示） |
| 对话框 | `dialogs.py` | `ExportDialog`（导出配置） |
| 预览 | `preview.py` | 帧预览、交互式 Marker 点选 |

#### PipelineWorker

```python
class PipelineWorker(QThread):
    """在后台线程执行 Pipeline，通过信号通知 GUI"""
    stage_changed = Signal(str)
    progress_updated = Signal(int, int)  # current, total
    result_ready = Signal(dict)
    error_occurred = Signal(str)
```

---

## 三、技术栈

| 组件 | 选型 | 版本 |
|------|------|------|
| 语言 | Python | 3.10+ |
| 图像处理 | OpenCV | 4.x |
| DICOM 读取 | pydicom | 3.x |
| 数值计算 | NumPy | 1.26+ |
| 曲线平滑 | SciPy (savgol_filter) | 1.12+ |
| 绘图 | Matplotlib | 3.8+ |
| GUI | PySide6 | 6.x (可选) |
| 数据结构 | dataclasses (stdlib) | - |

---

## 四、参数配置

详见 [2.0 配置管理](#20-配置管理--configpy) 和 [2.8 主流程编排](#28-主流程编排--pipelinepy)。

配置加载优先级：CLI 参数 > JSON 配置文件 > 预设模板 > 默认值

---

## 五、错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| DICOM 文件损坏 | 抛出明确异常，提示文件不可读 |
| 多帧 DICOM 帧数为 0 | 降级为单帧处理或报错 |
| 首帧点选位置越界 | 提示重新点选 |
| 全程跟丢（连续 10 帧失追） | 标记为不可恢复，继续处理其余 Marker |
| Pixel Spacing 缺失 | 只输出 px 结果，跳过 mm 换算 |
| Frame Time Vector 缺失 | 降级为 fps 或 frame index 时间轴 |
| Matplotlib 不可用 | 跳过 Chart/PDF 导出，不影响其余功能 |

---

## 六、目录结构

```
marker-tracker/
├── src/
│   ├── __init__.py          # 包入口，版本号 2.0.0，公共 API 导出
│   ├── config.py            # PipelineConfig + 预设模板 + JSON 序列化
│   ├── events.py            # EventBus 事件总线 + 内置回调
│   ├── image_io.py          # DICOM/视频输入解码 (DICOMReader/VideoReader)
│   ├── init_marker.py       # 首帧 Marker 检测/选取 (FrameInitializer)
│   ├── tracking.py          # 模板匹配 + 光流融合跟踪 (MarkerTracker)
│   ├── quality_gate.py      # 质量门控与异常检测 (QualityGate)
│   ├── metrics.py           # 距离/运动指标计算 (MetricsCalculator)
│   ├── report.py            # CSV/JSON/PNG/Chart/关键帧 报告导出 (ReportExporter)
│   ├── pipeline.py          # 主流程编排 + CLI 入口 (MarkerTrackerPipeline)
│   ├── synthetic.py         # 合成数据生成 (7 种测试序列 + ground truth)
│   └── gui/
│       ├── __init__.py      # GUI 包入口
│       ├── main_window.py   # 主窗口 + PipelineWorker 线程
│       ├── panels.py        # 参数面板 + 结果面板
│       ├── dialogs.py       # 导出对话框
│       └── preview.py       # 帧预览 + 交互式点选
├── tests/
│   ├── test_core.py         # tracking/metrics/quality_gate/config 单元测试
│   ├── test_image_io.py     # image_io 单元测试
│   ├── test_pipeline.py     # pipeline 端到端测试
│   ├── test_init_marker.py  # init_marker 单元测试 (17 用例)
│   └── test_report.py       # report 单元测试 (15 用例)
├── docs/
│   ├── PRD.md               # 产品需求文档
│   ├── TECHNICAL_DESIGN.md  # 技术方案设计（本文件）
│   ├── TEST_CASES.md        # 验收测试用例
│   └── TASKS.md             # 待办任务清单
├── output/                  # 默认输出目录
├── samples/                 # 示例数据
├── pyproject.toml           # 项目元数据 + 依赖声明
├── requirements.txt         # 全量依赖（核心+GUI+dev）
├── Makefile                 # 常用命令快捷方式
└── README.md
```
