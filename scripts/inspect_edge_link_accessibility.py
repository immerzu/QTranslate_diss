import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
HTML = ROOT / "tmp_patch" / "browser_accessibility_probe.html"

user32 = ctypes.WinDLL("user32", use_last_error=True)
oleacc = ctypes.OleDLL("oleacc")
oleaut32 = ctypes.OleDLL("oleaut32")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class VARIANT_UNION(ctypes.Union):
    _fields_ = [
        ("llVal", ctypes.c_longlong),
        ("lVal", ctypes.c_long),
        ("bstrVal", ctypes.c_void_p),
        ("pdispVal", ctypes.c_void_p),
    ]


class VARIANT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("data", VARIANT_UNION),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
user32.EnumWindows.restype = ctypes.c_bool
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetForegroundWindow.restype = ctypes.c_bool
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = ctypes.c_bool
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
user32.PostMessageW.restype = ctypes.c_bool

oleacc.AccessibleObjectFromPoint.argtypes = [POINT, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(VARIANT)]
oleacc.AccessibleObjectFromPoint.restype = ctypes.c_long
oleaut32.SysStringLen.argtypes = [ctypes.c_void_p]
oleaut32.SysStringLen.restype = ctypes.c_uint
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
oleaut32.SysFreeString.restype = None


def ensure_html(link_text: str, href: str) -> Path:
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text(
        f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Codex Browser Accessibility Probe</title>
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      background: #f5f1e8;
      font-family: Georgia, 'Times New Roman', serif;
    }}
    .wrap {{
      padding: 56px;
    }}
    a.probe {{
      display: inline-block;
      font-size: 48px;
      line-height: 1.2;
      color: #0d47a1;
      text-decoration: underline;
      padding: 24px 32px;
      background: #fff8e1;
      border: 3px solid #c62828;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <a class="probe" href="{href}">{link_text}</a>
  </div>
</body>
</html>
""",
        encoding="utf-8",
    )
    return HTML


def get_window_text(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def get_class_name(hwnd) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def list_windows_for_pid(pid: int):
    windows = []

    @WNDENUMPROC
    def enum_proc(hwnd, _lparam):
        current_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current_pid))
        if current_pid.value == pid:
            windows.append(
                {
                    "hwnd": int(hwnd),
                    "class": get_class_name(hwnd),
                    "title": get_window_text(hwnd),
                    "visible": bool(user32.IsWindowVisible(hwnd)),
                }
            )
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def find_edge_window(pid: int, timeout: float):
    deadline = time.time() + timeout
    while time.time() < deadline:
        windows = list_windows_for_pid(pid)
        for window in windows:
            if window["visible"] and window["class"] == "Chrome_WidgetWin_1":
                return window
        time.sleep(0.2)
    return None


def bstr_to_text(bstr: int | None):
    if not bstr:
        return None
    length = oleaut32.SysStringLen(bstr)
    if length == 0:
        return ""
    return ctypes.wstring_at(bstr, length)


def release_com(ptr: int):
    if not ptr:
        return
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[2])
    release(ptr)


def call_acc_method(ptr: int, method_index: int, child: VARIANT, out_kind: str):
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    fn_ptr = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[method_index]
    if out_kind == "bstr":
        out = ctypes.c_void_p()
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, VARIANT, ctypes.POINTER(ctypes.c_void_p))(fn_ptr)
        hr = fn(ptr, child, ctypes.byref(out))
        text = bstr_to_text(out.value)
        if out.value:
            oleaut32.SysFreeString(out)
        return hr, text, None
    if out_kind == "variant":
        out = VARIANT()
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, VARIANT, ctypes.POINTER(VARIANT))(fn_ptr)
        hr = fn(ptr, child, ctypes.byref(out))
        value = None
        if out.vt == 3:
            value = out.lVal
        elif out.vt == 2:
            value = out.lVal & 0xFFFF
        return hr, None, {"vt": out.vt, "value": value}
    raise ValueError(out_kind)


def inspect_point(point: POINT):
    acc_ptr = ctypes.c_void_p()
    child = VARIANT()
    hr = oleacc.AccessibleObjectFromPoint(point, ctypes.byref(acc_ptr), ctypes.byref(child))
    result = {
        "point": {"x": point.x, "y": point.y},
        "hr": hr,
        "acc_ptr": hex(acc_ptr.value) if acc_ptr.value else None,
        "child": {"vt": child.vt, "value": child.lVal if child.vt in (2, 3) else None},
        "name": None,
        "value": None,
        "role": None,
    }
    if hr < 0 or not acc_ptr.value:
        return result

    try:
        hr_name, name, _ = call_acc_method(acc_ptr.value, 10, child, "bstr")
        hr_value, value, _ = call_acc_method(acc_ptr.value, 11, child, "bstr")
        hr_role, _, role = call_acc_method(acc_ptr.value, 13, child, "variant")
        result["name"] = {"hr": hr_name, "text": name}
        result["value"] = {"hr": hr_value, "text": value}
        result["role"] = {"hr": hr_role, **(role or {})}
    finally:
        release_com(acc_ptr.value)
    return result


def scan_window(hwnd: int, step: int, target_text: str):
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())

    results = []
    left = rect.left + 80
    right = rect.right - 80
    top = rect.top + 120
    bottom = min(rect.bottom - 80, rect.top + 420)

    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    for y in range(top, bottom, step):
        for x in range(left, right, step):
            user32.SetCursorPos(x, y)
            time.sleep(0.01)
            item = inspect_point(POINT(x, y))
            name_text = (item.get("name") or {}).get("text")
            value_text = (item.get("value") or {}).get("text")
            if name_text or value_text:
                results.append(item)
            if name_text == target_text:
                return rect, results, item
    return rect, results, None


def close_window(hwnd: int):
    user32.PostMessageW(hwnd, 0x0010, 0, 0)


def main():
    parser = argparse.ArgumentParser(description="Inspect real browser accessibility over a local Edge page.")
    parser.add_argument("--link-text", default="ЧИТАТЬ")
    parser.add_argument("--link-url", default="https://browser.example/test-link")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--step", type=int, default=24)
    args = parser.parse_args()

    if not EDGE.exists():
        raise FileNotFoundError(EDGE)

    html_path = ensure_html(args.link_text, args.link_url)
    proc = subprocess.Popen(
        [
            str(EDGE),
            "--new-window",
            f"file:///{html_path.as_posix()}",
            "--window-position=120,80",
            "--window-size=1200,900",
        ],
        cwd=str(ROOT),
    )

    try:
        window = find_edge_window(proc.pid, args.timeout)
        if window is None:
            raise RuntimeError("Visible Edge window not found")

        rect, samples, match = scan_window(window["hwnd"], args.step, args.link_text)
        result = {
            "edge": str(EDGE),
            "html": str(html_path),
            "window": {**window, "rect": {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}},
            "sample_count": len(samples),
            "match": match,
            "samples": samples[:20],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if proc.poll() is None:
            windows = list_windows_for_pid(proc.pid)
            for window in windows:
                if window["visible"]:
                    close_window(window["hwnd"])
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5.0)


if __name__ == "__main__":
    main()
