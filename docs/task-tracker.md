# 显著性调整工具 — 任务追踪器

## 文档维护准则

| 准则 | 说明 |
|------|------|
| 同步更新 | 任何架构/接口/规则变更必须同步更新本文档对应区域 |
| 版本标记 | 每次更新在"最近变更摘要区"记录日期、变更人、变更内容 |
| 接口契约 | "核心接口签名区"中的函数签名是 core↔ui 的硬边界，修改须评审 |
| 规则溯源 | "业务逻辑核心规则区"中的每条规则须标注源自技术文档的节号 |
| 清理时机 | 每个 Phase 结束时清理对应的 .codex/plans/ 工作草稿 |

---

## V2.0 版本信息

- **版本**: V2.0
| 2026-06-20 | Codex | 14a | Phase 14a: Bug 修复 + 中文化 + 方向 UI 修正 (变量候选空修复, 方向UI复选框, QComboBox宽度, Y/X并排布局, 全应用中文化7文件)
| 2026-06-21 | Codex | final | V2.0 收尾封存 (文档封存/目录清理/70测试通过) |
| 2026-06-20 | Codex | 13 | Phase 13: 方向算法 + PyInstaller 打包 (_apply_direction_filter, 翻号+优化两阶段, 4新测试, 70 total, sigadjust.spec)
| 2026-06-20 | Codex | 11 | Phase 11: Stata 快速导入 + 因子变量 (StataCommandParser 纯逻辑解析器, StataImportDialog 解析/预览/因子展开/自动填充, 7 个纯逻辑测试, 61 total)
| 2026-06-20 | Codex | 10 | Phase 10: 模型配置页 (ModelCard + SetupPage, 多模型表单, XY冲突/Control排除, 配置JSON持久化, Stata导入占位)
| 2026-06-20 | Codex | 9 | Phase 9: PySide6 骨架 + 数据导入页 (main.py, ViewModel, MainWindow, DataPage, VariableSelector, 4 ViewModel tests, 54 total)
| 2026-06-20 | Codex | 4-5 | Phase 4: Logit/Probit + Phase 5: FE (9 new tests, 33 total, model type selector) Logit/Probit 支持 (6 tests, dfbetas standardized formula confirmed)
| 2026-06-20 | Codex | 1-3 | Batch 1: 前置清理 + 数据导入页面 + OLS 核心计算 + 全流程 UI (24 tests) |
- **创建日期**: 2026-06-18
- **状态**: 已完成
- **完成日期**: 2026-06-21
- **总测试**: 70

---

## Phase 清单

| Phase | 名称 | 状态 | 开始日期 | 完成日期 | 备注 |
|-------|------|------|---------|---------|------|
| 0-8 | V1.0 基础架构 (Phase 0-8) | 已完成 | 2026-06-18 | 2026-06-20 | Streamlit 基础架构与 5 种模型核心功能，48 测试 |
| 9 | PySide6 骨架 + 数据导入页 | 已完成 | 2026-06-20 | 2026-06-20 | main.py, ui/viewmodel.py, ui/main_window.py, ui/widgets/page_data.py, ui/widgets/variable_selector.py, 4 new tests |
| 10 | 模型配置页 | 已完成 | 2026-06-20 | 2026-06-20 | ui/widgets/page_setup.py (ModelCard + SetupPage + StataImportDialog), ViewModel config_changed + save/load_config, MainWindow switch_to_tab |
| 11 | Stata 快速导入 + 因子变量 | 已完成 | 2026-06-20 | 2026-06-20 | ui/widgets/stata_parser.py (StataCommandParser), 更新 StataImportDialog (解析/预览/因子展开/填充表单), 7 个 parser 测试 |
| 12 | 计算进度 + 结果展示 + 导出优化 | 已完成 | 2026-06-20 | 2026-06-20 |
| 13 | 方向算法 + PyInstaller 打包 | 已完成 | 2026-06-20 | 2026-06-20 | 方向选择(正/负/双向), 翻号+优化两阶段, 4新测试, 70 total
| 14a | Bug 修复 + 中文化 + 方向 UI 修正 | 已完成 | 2026-06-20 | 2026-06-20 | 变量候选为空修复, 方向UI改为勾选框, QComboBox宽度, Y/X并排, 全应用中文化(7个UI文件) page_progress.py (ComputationWorker+QThread), page_results.py (Plotly/QWebEngineView+导出), export.py (order列+light DTA+merge cmd), 3 个 export 测试, 70 total |

---

## 核心接口签名区

> **状态: 待填充** — Phase 2 起逐步填充 core/ 模块的公共函数签名

