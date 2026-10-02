# -*- coding: utf-8 -*-
"""
SnapCmd - 命令片段速取器
把每天重复敲的长命令，压缩成 3 个字母。
"""
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

APP_NAME = "SnapCmd"
APP_VERSION = "1.0.0"

# ---------- 配置存储 ----------
def config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d

CONFIG_PATH = os.path.join(config_dir(), "commands.json")

DEFAULT_COMMANDS = [
    {
        "alias": "dcd",
        "description": "Docker Compose 启动开发环境",
        "command": "docker compose -f docker-compose.dev.yml up -d --build {{service}}",
        "tags": ["docker", "dev"],
    },
    {
        "alias": "dcl",
        "description": "Docker Compose 查看日志",
        "command": "docker compose -f docker-compose.dev.yml logs -f --tail=100 {{service}}",
        "tags": ["docker", "log"],
    },
    {
        "alias": "kpg",
        "description": "K8s 查看生产 Pod",
        "command": "kubectl get pods -n {{namespace:production}} -o wide",
        "tags": ["k8s"],
    },
    {
        "alias": "kde",
        "description": "K8s 描述 Pod 排查事件",
        "command": "kubectl describe pod {{pod}} -n {{namespace:default}}",
        "tags": ["k8s", "debug"],
    },
    {
        "alias": "glo",
        "description": "Git 图形化日志",
        "command": "git log --oneline --graph --all --decorate",
        "tags": ["git"],
    },
    {
        "alias": "gph",
        "description": "Git 推送当前分支",
        "command": "git push origin {{branch:HEAD}}",
        "tags": ["git"],
    },
    {
        "alias": "gdc",
        "description": "Git 切换并拉取分支",
        "command": "git checkout {{branch}} && git pull origin {{branch}}",
        "tags": ["git"],
    },
    {
        "alias": "nis",
        "description": "查看本机 IP 信息",
        "command": "ipconfig | findstr /R /C:\"IPv4\"",
        "tags": ["net"],
    },
    {
        "alias": "pcu",
        "description": "清理 pip 缓存",
        "command": "pip cache purge && pip install --upgrade pip",
        "tags": ["python"],
    },
    {
        "alias": "pru",
        "description": "Python 运行脚本",
        "command": "python {{script.py}}",
        "tags": ["python"],
    },
]


def load_commands():
    if not os.path.exists(CONFIG_PATH):
        save_commands(DEFAULT_COMMANDS)
        return list(DEFAULT_COMMANDS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as e:
        messagebox.showwarning("配置读取失败", f"{e}\n将使用内置示例。")
    return list(DEFAULT_COMMANDS)


def save_commands(cmds):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cmds, f, ensure_ascii=False, indent=2)


# ---------- 参数解析 ----------
# 支持 {{param}} 与 {{param:default value}}
PARAM_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

def parse_params(template):
    """返回 [(name, default), ...]，按出现顺序去重。"""
    seen = []
    out = []
    for m in PARAM_RE.finditer(template):
        raw = m.group(1).strip()
        if ":" in raw:
            name, default = raw.split(":", 1)
            name = name.strip()
            default = default.strip()
        else:
            name, default = raw, ""
        if name not in seen:
            seen.append(name)
            out.append((name, default))
    return out


def render_template(template, values):
    def repl(m):
        raw = m.group(1).strip()
        if ":" in raw:
            name = raw.split(":", 1)[0].strip()
        else:
            name = raw
        v = values.get(name, "")
        return v if v is not None else ""
    return PARAM_RE.sub(repl, template)


