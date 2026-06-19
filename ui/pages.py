"""Shared page function references to avoid circular imports.

Import from here in any module that needs st.switch_page(page_fn).
"""
from ui.page_data import page_data
from ui.page_setup import page_setup
from ui.page_progress import page_progress
from ui.page_results import page_results

__all__ = ["page_data", "page_setup", "page_progress", "page_results"]
