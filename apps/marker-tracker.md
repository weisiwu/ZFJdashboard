# Marker Tracker

> X 光序列中高密度标记物的自动检测、逐帧跟踪与距离测量工具。

## 基本信息

| 项目 | 内容 |
|------|------|
| **技术栈** | Python · OpenCV · pydicom · NumPy |
| **状态** | ✅ PoC 阶段完成 |

## 核心功能

- **输入支持** — DICOM 多帧序列、MP4/AVI 视频统一接口
- **自动检测** — 首帧自适应阈值 + 轮廓圆度筛选自动定位 Marker
- **手动选取** — CLI 指定坐标精确初始化
- **融合跟踪** — 模板匹配 + Lucas-Kanade 光流双方法加权融合
- **质量门控** — 失追段检测、帧间跳变告警、Marker ID 串换检测
- **指标计算** — Marker 间距离序列、运动位移/速度、统计摘要
- **报告导出** — CSV 距离表 + JSON 完整结果 + PNG 轨迹可视化

## 项目结构

```
├── src/
│   ├── pipeline.py      # 主流程管线
│   ├── tracking.py      # 模板匹配 + 光流跟踪
│   ├── init_marker.py   # 首帧初始化
│   ├── image_io.py      # DICOM/MP4 读取
│   ├── metrics.py       # 距离与统计计算
│   ├── quality_gate.py  # 质量门控
│   ├── report.py        # 报告导出
│   └── config.py        # 配置参数
├── docs/
│   ├── PRD.md           # 产品需求文档
│   ├── TECHNICAL_DESIGN.md  # 技术方案设计
│   └── TEST_CASES.md    # 测试用例
└── tests/               # 单元测试
```

## 交付里程碑

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase 1: PoC | 标准 DICOM 样本跑出可信距离曲线 | ✅ 完成 |
| Phase 2: 增强 | 光流融合 + 失追恢复 + 串 ID 检测 | 🔲 待开始 |
| Phase 3: 测量 | 毫米换算 + 亚像素 + 批量处理 | 🔲 待开始 |
| Phase 4: 生产化 | GUI/Web + 深度学习 + GPU 加速 | 🔲 待开始 |
