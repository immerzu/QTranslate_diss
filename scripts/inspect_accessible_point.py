import argparse
import ctypes
import json
import time
import uuid

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
oleacc = ctypes.OleDLL("oleacc")
oleaut32 = ctypes.OleDLL("oleaut32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_TABSTOP = 0x00010000
ICC_LINK_CLASS = 0x00008000


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

oleacc.AccessibleObjectFromPoint.argtypes = [POINT, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(VARIANT)]
oleacc.AccessibleObjectFromPoint.restype = ctypes.c_long
oleaut32.SysStringLen.argtypes = [ctypes.c_void_p]
oleaut32.SysStringLen.restype = ctypes.c_uint
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
oleaut32.SysFreeString.restype = None


@WNDPROC
def wndproc(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def bstr_to_text(bstr: int | None) -> str | None:
    if not bstr:
        return None
    length = oleaut32.SysStringLen(bstr)
    if length == 0:
        return ""
    return ctypes.wstring_at(bstr, length)


def release_com(ptr: int) -> None:
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


def create_link_host(link_markup: str):
    icc = INITCOMMONCONTROLSEX(ctypes.sizeof(INITCOMMONCONTROLSEX), ICC_LINK_CLASS)
    comctl32.InitCommonControlsEx(ctypes.byref(icc))

    class_name = f"CodexInspectHost_{uuid.uuid4().hex[:8]}"
    wc = WNDCLASSW()
    wc.lpfnWndProc = wndproc
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.lpszClassName = class_name
    if not user32.RegisterClassW(ctypes.byref(wc)):
        raise ctypes.WinError(ctypes.get_last_error())

    hwnd = user32.CreateWindowExW(
        0,
        class_name,
        "Codex Inspect Host",
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


def inspect_current_point(point: POINT):
    acc_ptr = ctypes.c_void_p()
    child = VARIANT()
    hr = oleacc.AccessibleObjectFromPoint(point, ctypes.byref(acc_ptr), ctypes.byref(child))
    result = {
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


def main():
    parser = argparse.ArgumentParser(description="Inspect AccessibleObjectFromPoint under a local SysLink host.")
    parser.add_argument("--url", default="https://accessibility.example/test-link")
    parser.add_argument("--text", default="ЧИТАТЬ")
    args = parser.parse_args()

    host_hwnd = None
    try:
        host_hwnd, child_hwnd = create_link_host(f'<a href="{args.url}">{args.text}</a>')
        rect = RECT()
        if not user32.GetWindowRect(child_hwnd, ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())
        point = POINT((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        user32.SetForegroundWindow(host_hwnd)
        time.sleep(0.2)
        user32.SetCursorPos(point.x, point.y)
        time.sleep(0.2)
        result = {
            "point": {"x": point.x, "y": point.y},
            "inspection": inspect_current_point(point),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if host_hwnd:
            user32.DestroyWindow(host_hwnd)


if __name__ == "__main__":
    main()
