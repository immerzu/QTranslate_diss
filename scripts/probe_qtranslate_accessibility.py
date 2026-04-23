import argparse
import ctypes
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import probe_qtranslate_capture as probe


user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_TABSTOP = 0x00010000
ICC_LINK_CLASS = 0x00008000

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)


class INITCOMMONCONTROLSEX(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_uint), ("dwICC", ctypes.c_uint)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = ctypes.c_ushort
user32.CreateWindowExW.argtypes = [
    ctypes.c_uint,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_uint,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DestroyWindow.argtypes = [ctypes.c_void_p]
user32.DestroyWindow.restype = ctypes.c_bool
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_bool
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetForegroundWindow.restype = ctypes.c_bool


@WNDPROC
def wndproc(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def create_link_host(link_markup: str):
    icc = INITCOMMONCONTROLSEX(ctypes.sizeof(INITCOMMONCONTROLSEX), ICC_LINK_CLASS)
    comctl32.InitCommonControlsEx(ctypes.byref(icc))

    class_name = f"CodexAccHost_{uuid.uuid4().hex[:8]}"
    wc = WNDCLASSW()
    wc.lpfnWndProc = wndproc
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.lpszClassName = class_name
    if not user32.RegisterClassW(ctypes.byref(wc)):
        raise ctypes.WinError(ctypes.get_last_error())

    hwnd = user32.CreateWindowExW(
        0,
        class_name,
        "Codex Accessibility Host",
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        300,
        200,
        520,
        180,
        None,
        None,
        wc.hInstance,
        None,
    )
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())

    child = user32.CreateWindowExW(
        0,
        "SysLink",
        link_markup,
        WS_CHILD | WS_VISIBLE | WS_TABSTOP,
        40,
        40,
        380,
        40,
        hwnd,
        None,
        wc.hInstance,
        None,
    )
    if not child:
        raise ctypes.WinError(ctypes.get_last_error())
    return hwnd, child


def move_cursor_to_link(hwnd, child):
    rect = RECT()
    if not user32.GetWindowRect(child, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    if not user32.SetCursorPos(cx, cy):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.2)
    return {"x": cx, "y": cy}


def main():
    parser = argparse.ArgumentParser(description="Probe QTranslate's accessibility selection path with a local SysLink host.")
    parser.add_argument("--exe", required=True)
    parser.add_argument("--hotkey-field", default="HotKeyMainWindow")
    parser.add_argument("--hotkey", type=int, default=852)
    parser.add_argument("--link-url", default="https://accessibility.example/test-link")
    parser.add_argument("--link-text", default="ЧИТАТЬ")
    parser.add_argument("--timeout", type=float, default=4.0)
    args = parser.parse_args()

    exe_path = Path(args.exe).resolve()
    root_dir = exe_path.parent
    options_path = root_dir / "Data" / "Options.json"
    history_path = root_dir / "Data" / "History.json"

    options_backup = options_path.read_bytes()
    history_backup = history_path.read_bytes()
    link_markup = f'<a href="{args.link_url}">{args.link_text}</a>'

    result = {
        "exe": str(exe_path),
        "hotkey_field": args.hotkey_field,
        "hotkey": args.hotkey,
        "link_url": args.link_url,
        "link_text": args.link_text,
        "cursor": None,
        "poll": None,
        "mid_windows": [],
        "children": {},
        "richtexts": [],
    }

    host_hwnd = None
    proc = None
    try:
        host_hwnd, child_hwnd = create_link_host(link_markup)
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

        time.sleep(2.0)
        result["cursor"] = move_cursor_to_link(host_hwnd, child_hwnd)
        probe.trigger_hotkey_via_sendkeys()
        time.sleep(args.timeout)

        result["poll"] = proc.poll()
        if proc.poll() is None:
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
        if host_hwnd:
            user32.DestroyWindow(host_hwnd)
        options_path.write_bytes(options_backup)
        history_path.write_bytes(history_backup)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
