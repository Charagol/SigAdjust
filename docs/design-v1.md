# 显著性调整工具 — 设计蓝图 V1.0

> **版本**: V1.0-alpha
> **日期**: 2026-06-18
> **状态**: 进行中（当前活跃版本）

---

## 1. 版本目标与动机

本版本将现有手工 Stata do-file 工作流改造为一键式 Web 应用，消除重复的手工宏编辑和变量清理操作，并实现显著的性能提升和交互式可视化决策支持。

**核心目标**:
- 替代 `rangestat显著性调整代码.do` 手工流程 → 一站式 Web 应用
- DFBETA 解析解替代 brute-force LOO（N 次回归），性能提升 100×+
- 支持 2–4 个模型同时分析，提供冲突感知的删除建议
- 交互式可视化: t 值曲线、设定曲线、冲突热力图、维恩图

---

## 2. 功能清单

### 数据导入 (Phase 1)
- CSV / DTA / Excel 文件上传
- 自动识别列名和类型
- 缺失值统计展示

### 模型设定 (Phase 2-3)
- 多模型配置界面（OLS / Logit / Probit / FE / 2SLS）
- 控制变量组合枚举（`itertools.combinations`）
- 2SLS 工具变量选择器
- FE 固定效应变量选择器

### 计算引擎 (Phase 2-6)
- 贪心迭代删除: 每步重拟合 + 重算影响力
- DFBETA 解析诊断（单次 O(K²N) 而非 N·O(K³)）
- 多模型加权贪心联合优化
- 分层松弛搜索（严格模式无解时逐步放宽）

### 结果展示 (Phase 3)
- t 值变化曲线（按模型逐行）
- 删除路径详情表
- 设定曲线（不同控制变量组合的 t 值路径）

### 多模型联动 (Phase 6)
- 安全交集: 对所有模型都有利的删除集
- 冲突热力图（模型 × 观测值影响方向）
- 维恩图（各模型有害集重叠关系）
- 目标达成状态矩阵

### 导出 (Phase 8)
- CSV / DTA / Excel / HTML 报告
- 附带标识符变量（`drop_*` 0/1 标记列）

---

## 3. 技术决策

| 决策 | 选定方案 | 理由 |
|------|---------|------|
| 语言与框架 | Python + Streamlit（全栈，无前后端分离） | 快速原型、一键部署、数据科学生态 |
| 图表库 | Plotly | Streamlit 原生 `st.plotly_chart()` 支持 |
| 目录架构 | `core/`（纯计算）+ `ui/`（Streamlit 页面），严格分离 | core 无 UI 依赖可独立测试和复用 |
| 状态管理 | `st.session_state`，无数据库/Redis | 应用轻量、单机部署 |
| 诊断方式 | DFBETA 解析公式优先（`statsmodels.OLSInfluence`） | 性能关键: O(K²N) vs Stata 的 N·O(K³) |
| 删除策略 | 贪心迭代（非批量） | 每步重拟合确保诊断精度 |
| 排序目标 | t⁽ⁱ⁾ = β⁽ⁱ⁾ / se⁽ⁱ⁾（非仅 β⁽ⁱ⁾） | 修正 Stata 版缺陷 |
| 多模型上限 | 4 个 | 复杂度可控，UI 布局不超载 |
| 2SLS 策略 | CFA 分解为双 OLS | 天然双模型处理，F 统计量 + t 统计量联动 |
| FE 策略 | pyfixest feols + FWL 去均值退化 | 近似但有理论基础 |
| Logit/Probit | 一步牛顿近似（可切换 exact MLE） | 默认快速，必要时精确 |
| 部署方式 | `streamlit run app.py` 一键启动 | 零额外依赖 |

---

## 4. 数据模型

### 4.1 st.session_state 键名约定

| 键名 | 类型 | 写入页面 | 读取页面 | 说明 |
|------|------|---------|---------|------|
| `df` | `pd.DataFrame` | 数据导入 | 模型设定, 结果展示 | 原始上传数据 |
| `columns_info` | `dict` | 数据导入 | 模型设定 | 列名、类型、缺失率 |
| `config` | `dict` | 模型设定 | 计算进度 | 符合 compute_input 契约 |
| `results` | `dict` | 计算进度 | 结果展示 | 符合 compute_output 契约 |
| `export_df` | `pd.DataFrame` | 结果展示 | 结果展示（下载按钮） | 原始数据 + 标识符变量 |
| `progress` | `dict` | 计算进度 | 计算进度 | `{total, current, status_msg}` |

### 4.2 compute_input 契约

```python
compute_input = {
    "df": pd.DataFrame,
    "global_settings": {
        "significance_threshold": 0.05,
        "max_deletions_pct": 5.0,
        "mode": "greedy"             # "greedy" | "batch"
    },
    "models": [
        {
            "name": "主回归",
            "type": "ols",           # "ols" | "logit" | "probit" | "fe" | "iv"
            "priority": 5,           # 1-5, 较大 = 更高优先级
            "target_p": 0.01,
            "dependent_var": "y",
            "key_var": "x",
            "control_vars": ["c1", "c2", "c3"],
            # type=="iv" 时:
            "endogenous_var": "x",
            "instruments": ["z1", "z2"],
            # type=="fe" 时:
            "fe_vars": ["firm_id", "year"]
        }
    ]
}
```

### 4.3 compute_output 契约

```python
compute_output = {
    "models": {
        "<model_name>": {
            "baseline": {
                "beta": 0.342, "se": 0.224, "t_stat": 1.527,
                "p_value": 0.127, "r_squared": 0.213,
                "n_obs": 4000, "df": 3994
            },
            "deletion_path": [
                {"step": 1, "obs_id": 42, "t_after": 1.68, "p_after": 0.093},
                {"step": 2, "obs_id": 87, "t_after": 1.94, "p_after": 0.052}
            ],
            "final": {
                "beta": 0.411, "se": 0.156, "t_stat": 2.634,
                "p_value": 0.009, "r_squared": 0.287,
                "deleted_obs": [42, 87, 103, 56, 201],
                "n_deleted": 5
            },
            "spec_curves": [
                {
                    "control_set": "c1 c2 c3",
                    "path": [
                        {"n_del": 0, "t": 1.527},
                        {"n_del": 1, "t": 1.682}
                    ]
                }
            ]
        }
    },
    "multi_model": {
        "conflict_coefficient": 0.23,
        "safe_intersection": [42, 87],
        "conflict_matrix": [
            {
                "obs_id": 103,
                "effects": {"主回归": 0.18, "稳健性": -0.12},
                "recommendation": "caution",
                "note": "对稳健性检验有害 (-0.12)"
            }
        ],
        "status_by_model": {
            "主回归": {"target": "p<0.01", "achieved": "p=0.009", "status": "passed"}
        }
    }
}
```

---

## 5. 向后兼容性

**无** — 首个版本，无需兼容旧版。
