import argparse
import ctypes
import json
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
WM_CLOSE = 0x0010
WM_HOTKEY = 0x0312
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_T = 0x54

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_bool
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.c_bool
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
user32.RegisterClipboardFormatW.restype = ctypes.c_uint
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
user32.EnumWindows.restype = ctypes.c_bool
user32.EnumChildWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
user32.EnumChildWindows.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
user32.PostMessageW.restype = ctypes.c_bool
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_size_t

kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint), ("union", INPUTUNION)]


user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = ctypes.c_uint


class ClipboardGuard:
    def __enter__(self):
        for _ in range(50):
            if user32.OpenClipboard(None):
                return self
            time.sleep(0.05)
        raise OSError("OpenClipboard failed")

    def __exit__(self, exc_type, exc, tb):
        user32.CloseClipboard()


def set_clipboard_bytes(fmt_id, payload):
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        raise ctypes.WinError(ctypes.get_last_error())
    ctypes.memmove(ptr, payload, len(payload))
    kernel32.GlobalUnlock(handle)
    if not user32.SetClipboardData(fmt_id, handle):
        raise ctypes.WinError(ctypes.get_last_error())


def build_cf_html(fragment):
    prefix = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:08d}\r\n"
        "EndHTML:{end_html:08d}\r\n"
        "StartFragment:{start_fragment:08d}\r\n"
        "EndFragment:{end_fragment:08d}\r\n"
    )
    html = (
        "<html><body>"
        "<!--StartFragment-->"
        f"{fragment}"
        "<!--EndFragment-->"
        "</body></html>"
    )
    start_html = len(prefix.format(
        start_html=0,
        end_html=0,
        start_fragment=0,
        end_fragment=0,
    ))
    start_fragment = start_html + html.index("<!--StartFragment-->") + len("<!--StartFragment-->")
    end_fragment = start_html + html.index("<!--EndFragment-->")
    end_html = start_html + len(html)
    header = prefix.format(
        start_html=start_html,
        end_html=end_html,
        start_fragment=start_fragment,
        end_fragment=end_fragment,
    )
    return (header + html).encode("utf-8")


def set_clipboard_text_and_html(text, html_fragment=None):
    html_format = user32.RegisterClipboardFormatW("HTML Format")
    if not html_format:
        raise ctypes.WinError(ctypes.get_last_error())
    with ClipboardGuard():
        if not user32.EmptyClipboard():
            raise ctypes.WinError(ctypes.get_last_error())
        set_clipboard_bytes(CF_UNICODETEXT, text.encode("utf-16le") + b"\x00\x00")
        if html_fragment is not None:
            set_clipboard_bytes(html_format, build_cf_html(html_fragment) + b"\x00")


def get_window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def get_message_text(hwnd):
    length = int(user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, None))
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, ctypes.cast(buffer, ctypes.c_void_p))
    return buffer.value


def get_class_name(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def list_top_windows_for_pid(pid):
    windows = []

    @WNDENUMPROC
    def enum_proc(hwnd, _lparam):
        current_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current_pid))
        if current_pid.value == pid:
            text = get_window_text(hwnd)
            if not text:
                text = get_message_text(hwnd)
            windows.append({
                "hwnd": int(hwnd),
                "class": get_class_name(hwnd),
                "text": text,
                "visible": bool(user32.IsWindowVisible(hwnd)),
            })
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def list_child_windows(hwnd):
    children = []

    @WNDENUMPROC
    def enum_proc(child_hwnd, _lparam):
        text = get_window_text(child_hwnd)
        if not text:
            text = get_message_text(child_hwnd)
        children.append({
            "hwnd": int(child_hwnd),
            "class": get_class_name(child_hwnd),
            "text": text,
            "visible": bool(user32.IsWindowVisible(child_hwnd)),
        })
        return True

    user32.EnumChildWindows(hwnd, enum_proc, 0)
    return children


def find_window_by_class(pid, class_name, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for window in list_top_windows_for_pid(pid):
            if window["class"] == class_name:
                return window
        time.sleep(0.1)
    return None


def post_hotkey(hwnd, hotkey_value):
    modifiers = hotkey_value & 0xFF
    vkey = (hotkey_value >> 8) & 0xFF
    lparam = modifiers | (vkey << 16)
    if not user32.PostMessageW(hwnd, WM_HOTKEY, 0, lparam):
        raise ctypes.WinError(ctypes.get_last_error())
    return lparam


def send_key(vk_code, keyup=False):
    event = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUTUNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP if keyup else 0,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def trigger_hotkey_via_sendinput():
    send_key(VK_CONTROL, keyup=False)
    time.sleep(0.05)
    send_key(VK_MENU, keyup=False)
    time.sleep(0.05)
    send_key(VK_T, keyup=False)
    time.sleep(0.05)
    send_key(VK_T, keyup=True)
    time.sleep(0.05)
    send_key(VK_MENU, keyup=True)
    time.sleep(0.05)
    send_key(VK_CONTROL, keyup=True)


def trigger_hotkey_via_sendkeys():
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "$ws.SendKeys('^%t')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def close_process_windows(pid):
    windows = list_top_windows_for_pid(pid)
    for window in windows:
        user32.PostMessageW(window["hwnd"], WM_CLOSE, 0, 0)
    return windows


def wait_for_exit(proc, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    return False


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=3), encoding="utf-8-sig")


