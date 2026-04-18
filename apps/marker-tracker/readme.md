# Marker Tracker

X 光序列（DICOM 多帧 / MP4 视频）中高密度标记物的自动检测、逐帧跟踪与距离测量工具。

## 功能

- **输入支持**：DICOM 多帧序列、MP4/AVI 视频统一接口
- **自动检测**：首帧自适应阈值 + 轮廓圆度筛选自动定位 Marker
- **手动选取**：CLI 指定坐标或 GUI 点选精确初始化
- **融合跟踪**：模板匹配 + Lucas-Kanade 光流双方法加权融合，支持三种融合模式
- **质量门控**：失追段检测、帧间跳变告警、Marker ID 串换检测
- **指标计算**：Marker 间距离序列、运动位移/速度、统计摘要、Savitzky-Golay 平滑
- **Pixel Spacing 换算**：自动读取 DICOM Pixel Spacing 或人工校准，距离/运动指标支持 mm 单位
- **报告导出**：CSV 距离表 + JSON 完整结果 + PNG 轨迹可视化 + Matplotlib 高质量距离曲线图
- **关键帧截图**：自动选取首帧/末帧/距离极值帧，叠加轨迹+距离标注
- **预设模板**：心脏造影、肺部、通用视频三种预设参数模板
- **配置持久化**：PipelineConfig 支持 JSON 序列化/反序列化
- **合成数据**：7 种合成测试序列 + ground truth，用于验证和回归测试
- **GUI 界面**：PySide6 桌面界面，支持预览、参数面板、结果展示、曲线图查看、交互式导出

## 安装

```bash
# 克隆项目
cd marker-tracker

# 核心依赖（CLI 模式）
pip install -r requirements.txt

# 或使用 pip 可编辑安装
pip install -e .

# GUI 支持（可选）
pip install -e ".[gui]"

# 开发依赖（测试/lint）
pip install -e ".[dev]"
```

**依赖说明**：
- 核心依赖：numpy, opencv-python, pydicom, scipy
- GUI 可选：PySide6
- 开发可选：pytest, pytest-cov, ruff

## 快速开始

### 命令行

```bash
# 自动模式 — 检测暗色 Marker
python -m src.pipeline input.dcm -o ./output

# 自动模式 — 视频输入
python -m src.pipeline input.mp4 -o ./output --marker-type dark

# 手动模式 — 指定坐标
python -m src.pipeline input.dcm --mode manual --points "100,200;300,400" --radius 5

# 指定 Pixel Spacing 和参考距离
python -m src.pipeline input.dcm --spacing 0.154 --ref-distance 25.0

# 使用预设模板
python -m src.pipeline input.dcm --preset cardiac

# 生成合成测试数据
python -m src.pipeline --generate-test-data ./test_data

# 配置保存/加载
python -m src.pipeline input.dcm --config my_config.json --save-config saved.json
```

### GUI

```bash
python -m src.gui
```

### Python API

```python
from src import MarkerTrackerPipeline, PipelineConfig

# 方式 1：使用默认配置
pipeline = MarkerTrackerPipeline()
result = pipeline.run("input.dcm")
print(f"检测到 {result['init']['marker_count']} 个 Marker")
print(f"综合质量: {result['quality']['overall']:.2%}")
print(f"输出文件: {result['output_files']}")

# 方式 2：使用 PipelineConfig 精细控制
config = PipelineConfig()
config.init.marker_type = "dark"
config.tracking.fusion_mode = "weighted"
config.metric.pixel_spacing = 0.154      # mm/px
config.metric.known_distance_mm = 25.0   # 参考距离 mm
config.export.formats = ["csv", "json", "png"]

pipeline = MarkerTrackerPipeline(config=config)
result = pipeline.run("input.dcm")

# 方式 3：从 JSON 加载配置
config = PipelineConfig.from_json("my_config.json")
pipeline = MarkerTrackerPipeline(config=config)
```

### 分步执行

```python
from src import MarkerTrackerPipeline

pipeline = MarkerTrackerPipeline()

# 分步执行，可插入自定义逻辑
meta = pipeline.load_input("input.dcm")
init = pipeline.initialize()
tracks = pipeline.run_tracking()
quality = pipeline.evaluate_quality()
metrics = pipeline.compute_metrics()
files = pipeline.export_report()
```

