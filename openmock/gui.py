"""Tkinter GUI for Openmock — a dependency-free alternative to the Streamlit web UI."""

# pylint: disable=too-many-ancestors

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from openmock.behaviour.server_failure import server_failure
from openmock.fake_server import FakeOpenSearchServer


def _fmt(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


class _Tab(ttk.Frame):
    def __init__(
        self, parent: ttk.Notebook, server_ref: list[FakeOpenSearchServer]
    ) -> None:
        super().__init__(parent)
        self._srv = server_ref
        self._build()

    @property
    def server(self) -> FakeOpenSearchServer:
        return self._srv[0]

    def _build(self) -> None:
        pass

    def refresh(self) -> None:
        pass


class _IndicesTab(_Tab):
    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(top, text="Indices", font=("", 12, "bold")).pack(anchor="w")
        self._tree_frame = ttk.Frame(top)
        self._tree_frame.pack(fill="both", expand=True, pady=(4, 0))

        sep = ttk.Separator(top)
        sep.pack(fill="x", pady=8)

        ttk.Label(top, text="Index Document", font=("", 10, "bold")).pack(anchor="w")

        form = ttk.Frame(top)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Index Name").grid(row=0, column=0, sticky="w", pady=2)
        self._idx = ttk.Entry(form)
        self._idx.insert(0, "test-index")
        self._idx.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(form, text="Document ID").grid(row=1, column=0, sticky="w", pady=2)
        self._doc_id = ttk.Entry(form)
        self._doc_id.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(form, text="Pipeline").grid(row=2, column=0, sticky="w", pady=2)
        self._pipeline_var = tk.StringVar(value="(none)")
        self._pipeline_cb = ttk.Combobox(
            form, textvariable=self._pipeline_var, state="readonly"
        )
        self._pipeline_cb.grid(row=2, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(form, text="Document JSON").grid(row=3, column=0, sticky="nw", pady=2)
        self._doc_body = scrolledtext.ScrolledText(form, height=5, width=60)
        self._doc_body.insert("1.0", '{"foo": "bar", "count": 1}')
        self._doc_body.grid(row=3, column=1, sticky="ew", padx=(4, 0))

        self._status = ttk.Label(top, text="", foreground="green")
        self._status.pack(anchor="w")

        ttk.Button(top, text="Index Document", command=self._index_doc).pack(
            anchor="w", pady=4
        )

    def _index_doc(self) -> None:
        idx = self._idx.get().strip()
        doc_id = self._doc_id.get().strip() or None
        pipeline = self._pipeline_var.get()
        pipeline = None if pipeline == "(none)" else pipeline
        try:
            body = json.loads(self._doc_body.get("1.0", "end"))
            res = self.server.index_document(
                index=idx, body=body, document_id=doc_id, pipeline=pipeline
            )
            if isinstance(res, dict) and res.get("status_code", 200) >= 400:
                self._status.config(text=f"Error: {res.get('error')}", foreground="red")
            else:
                self._status.config(
                    text=f"Indexed: {res.get('_id')}", foreground="green"
                )
                self.refresh()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._status.config(text=f"Error: {exc}", foreground="red")

    def refresh(self) -> None:
        for w in self._tree_frame.winfo_children():
            w.destroy()
        docs_dict = self.server.es._FakeIndicesClient__documents_dict
        if not docs_dict:
            ttk.Label(self._tree_frame, text="No indices yet.").pack(anchor="w")
            return
        tree = ttk.Treeview(
            self._tree_frame, columns=("index", "count"), show="headings", height=8
        )
        tree.heading("index", text="Index")
        tree.heading("count", text="Docs")
        tree.column("count", width=60, anchor="center")
        for name, docs in sorted(docs_dict.items()):
            tree.insert("", "end", values=(name, len(docs)))
        sb = ttk.Scrollbar(self._tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        pipelines = ["(none)", *sorted(self.server._pipelines.keys())]
        self._pipeline_cb["values"] = pipelines
        if self._pipeline_var.get() not in pipelines:
            self._pipeline_var.set("(none)")


class _SearchTab(_Tab):
    def _build(self) -> None:
        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=6, pady=6)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="Search Sandbox", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(f, text="Index (* for all)").grid(row=1, column=0, sticky="w", pady=2)
        self._index = ttk.Entry(f)
        self._index.insert(0, "*")
        self._index.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(f, text="Query JSON").grid(row=2, column=0, sticky="nw", pady=2)
        self._query = scrolledtext.ScrolledText(f, height=7, width=60)
        self._query.insert("1.0", '{"query": {"match_all": {}}}')
        self._query.grid(row=2, column=1, sticky="ew", padx=(4, 0))

        ttk.Button(f, text="Execute Search", command=self._search).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=4
        )

        ttk.Label(f, text="Response").grid(row=4, column=0, columnspan=2, sticky="w")
        self._result = scrolledtext.ScrolledText(f, height=15, state="disabled")
        self._result.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(0, 4))
        f.rowconfigure(5, weight=1)

    def _search(self) -> None:
        idx_raw = self._index.get().strip()
        index = None if idx_raw in {"", "*"} else idx_raw
        try:
            body = json.loads(self._query.get("1.0", "end"))
            res = self.server.search_documents(index=index, body=body)
            self._show(_fmt(res))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._show(f"Error: {exc}")

    def _show(self, text: str) -> None:
        self._result.config(state="normal")
        self._result.delete("1.0", "end")
        self._result.insert("1.0", text)
        self._result.config(state="disabled")


