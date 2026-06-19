"""Page 3: Computation progress — background pipeline + live progress."""

import threading
import time
import streamlit as st
from core.pipeline import run_pipeline
from ui.pages import page_results


def page_progress():
    """Computation progress page. Runs pipeline in background thread."""
    st.title("计算进度")

    if "config" not in st.session_state or st.session_state.config is None:
        st.warning("请先在 **模型设定** 页面配置分析参数。")
        return

    # ── Already completed → redirect
    if st.session_state.get("results"):
        st.switch_page(page_results)
        return

    # ── Progress placeholders
    progress_bar = st.progress(0, "准备中...")
    status_text = st.empty()

    # ── Compute function (runs in thread)
    def _compute():
        try:
            config = st.session_state.config
            st.session_state.progress = {
                "current": 0,
                "total": 1,
                "status_msg": "正在执行基线回归...",
            }
            result = run_pipeline(config)
            st.session_state.progress = {
                "current": 1,
                "total": 1,
                "status_msg": "分析完成！",
            }
            st.session_state.results = result
        except Exception as e:
            st.session_state.progress = {
                "current": 0,
                "total": 1,
                "status_msg": f"计算失败: {e}",
            }

    # ── Start thread if not already running
    if not st.session_state.get("_compute_started"):
        st.session_state._compute_started = True
        st.session_state.progress = {
            "current": 0,
            "total": 1,
            "status_msg": "准备计算...",
        }
        thread = threading.Thread(target=_compute, daemon=True)
        thread.start()
        st.session_state._compute_thread = thread

    # ── Poll progress
    prog = st.session_state.get("progress", {})
    current = prog.get("current", 0)
    total = prog.get("total", 1)
    msg = prog.get("status_msg", "计算中...")

    if total > 0:
        progress_bar.progress(min(current / total, 1.0), msg)
    status_text.info(msg)

    # ── Check completion
    if st.session_state.get("results"):
        time.sleep(0.3)  # Brief pause for UX
        st.switch_page(page_results)
    elif current >= total and not st.session_state.get("results"):
        st.error("计算似乎未产生结果，请返回模型设定页面重试。")
    else:
        time.sleep(0.5)
        st.rerun()
