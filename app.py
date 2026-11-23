#!/usr/bin/env python3
"""VirtCore's small, dependency-free Linux/libvirt web interface."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
URI = os.environ.get("VIRTCORE_LIBVIRT_URI", "qemu:///system")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,47}$")


class VirtCoreError(Exception):
    pass


def run(*args: str, timeout: int = 12) -> str:
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise VirtCoreError(f"{args[0]} is not installed. Install libvirt and virt-install to manage VMs.")
    except subprocess.TimeoutExpired:
        raise VirtCoreError(f"{args[0]} timed out while contacting libvirt.")
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise VirtCoreError(message or f"{args[0]} failed.")
    return result.stdout.strip()


def vms() -> list[dict]:
    output = run("virsh", "--connect", URI, "list", "--all", "--uuid", "--name")
    names = [name for name in output.splitlines() if name.strip()]
    result = []
    for name in names:
        try:
            info = run("virsh", "--connect", URI, "dominfo", name)
            fields = dict(line.split(":", 1) for line in info.splitlines() if ":" in line)
            state = fields.get("State", "unknown").strip().lower()
            result.append({
                "name": name,
                "state": state,
                "memory": fields.get("Max memory", "—").strip(),
                "cpus": fields.get("CPU(s)", "—").strip(),
                "uuid": fields.get("UUID", "").strip(),
            })
        except VirtCoreError:
            result.append({"name": name, "state": "unknown", "memory": "—", "cpus": "—", "uuid": ""})
    return result


def host_status() -> dict:
    checks = {
        "libvirt": shutil.which("virsh") is not None,
        "virt_install": shutil.which("virt-install") is not None,
        "qemu": any(shutil.which(c) for c in ("qemu-system-x86_64", "qemu-system-aarch64")),
    }
    try:
        run("virsh", "--connect", URI, "uri")
        connected, error = True, ""
    except VirtCoreError as exc:
        connected, error = False, str(exc)
    return {"checks": checks, "connected": connected, "uri": URI, "error": error}


def create_vm(data: dict) -> dict:
    name = str(data.get("name", "")).strip()
    iso = str(data.get("iso", "")).strip()
    if not NAME_RE.fullmatch(name):
        raise VirtCoreError("Choose a name using letters, numbers, dots, underscores, or hyphens (up to 48 characters).")
    if not iso or not Path(iso).is_file() or not iso.lower().endswith((".iso", ".img")):
        raise VirtCoreError("Select an existing .iso or .img installer file on this Linux host.")
    try:
        memory = int(data.get("memory", 4096))
        cpus = int(data.get("cpus", 2))
        disk = int(data.get("disk", 32))
    except (TypeError, ValueError):
        raise VirtCoreError("Memory, CPU, and disk values must be numbers.")
    if not 512 <= memory <= 262144 or not 1 <= cpus <= 128 or not 8 <= disk <= 2048:
        raise VirtCoreError("Use memory 512–262144 MiB, CPUs 1–128, and disk 8–2048 GiB.")
    # Ensure the name is unused before invoking virt-install.
    if any(vm["name"] == name for vm in vms()):
        raise VirtCoreError(f"A VM named {name} already exists.")
    command = ["virt-install", "--connect", URI, "--name", name, "--memory", str(memory),
               "--vcpus", str(cpus), "--disk", f"size={disk},bus=virtio", "--cdrom", iso,
               "--osinfo", "detect=on,require=off", "--graphics", "spice", "--noautoconsole"]
    run(*command, timeout=45)
    return {"name": name}


def vm_action(name: str, action: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise VirtCoreError("Invalid VM name.")
    commands = {"start": ("start",), "shutdown": ("shutdown",), "pause": ("suspend",), "resume": ("resume",)}
    if action == "delete":
        run("virsh", "--connect", URI, "destroy", name) if any(x["name"] == name and x["state"] == "running" for x in vms()) else None
        run("virsh", "--connect", URI, "undefine", name, "--remove-all-storage")
    elif action in commands:
        run("virsh", "--connect", URI, *commands[action], name)
    else:
        raise VirtCoreError("Unsupported VM action.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"VirtCore: {self.address_string()} {fmt % args}")

    def send_json(self, code: int, data: dict | list) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/status":
            try:
                self.send_json(200, host_status())
            except VirtCoreError as exc:
                self.send_json(200, {"checks": {}, "connected": False, "uri": URI, "error": str(exc)})
        elif route == "/api/vms":
            try:
                self.send_json(200, {"vms": vms()})
            except VirtCoreError as exc:
                self.send_json(503, {"error": str(exc), "vms": []})
        else:
            path = (ROOT / ("index.html" if route == "/" else route.lstrip("/"))).resolve()
            if ROOT.resolve() not in path.parents and path != ROOT.resolve():
                self.send_error(404)
                return
            if not path.is_file():
                self.send_error(404)
                return
            content_type = "text/html; charset=utf-8" if path.suffix == ".html" else "text/css; charset=utf-8" if path.suffix == ".css" else "text/javascript; charset=utf-8"
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            route = urlparse(self.path).path
            if route == "/api/vms":
                result = create_vm(data)
            elif route.startswith("/api/vms/"):
                name, _, action = route[len("/api/vms/"):].partition("/")
                vm_action(name, action)
                result = {"ok": True}
            else:
                self.send_json(404, {"error": "Not found."})
                return
            self.send_json(200, result)
        except (VirtCoreError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VirtCore Linux virtual machine manager")
    parser.add_argument("--open", action="store_true", help="open VirtCore in the default browser")
    args = parser.parse_args()
    host = os.environ.get("VIRTCORE_HOST", "127.0.0.1")
    port = int(os.environ.get("VIRTCORE_PORT", "8765"))
    url = f"http://{host}:{port}"
    print(f"VirtCore 1.0.0 Beta running at {url} (libvirt: {URI})")
    if args.open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    ThreadingHTTPServer((host, port), Handler).serve_forever()