class _ClusterTab(_Tab):
    def _build(self) -> None:
        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=6, pady=6)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        ttk.Label(f, text="Cluster Status", font=("", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(f, text="Refresh", command=self.refresh).grid(
            row=0, column=1, sticky="e"
        )

        self._text = scrolledtext.ScrolledText(f, state="disabled")
        self._text.grid(row=2, column=0, columnspan=2, sticky="nsew")

    def refresh(self) -> None:
        try:
            health = self.server.health()
            info = self.server.info()
            self._show(_fmt({"health": health, "info": info}))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._show(f"Error: {exc}")

    def _show(self, text: str) -> None:
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.config(state="disabled")


class _CatTab(_Tab):
    def _build(self) -> None:
        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=6, pady=6)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="CAT", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        ttk.Label(f, text="Endpoint").grid(row=1, column=0, sticky="w", pady=2)
        self._endpoint = ttk.Combobox(f, values=["indices", "count"], state="readonly")
        self._endpoint.set("indices")
        self._endpoint.grid(row=1, column=1, sticky="w", padx=(4, 0))

        ttk.Label(f, text="Format").grid(row=2, column=0, sticky="w", pady=2)
        self._fmt_var = tk.StringVar(value="text")
        ttk.Radiobutton(f, text="text", variable=self._fmt_var, value="text").grid(
            row=2, column=1, sticky="w"
        )
        ttk.Radiobutton(f, text="json", variable=self._fmt_var, value="json").grid(
            row=2, column=2, sticky="w"
        )

        ttk.Button(f, text="Run", command=self._run).grid(
            row=2, column=3, sticky="e", padx=4
        )

        self._text = scrolledtext.ScrolledText(f, state="disabled")
        self._text.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(4, 0))

    def _run(self) -> None:
        endpoint = self._endpoint.get()
        fmt = self._fmt_var.get()
        verbose = fmt == "text"
        try:
            if endpoint == "indices":
                payload = self.server.cat_indices(format_type=fmt, verbose=verbose)
            else:
                payload = self.server.cat_count(format_type=fmt, verbose=verbose)
            text = payload if isinstance(payload, str) else _fmt(payload)
            self._show(text or "(empty)")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._show(f"Error: {exc}")

    def _show(self, text: str) -> None:
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.config(state="disabled")


