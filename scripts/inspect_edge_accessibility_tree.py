import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from collections import deque
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
HTML = ROOT / "tmp_patch" / "browser_accessibility_probe.html"

VT_EMPTY = 0
VT_I4 = 3
VT_BSTR = 8
VT_DISPATCH = 9

OBJID_WINDOW = 0x00000000
OBJID_CLIENT = 0xFFFFFFFC
CHILDID_SELF = 0

user32 = ctypes.WinDLL("user32", use_last_error=True)
ole32 = ctypes.OleDLL("ole32")
oleacc = ctypes.OleDLL("oleacc")
oleaut32 = ctypes.OleDLL("oleaut32")


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


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

IID_IAccessible = GUID(
    0x618736E0,
    0x3C3D,
    0x11CF,
    (ctypes.c_ubyte * 8)(0x81, 0x0C, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71),
)

user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
user32.EnumWindows.restype = ctypes.c_bool
user32.EnumChildWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
user32.EnumChildWindows.restype = ctypes.c_bool
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
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
user32.PostMessageW.restype = ctypes.c_bool

ole32.CoInitialize.argtypes = [ctypes.c_void_p]
ole32.CoInitialize.restype = ctypes.c_long
ole32.CoUninitialize.argtypes = []
ole32.CoUninitialize.restype = None

oleacc.AccessibleObjectFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
oleacc.AccessibleObjectFromWindow.restype = ctypes.c_long
oleacc.AccessibleChildren.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_long, ctypes.POINTER(VARIANT), ctypes.POINTER(ctypes.c_long)]
oleacc.AccessibleChildren.restype = ctypes.c_long

oleaut32.SysStringLen.argtypes = [ctypes.c_void_p]
oleaut32.SysStringLen.restype = ctypes.c_uint
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
oleaut32.SysFreeString.restype = None
oleaut32.VariantClear.argtypes = [ctypes.POINTER(VARIANT)]
oleaut32.VariantClear.restype = ctypes.c_long


def ensure_html(link_text: str, href: str) -> Path:
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text(
        f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Codex Browser Accessibility Tree Probe</title>
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


def list_visible_windows():
    windows = []

    @WNDENUMPROC
    def enum_proc(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            windows.append(
                {
                    "hwnd": int(hwnd),
                    "class": get_class_name(hwnd),
                    "title": get_window_text(hwnd),
                    "visible": True,
                }
            )
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def list_child_windows(parent_hwnd: int, limit: int):
    windows = []

    @WNDENUMPROC
    def enum_proc(hwnd, _lparam):
        windows.append(
            {
                "hwnd": int(hwnd),
                "class": get_class_name(hwnd),
                "title": get_window_text(hwnd),
                "visible": bool(user32.IsWindowVisible(hwnd)),
            }
        )
        return len(windows) < limit

    user32.EnumChildWindows(parent_hwnd, enum_proc, 0)
    return windows


def find_edge_window(pid: int, timeout: float, baseline_hwnds: set[int], title_hint: str):
    deadline = time.time() + timeout
    while time.time() < deadline:
        windows = list_windows_for_pid(pid)
        for window in windows:
            if window["visible"] and window["class"] == "Chrome_WidgetWin_1":
                return window
        all_windows = list_visible_windows()
        for window in all_windows:
            if window["class"] != "Chrome_WidgetWin_1":
                continue
            if window["hwnd"] in baseline_hwnds:
                continue
            if title_hint and title_hint not in window["title"]:
                continue
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


def query_iaccessible(ptr: int):
    if not ptr:
        return None
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    query_interface = ctypes.WINFUNCTYPE(
        ctypes.c_long,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    )(ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[0])
    out = ctypes.c_void_p()
    hr = query_interface(ptr, ctypes.byref(IID_IAccessible), ctypes.byref(out))
    if hr < 0 or not out.value:
        return None
    return out.value


def make_self_variant() -> VARIANT:
    child = VARIANT()
    child.vt = VT_I4
    child.lVal = CHILDID_SELF
    return child


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
        return hr, text
    if out_kind == "variant":
        out = VARIANT()
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, VARIANT, ctypes.POINTER(VARIANT))(fn_ptr)
        hr = fn(ptr, child, ctypes.byref(out))
        value = {"vt": out.vt}
        if out.vt == VT_I4:
            value["value"] = out.lVal
        elif out.vt == VT_DISPATCH:
            value["ptr"] = out.pdispVal
        else:
            value["value"] = None
        safe_variant_clear(out)
        return hr, value
    if out_kind == "long":
        out = ctypes.c_long()
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_long))(fn_ptr)
        hr = fn(ptr, ctypes.byref(out))
        return hr, out.value
    if out_kind == "dispatch":
        out = ctypes.c_void_p()
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, VARIANT, ctypes.POINTER(ctypes.c_void_p))(fn_ptr)
        hr = fn(ptr, child, ctypes.byref(out))
        return hr, out.value
    raise ValueError(out_kind)


