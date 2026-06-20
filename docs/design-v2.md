# 显著性调整工具 — 设计蓝图 V2.0

> **V2.0 设计蓝图 — 已封存** | 完成日期: 2026-06-21 | 测试: 70/70
> 此文件为版本启动时的设计文档。实际实施偏差见 task-tracker.md 各 Phase 记录。

---

## 1. 版本目标与动机

### 1.1 动机

V1.0 使用 Streamlit 全栈框架实现了完整的回归诊断与样本优化功能（48 测试，5 种模型），但存在三个致命缺陷：

1. **三个 UI 层 Bug 无法快速修复**：循环导入、`st.switch_page` 参数类型错误、后台线程写入 `st.session_state` 被禁止——三者全部源于 Streamlit 框架本身的限制和 API 变更，修完一个可能引出下一个
2. **无法打包为单文件分发**：Streamlit 应用需要 `streamlit run` + 浏览器，难以给不熟悉 Python 的协作者分发
3. **UI 层不可测试**：Streamlit 页面逻辑与框架深度耦合，无法做单元测试

### 1.2 核心目标

- **替换 UI 层**：PySide6 桌面框架替代 Streamlit，彻底消除 V1 的三个 Bug
- **单文件分发**：PyInstaller 打包为 `.exe`，零依赖运行
- **保留 core/ 全部资产**：48 个测试、5 个模型、贪心算法、多模型联动——一行不改
- **新增功能**：方向选择、Stata 快速导入、因子变量处理、导出优化、配置持久化

### 1.3 版本范围

| 分类 | 包含 | 不包含（留 V3） |
|------|------|----------------|
| 架构 | PySide6 重写 UI 层 | 更多诊断面板 |
| 功能 | 方向选择、Stata 导入、因子变量、导出优化 | 分组/分层贪心 |
| UX | 模型删除、XY 冲突、标签式选择器、配置持久化 | 教程/引导模式 |
| 部署 | PyInstaller 打包 | Docker、云部署 |

---

## 2. 架构设计

### 2.1 整体架构

```
main.py → QApplication
              │
        MainWindow(QTabWidget, 4 页 Tab)
              │
    ┌─────────┼──────────┐
    │         │          │
DataPage  SetupPage  ResultsPage    ← Qt Widgets
    │         │          │
    └──── ViewModel ────┘              ← 信号桥接层
              │
           core/                        ← 纯计算，48 测试不变
```

### 2.2 与 V1 架构对比

| 层面 | V1 (Streamlit) | V2 (PySide6) | 说明 |
|------|:--------------:|:------------:|------|
| 入口 | `app.py` → `st.navigation` | `main.py` → `QApplication` | 完全替换 |
| 页面管理 | Streamlit 页面函数 | `QTabWidget` + 独立 Widget 类 | 完全替换 |
| 页面跳转 | `st.switch_page(function)` → Bug 源 | Tab 切换，无外部依赖 | 彻底消除 Bug 1&2 |
| 后台计算 | `threading.Thread` → Bug 源 | `QThread` + Signal，Qt 原生线程安全 | 彻底消除 Bug 3 |
| 状态管理 | `st.session_state` dict | `ViewModel` 单例 + Qt Signal/Slot | 类型安全 |
| 测试覆盖 | core 层 48 测试，ui 层 0 | core 48 + ViewModel 可测 + UI 可部分测 | 改善 |
| 分发 | `streamlit run app.py` | `PyInstaller → single .exe` | 新增 |

### 2.3 ViewModel 层设计

ViewModel 是 V2 架构的核心设计。它负责：

1. **持有状态**：替换 `st.session_state`。所有应用状态集中在 ViewModel 中。
2. **桥接信号**：core/ 返回的 dict 结果 → ViewModel 转换为 Qt Signal → Widget 订阅更新。
3. **管理计算生命周期**：`QThread` 启动/进度/完成/错误信号。

```python
class SigAdjustViewModel(QObject):
    # ——— 信号 ———
    data_loaded = Signal(pd.DataFrame)         # 数据导入完成
    config_changed = Signal(dict)              # 模型配置变更
    calculation_started = Signal()
    progress_updated = Signal(int, int, str)   # current, total, message
    calculation_finished = Signal(dict)        # compute_output
    calculation_error = Signal(str)
    
    # ——— 状态（直接属性） ———
    df: pd.DataFrame = None
    columns_info: dict = {}          # 与 V1 兼容格式
    config: dict = None              # compute_input 契约
    results: dict = None             # compute_output 契约
    
    # ——— 方法 ———
    def run_calculation(self) -> None: ...
    def load_data(self, path: str) -> bool: ...
    def save_config(self, path: str) -> None: ...
    def load_config(self, path: str) -> bool: ...
```

**ViewModel 的生命周期**：应用启动时创建为单例，通过依赖注入传递给所有 Page Widget。Widget 不直接持有数据，通过 ViewModel 的属性和信号访问。

### 2.4 与 V1 兼容策略

