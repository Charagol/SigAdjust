# SigAdjust — Agent 项目手册

## 项目概况

显著性调整工具 — 一键式回归诊断与样本优化 PySide6 桌面应用。 V2.0 已完成 (70 测试通过, 2026-06-21)。
技术栈: Python + PySide6 + statsmodels + pandas + plotly。
每个 Phase 完成后都必须更新 `docs/task-tracker.md`。

## 核心架构约束

1. **core/ 禁止 import streamlit**。core 是纯计算模块，函数接收和返回 dict/DataFrame，不依赖任何 UI 框架。
2. **ui/ 通过 ViewModel 共享数据** (SigAdjustViewModel 单例 + Qt Signal/Slot)，状态属性: `df` → `columns_info` → `config` → `results` 。
3. **compute_input / compute_output 数据契约**见 `docs/design-v1.md` 第 4.2-4.3 节。这是硬接口，必须严格遵守。
4. **测试驱动**: 先写测试再写实现。每个 core 模块配独立测试文件。
5. **最小化改动**: 不修改与本 Phase 无关的文件。

## Git 提交规范

- **格式**: `<type>: <中文简述>`（如 `feat: OLS 贪心迭代删除核心算法`、`test: 新增 influence 模块测试`、`docs: 更新 task-tracker Phase 2 状态`）
- **每个 Phase 独立提交**。不在多个 Phase 完成后批量提交。一个 Phase 的前后端紧密关联改动合并为一次提交。
- **前置清理单独提交**（如重命名目录、删除残留文件）。
- **task-tracker 更新随 Phase 代码一起提交**，不单独拆出来。
- **提交前清理锁**: 若 git 操作报 `index.lock` 存在或 `Permission denied`，先执行 `rm -f .git/index.lock` 再重试。不要跳过提交。
- **提交前确认** `pytest tests/ -v` 全部通过。

## 文档更新规则

- 每个 Phase 完成后更新 `docs/task-tracker.md`:
  - Phase 清单中该 Phase 状态改为"已完成"，填写完成日期
  - 最近变更摘要区新增一条记录
  - 版本信息区的状态随批次推进更新
- **不要修改 `docs/design-v1.md`**（它是版本蓝图，只在版本结束时封存）
- `.codex/plans/` 存放临时规划文件，大版本结束时全部删除

## 已知陷阱

- `statsmodels.OLSInfluence.params_not_obsi` 返回形状 (N, K)，需按 `key_var_index` 提取对应列
- 删除后 t 值公式: `t⁽ⁱ⁾ = β⁽ⁱ⁾ / sqrt(σ²_{(i)} × [(X'X)⁻¹]_{jj})`，排序目标必须是 t 值而非 β
- PySide6 中不要在非主线程中直接操作 UI 组件，应使用 QThread + Signal/Slot 解决
- `git reset --soft` 后取消的提交尚可通过 `git reflog` 恢复
- .git 目录只读时需提权（`require_escalated`）执行 git 操作
- Windows 终端下不要在 docstring 中直接用 Unicode 上标/下标字符（会乱码），用 ASCII 替代或 TeX 写法

## 止损规则

- 连续 2 次修复不通过测试 → `git restore` 回退 → 停止编码 → 向用户汇报失败原因 → 重新规划方案
- 宁可回退重来，不接受补丁式修复
