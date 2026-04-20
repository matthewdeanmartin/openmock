import sys
import json
from unittest.mock import MagicMock, patch
import pytest
from openmock.web import website, main, _get_response_error
from openmock.fake_server import FakeOpenSearchServer


def test_get_response_error():
    assert (
        _get_response_error({"status_code": 404, "error": "Not Found"}) == "Not Found"
    )
    assert _get_response_error({"status_code": 200}) is None
    assert _get_response_error({}) is None


@patch("streamlit.web.bootstrap.run")
def test_main_success(mock_bootstrap_run):
    assert main(["arg1"]) == 0
    mock_bootstrap_run.assert_called_once()


def test_main_missing_streamlit():
    with patch.dict(sys.modules, {"streamlit.web": None}):
        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert "Install the web extra" in str(excinfo.value)


@patch("streamlit.set_page_config")
@patch("streamlit.title")
@patch("streamlit.sidebar")
@patch("streamlit.tabs")
@patch("streamlit.session_state", spec=dict)
@patch("streamlit.toggle")
@patch("streamlit.button")
@patch("streamlit.text_input")
@patch("streamlit.text_area")
@patch("streamlit.form")
@patch("streamlit.selectbox")
@patch("streamlit.radio")
@patch("streamlit.rerun")
@patch("streamlit.success")
@patch("streamlit.error")
@patch("streamlit.info")
@patch("streamlit.json")
@patch("streamlit.code")
@patch("streamlit.expander")
@patch("streamlit.divider")
@patch("streamlit.header")
@patch("streamlit.subheader")
@patch("streamlit.caption")
@patch("streamlit.write")
@patch("streamlit.form_submit_button")
def test_website_mocked(
    mock_submit,
    mock_write,
    mock_caption,
    mock_subheader,
    mock_header,
    mock_divider,
    mock_expander,
    mock_code,
    mock_json,
    mock_info,
    mock_error,
    mock_success,
    mock_rerun,
    mock_radio,
    mock_selectbox,
    mock_form,
    mock_text_area,
    mock_text_input,
    mock_button,
    mock_toggle,
    mock_session_state,
    mock_tabs,
    mock_sidebar,
    mock_title,
    mock_set_page_config,
):
    mock_tabs.side_effect = lambda labels: [MagicMock() for _ in labels]
    mock_session_state.__contains__.return_value = False

    server = FakeOpenSearchServer()
    server.put_user("test-user", {})
    server.index_document("idx", {"f": "v"})

    def get_item(key):
        if key == "server":
            return server
        raise KeyError(key)

    mock_session_state.__getitem__.side_effect = get_item

    # 1. No interaction, but with some data
    mock_button.return_value = False
    mock_submit.return_value = False
    mock_text_input.return_value = "*"
    mock_text_area.return_value = '{"foo": "bar"}'
    website()

    # 2. Click Search (should work)
    mock_button.side_effect = lambda label, **kwargs: label == "Execute Search"
    website()

    # 3. Success case for Index (not in a form? wait, st.form is used)
    # Form submit button
    mock_button.side_effect = None
    mock_button.return_value = False
    mock_submit.side_effect = lambda label, **kwargs: label == "Index Document"
    website()

    # 4. Success case for Put User
    mock_submit.side_effect = lambda label, **kwargs: label == "Create / Update User"
    website()

    # 5. Success case for Put Role
    mock_submit.side_effect = lambda label, **kwargs: label == "Create / Update Role"
    website()

    # 6. Success case for Put Pipeline
    mock_submit.side_effect = (
        lambda label, **kwargs: label == "Create / Update Pipeline"
    )
    website()

    # 7. Success case for Simulate
    mock_submit.side_effect = lambda label, **kwargs: label == "Simulate Pipeline"
    website()