# pylint: disable=too-many-instance-attributes
class _SecurityTab(_Tab):
    def _build(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(outer, text="Security", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(
            outer, text="Permissive fake CRUD — no auth enforced.", foreground="gray"
        ).pack(anchor="w")

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True, pady=6)

        self._users_frame = ttk.Frame(nb)
        self._roles_frame = ttk.Frame(nb)
        nb.add(self._users_frame, text="Users")
        nb.add(self._roles_frame, text="Roles")

        self._build_users(self._users_frame)
        self._build_roles(self._roles_frame)

    def _build_users(self, parent: ttk.Frame) -> None:
        # pylint: disable=attribute-defined-outside-init
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="Current Users").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=2
        )
        self._users_text = scrolledtext.ScrolledText(parent, height=6, state="disabled")
        self._users_text.grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Separator(parent).grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(parent, text="Create / Update User", font=("", 10, "bold")).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(parent, text="Username").grid(row=4, column=0, sticky="w")
        self._uname = ttk.Entry(parent)
        self._uname.insert(0, "demo-user")
        self._uname.grid(row=4, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(parent, text="User JSON").grid(row=5, column=0, sticky="nw")
        self._user_body = scrolledtext.ScrolledText(parent, height=4)
        self._user_body.insert(
            "1.0",
            '{"password":"not-checked","backend_roles":["admin"],"attributes":{"team":"demo"}}',
        )
        self._user_body.grid(row=5, column=1, sticky="ew", padx=(4, 0))

        self._user_status = ttk.Label(parent, text="")
        self._user_status.grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Button(parent, text="Create / Update", command=self._upsert_user).grid(
            row=7, column=0, sticky="w", pady=2
        )

        ttk.Separator(parent).grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(parent, text="Delete Username").grid(row=9, column=0, sticky="w")
        self._del_uname = ttk.Entry(parent)
        self._del_uname.grid(row=9, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(parent, text="Delete User", command=self._delete_user).grid(
            row=10, column=0, sticky="w", pady=2
        )

    def _upsert_user(self) -> None:
        name = self._uname.get().strip()
        try:
            body = json.loads(self._user_body.get("1.0", "end"))
            res = self.server.put_user(name, body)
            self._user_status.config(text=res["message"], foreground="green")
            self.refresh()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._user_status.config(text=f"Error: {exc}", foreground="red")

    def _delete_user(self) -> None:
        name = self._del_uname.get().strip()
        res = self.server.delete_user(name)
        if res is None:
            messagebox.showerror("Not found", f"User '{name}' not found.")
        else:
            messagebox.showinfo("Deleted", res["message"])
            self.refresh()

    def _build_roles(self, parent: ttk.Frame) -> None:
        # pylint: disable=attribute-defined-outside-init
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="Current Roles").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=2
        )
        self._roles_text = scrolledtext.ScrolledText(parent, height=6, state="disabled")
        self._roles_text.grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Separator(parent).grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(parent, text="Create / Update Role", font=("", 10, "bold")).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(parent, text="Role Name").grid(row=4, column=0, sticky="w")
        self._rname = ttk.Entry(parent)
        self._rname.insert(0, "demo-role")
        self._rname.grid(row=4, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(parent, text="Role JSON").grid(row=5, column=0, sticky="nw")
        self._role_body = scrolledtext.ScrolledText(parent, height=4)
        self._role_body.insert(
            "1.0",
            '{"cluster_permissions":["cluster_all"],"index_permissions":[{"index_patterns":["*"],"allowed_actions":["read"]}]}',
        )
        self._role_body.grid(row=5, column=1, sticky="ew", padx=(4, 0))

        self._role_status = ttk.Label(parent, text="")
        self._role_status.grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Button(parent, text="Create / Update", command=self._upsert_role).grid(
            row=7, column=0, sticky="w", pady=2
        )

        ttk.Separator(parent).grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(parent, text="Delete Role").grid(row=9, column=0, sticky="w")
        self._del_rname = ttk.Entry(parent)
        self._del_rname.grid(row=9, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(parent, text="Delete Role", command=self._delete_role).grid(
            row=10, column=0, sticky="w", pady=2
        )

    def _upsert_role(self) -> None:
        name = self._rname.get().strip()
        try:
            body = json.loads(self._role_body.get("1.0", "end"))
            res = self.server.put_role(name, body)
            self._role_status.config(text=res["message"], foreground="green")
            self.refresh()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._role_status.config(text=f"Error: {exc}", foreground="red")

    def _delete_role(self) -> None:
        name = self._del_rname.get().strip()
        res = self.server.delete_role(name)
        if res is None:
            messagebox.showerror("Not found", f"Role '{name}' not found.")
        else:
            messagebox.showinfo("Deleted", res["message"])
            self.refresh()

    def refresh(self) -> None:
        self._users_text.config(state="normal")
        self._users_text.delete("1.0", "end")
        self._users_text.insert("1.0", _fmt(self.server._users))
        self._users_text.config(state="disabled")

        self._roles_text.config(state="normal")
        self._roles_text.delete("1.0", "end")
        self._roles_text.insert("1.0", _fmt(self.server._roles))
        self._roles_text.config(state="disabled")


class _IngestTab(_Tab):
    def _build(self) -> None:
        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=6, pady=6)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Ingest", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            f,
            text="Fake in-memory pipelines. Supported: set, rename, remove, append, lowercase, uppercase, trim, split, convert, gsub, json.",
            foreground="gray",
            wraplength=500,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w")

        ttk.Label(f, text="Current Pipelines").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        self._pipelines_text = scrolledtext.ScrolledText(f, height=5, state="disabled")
        self._pipelines_text.grid(row=3, column=0, columnspan=2, sticky="ew")

        ttk.Separator(f).grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(f, text="Create / Update Pipeline", font=("", 10, "bold")).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(f, text="Pipeline ID").grid(row=6, column=0, sticky="w")
        self._pid = ttk.Entry(f)
        self._pid.insert(0, "normalize-message")
        self._pid.grid(row=6, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(f, text="Pipeline JSON").grid(row=7, column=0, sticky="nw")
        self._pipeline_body = scrolledtext.ScrolledText(f, height=5)
        self._pipeline_body.insert(
            "1.0",
            '{"description":"Normalize message","processors":[{"trim":{"field":"message"}},{"lowercase":{"field":"message"}}]}',
        )
        self._pipeline_body.grid(row=7, column=1, sticky="ew", padx=(4, 0))

        self._pipe_status = ttk.Label(f, text="")
        self._pipe_status.grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Button(f, text="Create / Update", command=self._upsert_pipeline).grid(
            row=9, column=0, sticky="w", pady=2
        )

        ttk.Separator(f).grid(row=10, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(f, text="Simulate Pipeline", font=("", 10, "bold")).grid(
            row=11, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(f, text="Pipeline ID").grid(row=12, column=0, sticky="w")
        self._sim_pid_var = tk.StringVar()
        self._sim_pid_cb = ttk.Combobox(
            f, textvariable=self._sim_pid_var, state="readonly"
        )
        self._sim_pid_cb.grid(row=12, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(f, text="Simulation JSON").grid(row=13, column=0, sticky="nw")
        self._sim_body = scrolledtext.ScrolledText(f, height=4)
        self._sim_body.insert(
            "1.0", '{"docs":[{"_source":{"message":"  HELLO WORLD  ","count":"3"}}]}'
        )
        self._sim_body.grid(row=13, column=1, sticky="ew", padx=(4, 0))

        ttk.Button(f, text="Simulate", command=self._simulate).grid(
            row=14, column=0, sticky="w", pady=2
        )

        ttk.Label(f, text="Result").grid(row=15, column=0, columnspan=2, sticky="w")
        self._sim_result = scrolledtext.ScrolledText(f, height=5, state="disabled")
        self._sim_result.grid(row=16, column=0, columnspan=2, sticky="ew")

        ttk.Separator(f).grid(row=17, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(f, text="Delete Pipeline").grid(row=18, column=0, sticky="w")
        self._del_pid = ttk.Entry(f)
        self._del_pid.grid(row=18, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(f, text="Delete", command=self._delete_pipeline).grid(
            row=19, column=0, sticky="w", pady=2
        )

    def _upsert_pipeline(self) -> None:
        pid = self._pid.get().strip()
        try:
            body = json.loads(self._pipeline_body.get("1.0", "end"))
            res = self.server.put_pipeline(pid, body)
            self._pipe_status.config(text=res["message"], foreground="green")
            self.refresh()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._pipe_status.config(text=f"Error: {exc}", foreground="red")

    def _simulate(self) -> None:
        pid = self._sim_pid_var.get()
        try:
            body = json.loads(self._sim_body.get("1.0", "end"))
            res = self.server.simulate_pipeline(body=body, pipeline_id=pid)
            self._sim_result.config(state="normal")
            self._sim_result.delete("1.0", "end")
            self._sim_result.insert("1.0", _fmt(res))
            self._sim_result.config(state="disabled")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._sim_result.config(state="normal")
            self._sim_result.delete("1.0", "end")
            self._sim_result.insert("1.0", f"Error: {exc}")
            self._sim_result.config(state="disabled")

    def _delete_pipeline(self) -> None:
        pid = self._del_pid.get().strip()
        res = self.server.delete_pipeline(pid)
        if res is None:
            messagebox.showerror("Not found", f"Pipeline '{pid}' not found.")
        else:
            messagebox.showinfo("Deleted", res["message"])
            self.refresh()

    def refresh(self) -> None:
        self._pipelines_text.config(state="normal")
        self._pipelines_text.delete("1.0", "end")
        self._pipelines_text.insert("1.0", _fmt(self.server._pipelines))
        self._pipelines_text.config(state="disabled")

        pids = sorted(self.server._pipelines.keys())
        self._sim_pid_cb["values"] = pids
        if pids and self._sim_pid_var.get() not in pids:
            self._sim_pid_var.set(pids[0])


# pylint: disable=too-many-instance-attributes
class OpenmockApp:
    def __init__(self) -> None:
        self._server_ref: list[FakeOpenSearchServer] = [FakeOpenSearchServer()]

        self._root = tk.Tk()
        self._root.title("Openmock Management Console")
        self._root.geometry("860x680")

        self._build_sidebar()
        self._build_tabs()

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self._root, width=180)
        sidebar.pack(side="left", fill="y", padx=4, pady=4)
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="Behaviors", font=("", 11, "bold")).pack(
            anchor="w", pady=(4, 2)
        )

        self._failure_var = tk.BooleanVar(value=server_failure.is_enabled())
        ttk.Checkbutton(
            sidebar,
            text="Simulate Server Failure",
            variable=self._failure_var,
            command=self._toggle_failure,
        ).pack(anchor="w")

        ttk.Separator(sidebar).pack(fill="x", pady=8)
        ttk.Button(sidebar, text="Reset Openmock", command=self._reset).pack(anchor="w")

    def _toggle_failure(self) -> None:
        if self._failure_var.get():
            server_failure.enable()
        else:
            server_failure.disable()

    def _reset(self) -> None:
        self._server_ref[0] = FakeOpenSearchServer()
        for tab in self._tabs:
            tab.refresh()

    def _build_tabs(self) -> None:
        nb = ttk.Notebook(self._root)
        nb.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=4)

        tab_classes = [
            ("Indices", _IndicesTab),
            ("Search Sandbox", _SearchTab),
            ("Cluster Stats", _ClusterTab),
            ("CAT", _CatTab),
            ("Security", _SecurityTab),
            ("Ingest", _IngestTab),
        ]
        self._tabs: list[_Tab] = []
        for label, cls in tab_classes:
            tab = cls(nb, self._server_ref)
            nb.add(tab, text=label)
            self._tabs.append(tab)

        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event: tk.Event) -> None:
        nb: ttk.Notebook = event.widget
        idx = nb.index(nb.select())
        self._tabs[idx].refresh()

    def run(self) -> None:
        self._root.mainloop()


def main() -> int:
    app = OpenmockApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
