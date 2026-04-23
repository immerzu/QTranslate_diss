from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
import traceback
from ctypes import wintypes
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_CLOSE = 0x0010
WM_HOTKEY = 0x0312
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
EM_SETSEL = 0x00B1
EM_GETSEL = 0x00B0
EM_SETREADONLY = 0x00CF
EM_SETCHARFORMAT = 0x0444
EM_GETCHARFORMAT = 0x043A
EM_SETTEXTMODE = 0x0459
TM_RICHTEXT = 0x0000
SCF_SELECTION = 0x0001
SCF_DEFAULT = 0x0000
CFM_LINK = 0x00000020
CFE_LINK = 0x00000020
CFM_HIDDEN = 0x00000100
CFE_HIDDEN = 0x00000100

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetDlgCtrlID.argtypes = [ctypes.c_void_p]
user32.GetDlgCtrlID.restype = ctypes.c_int
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

kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_bool
kernel32.VirtualAllocEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_uint,
    ctypes.c_uint,
]
kernel32.VirtualAllocEx.restype = ctypes.c_void_p
kernel32.VirtualFreeEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint]
kernel32.VirtualFreeEx.restype = ctypes.c_bool
kernel32.WriteProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WriteProcessMemory.restype = ctypes.c_bool
kernel32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = ctypes.c_bool
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool


class CHARFORMAT2W(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwMask", wintypes.DWORD),
        ("dwEffects", wintypes.DWORD),
        ("yHeight", ctypes.c_long),
        ("yOffset", ctypes.c_long),
        ("crTextColor", wintypes.COLORREF),
        ("bCharSet", wintypes.BYTE),
        ("bPitchAndFamily", wintypes.BYTE),
        ("szFaceName", wintypes.WCHAR * 32),
        ("wWeight", wintypes.WORD),
        ("sSpacing", ctypes.c_short),
        ("crBackColor", wintypes.COLORREF),
        ("lcid", wintypes.LCID),
        ("dwReserved", wintypes.DWORD),
        ("sStyle", ctypes.c_short),
        ("wKerning", wintypes.WORD),
        ("bUnderlineType", wintypes.BYTE),
        ("bAnimation", wintypes.BYTE),
        ("bRevAuthor", wintypes.BYTE),
        ("bReserved1", wintypes.BYTE),
    ]


def get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def get_message_text(hwnd: int) -> str:
    length = int(user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, None))
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, ctypes.cast(buffer, ctypes.c_void_p))
    return buffer.value


def get_class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def list_top_windows_for_pid(pid: int) -> list[dict]:
    windows = []

    @WNDENUMPROC
    def enum_proc(hwnd, _lparam):
        current_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current_pid))
        if current_pid.value == pid:
            text = get_window_text(hwnd) or get_message_text(hwnd)
            windows.append(
                {
                    "hwnd": int(hwnd),
                    "class": get_class_name(hwnd),
                    "text": text,
                    "visible": bool(user32.IsWindowVisible(hwnd)),
                }
            )
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def list_child_windows(hwnd: int) -> list[dict]:
    children = []

    @WNDENUMPROC
    def enum_proc(child_hwnd, _lparam):
        text = get_window_text(child_hwnd) or get_message_text(child_hwnd)
        children.append(
            {
                "hwnd": int(child_hwnd),
                "id": int(user32.GetDlgCtrlID(child_hwnd)),
                "class": get_class_name(child_hwnd),
                "text": text,
                "visible": bool(user32.IsWindowVisible(child_hwnd)),
            }
        )
        return True

    user32.EnumChildWindows(hwnd, enum_proc, 0)
    return children


def find_window_by_class(pid: int, class_name: str, timeout: float = 10.0) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for window in list_top_windows_for_pid(pid):
            if window["class"] == class_name:
                return window
        time.sleep(0.1)
    return None