- `core/` 所有模块：**零修改**
- `core/pipeline.py` 的 `compute_input` / `compute_output` 数据契约：**完全保留**
- `core/export.py` 的函数签名：**完全保留**（新增函数追加，不改现有）
- `tests/` 所有测试：**原样保留**并继续在 CI 中运行

唯一需要修改 `core/` 的情况是 Phase 13 的方向算法——那是在 core 层新增逻辑，不破坏现有接口。

---

## 3. 功能清单

### 3.1 Phase 9: PySide6 骨架 + 数据导入页

- `main.py`：应用入口，`QApplication` 初始化
- `ui/main_window.py`：`MainWindow(QMainWindow)`，内含 `QTabWidget`，4 个 Tab 页
- `ui/viewmodel.py`：`SigAdjustViewModel(QObject)`，状态持有 + 信号桥接
- `ui/widgets/page_data.py`：文件上传（CSV/DTA/Excel），数据预览表格，列信息展示
- `ui/widgets/variable_selector.py`：标签式多选下拉组件（可搜索、标签 × 移除、支持多处复用）

### 3.2 Phase 10: 模型配置页

- **多模型表单**（1-4 个模型，每个折叠面板）
  - 模型名称、类型（OLS/Logit/Probit/FE/2SLS）、被解释变量、核心解释变量、控制变量
  - 条件字段：FE 固定效应变量 / 2SLS 内生变量+工具变量
  - 优先级滑块、目标 p 值
  - **模型删除按钮**：第 2-4 个模型显示"× 删除"按钮
  - **XY 冲突检测**：若被解释变量与核心解释变量已相同时，后选者自动取消前选者的选择（同当前控制变量的冲突机制）
  - **方向选择**：新增"期望方向"下拉（正向/负向/双向），默认双向
- **全局设置**：显著性阈值、最大删除比例
- **标签式变量选择器**：替代当前 Streamlit 原生 selectbox/multiselect，支持搜索和标签显示
- **配置持久化**：保存为 `.sigadjust.json` / 加载配置恢复表单

### 3.3 Phase 11: Stata 快速导入 + 因子变量

- **Stata Parser** `ui/widgets/stata_parser.py`
  - 解析命令：`reg` / `logit` / `probit` / `ologit` / `oprobit`
  - 结构：`command depvar [indepvars] [if] [in] [weight] [, options]`
  - 提取：被解释变量(depvar)、核心解释变量(第一个 indepvar)、控制变量(其余 indepvars)
  - 变量存在性校验：与当前数据集列名匹配
  - 成功后自动填入 SetupPage 表单
- **因子变量处理**
  - 检测 `i.varname` 语法
  - 自动创建对应的分类虚拟变量（pandas `get_dummies`）
  - 将生成的虚拟变量加入控制变量列表
- **入口**：SetupPage 上的"Stata 导入"按钮 → 弹窗输入

### 3.4 Phase 12: 计算 + 结果 + 导出

- **计算进度页** `ui/widgets/page_progress.py`
  - `QThread` 后台执行 `core.pipeline.run_pipeline()`
  - 进度条 + 状态文本（绑定 ViewModel 的 `progress_updated` 信号）
  - 完成自动跳转结果 Tab
- **结果展示页** `ui/widgets/page_results.py`
  - 单模型 Tab：t 值曲线（Plotly）、删除路径表、F 统计量曲线（2SLS）
  - 多模型 Tab：安全交集大小、冲突系数、冲突热力图（Plotly Heatmap）、帕累托叠加
  - 指标卡片：基线/最终 t 值、p 值、R²、删除数
- **导出优化**
  - **乱码修复**：中文变量名在 DTA 导出时按 pandas 规范处理，确保非乱码
  - **新增 `drop_*_order` 列**：从 1 开始计数的删除顺序标识符
  - **轻量 DTA 文件**：仅含用户指定的标识变量（通常 id + year）+ `drop_*` 变量
  - **merge 命令提示**：生成 `merge 1:1 id year using "C:\Users\[username]\Downloads\drop_*.dta", keepusing(drop_*) nogen` 并显示/可复制

### 3.5 Phase 13: 方向算法 + PyInstaller 打包

- **两步式方向算法**（在 `core/greedy_search.py` 或新增 `core/direction_search.py`）
  - **阶段一（翻号）**：如果当前 `β` 符号与期望方向相反，优先删除使 `β` 向零趋近的观测，直到 `β` 翻正/翻负或达到符号一致
  - **阶段二（优化）**：符号一致后，在候选集中只保留使 `t` 值朝期望方向改善的观测，继续贪心迭代
  - 双向 = 不做方向过滤 = V1 原有行为
  - 控制器：`compute_input` 中新增 `"direction": "positive" | "negative" | "both"` 字段
- **PyInstaller 打包**
  - `sigadjust.spec`：单文件 exe，包含 core/ + ui/ + PySide6 依赖
  - 图标、版本号、公司名等元数据
  - `--onefile` 模式

---

## 4. 数据模型变动

### 4.1 compute_input 新增字段