def safe_text(text):
    if text is None:
        return None
    return text.replace("\r", "\\r").replace("\n", "\\n")


def safe_variant_clear(variant: VARIANT):
    if variant.vt not in (VT_EMPTY, VT_I4, VT_BSTR, VT_DISPATCH):
        return
    try:
        oleaut32.VariantClear(ctypes.byref(variant))
    except OSError:
        return


def get_props(ptr: int, include_extended: bool):
    child = make_self_variant()
    hr_name, name = call_acc_method(ptr, 10, child, "bstr")
    hr_value, value = call_acc_method(ptr, 11, child, "bstr")
    hr_role, role = call_acc_method(ptr, 13, child, "variant")
    props = {
        "name": {"hr": hr_name, "text": safe_text(name)},
        "value": {"hr": hr_value, "text": safe_text(value)},
        "role": {"hr": hr_role, **role},
    }
    if include_extended:
        hr_state, state = call_acc_method(ptr, 14, child, "variant")
        hr_default, default_action = call_acc_method(ptr, 20, child, "bstr")
        props["state"] = {"hr": hr_state, **state}
        props["default_action"] = {"hr": hr_default, "text": safe_text(default_action)}
    return props


def get_child_count(ptr: int) -> int:
    hr, count = call_acc_method(ptr, 8, make_self_variant(), "long")
    if hr < 0:
        return 0
    return max(count, 0)


def child_variant_to_ptr(owner_ptr: int, variant: VARIANT):
    if variant.vt == VT_DISPATCH and variant.pdispVal:
        accessible_ptr = query_iaccessible(variant.pdispVal)
        if accessible_ptr:
            return accessible_ptr, "dispatch"
        return None, "dispatch"
    if variant.vt == VT_I4 and variant.lVal > 0:
        hr, child_ptr = call_acc_method(owner_ptr, 9, variant, "dispatch")
        if hr >= 0 and child_ptr:
            try:
                accessible_ptr = query_iaccessible(child_ptr)
                if accessible_ptr:
                    return accessible_ptr, f"childid:{variant.lVal}"
            finally:
                release_com(child_ptr)
        return None, f"childid:{variant.lVal}"
    return None, None


def enumerate_children(ptr: int, limit: int):
    count = get_child_count(ptr)
    if count <= 0:
        return []
    want = min(count, limit)
    variants = (VARIANT * want)()
    obtained = ctypes.c_long()
    hr = oleacc.AccessibleChildren(ptr, 0, want, variants, ctypes.byref(obtained))
    if hr < 0:
        return []

    children = []
    for index in range(obtained.value):
        variant = variants[index]
        child_ptr, via = child_variant_to_ptr(ptr, variant)
        if child_ptr:
            children.append((child_ptr, via, index + 1))
        safe_variant_clear(variants[index])
    return children


def traverse_tree(root_ptr: int, *, max_depth: int, max_nodes: int, child_limit: int, target_text: str, target_url: str, include_extended: bool):
    queue = deque([(root_ptr, 0, "root", 0)])
    visited = set()
    nodes = []
    matches = []

    while queue and len(nodes) < max_nodes:
        ptr, depth, via, sibling_index = queue.popleft()
        ptr_key = int(ptr)
        if ptr_key in visited:
            release_com(ptr)
            continue
        visited.add(ptr_key)

        try:
            props = get_props(ptr, include_extended)
            node = {
                "depth": depth,
                "via": via,
                "sibling_index": sibling_index,
                "ptr": hex(ptr_key),
                **props,
            }
            nodes.append(node)

            haystacks = [
                props["name"]["text"] or "",
                props["value"]["text"] or "",
            ]
            if include_extended:
                haystacks.append(props["default_action"]["text"] or "")
            is_match = False
            if target_text and any(target_text in text for text in haystacks):
                is_match = True
            if target_url and any(target_url in text for text in haystacks):
                is_match = True
            if is_match:
                matches.append(node)

            if depth >= max_depth:
                continue

            for child_ptr, child_via, child_index in enumerate_children(ptr, child_limit):
                queue.append((child_ptr, depth + 1, child_via, child_index))
        finally:
            release_com(ptr)

    return nodes, matches


def close_window(hwnd: int):
    user32.PostMessageW(hwnd, 0x0010, 0, 0)