def find_visible_richedits(pid: int) -> list[dict]:
    result = []
    for window in list_top_windows_for_pid(pid):
        if not window["visible"]:
            continue
        for child in list_child_windows(window["hwnd"]):
            if child["visible"] and child["class"] == "RICHEDIT50W":
                item = dict(child)
                item["parent_hwnd"] = window["hwnd"]
                item["parent_class"] = window["class"]
                item["parent_text"] = window["text"]
                result.append(item)
    return result


class ClipboardGuard:
    def __enter__(self):
        for _ in range(50):
            if user32.OpenClipboard(None):
                return self
            time.sleep(0.05)
        raise OSError("OpenClipboard failed")

    def __exit__(self, exc_type, exc, tb):
        user32.CloseClipboard()


def set_clipboard_bytes(fmt_id: int, payload: bytes) -> None:
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


def build_cf_html(fragment: str) -> bytes:
    prefix = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:08d}\r\n"
        "EndHTML:{end_html:08d}\r\n"
        "StartFragment:{start_fragment:08d}\r\n"
        "EndFragment:{end_fragment:08d}\r\n"
    )
    html = "<html><body><!--StartFragment-->" + fragment + "<!--EndFragment--></body></html>"
    start_html = len(prefix.format(start_html=0, end_html=0, start_fragment=0, end_fragment=0))
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


def set_clipboard_text(text: str, html_fragment: str | None = None) -> None:
    html_format = user32.RegisterClipboardFormatW("HTML Format")
    if html_fragment is not None and not html_format:
        raise ctypes.WinError(ctypes.get_last_error())
    with ClipboardGuard():
        if not user32.EmptyClipboard():
            raise ctypes.WinError(ctypes.get_last_error())
        set_clipboard_bytes(CF_UNICODETEXT, text.encode("utf-16le") + b"\x00\x00")
        if html_fragment is not None:
            set_clipboard_bytes(html_format, build_cf_html(html_fragment) + b"\x00")


def post_hotkey(hwnd: int, hotkey_value: int) -> int:
    modifiers = hotkey_value & 0xFF
    vkey = (hotkey_value >> 8) & 0xFF
    lparam = modifiers | (vkey << 16)
    if not user32.PostMessageW(hwnd, WM_HOTKEY, 0, lparam):
        raise ctypes.WinError(ctypes.get_last_error())
    return lparam