```python
compute_input = {
    "df": pd.DataFrame,
    "global_settings": {
        "significance_threshold": 0.05,
        "max_deletions_pct": 5.0,
        "mode": "greedy",              # 不变
        "direction": "positive"         # 新增: "positive" | "negative" | "both"
    },
    "models": [
        {
            # ... 全部 V1 字段不变 ...
            "name": "主回归",
            "type": "ols",             # 不变
            # ... V1 字段 ...
        }
    ]
}
```

### 4.2 compute_output 新增字段

```python
compute_output = {
    "models": {
        "<model_name>": {
            # ... V1 全部字段不变 ...
            "deletion_path": [
                {
                    "step": 1, "obs_id": 42, "t_after": 1.68, "p_after": 0.093
                    # "direction": "sign_flip" | "optimize"  # 新增: 标记阶段
                }
            ],
            "final": {
                # ... V1 字段 ...
                "direction_achieved": "positive"  # 新增: 最终方向状态
            }
        }
    }
}
```

### 4.3 导出新增列

| 列名 | 说明 | 示例 |
|------|------|------|
| `drop_{name}` | 0/1 标记是否被删除 | `drop_主回归` |
| `drop_{name}_order` | 删除顺序（从 1 开始），0=未删除 | `drop_主回归_order` |
| `drop_all_safe` | 多模型安全交集标记 | 0/1 |

### 4.4 配置持久化格式

```json
{
    "version": "2.0",
    "global_settings": {
        "significance_threshold": 0.05,
        "max_deletions_pct": 5.0,
        "direction": "positive"
    },
    "models": [
        {
            "name": "模型_1", "type": "ols",
            "dependent_var": "y", "key_var": "x",
            "control_vars": ["c1", "c2"],
            "fe_vars": [], "endogenous_var": "", "instruments": [],
            "priority": 5, "target_p": 0.05,
            "direction": "positive"
        }
    ]
}
```

---

## 5. 向后兼容性

| 项目 | 兼容策略 |
|------|---------|
| `core/` 模块 | 100% 保留，零修改。方向算法通过新增 `core/direction_search.py` 或参数扩展实现 |
| `tests/` | 48 个测试全部保留并继续通过 |
| V1 计算的存档结果 | V1 导出文件（CSV/DTA/Excel）与 V2 兼容——新增的 `_order` 列仅在 V2 导出中出现 |
| 用户工作流 | V1 用户迁移到 V2 需重新安装（exe 替换），但数据文件和分析结果完全可读 |

**需要打破的兼容项**：
- Streamlit 的 `st.session_state` 状态管理 → ViewModel
- 页面跳转机制 → QTabWidget
- 线程模型 → QThread

这些都是 UI 层内部替换，不影响 core/ 数据契约和用户数据文件。

---

## 6. 新增技术决策

| 决策 | 选定方案 | 理由 |
|------|---------|------|
| UI 框架 | PySide6（非 PyQt6） | LGPL 许可、商业化友好、官方推荐 |
| 打包方案 | PyInstaller `--onefile` | 成熟稳定、单 exe 分发 |
| 架构模式 | ViewModel + Signal/Slot | 保持 core/ 纯函数、UI 独立可测、V1 数据契约完整保留 |
| 后台计算 | QThread + Signal（非 concurrent.futures） | Qt 原生线程方案、与 Signal/Slot 天然集成 |
| 图表库 | Plotly（与 V1 一致） | 交互式图表质量高、PySide6 可通过 `QWebEngineView` 嵌入 |
| 配置持久化 | JSON 格式（非 pickle/TOML） | 人类可读、跨平台、便于版本控制 |
| Stata parser | 正则解析，5 个命令 | 第一期需求明确，无需引入 parso/tokenize 等重型工具 |
| 方向算法 | 两步式（翻号 → 优化） | 行为可解释、用户可预期、与现有贪心框架兼容 |
| 变量选择器 | 自定义 QWidget：标签区 + 搜索框 + 变量名矩形块候选网格 | 变量名块即点击目标、无复选框、X/Y互斥/优先级最高、Control自动排除已占变量 |

---

## 7. 测试策略

| 层 | 来源 | 测试数 | 说明 |
|----|------|:-----:|------|
| core/ 现有 | V1 保留 | 48 | 零修改，继续全部通过 |
| core/ 新增 | 方向算法 | 4-6 | 翻号逻辑、方向过滤、边界情况 |
| Stata parser | 新增 | 4-6 | 5 种命令解析、变量校验、无效输入 |
| ViewModel | 新增 | 4-6 | 核心状态流转、信号发射 |
| 导出 | V1 扩展 | +2 | order 列、轻量 DTA 格式 |
| **总计** | | **~64-68** | |

---

## 8. 向后兼容（已封存设计参考）

设计中参考了 V1 封存后的经验教训（见 `docs/design-v1.md` 中 §6 Design-Implementation Deviations）：

- 加权贪心的 1.96 硬编码 → V2 仍需改进，但优先级较低
- FE 每迭代重新去均值 → V2 保留当前行为
- 设定曲线枚举 → 延期至 V3