def get_root_accessible(hwnd: int, root_object: str):
    failures = []
    candidates = []
    if root_object == "client":
        candidates = [(OBJID_CLIENT, "OBJID_CLIENT")]
    elif root_object == "window":
        candidates = [(OBJID_WINDOW, "OBJID_WINDOW")]
    else:
        candidates = [(OBJID_CLIENT, "OBJID_CLIENT"), (OBJID_WINDOW, "OBJID_WINDOW")]

    for object_id, label in candidates:
        ptr = ctypes.c_void_p()
        hr = oleacc.AccessibleObjectFromWindow(hwnd, object_id, ctypes.byref(IID_IAccessible), ctypes.byref(ptr))
        if hr >= 0 and ptr.value:
            return ptr.value, hr, label
        failures.append(f"{label}={hr:#x}")
    raise RuntimeError(f"AccessibleObjectFromWindow failed for hwnd={hwnd:#x}: {', '.join(failures)}")


def summarize_accessible_root(hwnd: int):
    summary = {
        "hwnd": hwnd,
        "class": get_class_name(hwnd),
        "title": get_window_text(hwnd),
        "visible": bool(user32.IsWindowVisible(hwnd)),
    }
    for root_object in ("client", "window"):
        try:
            ptr, hr, kind = get_root_accessible(hwnd, root_object)
        except RuntimeError as exc:
            summary[f"{root_object}_root"] = {"error": str(exc)}
            continue
        try:
            summary[f"{root_object}_root"] = {
                "hr": hr,
                "kind": kind,
                **get_props(ptr, False),
            }
        finally:
            release_com(ptr)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Traverse the Edge MSAA tree for a local probe page.")
    parser.add_argument("--link-text", default="ЧИТАТЬ")
    parser.add_argument("--link-url", default="https://browser.example/test-link")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--settle-ms", type=int, default=1500)
    parser.add_argument("--root-object", choices=["auto", "client", "window"], default="auto")
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=400)
    parser.add_argument("--child-limit", type=int, default=64)
    parser.add_argument("--child-window-limit", type=int, default=24)
    parser.add_argument("--target-child-class", default="")
    parser.add_argument("--root-only", action="store_true")
    parser.add_argument("--include-extended", action="store_true")
    args = parser.parse_args()

    if not EDGE.exists():
        raise FileNotFoundError(EDGE)

    coinit_hr = ole32.CoInitialize(None)
    html_path = ensure_html(args.link_text, args.link_url)
    baseline_hwnds = {window["hwnd"] for window in list_visible_windows() if window["class"] == "Chrome_WidgetWin_1"}
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
        window = find_edge_window(proc.pid, args.timeout, baseline_hwnds, "Codex Browser Accessibility Tree Probe")
        if window is None:
            raise RuntimeError("Visible Edge window not found")
        if args.settle_ms > 0:
            time.sleep(args.settle_ms / 1000.0)

        rect = RECT()
        if not user32.GetWindowRect(window["hwnd"], ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())
        child_windows = list_child_windows(window["hwnd"], args.child_window_limit)
        child_window_roots = [summarize_accessible_root(item["hwnd"]) for item in child_windows]
        target_hwnd = window["hwnd"]
        target_window = window
        if args.target_child_class:
            for item in child_windows:
                if item["class"] == args.target_child_class:
                    target_hwnd = item["hwnd"]
                    target_window = item
                    break
            else:
                raise RuntimeError(f"Target child class not found: {args.target_child_class}")

        root_ptr, root_hr, root_kind = get_root_accessible(target_hwnd, args.root_object)
        try:
            if args.root_only:
                nodes = [{
                    "depth": 0,
                    "via": "root",
                    "sibling_index": 0,
                    "ptr": hex(int(root_ptr)),
                    **get_props(root_ptr, args.include_extended),
                }]
                matches = []
            else:
                nodes, matches = traverse_tree(
                    root_ptr,
                    max_depth=args.max_depth,
                    max_nodes=args.max_nodes,
                    child_limit=args.child_limit,
                    target_text=args.link_text,
                    target_url=args.link_url,
                    include_extended=args.include_extended,
                )
        finally:
            if args.root_only:
                release_com(root_ptr)
        result = {
            "edge": str(EDGE),
            "html": str(html_path),
            "coinit_hr": coinit_hr,
            "window": {
                **window,
                "rect": {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom},
            },
            "target_window": target_window,
            "root_hr": root_hr,
            "root_kind": root_kind,
            "node_count": len(nodes),
            "match_count": len(matches),
            "matches": matches,
            "child_window_roots": child_window_roots,
            "first_nodes": nodes[:80],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=5.0)
        ole32.CoUninitialize()
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
