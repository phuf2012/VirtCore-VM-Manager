#!/usr/bin/env python3
"""VirtCore 1.0.0 Beta 2: a local desktop manager for libvirt VMs."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

URI = os.environ.get("VIRTCORE_LIBVIRT_URI", "qemu:///system")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,47}$")
BG = "#111514"
PANEL = "#191f1c"
PANEL_LIGHT = "#222a25"
LINE = "#344039"
TEXT = "#eef2ef"
MUTED = "#9aa79f"
GREEN = "#b7f36a"
RED = "#f08d7d"


class VirtCoreError(Exception):
    """An actionable error from the VM backend."""


def command(*args: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise VirtCoreError(f"{args[0]} is not installed. Install the VirtCore package dependencies.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VirtCoreError(f"{args[0]} timed out while contacting the hypervisor.") from exc
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise VirtCoreError(message or f"{args[0]} failed with exit code {result.returncode}.")
    return result.stdout.strip()


def connection_status() -> tuple[bool, str]:
    try:
        command("virsh", "--connect", URI, "uri")
        return True, f"Connected · {URI}"
    except VirtCoreError as exc:
        return False, str(exc)


def list_vms() -> list[dict[str, str]]:
    output = command("virsh", "--connect", URI, "list", "--all", "--name")
    result = []
    for name in (line.strip() for line in output.splitlines()):
        if not name:
            continue
        info = command("virsh", "--connect", URI, "dominfo", name)
        fields = {k.strip(): v.strip() for line in info.splitlines() if ":" in line for k, v in [line.split(":", 1)]}
        memory_kib = fields.get("Max memory", "0 KiB").split()[0]
        try:
            memory = f"{max(1, int(memory_kib) // 1024)} MiB"
        except ValueError:
            memory = fields.get("Max memory", "—")
        result.append({
            "name": name,
            "state": fields.get("State", "unknown").lower(),
            "cpus": fields.get("CPU(s)", "—"),
            "memory": memory,
            "uuid": fields.get("UUID", ""),
        })
    return result


def create_vm(name: str, iso: str, memory: int, cpus: int, disk: int) -> None:
    if not NAME_RE.fullmatch(name):
        raise VirtCoreError("Use a name with letters, numbers, dots, underscores, or hyphens (up to 48 characters).")
    if not os.path.isfile(iso) or not iso.lower().endswith((".iso", ".img")):
        raise VirtCoreError("Choose an existing .iso or .img installer image.")
    if not 512 <= memory <= 262144 or not 1 <= cpus <= 128 or not 8 <= disk <= 2048:
        raise VirtCoreError("Memory must be 512–262144 MiB, processors 1–128, and disk 8–2048 GiB.")
    if any(vm["name"] == name for vm in list_vms()):
        raise VirtCoreError(f"A virtual machine named {name} already exists.")
    command(
        "virt-install", "--connect", URI, "--name", name,
        "--memory", str(memory), "--vcpus", str(cpus),
        "--disk", f"size={disk},bus=virtio", "--cdrom", iso,
        "--osinfo", "detect=on,require=off", "--graphics", "spice",
        "--noautoconsole", timeout=120,
    )


def vm_action(name: str, action: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise VirtCoreError("Invalid virtual machine name.")
    commands = {
        "start": ("start",),
        "shutdown": ("shutdown",),
        "pause": ("suspend",),
        "resume": ("resume",),
        "force-stop": ("destroy",),
    }
    if action == "delete":
        state = next((vm["state"] for vm in list_vms() if vm["name"] == name), None)
        if state is None:
            raise VirtCoreError(f"Could not find {name}.")
        if state == "running":
            command("virsh", "--connect", URI, "destroy", name)
        command("virsh", "--connect", URI, "undefine", name, "--remove-all-storage", timeout=60)
    elif action in commands:
        command("virsh", "--connect", URI, *commands[action], name)
    else:
        raise VirtCoreError("Unsupported virtual machine action.")


class CreateDialog(tk.Toplevel):
    def __init__(self, parent: "VirtCoreApp"):
        super().__init__(parent)
        self.parent = parent
        self.title("Create a virtual machine")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self.name_var = tk.StringVar(value="linux-vm")
        self.iso_var = tk.StringVar()
        self.memory_var = tk.StringVar(value="4096")
        self.cpu_var = tk.StringVar(value="2")
        self.disk_var = tk.StringVar(value="32")
        self._build()
        self.update_idletasks()
        self.geometry(f"520x500+{parent.winfo_rootx()+max(20,(parent.winfo_width()-520)//2)}+{parent.winfo_rooty()+max(20,(parent.winfo_height()-500)//2)}")
        self.name_entry.focus_set()

    def _build(self):
        outer = tk.Frame(self, bg=BG, padx=28, pady=24)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="NEW INSTANCE", bg=BG, fg=GREEN, font=("TkFixedFont", 9, "bold")).pack(anchor="w")
        tk.Label(outer, text="Create a virtual machine", bg=BG, fg=TEXT, font=("TkDefaultFont", 20, "bold")).pack(anchor="w", pady=(8, 4))
        tk.Label(outer, text="Choose an installer and allocate resources for your Linux VM.", bg=BG, fg=MUTED, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(0, 20))

        self.name_entry = self._field(outer, "Machine name", self.name_var)
        tk.Label(outer, text="Installer image  ·  local file", bg=BG, fg="#cbd4cd", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(13, 6))
        iso_row = tk.Frame(outer, bg=BG)
        iso_row.pack(fill="x")
        tk.Entry(iso_row, textvariable=self.iso_var, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", font=("TkFixedFont", 9), highlightthickness=1, highlightbackground=LINE, highlightcolor=GREEN).pack(side="left", fill="x", expand=True, ipady=9)
        self._button(iso_row, "Browse…", self._browse, secondary=True).pack(side="left", padx=(8, 0), ipady=4)

        fields = tk.Frame(outer, bg=BG)
        fields.pack(fill="x", pady=(16, 0))
        for idx, (label, var, low, high) in enumerate((("Memory · MiB", self.memory_var, 512, 262144), ("Processors", self.cpu_var, 1, 128), ("Disk · GiB", self.disk_var, 8, 2048))):
            cell = tk.Frame(fields, bg=BG)
            cell.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 10, 0))
            fields.columnconfigure(idx, weight=1)
            tk.Label(cell, text=label, bg=BG, fg="#cbd4cd", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(0, 6))
            spin = tk.Spinbox(cell, from_=low, to=high, textvariable=var, bg=PANEL, fg=TEXT, buttonbackground=PANEL_LIGHT, insertbackground=TEXT, relief="flat", font=("TkFixedFont", 10), highlightthickness=1, highlightbackground=LINE, highlightcolor=GREEN)
            spin.pack(fill="x", ipady=5)

        self.error = tk.Label(outer, text="", bg=BG, fg=RED, wraplength=455, justify="left", font=("TkDefaultFont", 9))
        self.error.pack(anchor="w", pady=(9, 0))
        actions = tk.Frame(outer, bg=BG)
        actions.pack(side="bottom", fill="x", pady=(16, 0))
        self._button(actions, "Cancel", self.destroy, secondary=True).pack(side="right")
        self.create_button = self._button(actions, "Create VM  →", self._submit)
        self.create_button.pack(side="right", padx=(0, 8))
        tk.Label(outer, text="Creates a QEMU/KVM machine through libvirt.", bg=BG, fg="#68756d", font=("TkFixedFont", 8)).pack(side="bottom", anchor="e", pady=(14, 0))

    def _field(self, parent, label, variable):
        tk.Label(parent, text=label, bg=BG, fg="#cbd4cd", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 6))
        field = tk.Entry(parent, textvariable=variable, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", font=("TkFixedFont", 10), highlightthickness=1, highlightbackground=LINE, highlightcolor=GREEN)
        field.pack(fill="x", ipady=9)
        return field

    def _button(self, parent, text, action, secondary=False):
        bg = PANEL_LIGHT if secondary else GREEN
        fg = TEXT if secondary else "#172110"
        return tk.Button(parent, text=text, command=action, bg=bg, fg=fg, activebackground=LINE if secondary else "#c9ff86", activeforeground=fg, relief="flat", bd=0, padx=13, pady=8, cursor="hand2", font=("TkDefaultFont", 9, "bold"))

    def _browse(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a Linux installer image", filetypes=(("ISO and disk images", "*.iso *.img"), ("All files", "*")))
        if path:
            self.iso_var.set(path)

    def _submit(self):
        try:
            name = self.name_var.get().strip()
            iso = self.iso_var.get().strip()
            memory, cpus, disk = int(self.memory_var.get()), int(self.cpu_var.get()), int(self.disk_var.get())
        except (VirtCoreError, ValueError) as exc:
            self.error.config(text="Enter whole numbers for memory, processors, and disk size.")
            return
        self.create_button.configure(state="disabled", text="Creating…")
        self.parent.busy = True
        self.parent.status_message(f"Creating {name}…")

        def worker():
            try:
                create_vm(name, iso, memory, cpus, disk)
                outcome = None
            except VirtCoreError as exc:
                outcome = str(exc)
            self.after(0, lambda: self._submit_done(name, outcome))

        threading.Thread(target=worker, daemon=True).start()

    def _request_close(self):
        if self.create_button.cget("state") == "disabled":
            return
        self.destroy()

    def _submit_done(self, name, error):
        self.parent.busy = False
        if error:
            self.error.configure(text=error)
            self.create_button.configure(state="normal", text="Create VM  →")
            self.parent.status_message("VM creation failed", bad=True)
            return
        self.destroy()
        self.parent.status_message(f"Created {name}", good=True)
        self.parent.refresh()
        if messagebox.askyesno("VM created", f"{name} is ready. Open its console now?", parent=self.parent):
            self.parent.open_console(name)


class VirtCoreApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VirtCore 1.0.0 Beta 2")
        self.geometry("1050x690")
        self.minsize(820, 560)
        self.configure(bg=BG)
        self.selected: dict[str, dict[str, str]] = {}
        self.busy = False
        self._style()
        self._build()
        self.refresh()
        self.after(10000, self._poll)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, borderwidth=0, rowheight=43, font=("TkDefaultFont", 10))
        style.configure("Treeview.Heading", background=BG, foreground=MUTED, borderwidth=0, relief="flat", font=("TkDefaultFont", 8, "bold"))
        style.map("Treeview", background=[("selected", "#2c3a2b")], foreground=[("selected", TEXT)])

    def _build(self):
        top = tk.Frame(self, bg="#151a17", height=58, highlightthickness=1, highlightbackground="#26302a")
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="V", bg=GREEN, fg="#172110", width=2, height=1, font=("TkDefaultFont", 12, "bold")).pack(side="left", padx=(22, 9))
        tk.Label(top, text="VirtCore", bg="#151a17", fg=TEXT, font=("TkDefaultFont", 14, "bold")).pack(side="left")
        tk.Label(top, text="1.0.0 BETA 2", bg="#151a17", fg="#93a18f", font=("TkFixedFont", 8)).pack(side="left", padx=12)
        self.host_label = tk.Label(top, text="Checking libvirt…", bg="#151a17", fg=MUTED, font=("TkFixedFont", 9))
        self.host_label.pack(side="right", padx=22)

        body = tk.Frame(self, bg=BG, padx=32, pady=28)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="YOUR VIRTUAL WORKSPACE", bg=BG, fg=GREEN, font=("TkFixedFont", 9, "bold")).pack(anchor="w")
        tk.Label(body, text="Virtual machines", bg=BG, fg=TEXT, font=("TkDefaultFont", 23, "bold")).pack(anchor="w", pady=(7, 2))
        tk.Label(body, text="Create and manage Linux VMs on this computer.", bg=BG, fg=MUTED, font=("TkDefaultFont", 10)).pack(anchor="w")

        toolbar = tk.Frame(body, bg=BG)
        toolbar.pack(fill="x", pady=(24, 12))
        self._button(toolbar, "＋  New machine", self.new_vm).pack(side="left")
        self._button(toolbar, "Refresh  ↻", self.refresh, secondary=True).pack(side="right")

        table_frame = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        table_frame.pack(fill="both", expand=True)
        columns = ("name", "state", "cpu", "memory")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.table.heading("name", text="MACHINE")
        self.table.heading("state", text="STATUS")
        self.table.heading("cpu", text="PROCESSORS")
        self.table.heading("memory", text="MEMORY")
        self.table.column("name", width=340, anchor="w")
        self.table.column("state", width=180, anchor="w")
        self.table.column("cpu", width=130, anchor="w")
        self.table.column("memory", width=150, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=7)
        scroll.pack(side="right", fill="y", padx=8, pady=7)
        self.table.bind("<<TreeviewSelect>>", self._selection_changed)
        self.table.bind("<Double-1>", lambda _event: self.open_selected_console())
        self.table.bind("<Button-3>", self._context_menu)

        self.empty = tk.Label(table_frame, text="", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 10))
        self.empty.place(relx=.5, rely=.52, anchor="center")
        actionbar = tk.Frame(body, bg=BG)
        actionbar.pack(fill="x", pady=(13, 0))
        self.selection_label = tk.Label(actionbar, text="Select a machine to manage it", bg=BG, fg=MUTED, font=("TkDefaultFont", 9))
        self.selection_label.pack(side="left")
        self.action_buttons = {}
        for key, label in (("console", "Console"), ("start", "Start"), ("shutdown", "Shut down"), ("pause", "Pause"), ("resume", "Resume"), ("delete", "Delete")):
            button = self._button(actionbar, label, lambda act=key: self.action(act), secondary=(key != "delete"))
            button.pack(side="right", padx=(5, 0))
            self.action_buttons[key] = button

        self.status = tk.Label(self, text="Ready", bg="#151a17", fg=MUTED, anchor="w", padx=20, font=("TkFixedFont", 9), height=2)
        self.status.pack(fill="x", side="bottom")
        self._set_action_states(None)

    def _button(self, parent, text, action, secondary=False):
        bg = PANEL_LIGHT if secondary else GREEN
        fg = TEXT if secondary else "#172110"
        return tk.Button(parent, text=text, command=action, bg=bg, fg=fg, activebackground=LINE if secondary else "#c9ff86", activeforeground=fg, relief="flat", bd=0, padx=13, pady=8, cursor="hand2", font=("TkDefaultFont", 9, "bold"))

    def _selection_changed(self, _event=None):
        vm = self._selected_vm()
        self._set_action_states(vm)

    def _selected_vm(self):
        selection = self.table.selection()
        return self.selected.get(selection[0]) if selection else None

    def _set_action_states(self, vm):
        state = vm["state"] if vm else ""
        active = {
            "console": bool(vm) and shutil.which("virt-viewer") is not None,
            "start": bool(vm) and state in ("shut off", "shutoff", "crashed", "unknown"),
            "shutdown": bool(vm) and state == "running",
            "pause": bool(vm) and state == "running",
            "resume": bool(vm) and state in ("paused", "pmsuspended"),
            "delete": bool(vm),
        }
        for key, button in self.action_buttons.items():
            button.configure(state=("normal" if active[key] and not self.busy else "disabled"))
        self.selection_label.configure(text=f"{vm['name']} · {state}" if vm else "Select a machine to manage it")

    def _context_menu(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self.table.selection_set(row)
            menu = tk.Menu(self, tearoff=False, bg=PANEL_LIGHT, fg=TEXT, activebackground="#344039", activeforeground=TEXT)
            for label, action in (("Open console", "console"), ("Start", "start"), ("Shut down", "shutdown"), ("Pause", "pause"), ("Resume", "resume"), ("Delete…", "delete")):
                menu.add_command(label=label, command=lambda a=action: self.action(a))
            menu.tk_popup(event.x_root, event.y_root)

    def _poll(self):
        if not self.busy:
            self.refresh()
        self.after(10000, self._poll)

    def refresh(self):
        if self.busy:
            return
        self.busy = True
        self._set_action_states(self._selected_vm())
        self.status_message("Refreshing machine list…")

        def worker():
            connected, detail = connection_status()
            try:
                machines = list_vms() if connected else []
                error = "" if connected else detail
            except VirtCoreError as exc:
                machines, error = [], str(exc)
            self.after(0, lambda: self._refresh_done(connected, detail, machines, error))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_done(self, connected, detail, machines, error):
        self.busy = False
        self.host_label.configure(text=(f"●  {detail}" if connected else "!  Hypervisor unavailable"), fg=(GREEN if connected else RED))
        self.table.delete(*self.table.get_children())
        self.selected.clear()
        for index, vm in enumerate(machines):
            item = str(index)
            self.selected[item] = vm
            self.table.insert("", "end", iid=item, values=(vm["name"], vm["state"].upper(), vm["cpus"], vm["memory"]))
        self.empty.configure(text=("No virtual machines yet. Choose ‘New machine’ to create one." if connected and not machines else ""))
        self._set_action_states(None)
        if error:
            self.status_message(error, bad=True)
        else:
            self.status_message(f"{len(machines)} machine{'s' if len(machines) != 1 else ''} · refreshed", good=True)

    def status_message(self, text, good=False, bad=False):
        self.status.configure(text=text, fg=RED if bad else GREEN if good else MUTED)

    def new_vm(self):
        if self.busy:
            return
        CreateDialog(self)

    def action(self, action):
        vm = self._selected_vm()
        if not vm or self.busy:
            return
        name = vm["name"]
        if action == "console":
            self.open_console(name)
            return
        if action == "delete":
            confirmed = messagebox.askyesno("Delete virtual machine?", f"Delete {name} and remove its virtual disk files? If it is running, it will be powered off immediately. Unsaved guest data may be lost. This cannot be undone.", icon="warning", parent=self)
            if not confirmed:
                return
        if action == "force-stop" and not messagebox.askyesno("Force stop?", f"Immediately cut power to {name}? Unsaved guest data may be lost.", icon="warning", parent=self):
            return
        self.busy = True
        self._set_action_states(vm)
        progress = {"start": "Starting", "shutdown": "Shutting down", "pause": "Pausing", "resume": "Resuming", "force-stop": "Force stopping", "delete": "Deleting"}[action]
        self.status_message(f"{progress} {name}…")

        def worker():
            try:
                vm_action(name, action)
                outcome = None
            except VirtCoreError as exc:
                outcome = str(exc)
            self.after(0, lambda: self._action_done(name, action, outcome))

        threading.Thread(target=worker, daemon=True).start()

    def _action_done(self, name, action, error):
        self.busy = False
        if error:
            self.status_message(error, bad=True)
            messagebox.showerror("VirtCore could not complete the action", error, parent=self)
        else:
            self.status_message(f"{name}: {action} complete", good=True)
        self.refresh()

    def open_console(self, name):
        executable = shutil.which("virt-viewer")
        if not executable:
            messagebox.showerror("Console unavailable", "virt-viewer is not installed. Install virt-viewer to open the VM console.", parent=self)
            return
        try:
            subprocess.Popen([executable, "--connect", URI, name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.status_message(f"Opened console for {name}", good=True)
        except OSError as exc:
            messagebox.showerror("Could not open console", str(exc), parent=self)

    def open_selected_console(self):
        vm = self._selected_vm()
        if vm:
            self.open_console(vm["name"])


if __name__ == "__main__":
    VirtCoreApp().mainloop()