| 模块 | 函数 | 签名 | 说明 | 最后更新 |
|------|------|------|------|---------|
| ols_model | fit_ols | (df, dv, kv, cv) -> dict | Baseline + diagnostics via statsmodels OLS | 2026-06-20 |
| logit_model | fit_logit | (df, dv, kv, cv, type) -> dict | Logit/Probit fit + one-step Newton diagnostics | 2026-06-20 |
| logit_model | run_logit_greedy | (df, dv, kv, cv, thresh, max_pct, type, exact) -> dict | Logit/Probit greedy deletion | 2026-06-20 |
| fe_model | fit_fe | (df, dv, kv, cv, fe_vars) -> dict | FWL demean + OLS diagnostics | 2026-06-20 |
| fe_model | run_fe_greedy | (df, dv, kv, cv, fe_vars, thresh, max_pct) -> dict | FE greedy deletion | 2026-06-20 |
| iv_model | fit_iv | (df, dv, kv, cv, endog, instr) -> dict | CFA dual-stage fit | 2026-06-20 |
| iv_model | run_iv_greedy | (df, dv, kv, cv, endog, instr, thresh, max_pct) -> dict | IV greedy deletion | 2026-06-20 |
| influence | compute_deletion_t_values | (params_not_obsi, sigma2, XtX_inv_diag, idx) -> ndarray | Post-deletion t-values (OLS) | 2026-06-20 |
| greedy_search | greedy_deletion | (df, dv, kv, cv, thresh, max_pct, direction) -> dict | OLS single-model greedy loop | 2026-06-21 |
| pipeline | run_pipeline | (compute_input) -> compute_output | Orchestrator, routes to model-specific functions | 2026-06-20 |
| multi_model | arbitrate | (results, configs, df) -> dict | Safe intersection + conflict matrix + weighted greedy | 2026-06-20 |
| export | export_csv/export_dta/export_excel/export_html | (df, deleted_obs, model_name, ...) -> bytes | 4-format export | 2026-06-20 |
| viewmodel | SigAdjustViewModel | Signal: data_loaded/calculation_finished, Property: df/columns_info/config/results | UI state management | 2026-06-21 |
| variable_selector | VariableSelector | set_items/select_selection/set_max_selection -> list[str] | Tag-based search+select widget | 2026-06-21 |

---

## 业务逻辑核心规则区

> 以下规则提取自 `references/显著性调整工具-技术交接文档.md`，标注来源节号。

### 诊断方式（§4）

- 排序目标为 t⁽ⁱ⁾ = β⁽ⁱ⁾ / se⁽ⁱ⁾，而非单独的 b⁽ⁱ⁾（修正 Stata 版缺陷）
- OLS: DFBETA 精确解析解，O(K²N) 复杂度，基于 `statsmodels.OLSInfluence`
- Logit/Probit: 一步牛顿近似，可切换 exact=True 进行完整 MLE 重拟合
- FE: FWL 去均值退化到 OLS，忽略二阶组均值效应
- 2SLS: CFA 分解为双 OLS，天然双模型联动

### 删除算法（§5）

- 贪心迭代: `while (p > threshold) and (deleted < max)` → 删最优观测值 → 重跑回归 → 重算影响力
- 不保证全局最优子集（组合优化固有困难）
- 多模型适应度函数: `score(S) = Σ w_m × max(0, t_m(S) - t_m_threshold)`
- 分层松弛搜索: 严格模式无解时，从低优先级模型开始逐步放宽阈值

### 多模型仲裁（§6）

- 安全交集 = A₁ ∩ A₂ ∩ ... ∩ A_M（对所有模型都有利的删除集）
- 冲突系数 = 1 − |安全交集| / |并集|
- 冲突矩阵: 逐观测值影响方向（+有利/−有害）+ 影响幅度
- 建议逻辑: 全同向推荐 / 部分有害警告 / 严重不可逆阻止 / 无交集建议拆分

### 方向算法（§3.5）
- 两步式：翻号阶段（β符号不一致时优先删除使β朝目标方向移动的观测）→ 优化阶段（符号一致后只保留使t值朝目标方向改善的候选）
- direction="both" = 不区分方向，等价于V1原有行为

### 标识符变量（§9.1）

- 单模型: `drop_{model_name}` (0/1)
- 多模型: `drop_{model_name_N}` (0/1) + `drop_all_safe` (0/1)
- 命名规则: `drop_` + 用户输入名（特殊字符替换为下划线）

### 方法边界（§11.2）

- 贪心算法非全局最优
- 删除可能改变样本代表性
- 工具只执行计算，不背书科学结论
- 多模型上限 4 个
- 模型类型限于: OLS / Logit / Probit / FE / 2SLS（不含系统 GMM、空间计量等）

---

## 最近变更摘要区

| 日期 | 变更人 | Phase | 变更内容 |
|------|--------|-------|---------|
| 2026-06-20 | Codex | 14a | Phase 14a: Bug 修复 + 中文化 + 方向 UI 修正 (变量候选空修复, 方向UI复选框, QComboBox宽度, Y/X并排布局, 全应用中文化7文件)
| 2026-06-20 | Codex | 13 | Phase 13: 方向算法 + PyInstaller 打包 (_apply_direction_filter, 翻号+优化两阶段, 4新测试, 70 total, sigadjust.spec)
| 2026-06-20 | Codex | 11 | Phase 11: Stata 快速导入 + 因子变量 (StataCommandParser 纯逻辑解析器, StataImportDialog 解析/预览/因子展开/自动填充, 7 个纯逻辑测试, 61 total)
| 2026-06-20 | Codex | 10 | Phase 10: 模型配置页 (ModelCard + SetupPage, 多模型表单, XY冲突/Control排除, 配置JSON持久化, Stata导入占位)
| 2026-06-20 | Codex | 9 | Phase 9: PySide6 骨架 + 数据导入页 (main.py, ViewModel, MainWindow, DataPage, VariableSelector, 4 ViewModel tests, 54 total)
| 2026-06-20 | Codex | 4-5 | Phase 4: Logit/Probit + Phase 5: FE (9 new tests, 33 total, model type selector) Logit/Probit 支持 (6 tests, dfbetas standardized formula confirmed)
| 2026-06-20 | Codex | 1-3 | Batch 1: 前置清理 + 数据导入页面 + OLS 核心计算 + 全流程 UI (24 tests) |
| 2026-06-18 | Qoder | 0 | 项目初始化: 创建任务追踪器、目录骨架、依赖清单 |
| 2026-06-20 | Codex | 1-3 | Batch 1: 前置清理 + 数据导入页面 + OLS 核心计算 + 全流程 UI (24 tests) |
| 2026-06-18 | Qoder | 0 | Phase 0 完成: 12 个文件、pytest 验证通过、Git 仓库初始化、references/ 加入 .gitignore |
