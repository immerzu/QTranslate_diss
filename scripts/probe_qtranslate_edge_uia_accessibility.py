import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import probe_qtranslate_capture as probe


user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetForegroundWindow.restype = ctypes.c_bool


def launch_edge_probe(link_text: str, link_url: str, timeout: int, settle_ms: int):
    helper = ROOT / "tmp_patch" / "inspect_edge_uia_x86.exe"
    cmd = [str(helper), "--leave-open"]
    last_error = None
    for _attempt in range(3):
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process msedge -ErrorAction SilentlyContinue | "
                "Where-Object { $_.MainWindowTitle -like '*Codex Browser UIA Native Probe*' } | "
                "Stop-Process -Force",
            ],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode == 0:
            data = {}
            for raw_line in completed.stdout.splitlines():
                line = raw_line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                data[key] = value
            if not data.get("link_name") or not data.get("link_value"):
                last_error = (
                    "edge helper returned an empty hyperlink result: "
                    f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
                )
                time.sleep(1.0)
                continue
            return {
                "Window": {
                    "Id": int(data["edge_pid"]),
                    "MainWindowHandle": int(data["top_window"], 16),
                },
                "RenderWidget": {
                    "Hwnd": int(data["render_window"], 16),
                    "PointProbe": {
                        "X": float(data["point_center"].split(",", 1)[0]),
                        "Y": float(data["point_center"].split(",", 1)[1]),
                        "Element": {
                            "Name": data.get("point_name", ""),
                            "Value": data.get("point_value", ""),
                        },
                    },
                    "Match": {
                        "Name": data.get("link_name", ""),
                        "Value": data.get("link_value", ""),
                    },
                },
                "TopLevel": {
                    "DescendantCount": int(data.get("top_descendants", "-1")),
                },
            }
        last_error = (
            "edge helper failed: "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    raise RuntimeError(last_error or "edge helper failed")


def kill_process(pid: int):
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F", "/T"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def move_cursor_to_point(hwnd: int, x: int, y: int):
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    if not user32.SetCursorPos(x, y):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.3)


def main():
    parser = argparse.ArgumentParser(description="Probe QTranslate accessibility path against a real Edge hyperlink resolved via UIA.")
    parser.add_argument("--exe", required=True)
    parser.add_argument("--hotkey-field", default="HotKeyMainWindow")
    parser.add_argument("--hotkey", type=int, default=852)
    parser.add_argument("--link-text", default="ЧИТАТЬ")
    parser.add_argument("--link-url", default="https://browser.example/test-link")
    parser.add_argument("--startup-delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--edge-timeout", type=int, default=15)
    parser.add_argument("--edge-settle-ms", type=int, default=3000)
    args = parser.parse_args()

    exe_path = Path(args.exe).resolve()
    root_dir = exe_path.parent
    options_path = root_dir / "Data" / "Options.json"
    history_path = root_dir / "Data" / "History.json"

    options_backup = options_path.read_bytes()
    history_backup = history_path.read_bytes()

    result = {
        "exe": str(exe_path),
        "hotkey_field": args.hotkey_field,
        "hotkey": args.hotkey,
        "link_text": args.link_text,
        "link_url": args.link_url,
        "edge_probe": None,
        "cursor": None,
        "poll": None,
        "mid_windows": [],
        "children": {},
        "richtexts": [],
    }

    proc = None
    edge_pid = None
    try:
        edge_probe = launch_edge_probe(args.link_text, args.link_url, args.edge_timeout, args.edge_settle_ms)
        result["edge_probe"] = edge_probe
        edge_pid = int(edge_probe["Window"]["Id"])
        edge_hwnd = int(edge_probe["Window"]["MainWindowHandle"])
        point = edge_probe["RenderWidget"]["PointProbe"]
        x = int(round(point["X"]))
        y = int(round(point["Y"]))

        options = probe.load_json(options_path)
        options["HotKeys"]["EnableHotKeys"] = True
        options["HotKeys"][args.hotkey_field] = args.hotkey
        if args.hotkey_field != "HotKeyTranslateClipboardInMainWindow":
            options["HotKeys"]["HotKeyTranslateClipboardInMainWindow"] = 0
        options["Contents"]["EditSource"] = "BASELINE_SOURCE"
        options["Contents"]["EditTranslation"] = "BASELINE_TRANSLATION"
        probe.dump_json(options_path, options)
        history_path.write_text("[]", encoding="utf-8")
        probe.set_clipboard_text_and_html("CLIPBOARD_SHOULD_NOT_APPEAR")

        proc = subprocess.Popen([str(exe_path)], cwd=str(root_dir))
        if probe.find_window_by_class(proc.pid, "QTranslate_ApplicationWindow", timeout=10.0) is None:
            raise RuntimeError("QTranslate_ApplicationWindow not found")

        time.sleep(args.startup_delay)
        move_cursor_to_point(edge_hwnd, x, y)
        result["cursor"] = {"x": x, "y": y}
        probe.trigger_hotkey_via_sendkeys()
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            result["poll"] = proc.poll()
            if proc.poll() is not None:
                break
            result["mid_windows"] = probe.list_top_windows_for_pid(proc.pid)
            for window in result["mid_windows"]:
                if window["visible"]:
                    result["children"][str(window["hwnd"])] = probe.list_child_windows(window["hwnd"])
            result["richtexts"] = probe.extract_visible_richtexts(result)
            if len(result["richtexts"]) >= 2 and result["richtexts"][0].strip() and result["richtexts"][1].strip():
                break
            time.sleep(1.0)

        result["poll"] = proc.poll()
        if proc.poll() is None and (
            len(result["richtexts"]) < 2
            or not result["richtexts"][0].strip()
            or not result["richtexts"][1].strip()
        ):
            result["mid_windows"] = probe.list_top_windows_for_pid(proc.pid)
            for window in result["mid_windows"]:
                if window["visible"]:
                    result["children"][str(window["hwnd"])] = probe.list_child_windows(window["hwnd"])
            result["richtexts"] = probe.extract_visible_richtexts(result)
    finally:
        if proc is not None and proc.poll() is None:
            probe.close_process_windows(proc.pid)
            if not probe.wait_for_exit(proc, 4.0):
                proc.kill()
                proc.wait(timeout=5.0)
        if edge_pid is not None:
            kill_process(edge_pid)
        options_path.write_bytes(options_backup)
        history_path.write_bytes(history_backup)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