# ---------- 编辑对话框 ----------
class CommandDialog(tk.Toplevel):
    def __init__(self, master, cmd=None):
        super().__init__(master)
        self.title("编辑命令" if cmd else "新增命令")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="别名 (3字母):").grid(row=0, column=0, sticky="w", pady=4)
        self.alias_var = tk.StringVar(value=(cmd or {}).get("alias", ""))
        ttk.Entry(frame, textvariable=self.alias_var, width=20).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="描述:").grid(row=1, column=0, sticky="w", pady=4)
        self.desc_var = tk.StringVar(value=(cmd or {}).get("description", ""))
        ttk.Entry(frame, textvariable=self.desc_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="命令模板:").grid(row=2, column=0, sticky="nw", pady=4)
        self.cmd_text = tk.Text(frame, height=5, width=60, wrap="word")
        self.cmd_text.grid(row=2, column=1, sticky="nsew", pady=4)
        self.cmd_text.insert("1.0", (cmd or {}).get("command", ""))
        frame.rowconfigure(2, weight=1)

        ttk.Label(frame, text="标签 (逗号分隔):").grid(row=3, column=0, sticky="w", pady=4)
        tags = (cmd or {}).get("tags", [])
        self.tags_var = tk.StringVar(value=",".join(tags))
        ttk.Entry(frame, textvariable=self.tags_var).grid(row=3, column=1, sticky="ew", pady=4)

        hint = ttk.Label(frame, text="提示：用 {{参数名}} 或 {{参数名:默认值}} 标记需要交互式填充的位置。",
                         foreground="#666")
        hint.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        btns = ttk.Frame(frame)
        btns.grid(row=5, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btns, text="保存", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry("640x360")
        self.alias_var.trace_add("write", lambda *a: self.alias_var.set(self.alias_var.get().lower()))

    def on_save(self):
        alias = self.alias_var.get().strip().lower()
        desc = self.desc_var.get().strip()
        command = self.cmd_text.get("1.0", "end").rstrip()
        tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        if not alias or not command:
            messagebox.showwarning("缺字段", "别名和命令模板不能为空。", parent=self)
            return
        self.result = {"alias": alias, "description": desc, "command": command, "tags": tags}
        self.destroy()


# ---------- 主窗口 ----------
class SnapCmdApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}  -  命令片段速取器")
        self.geometry("1080x680")
        self.minsize(900, 560)

        self.commands = load_commands()
        self.param_entries = {}   # name -> tk.Variable
        self.selected_idx = None

        self._build_ui()
        self._refresh_list("")

        self.search_var.trace_add("write", lambda *a: self._refresh_list(self.search_var.get()))
        self.bind("<Control-n>", lambda e: self.on_add())
        self.bind("<F5>", lambda e: self._refresh_list(self.search_var.get()))
        self.bind("<Escape>", lambda e: self.search_var.set(""))
        self.search_entry.focus_set()

    # ---------- UI ----------
    def _build_ui(self):
        # 顶部搜索栏
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="🔍 搜索", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top, textvariable=self.search_var, font=("Consolas", 12))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(top, text="别名/描述/标签模糊匹配  ·  Ctrl+N 新增", foreground="#888").pack(side="right")

        # 主体：左右分栏
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # 左：列表
        left = ttk.Frame(paned)
        paned.add(left, weight=3)
        cols = ("alias", "desc", "tags")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("alias", text="别名")
        self.tree.heading("desc", text="描述")
        self.tree.heading("tags", text="标签")
        self.tree.column("alias", width=80, anchor="center")
        self.tree.column("desc", width=320)
        self.tree.column("tags", width=140)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.on_copy())

        # 右：详情 + 参数
        right = ttk.Frame(paned, padding=(10, 0, 0, 0))
        paned.add(right, weight=4)

        ttk.Label(right, text="命令模板", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tmpl_label = ttk.Label(right, text="(选择左侧命令)", foreground="#666", wraplength=520,
                                    font=("Consolas", 10))
        self.tmpl_label.pack(anchor="w", pady=(2, 8))

        ttk.Separator(right).pack(fill="x", pady=4)

        ttk.Label(right, text="参数填充", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        self.param_frame = ttk.Frame(right)
        self.param_frame.pack(fill="x")
        self.placeholder = ttk.Label(self.param_frame, text="该命令无参数。", foreground="#999")
        self.placeholder.pack(anchor="w", pady=6)

        ttk.Separator(right).pack(fill="x", pady=8)

        ttk.Label(right, text="最终命令", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.result_text = tk.Text(right, height=4, wrap="word", state="disabled",
                                    background="#f5f5f5", font=("Consolas", 10))
        self.result_text.pack(fill="both", expand=True, pady=(2, 8))

        # 底部按钮
        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="✨ 复制到剪贴板 (Enter)", command=self.on_copy).pack(side="left", padx=4)
        ttk.Button(bottom, text="▶ 在新终端执行 (Ctrl+Enter)", command=self.on_run).pack(side="left", padx=4)
        ttk.Button(bottom, text="✎ 编辑", command=self.on_edit).pack(side="left", padx=4)
        ttk.Button(bottom, text="＋ 新增", command=self.on_add).pack(side="left", padx=4)
        ttk.Button(bottom, text="🗑 删除", command=self.on_delete).pack(side="left", padx=4)
        ttk.Button(bottom, text="📂 打开配置文件", command=self.open_config).pack(side="right", padx=4)

        self.bind("<Control-Return>", lambda e: self.on_run())
        self.bind("<Return>", lambda e: self.on_copy())

        self.status = ttk.Label(self, text=f"共 {len(self.commands)} 条命令  ·  配置：{CONFIG_PATH}",
                                foreground="#888", padding=(10, 4))
        self.status.pack(fill="x", side="bottom")

    # ---------- 数据 ----------
    def _filtered(self, kw):
        kw = kw.strip().lower()
        if not kw:
            return list(range(len(self.commands)))
        out = []
        for i, c in enumerate(self.commands):
            hay = " ".join([
                c.get("alias", ""),
                c.get("description", ""),
                c.get("command", ""),
                " ".join(c.get("tags", [])),
            ]).lower()
            if kw in hay:
                out.append(i)
        return out

    def _refresh_list(self, kw):
        for item in self.tree.get_children():
            self.tree.delete(item)
        idxs = self._filtered(kw)
        # 别名优先排序
        idxs.sort(key=lambda i: self.commands[i].get("alias", ""))
        for i in idxs:
            c = self.commands[i]
            self.tree.insert("", "end", iid=str(i),
                             values=(c.get("alias", ""), c.get("description", ""),
                                     ", ".join(c.get("tags", []))))
        self.status.config(text=f"匹配 {len(idxs)} / {len(self.commands)} 条命令  ·  配置：{CONFIG_PATH}")

    def on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_idx = int(sel[0])
        c = self.commands[self.selected_idx]
        self.tmpl_label.config(text=c.get("command", ""))

        # 重建参数表单
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries = {}

        params = parse_params(c.get("command", ""))
        if not params:
            ttk.Label(self.param_frame, text="该命令无参数。", foreground="#999").pack(anchor="w", pady=6)
        else:
            for name, default in params:
                row = ttk.Frame(self.param_frame)
                row.pack(fill="x", pady=2)
                ttk.Label(row, text=name, width=14, anchor="w").pack(side="left")
                var = tk.StringVar(value=default)
                ent = ttk.Entry(row, textvariable=var)
                ent.pack(side="left", fill="x", expand=True, padx=(4, 0))
                var.trace_add("write", lambda *a: self._render_result())
                self.param_entries[name] = var
        self._render_result()

    def _render_result(self):
        if self.selected_idx is None:
            return
        c = self.commands[self.selected_idx]
        values = {k: v.get() for k, v in self.param_entries.items()}
        rendered = render_template(c.get("command", ""), values)
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", rendered)
        self.result_text.config(state="disabled")

    # ---------- 动作 ----------
    def _current_command(self):
        if self.selected_idx is None:
            messagebox.showinfo("提示", "请先在左侧选择一条命令。")
            return None, None
        c = self.commands[self.selected_idx]
        values = {k: v.get() for k, v in self.param_entries.items()}
        return c, render_template(c.get("command", ""), values)

    def on_copy(self):
        c, cmd = self._current_command()
        if not cmd:
            return
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.update()
        self.status.config(text=f"✅ 已复制到剪贴板：{cmd[:80]}")

    def on_run(self):
        c, cmd = self._current_command()
        if not cmd:
            return
        if not messagebox.askyesno("确认执行", f"将在新的命令行窗口执行：\n\n{cmd}\n\n继续？"):
            return
        try:
            subprocess.Popen(["cmd", "/k", cmd], cwd=os.getcwd())
            self.status.config(text=f"🚀 已启动：{cmd[:80]}")
        except Exception as e:
            messagebox.showerror("执行失败", str(e))

    def on_add(self):
        dlg = CommandDialog(self, None)
        self.wait_window(dlg)
        if dlg.result:
            # 别名冲突检查
            if any(x.get("alias") == dlg.result["alias"] for x in self.commands):
                messagebox.showwarning("别名冲突", f"别名 {dlg.result['alias']} 已存在。")
                return
            self.commands.append(dlg.result)
            save_commands(self.commands)
            self._refresh_list(self.search_var.get())

    def on_edit(self):
        if self.selected_idx is None:
            messagebox.showinfo("提示", "请先选择一条命令。")
            return
        old = self.commands[self.selected_idx]
        dlg = CommandDialog(self, old)
        self.wait_window(dlg)
        if dlg.result:
            self.commands[self.selected_idx] = dlg.result
            save_commands(self.commands)
            self._refresh_list(self.search_var.get())
            self.selected_idx = None
            self.on_select()

    def on_delete(self):
        if self.selected_idx is None:
            return
        c = self.commands[self.selected_idx]
        if not messagebox.askyesno("确认删除", f"删除命令 [{c.get('alias')}] {c.get('description')}？"):
            return
        del self.commands[self.selected_idx]
        save_commands(self.commands)
        self.selected_idx = None
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.tmpl_label.config(text="(选择左侧命令)")
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.config(state="disabled")
        self._refresh_list(self.search_var.get())

    def open_config(self):
        os.startfile(CONFIG_PATH)


def main():
    app = SnapCmdApp()
    app.mainloop()


if __name__ == "__main__":
    main()
