from unittest.mock import MagicMock, patch

from openmock.gui import OpenmockApp, main


@patch("tkinter.messagebox.showinfo")
@patch("tkinter.messagebox.showerror")
@patch("tkinter.Tk")
@patch("tkinter.BooleanVar")
@patch("tkinter.StringVar")
@patch("tkinter.ttk.Notebook")
@patch("tkinter.ttk.Frame")
@patch("tkinter.ttk.Label")
@patch("tkinter.ttk.Button")
@patch("tkinter.ttk.Entry")
@patch("tkinter.ttk.Separator")
@patch("tkinter.ttk.Combobox")
@patch("tkinter.ttk.Treeview")
@patch("tkinter.scrolledtext.ScrolledText")
def test_gui_app_init(
    mock_st,
    mock_tv,
    mock_cb,
    mock_sep,
    mock_entry,
    mock_btn,
    mock_lbl,
    mock_frame,
    mock_nb,
    mock_sv,
    mock_bv,
    mock_tk,
    mock_showerror,
    mock_showinfo,
):
    # Setup mock returns to avoid errors during widget creation
    mock_tk.return_value
    mock_nb_inst = mock_nb.return_value
    mock_nb_inst.index.return_value = 0
    mock_nb_inst.select.return_value = "tab0"

    app = OpenmockApp()
    assert app._server_ref is not None
    mock_tk.assert_called_once()

    # Test all tabs refresh
    for tab in app._tabs:
        tab.refresh()

    # Test index doc in _IndicesTab
    indices_tab = app._tabs[0]
    indices_tab._idx.insert(0, "test-index")
    indices_tab._doc_body.insert("1.0", '{"a": 1}')
    indices_tab._index_doc()
    # Error case (invalid json)
    indices_tab._doc_body.delete("1.0", "end")
    indices_tab._doc_body.insert("1.0", "invalid json")
    indices_tab._index_doc()

    # Test search in _SearchTab
    search_tab = app._tabs[1]
    search_tab._search()

    # Test cluster status
    cluster_tab = app._tabs[2]
    cluster_tab.refresh()

    # Test cat
    cat_tab = app._tabs[3]
    cat_tab._run()

    # Test security
    sec_tab = app._tabs[4]
    sec_tab._upsert_user()
    sec_tab._delete_user()
    sec_tab._upsert_role()
    sec_tab._delete_role()

    # Test ingest
    ingest_tab = app._tabs[5]
    ingest_tab._pid.insert(0, "p1")
    ingest_tab._pipeline_body.insert("1.0", '{"processors": []}')
    ingest_tab._upsert_pipeline()
    ingest_tab._sim_body.insert("1.0", '{"docs": []}')
    ingest_tab._simulate()
    ingest_tab._delete_pipeline()

    # Test tab change
    event = MagicMock()
    event.widget = mock_nb_inst
    app._on_tab_change(event)

    # Test reset
    app._reset()


@patch("openmock.gui.OpenmockApp")
def test_main(mock_app_class):
    mock_app = mock_app_class.return_value
    assert main() == 0
    mock_app.run.assert_called_once()
