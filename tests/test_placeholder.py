def test_import():
    """验证环境依赖可正常导入。"""
    import streamlit
    assert streamlit is not None