def trigger_hotkey_via_sendkeys() -> None:
    script = "$ws = New-Object -ComObject WScript.Shell; $ws.SendKeys('^%t')"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class RemoteMemory:
    def __init__(self, pid: int, size: int):
        access = PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE
        self.process = kernel32.OpenProcess(access, False, pid)
        if not self.process:
            raise ctypes.WinError(ctypes.get_last_error())
        self.size = size
        self.address = kernel32.VirtualAllocEx(
            self.process,
            None,
            size,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_READWRITE,
        )
        if not self.address:
            kernel32.CloseHandle(self.process)
            raise ctypes.WinError(ctypes.get_last_error())

    def write(self, obj) -> None:
        written = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(
            self.process,
            self.address,
            ctypes.byref(obj),
            ctypes.sizeof(obj),
            ctypes.byref(written),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def read_into(self, obj) -> None:
        read = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(
            self.process,
            self.address,
            ctypes.byref(obj),
            ctypes.sizeof(obj),
            ctypes.byref(read),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self.address:
            kernel32.VirtualFreeEx(self.process, self.address, 0, MEM_RELEASE)
            self.address = None
        if self.process:
            kernel32.CloseHandle(self.process)
            self.process = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def set_plain_text(hwnd: int, text: str) -> None:
    if not user32.SendMessageW(hwnd, WM_SETTEXT, 0, ctypes.c_wchar_p(text)):
        raise ctypes.WinError(ctypes.get_last_error())


def apply_char_format(pid: int, hwnd: int, start: int, end: int, mask: int, effects: int) -> dict:
    user32.SendMessageW(hwnd, EM_SETSEL, start, ctypes.c_void_p(end))
    fmt = CHARFORMAT2W()
    fmt.cbSize = ctypes.sizeof(CHARFORMAT2W)
    fmt.dwMask = mask
    fmt.dwEffects = effects
    with RemoteMemory(pid, ctypes.sizeof(fmt)) as mem:
        remote_address = int(mem.address)
        mem.write(fmt)
        applied = int(user32.SendMessageW(hwnd, EM_SETCHARFORMAT, SCF_SELECTION, ctypes.c_void_p(mem.address)))
        probe = CHARFORMAT2W()
        probe.cbSize = ctypes.sizeof(CHARFORMAT2W)
        probe.dwMask = mask
        mem.write(probe)
        got = int(user32.SendMessageW(hwnd, EM_GETCHARFORMAT, SCF_SELECTION, ctypes.c_void_p(mem.address)))
        mem.read_into(probe)
    return {
        "setcharformat_return": applied,
        "getcharformat_return": got,
        "remote_address": remote_address,
        "mask": int(probe.dwMask),
        "effects": int(probe.dwEffects),
        "has_cfe_link": bool(probe.dwEffects & CFE_LINK),
        "has_cfe_hidden": bool(probe.dwEffects & CFE_HIDDEN),
    }


def query_char_format(pid: int, hwnd: int, start: int, end: int, mask: int = CFM_LINK | CFM_HIDDEN) -> dict:
    user32.SendMessageW(hwnd, EM_SETSEL, start, ctypes.c_void_p(end))
    probe = CHARFORMAT2W()
    probe.cbSize = ctypes.sizeof(CHARFORMAT2W)
    probe.dwMask = mask
    with RemoteMemory(pid, ctypes.sizeof(probe)) as mem:
        remote_address = int(mem.address)
        mem.write(probe)
        got = int(user32.SendMessageW(hwnd, EM_GETCHARFORMAT, SCF_SELECTION, ctypes.c_void_p(mem.address)))
        mem.read_into(probe)
    return {
        "getcharformat_return": got,
        "remote_address": remote_address,
        "mask": int(probe.dwMask),
        "effects": int(probe.dwEffects),
        "has_cfe_link": bool(probe.dwEffects & CFE_LINK),
        "has_cfe_hidden": bool(probe.dwEffects & CFE_HIDDEN),
    }


def find_first_link_pattern(text: str, link_text: str) -> tuple[int, int, int, int] | None:
    start = text.find(link_text)
    if start < 0:
        return None
    url_start = text.find("(http", start)
    if url_start < 0:
        url_start = text.find("(www.", start)
    if url_start < 0:
        return None
    url_end = text.find(")", url_start)
    if url_end < 0:
        return None
    return start, start + len(link_text), url_start, url_end + 1


def apply_link_format(pid: int, hwnd: int, text: str, start: int, end: int, hide_url: bool) -> dict:
    readonly_off = int(user32.SendMessageW(hwnd, EM_SETREADONLY, 0, None))
    set_plain_text(hwnd, "")
    textmode_return = int(user32.SendMessageW(hwnd, EM_SETTEXTMODE, TM_RICHTEXT, None))
    set_plain_text(hwnd, text)
    result = {
        "readonly_off_return": readonly_off,
        "settextmode_rich_return": textmode_return,
        "link": apply_char_format(pid, hwnd, start, end, CFM_LINK, CFE_LINK),
    }
    if hide_url:
        url_start = text.find("(http")
        if url_start < 0:
            url_start = text.find("(www.")
        if url_start >= 0:
            url_end = text.find(")", url_start)
            if url_end >= 0:
                url_end += 1
                result["hidden_url_range"] = [url_start, url_end]
                result["hidden_url"] = apply_char_format(pid, hwnd, url_start, url_end, CFM_HIDDEN, CFE_HIDDEN)
    return result


def close_process_windows(pid: int) -> list[dict]:
    windows = list_top_windows_for_pid(pid)
    for window in windows:
        user32.PostMessageW(window["hwnd"], WM_CLOSE, 0, 0)
    return windows


def wait_for_exit(proc: subprocess.Popen, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    return False


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=3), encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe whether QTranslate's output RichEdit can carry CFE_LINK formatting on hidden-link display text."
    )
    parser.add_argument(
        "--exe",
        default=r"F:\Codex\QTranslate_diss\release\QTranslate_portable_clean\QTranslate.exe",
    )
    parser.add_argument("--trigger", choices=["sendkeys", "postmessage"], default="sendkeys")
    parser.add_argument("--post-hotkey-delay", type=float, default=8.0)
    parser.add_argument("--clipboard-visible", default="QTranslate output RichEdit link probe clipboard")
    parser.add_argument("--clipboard-html")
    parser.add_argument(
        "--sample",
        default="FreeTranslations nutzt translate-pa.googleapis.com READ und bleibt sauber.",
    )
    parser.add_argument("--link-text", default="READ")
    parser.add_argument("--hide-url", action="store_true")
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    root = exe.parent
    options_path = root / "Data" / "Options.json"
    options_backup = options_path.read_bytes()
    result = {
        "exe": str(exe),
        "richedits_before": [],
        "target_hwnd": None,
        "plain_text": None,
        "link_range": None,
        "after_text": None,
        "format_probe": None,
        "error": None,
    }
    proc = None
    try:
        options = load_json(options_path)
        options["HotKeys"]["EnableHotKeys"] = True
        options["HotKeys"]["HotKeyTranslateClipboardInMainWindow"] = 852
        options["Contents"]["EditSource"] = "QTranslate output RichEdit link probe source"
        options["Contents"]["EditTranslation"] = "QTranslate output RichEdit link probe translation"
        dump_json(options_path, options)
        set_clipboard_text(args.clipboard_visible, args.clipboard_html)

        proc = subprocess.Popen([str(exe)], cwd=str(root))
        app_window = find_window_by_class(proc.pid, "QTranslate_ApplicationWindow", timeout=10.0)
        if app_window is None:
            raise RuntimeError("QTranslate_ApplicationWindow not found")
        time.sleep(2.0)
        if args.trigger == "postmessage":
            result["hotkey_lparam"] = post_hotkey(app_window["hwnd"], 852)
        else:
            result["hotkey_lparam"] = 0x00540003
            trigger_hotkey_via_sendkeys()
        time.sleep(args.post_hotkey_delay)

        richedits = find_visible_richedits(proc.pid)
        result["richedits_before"] = richedits
        if len(richedits) < 2:
            raise RuntimeError(f"Expected at least two visible RICHEDIT50W controls, found {len(richedits)}")

        target = richedits[1]
        hwnd = target["hwnd"]
        text = target["text"] if args.inspect_only else args.sample
        link_text = args.link_text
        result["target_hwnd"] = hwnd
        result["plain_text"] = text
        pattern = find_first_link_pattern(text, link_text)
        if pattern is None:
            start = text.index(link_text)
            end = start + len(link_text)
            result["link_range"] = [start, end]
            result["format_probe"] = (
                query_char_format(proc.pid, hwnd, start, end) if args.inspect_only
                else apply_link_format(proc.pid, hwnd, text, start, end, args.hide_url)
            )
        else:
            start, end, url_start, url_end = pattern
            result["link_range"] = [start, end]
            result["url_range"] = [url_start, url_end]
            if args.inspect_only:
                result["format_probe"] = {
                    "link": query_char_format(proc.pid, hwnd, start, end),
                    "url": query_char_format(proc.pid, hwnd, url_start, url_end),
                    "whole": query_char_format(proc.pid, hwnd, start, url_end),
                }
            else:
                result["format_probe"] = apply_link_format(proc.pid, hwnd, text, start, end, args.hide_url)
        result["after_text"] = get_message_text(hwnd)

        if not args.keep_open:
            result["close_windows"] = close_process_windows(proc.pid)
            wait_for_exit(proc, 5.0)
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5.0)
            result["exit_code"] = proc.returncode
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        if proc is not None and proc.poll() is None and not args.keep_open:
            close_process_windows(proc.pid)
            if not wait_for_exit(proc, 4.0):
                proc.kill()
                proc.wait(timeout=5.0)
            result["exit_code"] = proc.returncode
    finally:
        options_path.write_bytes(options_backup)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