## 参数说明

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `input` | - | 输入文件路径 (DICOM 或 MP4/AVI) |
| `-o`, `--output` | `./output` | 输出目录 |
| `--mode` | auto | 初始化模式：auto/manual |
| `--marker-type` | dark | Marker 类型：dark(暗点)/bright(亮点) |
| `--points` | - | 手动坐标，格式: x1,y1;x2,y2 |
| `--radius` | - | 手动指定 Marker 半径 (px) |
| `--spacing` | - | Pixel Spacing (mm/px) |
| `--ref-distance` | - | 已知参考距离 (mm) |
| `--template-threshold` | 0.5 | 模板匹配置信度下界 |
| `--max-jump` | 50.0 | 帧间最大允许跳变 (px) |
| `--preset` | - | 预设模板：cardiac / lung / video |
| `--config` | - | 从 JSON 文件加载配置 |
| `--save-config` | - | 将当前配置保存到 JSON 文件 |
| `--generate-test-data` | - | 生成合成测试数据到指定目录 |
| `-v`, `--verbose` | - | 详细日志 |
| `--debug` | - | 调试模式（保存中间帧、详细日志） |

### PipelineConfig 主要字段

| 分组 | 字段 | 默认值 | 说明 |
|------|------|--------|------|
| init | mode | auto | 初始化模式 |
| init | marker_type | dark | Marker 类型 |
| init | roi_radius | 32 | ROI 搜索半径 (px) |
| tracking | template_threshold | 0.5 | 模板匹配置信度阈值 |
| tracking | fusion_mode | weighted | 融合模式：weighted/template_only/optflow_only |
| tracking | search_radius | 32 | 搜索窗半径 (px) |
| quality | max_jump_px | 50.0 | 帧间最大允许跳变 (px) |
| quality | swap_check | True | 是否检查 ID 串换 |
| metric | pixel_spacing | None | mm/px，None 则不换算 |
| metric | known_distance_mm | None | 参考已知距离 (mm) |
| metric | smooth_window | 11 | Savitzky-Golay 平滑窗口 |
| export | formats | csv,json,png | 导出格式 |
| export | key_frame_count | 5 | 关键帧截图数量 |

## 输出文件

| 文件 | 说明 |
|------|------|
| `distance_series.csv` | 逐帧距离序列 (frame_idx, time_ms, distance_px, distance_mm, dx, dy) |
| `tracking_result.json` | 完整结果 (元信息 + 轨迹 + 指标 + 质量报告) |
| `tracking_visualization.png` | 轨迹叠加 + 距离曲线图 (OpenCV) |
| `distance_chart.png` | Matplotlib 高质量距离曲线图 (原始+平滑+质量标记) |
| `key_frames/` | 关键帧截图目录 (首帧/末帧/距离极值帧，叠加轨迹+距离标注) |

## 项目结构

```
marker-tracker/
├── src/
│   ├── __init__.py          # 包入口，版本号，公共 API 导出
│   ├── config.py            # PipelineConfig + 预设模板 + JSON 序列化
│   ├── events.py            # EventBus 事件总线 + 日志
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
│       ├── panels.py        # 参数面板 + 结果面板 (ParameterPanel/ResultPanel)
│       ├── dialogs.py       # 导出对话框 (ExportDialog)
│       └── preview.py       # 帧预览 + 交互式点选
├── tests/
│   ├── test_core.py         # tracking/metrics/quality_gate/config 单元测试
│   ├── test_image_io.py     # image_io 单元测试
│   ├── test_pipeline.py     # pipeline 端到端测试
│   ├── test_init_marker.py  # init_marker 单元测试
│   └── test_report.py       # report 单元测试
├── docs/
│   ├── PRD.md               # 产品需求文档
│   ├── TECHNICAL_DESIGN.md  # 技术设计文档
│   ├── TEST_CASES.md        # 验收测试用例
│   └── TASKS.md             # 待办任务清单
├── output/                  # 默认输出目录
├── samples/                 # 示例数据
├── pyproject.toml           # 项目元数据 + 依赖声明
├── requirements.txt         # 全量依赖（核心+GUI+dev）
├── Makefile                 # 常用命令快捷方式
└── README.md
```

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 带覆盖率
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# 仅运行核心模块测试
python -m pytest tests/test_core.py tests/test_tracking.py -v
```

## License

MIT
