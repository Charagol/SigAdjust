"""
显著性调整工具 (Significance Adjustment Tool)
==============================================
一键式回归诊断与样本优化 Web 应用。

通过迭代删除对统计显著性影响最大的观测值，帮助研究者
优化回归模型中关键变量的显著性水平。

技术栈: Python + Streamlit + statsmodels + pandas + plotly
架构: core/（纯计算，无 UI 依赖）+ ui/（Streamlit 页面，调用 core）

工作流:
  1. 数据导入 — 上传 CSV/DTA/Excel 文件
  2. 模型设定 — 配置回归模型（OLS/Logit/Probit/FE/2SLS）
  3. 计算进度 — 贪心迭代删除 + 实时进度
  4. 结果展示 — t 值曲线、删除路径、多模型冲突分析
"""

import streamlit as st


# ── 占位页面函数 ──────────────────────────────────────────
# Phase 1-3 将替换为 ui/ 模块中的实际页面函数


def page_data():
    """数据导入页面 — Phase 1 实现。"""
    st.title("数据导入")
    st.info("📂 Phase 1 将实现: 文件上传、数据预览、缺失值统计")


def page_setup():
    """模型设定页面 — Phase 2-3 实现。"""
    st.title("模型设定")
    st.info("⚙️ Phase 2-3 将实现: 多模型配置、控制变量枚举、显著性阈值设定")


def page_progress():
    """计算进度页面 — Phase 3 实现。"""
    st.title("计算进度")
    st.info("🔄 Phase 3 将实现: 贪心迭代删除、实时进度条、后台线程计算")


def page_results():
    """结果展示页面 — Phase 3 实现。"""
    st.title("结果展示")
    st.info("📊 Phase 3 将实现: t 值曲线、删除路径、设定曲线、多模型冲突分析")


# ── 页面配置 ──────────────────────────────────────────────

st.set_page_config(
    page_title="显著性调整工具",
    page_icon="📊",
    layout="wide",
)

st.title("显著性调整工具")

# ── 导航结构 ──────────────────────────────────────────────

pages = [
    st.Page(page_data, title="数据导入", icon=":material/upload:"),
    st.Page(page_setup, title="模型设定", icon=":material/settings:"),
    st.Page(page_progress, title="计算进度", icon=":material/progress_activity:"),
    st.Page(page_results, title="结果展示", icon=":material/assessment:"),
]

pg = st.navigation(pages)

# ── 侧边栏 ────────────────────────────────────────────────

st.sidebar.title("SigAdjust")
st.sidebar.caption("v1.0.0-alpha")
st.sidebar.divider()
st.sidebar.info("一键式回归诊断与样本优化")

# ── 运行导航 ──────────────────────────────────────────────

pg.run()