def extract_matching_history(history_data, marker):
    matches = []
    for item in history_data:
        if not item:
            continue
        source = item[0]
        if marker in source:
            matches.append(item)
    return matches


def extract_visible_richtexts(result):
    for window in result.get("mid_windows", []):
        if not window.get("visible"):
            continue
        if window.get("class") != "#32770":
            continue
        children = result.get("children", {}).get(str(window["hwnd"]), [])
        richtexts = [
            child.get("text", "")
            for child in children
            if child.get("class") == "RICHEDIT50W" and child.get("visible")
        ]
        if richtexts:
            return richtexts
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--mode", choices=["unicode", "html"], required=True)
    parser.add_argument("--trigger", choices=["postmessage", "sendinput", "sendkeys"], default="sendkeys")
    parser.add_argument("--startup-delay", type=float, default=3.0)
    parser.add_argument("--url", default="https://example.com/test-link")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--visible-text")
    parser.add_argument("--html-fragment")
    args = parser.parse_args()

    exe_path = Path(args.exe).resolve()
    root_dir = exe_path.parent
    data_dir = root_dir / "Data"
    options_path = data_dir / "Options.json"
    history_path = data_dir / "History.json"

    options_backup = options_path.read_bytes()
    history_backup = history_path.read_bytes()
    marker = f"QTLINK_{uuid.uuid4().hex[:8]}"
    visible_text = args.visible_text or f"{marker} ЧИТАТЬ {marker}"
    baseline_source = f"BASELINE_SOURCE_{marker}"
    baseline_translation = f"BASELINE_TRANSLATION_{marker}"
    html_fragment = None
    if args.mode == "html":
        html_fragment = args.html_fragment or f'<div>{marker} <a href="{args.url}">ЧИТАТЬ</a> {marker}</div>'

    result = {
        "exe": str(exe_path),
        "mode": args.mode,
        "url": args.url,
        "marker": marker,
        "visible_text": visible_text,
        "lparam": None,
        "initial_windows": [],
        "mid_windows": [],
        "children": {},
        "close_windows": [],
        "exit_code": None,
        "saved_edit_source": None,
        "saved_edit_translation": None,
        "history_matches": [],
        "ui_source_text": None,
        "ui_translation_text": None,
        "error": None,
    }

    proc = None
    try:
        options = load_json(options_path)
        options["HotKeys"]["EnableHotKeys"] = True
        options["HotKeys"]["HotKeyTranslateClipboardInMainWindow"] = 852
        options["Contents"]["EditSource"] = baseline_source
        options["Contents"]["EditTranslation"] = baseline_translation
        dump_json(options_path, options)
        history_path.write_text("[]", encoding="utf-8")

        set_clipboard_text_and_html(visible_text, html_fragment)

        proc = subprocess.Popen([str(exe_path)], cwd=str(root_dir))
        app_window = find_window_by_class(proc.pid, "QTranslate_ApplicationWindow", timeout=10.0)
        if app_window is None:
            raise RuntimeError("QTranslate_ApplicationWindow not found")

        result["initial_windows"] = list_top_windows_for_pid(proc.pid)
        time.sleep(args.startup_delay)
        if args.trigger == "postmessage":
            result["lparam"] = post_hotkey(app_window["hwnd"], 852)
        elif args.trigger == "sendinput":
            result["lparam"] = 0x00540003
            trigger_hotkey_via_sendinput()
        else:
            result["lparam"] = 0x00540003
            trigger_hotkey_via_sendkeys()

        time.sleep(args.timeout)

        result["mid_windows"] = list_top_windows_for_pid(proc.pid)
        for window in result["mid_windows"]:
            if window["visible"]:
                result["children"][str(window["hwnd"])] = list_child_windows(window["hwnd"])
        richtexts = extract_visible_richtexts(result)
        if len(richtexts) >= 1:
            result["ui_source_text"] = richtexts[0]
        if len(richtexts) >= 2:
            result["ui_translation_text"] = richtexts[1]

        result["close_windows"] = close_process_windows(proc.pid)
        wait_for_exit(proc, 8.0)
        result["exit_code"] = proc.poll()

        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5.0)
            result["exit_code"] = proc.returncode

        saved_options = load_json(options_path)
        saved_history = load_json(history_path)
        result["saved_edit_source"] = saved_options["Contents"]["EditSource"]
        result["saved_edit_translation"] = saved_options["Contents"]["EditTranslation"]
        result["history_matches"] = extract_matching_history(saved_history, marker)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        if proc is not None and proc.poll() is None:
            close_process_windows(proc.pid)
            if not wait_for_exit(proc, 4.0):
                proc.kill()
                proc.wait(timeout=5.0)
            result["exit_code"] = proc.returncode
    finally:
        options_path.write_bytes(options_backup)
        history_path.write_bytes(history_backup)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
