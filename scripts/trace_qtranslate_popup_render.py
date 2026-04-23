from __future__ import annotations

import argparse
import ctypes
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(r"F:\Codex\QTranslate_diss")
CDB_X86 = Path(r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe")
DEFAULT_EXE = ROOT / "release" / "QTranslate_portable_clean" / "QTranslate.exe"
DEFAULT_LOG = ROOT / "tmp_patch" / "qtranslate_popup_render_trace.log"

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

EM_POSFROMCHAR = 0x00D6
EM_SETSEL = 0x00B1
EM_GETCHARFORMAT = 0x043A
WM_SETCURSOR = 0x0020
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
HTCLIENT = 1
MK_LBUTTON = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
CFM_UNDERLINE = 0x00000004
CFE_UNDERLINE = 0x00000004
CFM_LINK = 0x00000020
CFE_LINK = 0x00000020
CFM_HIDDEN = 0x00000100
CFE_HIDDEN = 0x00000100
CFM_COLOR = 0x40000000


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINTL(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class CHARFORMAT2W(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwMask", ctypes.c_uint),
        ("dwEffects", ctypes.c_uint),
        ("yHeight", ctypes.c_long),
        ("yOffset", ctypes.c_long),
        ("crTextColor", ctypes.c_uint),
        ("bCharSet", ctypes.c_ubyte),
        ("bPitchAndFamily", ctypes.c_ubyte),
        ("szFaceName", ctypes.c_wchar * 32),
        ("wWeight", ctypes.c_ushort),
        ("sSpacing", ctypes.c_short),
        ("crBackColor", ctypes.c_uint),
        ("lcid", ctypes.c_uint),
        ("dwReserved", ctypes.c_uint),
        ("sStyle", ctypes.c_short),
        ("wKerning", ctypes.c_ushort),
        ("bUnderlineType", ctypes.c_ubyte),
        ("bAnimation", ctypes.c_ubyte),
        ("bRevAuthor", ctypes.c_ubyte),
        ("bReserved1", ctypes.c_ubyte),
    ]


user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_bool
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.IsWindow.restype = ctypes.c_bool
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = ctypes.c_void_p
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = ctypes.c_bool
user32.mouse_event.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t]
user32.mouse_event.restype = None
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_size_t
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
user32.PostMessageW.restype = ctypes.c_bool
user32.GetDpiForWindow.argtypes = [ctypes.c_void_p]
user32.GetDpiForWindow.restype = ctypes.c_uint
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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=3), encoding="utf-8-sig")


def build_cdb_commands(log_path: Path) -> str:
    # Stack layout, stdcall x86:
    # SendMessageW(hwnd,msg,wParam,lParam): esp+4/+8/+c/+10
    # SetWindowTextW(hwnd,text): esp+4/+8
    # DrawTextW(hdc,text,cch,rect,fmt): esp+4/+8/+c/+10/+14
    # ExtTextOutW(hdc,x,y,opts,rect,text,c,dx): esp+4 ... esp+18/+1c
    return rf"""
.printf "QTranslate popup render trace start\n"
bp QTranslate+0x8924 ".printf \"QT_SET_TEXT entry caller=%p ecx=%p strObj=%p mode=%p text=\", poi(@esp), @ecx, poi(@esp+4), poi(@esp+8); du poi(poi(@esp+4)) L80; gc"
bp QTranslate+0x99F3 ".printf \"QT_REPLACE/APPEND caller=%p ecx=%p a1=%p a2=%p a3=%p\n\", poi(@esp), @ecx, poi(@esp+4), poi(@esp+8), poi(@esp+c); gc"
bp QTranslate+0x1A8000 ".printf \"QTLNK build 2026-04-23 fix13-subclass-stability; WRAPPER enter ret=%p esp=%p ecx=%p strObj=%p mode=%p text=\", poi(@esp), @esp, @ecx, poi(@esp+4), poi(@esp+8); du poi(poi(@esp+4)) L80; gc"
bp QTranslate+0x1A836B ".printf \"QTLNK_SUBCLASS msg=%x hwnd=%p wp=%p lp=%p\n\", poi(@esp+8), poi(@esp+4), poi(@esp+c), poi(@esp+10); gc"
bp QTranslate+0x1A8607 ".printf \"QTLNK_CURSOR_HIT hoverCp=%p readCp=[%p,%p) pt=(%p,%p)\n\", poi(@ebp-30), poi(@ebp-28), poi(@ebp-2c), poi(@ebp-8), poi(@ebp-4); gc"
bp QTranslate+0x1A8726 ".printf \"QTLNK_CHARFROMPOS lp=%p raw=%p cp=%p pt=(%p,%p)\n\", poi(@ebp+14), poi(@ebp-c), poi(@ebp-30), poi(@ebp-8), poi(@ebp-4); gc"
bp QTranslate+0x1A875F ".printf \"QTLNK_GETTEXT len=%p text=\", poi(@ebp-10); du poi(@ebp-14) L120; gc"
bp QTranslate+0x1A88DD ".printf \"QTLNK_MATCH clickCp=%p readCp=[%p,%p) url=\", poi(@ebp-30), poi(@ebp-28), poi(@ebp-2c); du poi(@ebp-34) L80; gc"
bp QTranslate+0x1A88F7 ".printf \"QTLNK_IGNORE_SELECTION cpMin=%p cpMax=%p lp=%p\n\", poi(@ebp-40), poi(@ebp-3c), poi(@ebp+14); gc"
bp QTranslate+0x1A88F9 ".printf \"QTLNK_IGNORE_DRAG delta=%p upLp=%p\n\", @ecx, poi(@ebp+14); gc"
bp QTranslate+0x1A8297 ".printf \"QTLNK_ANCHOR_VISUAL start=%p end=%p sendmsg=%p\n\", poi(@esp+4), poi(@esp+8), poi(@esp+c); gc"
bp QTranslate+0x1A898C ".printf \"QTLNK_APPLY_FORMAT ret=%p hwnd=%p start=%p end=%p mask=%p effects=%p text=\", poi(@esp), @ebx, poi(@esp+4), poi(@esp+8), poi(@esp+c), poi(@esp+10); du (poi(poi(@ebp)-84)+poi(@esp+4)*2) L40; gc"
bu user32!SendMessageW ".if ((poi(@esp+8)==0xc) or (poi(@esp+8)==0x4e) or (poi(@esp+8)==0x201) or (poi(@esp+8)==0x202) or (poi(@esp+8)==0x43b) or (poi(@esp+8)==0x437) or (poi(@esp+8)==0x444) or (poi(@esp+8)==0x445) or (poi(@esp+8)==0x449) or (poi(@esp+8)==0x459) or (poi(@esp+8)==0x45b) or (poi(@esp+8)==0x461)) {{ .printf \"SENDMESSAGE caller=%p hwnd=%p msg=%x wp=%p lp=%p\", poi(@esp), poi(@esp+4), poi(@esp+8), poi(@esp+c), poi(@esp+10); .if (poi(@esp+8)==0xc) {{ .printf \" text=\"; du poi(@esp+10) L80; }} .elsif (poi(@esp+8)==0x4e) {{ .printf \" notifyCode=%x notifyHwnd=%p enMsg=%x cpMin=%x cpMax=%x\\n\", poi(poi(@esp+10)+8), poi(poi(@esp+10)), poi(poi(@esp+10)+c), poi(poi(@esp+10)+18), poi(poi(@esp+10)+1c); }} .elsif (poi(@esp+8)==0x437) {{ .printf \" cpMin=%x cpMax=%x\\n\", poi(poi(@esp+10)), poi(poi(@esp+10)+4); }} .elsif (poi(@esp+8)==0x444) {{ .printf \" cb=%x mask=%x effects=%x\\n\", poi(poi(@esp+10)), poi(poi(@esp+10)+4), poi(poi(@esp+10)+8); }} .else {{ .printf \"\\n\"; }} }}; gc"
bu shell32!ShellExecuteW ".printf \"SHELLEXECUTEW caller=%p hwnd=%p op=\", poi(@esp), poi(@esp+4); du poi(@esp+8) L20; .printf \" file=\"; du poi(@esp+c) L80; gc"
bu shell32!ShellExecuteExW ".printf \"SHELLEXECUTEEXW caller=%p info=%p file=\", poi(@esp), poi(@esp+4); du poi(poi(@esp+4)+10) L80; gc"
bu user32!DispatchMessageW ".if ((poi(poi(@esp+4)+4)==0x20) or (poi(poi(@esp+4)+4)==0x200) or (poi(poi(@esp+4)+4)==0x201) or (poi(poi(@esp+4)+4)==0x202) or (poi(poi(@esp+4)+4)==0x204) or (poi(poi(@esp+4)+4)==0x205)) {{ .printf \"DISPATCHMSG caller=%p hwnd=%p msg=%x wp=%p lp=%p pt=(%x,%x)\\n\", poi(@esp), poi(poi(@esp+4)), poi(poi(@esp+4)+4), poi(poi(@esp+4)+8), poi(poi(@esp+4)+c), poi(poi(@esp+4)+14), poi(poi(@esp+4)+18); }}; gc"
bu user32!SetWindowTextW ".printf \"SETWINDOWTEXT caller=%p hwnd=%p text=\", poi(@esp), poi(@esp+4); du poi(@esp+8) L80; gc"
bu user32!DrawTextW ".if ((poi(@esp+c)>0) and (poi(@esp+c)<1000)) {{ .printf \"DRAWTEXT caller=%p text=\", poi(@esp); du poi(@esp+8) L80; }}; gc"
bu gdi32!ExtTextOutW ".if ((poi(@esp+1c)>0) and (poi(@esp+1c)<1000)) {{ .printf \"EXTTEXTOUT caller=%p cch=%x text=\", poi(@esp), poi(@esp+1c); du poi(@esp+18) L80; }}; gc"
g
""" 


class RemoteMemory:
    def __init__(self, pid: int, size: int):
        access = PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE
        self.process = kernel32.OpenProcess(access, False, pid)
        if not self.process:
            raise ctypes.WinError(ctypes.get_last_error())
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


def text_index_to_cp(text: str, target_index: int) -> int:
    text_index = 0
    cp = 0
    target_index = max(0, min(target_index, len(text)))
    while text_index < target_index:
        if text[text_index] == "\r":
            cp += 1
            text_index += 1
            if text_index < target_index and text[text_index] == "\n":
                text_index += 1
            continue
        cp += 1
        text_index += 1
    return cp


def get_pos_from_char(pid: int, hwnd: int, cp: int) -> POINTL | None:
    with RemoteMemory(pid, ctypes.sizeof(POINTL)) as mem:
        result = user32.SendMessageW(
            ctypes.c_void_p(hwnd),
            EM_POSFROMCHAR,
            ctypes.c_size_t(mem.address),
            ctypes.c_void_p(cp),
        )
        if result in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            return None
        point = POINTL()
        mem.read_into(point)
        return point


def query_char_format(pid: int, hwnd: int, start: int, end: int) -> dict:
    user32.SendMessageW(ctypes.c_void_p(hwnd), EM_SETSEL, start, ctypes.c_void_p(end))
    probe = CHARFORMAT2W()
    probe.cbSize = ctypes.sizeof(CHARFORMAT2W)
    probe.dwMask = CFM_LINK | CFM_HIDDEN | CFM_UNDERLINE | CFM_COLOR
    with RemoteMemory(pid, ctypes.sizeof(probe)) as mem:
        read = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(
            mem.process,
            mem.address,
            ctypes.byref(probe),
            ctypes.sizeof(probe),
            ctypes.byref(read),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        result = user32.SendMessageW(
            ctypes.c_void_p(hwnd),
            EM_GETCHARFORMAT,
            1,
            ctypes.c_void_p(mem.address),
        )
        mem.read_into(probe)
    return {
        "start": start,
        "end": end,
        "getcharformat_return": int(result),
        "cbSize": int(probe.cbSize),
        "mask": int(probe.dwMask),
        "effects": int(probe.dwEffects),
        "color": int(probe.crTextColor),
        "has_link": bool(probe.dwEffects & CFE_LINK),
        "has_hidden": bool(probe.dwEffects & CFE_HIDDEN),
        "has_underline": bool(probe.dwEffects & CFE_UNDERLINE),
    }


def append_format_summary(log_path: Path, lines: list[str]) -> None:
    with log_path.open("a", encoding="utf-8", errors="ignore") as handle:
        for line in lines:
            handle.write(line.rstrip() + "\n")


def inspect_popup_formats(debuggee_pid: int, hwnd: int, text: str, log_path: Path) -> list[str]:
    read_index = text.find("READ")
    if read_index < 0:
        lines = ["FORMAT_SUMMARY no READ anchor found"]
        append_format_summary(log_path, lines)
        return lines
    anchor_start = text_index_to_cp(text, read_index)
    anchor_end = text_index_to_cp(text, read_index + 4)
    close_index = text.find(")", read_index)
    if close_index < 0:
        lines = ["FORMAT_SUMMARY no closing ')' found"]
        append_format_summary(log_path, lines)
        return lines
    suffix_start = anchor_end
    suffix_end = text_index_to_cp(text, close_index + 1)
    full_end = suffix_end
    anchor = query_char_format(debuggee_pid, hwnd, anchor_start, anchor_end)
    suffix = query_char_format(debuggee_pid, hwnd, suffix_start, suffix_end)
    full = query_char_format(debuggee_pid, hwnd, anchor_start, full_end)
    lines = [
        "FORMAT_SUMMARY anchor cp=[{start:08X},{end:08X}) mask={mask:08X} effects={effects:08X} color={color:08X} link={has_link} hidden={has_hidden} underline={has_underline}".format(**anchor),
        "FORMAT_SUMMARY suffix cp=[{start:08X},{end:08X}) mask={mask:08X} effects={effects:08X} color={color:08X} link={has_link} hidden={has_hidden} underline={has_underline}".format(**suffix),
        "FORMAT_SUMMARY full cp=[{start:08X},{end:08X}) mask={mask:08X} effects={effects:08X} color={color:08X} link={has_link} hidden={has_hidden} underline={has_underline}".format(**full),
    ]
    append_format_summary(log_path, lines)
    return lines


def find_popup_richedit(debuggee_pid: int, probe) -> tuple[int, str] | None:
    for window in probe.list_top_windows_for_pid(debuggee_pid):
        if not window.get("visible"):
            continue
        if not str(window.get("class", "")).startswith("ATL:"):
            continue
        for child in probe.list_child_windows(window["hwnd"]):
            if child.get("class") != "RICHEDIT50W" or not child.get("visible"):
                continue
            text = child.get("text", "")
            if "READ" in text:
                return child["hwnd"], text
    return None


def read_last_hook_hwnd(log_path: Path) -> int | None:
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    matches = re.findall(r"QTLNK_APPLY_FORMAT[^\r\n]*hwnd=([0-9a-fA-F]+)", text)
    if not matches:
        matches = re.findall(r"SENDMESSAGE[^\r\n]*caller=005e[0-9a-fA-F]+[^\r\n]*hwnd=([0-9a-fA-F]+)", text)
    if not matches:
        return None
    return int(matches[-1], 16)


def wait_for_hook_hwnd(log_path: Path, timeout: float = 30.0) -> int | None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        current = read_last_hook_hwnd(log_path)
        if current:
            return current
        if current != last:
            last = current
        time.sleep(0.25)
    return None


def find_debuggee_pid(exe: Path, cdb_pid: int, timeout: float = 15.0) -> int | None:
    deadline = time.time() + timeout
    exe_text = str(exe).lower()
    while time.time() < deadline:
        script = (
            "$parent = " + str(cdb_pid) + "; "
            "Get-CimInstance Win32_Process -Filter \"Name='QTranslate.exe'\" | "
            "Where-Object { $_.ParentProcessId -eq $parent -and $_.ExecutablePath -and ($_.ExecutablePath.ToLower() -eq '" + exe_text.replace("'", "''") + "') } | "
            "Sort-Object CreationDate -Descending | "
            "Select-Object -First 1 -ExpandProperty ProcessId"
        )
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", script],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if out:
                return int(out.splitlines()[0])
        except Exception:
            pass
        fallback = (
            "Get-CimInstance Win32_Process -Filter \"Name='QTranslate.exe'\" | "
            "Where-Object { $_.ExecutablePath -and ($_.ExecutablePath.ToLower() -eq '" + exe_text.replace("'", "''") + "') } | "
            "Sort-Object CreationDate -Descending | "
            "Select-Object -First 1 -ExpandProperty ProcessId"
        )
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", fallback],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if out:
                return int(out.splitlines()[0])
        except Exception:
            pass
        time.sleep(0.25)
    return None


def click_first_read(debuggee_pid: int, probe, target_hwnd: int | None = None) -> bool:
    def try_click_control(hwnd: int, text: str) -> bool:
        print(
            "candidate hwnd=0x{hwnd:x} len={length} text={text!r}".format(
                hwnd=hwnd,
                length=len(text),
                text=text[:160],
            ),
            flush=True,
        )
        read_index = text.find("READ")
        if read_index < 0:
            return False
        read_start_cp = text_index_to_cp(text, read_index)
        read_end_cp = text_index_to_cp(text, read_index + 4)
        read_probe_cp = min(read_end_cp - 1, read_start_cp + 1)
        start_pt = get_pos_from_char(debuggee_pid, hwnd, read_start_cp)
        probe_pt = get_pos_from_char(debuggee_pid, hwnd, read_probe_cp)
        if start_pt is None or probe_pt is None:
            print(f"failed to resolve EM_POSFROMCHAR for hwnd=0x{hwnd:x}", flush=True)
            return False
        rect = RECT()
        if not user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
            return False
        client_x = max(2, ((start_pt.x + probe_pt.x) // 2) + 4)
        client_y = max(2, start_pt.y + 10)
        dpi = int(user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) or 96)
        scale = dpi / 96.0
        send_x = max(0, round(client_x / scale))
        send_y = max(0, round(client_y / scale))
        lparam = ((send_y & 0xFFFF) << 16) | (send_x & 0xFFFF)
        print(
            "click_first_read hwnd=0x{hwnd:x} read_index={read_index} read_cp=[{start_cp},{end_cp}) "
            "client=({client_x},{client_y}) dpi={dpi} send=({send_x},{send_y}) lp=0x{lparam:x}".format(
                hwnd=hwnd,
                read_index=read_index,
                start_cp=read_start_cp,
                end_cp=read_end_cp,
                client_x=client_x,
                client_y=client_y,
                dpi=dpi,
                send_x=send_x,
                send_y=send_y,
                lparam=lparam,
            ),
            flush=True,
        )
        user32.PostMessageW(ctypes.c_void_p(hwnd), WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        time.sleep(0.08)
        user32.PostMessageW(ctypes.c_void_p(hwnd), WM_LBUTTONUP, 0, lparam)
        return True

    print(f"click_first_read scan pid={debuggee_pid}", flush=True)
    if target_hwnd and user32.IsWindow(ctypes.c_void_p(target_hwnd)):
        text = probe.get_message_text(target_hwnd)
        print(
            f"hook hwnd=0x{target_hwnd:x} class={probe.get_class_name(target_hwnd)} visible={bool(user32.IsWindowVisible(target_hwnd))}",
            flush=True,
        )
        if text and try_click_control(target_hwnd, text):
            return True
    popup = find_popup_richedit(debuggee_pid, probe)
    if popup:
        hwnd, text = popup
        return try_click_control(hwnd, text)
    print("click_first_read no visible popup RICHEDIT50W containing READ found", flush=True)
    return False


def hover_first_read(debuggee_pid: int, probe, target_hwnd: int | None = None) -> bool:
    def try_hover_control(hwnd: int, text: str) -> bool:
        read_index = text.find("READ")
        if read_index < 0:
            return False
        read_start_cp = text_index_to_cp(text, read_index)
        read_end_cp = text_index_to_cp(text, read_index + 4)
        read_probe_cp = min(read_end_cp - 1, read_start_cp + 1)
        start_pt = get_pos_from_char(debuggee_pid, hwnd, read_start_cp)
        probe_pt = get_pos_from_char(debuggee_pid, hwnd, read_probe_cp)
        if start_pt is None or probe_pt is None:
            print(f"failed to resolve hover EM_POSFROMCHAR for hwnd=0x{hwnd:x}", flush=True)
            return False
        rect = RECT()
        if not user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
            return False
        client_x = max(2, ((start_pt.x + probe_pt.x) // 2) + 4)
        client_y = max(2, start_pt.y + 10)
        dpi = int(user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) or 96)
        scale = dpi / 96.0
        send_x = max(0, round(client_x / scale))
        send_y = max(0, round(client_y / scale))
        screen_x = rect.left + send_x
        screen_y = rect.top + send_y
        setcursor_lparam = ((WM_MOUSEMOVE & 0xFFFF) << 16) | HTCLIENT
        mouse_lparam = ((send_y & 0xFFFF) << 16) | (send_x & 0xFFFF)
        print(
            "hover_first_read hwnd=0x{hwnd:x} read_index={read_index} read_cp=[{start_cp},{end_cp}) "
            "client=({client_x},{client_y}) dpi={dpi} screen=({screen_x},{screen_y}) "
            "setcursor_lp=0x{setcursor_lparam:x}".format(
                hwnd=hwnd,
                read_index=read_index,
                start_cp=read_start_cp,
                end_cp=read_end_cp,
                client_x=client_x,
                client_y=client_y,
                dpi=dpi,
                screen_x=screen_x,
                screen_y=screen_y,
                setcursor_lparam=setcursor_lparam,
            ),
            flush=True,
        )
        user32.SetCursorPos(screen_x, screen_y)
        time.sleep(0.15)
        user32.PostMessageW(ctypes.c_void_p(hwnd), WM_SETCURSOR, hwnd, setcursor_lparam)
        user32.PostMessageW(ctypes.c_void_p(hwnd), WM_MOUSEMOVE, 0, mouse_lparam)
        return True

    print(f"hover_first_read scan pid={debuggee_pid}", flush=True)
    if target_hwnd and user32.IsWindow(ctypes.c_void_p(target_hwnd)):
        text = probe.get_message_text(target_hwnd)
        print(
            f"hover hook hwnd=0x{target_hwnd:x} class={probe.get_class_name(target_hwnd)} visible={bool(user32.IsWindowVisible(target_hwnd))}",
            flush=True,
        )
        if text and try_hover_control(target_hwnd, text):
            return True
    popup = find_popup_richedit(debuggee_pid, probe)
    if popup:
        hwnd, text = popup
        return try_hover_control(hwnd, text)
    print("hover_first_read no visible popup RICHEDIT50W containing READ found", flush=True)
    return False


def kill_existing_instances(exe: Path) -> None:
    exe_text = str(exe).lower().replace("'", "''")
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='QTranslate.exe'\" | "
        "Where-Object { $_.ExecutablePath -and ($_.ExecutablePath.ToLower() -eq '" + exe_text + "') } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace QTranslate popup text render/write path with cdb.")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--seconds", type=float, default=45.0)
    parser.add_argument(
        "--clipboard-text",
        default="FreeTranslations nutzt translate-pa.googleapis.com READ (https://www.perplexity.ai/search/example) und bietet ...",
    )
    parser.add_argument("--clipboard-html-fragment")
    parser.add_argument("--no-hotkey", action="store_true")
    parser.add_argument("--hover-read", action="store_true")
    parser.add_argument("--click-read", action="store_true")
    parser.add_argument("--skip-format-inspect", action="store_true")
    args = parser.parse_args()

    if not CDB_X86.exists():
        print(f"cdb not found: {CDB_X86}", file=sys.stderr)
        return 1

    exe = args.exe.resolve()
    root = exe.parent
    options_path = root / "Data" / "Options.json"
    history_path = root / "Data" / "History.json"
    kill_existing_instances(exe)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    if args.log.exists():
        args.log.unlink()

    # Reuse the existing probe helper for clipboard/hotkey routines.
    sys.path.insert(0, str(ROOT))
    from scripts import probe_qtranslate_capture as probe  # noqa: PLC0415

    options_backup = options_path.read_bytes()
    history_backup = history_path.read_bytes() if history_path.exists() else b"[]"
    proc: subprocess.Popen | None = None
    cmd_file = None
    format_summaries: list[str] = []
    try:
        options = load_json(options_path)
        options["HotKeys"]["EnableHotKeys"] = True
        options["HotKeys"]["HotKeyTranslateClipboardInPopupWindow"] = 852
        options["HotKeys"]["HotKeyTranslateClipboardInMainWindow"] = 0
        options["Appearance"]["PopupTimeout"] = 30
        dump_json(options_path, options)
        history_path.write_text("[]", encoding="utf-8")
        probe.set_clipboard_text_and_html(args.clipboard_text, args.clipboard_html_fragment)

        with tempfile.NamedTemporaryFile("w", suffix=".cdb", delete=False, encoding="utf-8") as f:
            cmd_file = Path(f.name)
            f.write(build_cdb_commands(args.log))

        proc = subprocess.Popen(
            [str(CDB_X86), "-logo", str(args.log), "-cf", str(cmd_file), str(exe)],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if not args.no_hotkey:
            debuggee_pid = find_debuggee_pid(exe, proc.pid)
            deadline = time.time() + 15.0
            app = None
            while time.time() < deadline:
                if debuggee_pid is None:
                    debuggee_pid = find_debuggee_pid(exe, proc.pid, timeout=0.25)
                if debuggee_pid is None:
                    time.sleep(0.25)
                    continue
                for window in probe.list_top_windows_for_pid(debuggee_pid):
                    if window["class"] == "QTranslate_ApplicationWindow":
                        app = window
                        break
                if app:
                    break
                time.sleep(0.25)
            time.sleep(2.0)
            for _ in range(3):
                if app:
                    probe.post_hotkey(app["hwnd"], 852)
                probe.trigger_hotkey_via_sendkeys()
                time.sleep(1.0)
            if debuggee_pid is not None and not args.skip_format_inspect:
                popup = find_popup_richedit(debuggee_pid, probe)
                if popup:
                    format_summaries.extend(inspect_popup_formats(debuggee_pid, popup[0], popup[1], args.log))
            if (args.hover_read or args.click_read) and debuggee_pid is not None:
                target_hwnd = wait_for_hook_hwnd(args.log, timeout=30.0)
                if target_hwnd:
                    print(f"last hook hwnd from log=0x{target_hwnd:x}", flush=True)
                    time.sleep(1.0)
                    text = probe.get_message_text(target_hwnd)
                    if text and not args.skip_format_inspect:
                        format_summaries.extend(inspect_popup_formats(debuggee_pid, target_hwnd, text, args.log))
                else:
                    print("no hook hwnd appeared before pointer attempt", flush=True)
                if args.hover_read:
                    hover_first_read(debuggee_pid, probe, target_hwnd)
                    time.sleep(1.0)
            if args.click_read and debuggee_pid is not None:
                target_hwnd = wait_for_hook_hwnd(args.log, timeout=1.0)
                click_first_read(debuggee_pid, probe, target_hwnd)
                time.sleep(3.0)

        time.sleep(args.seconds)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        options_path.write_bytes(options_backup)
        history_path.write_bytes(history_backup)
        if cmd_file is not None:
            try:
                cmd_file.unlink()
            except OSError:
                pass
        if format_summaries:
            append_format_summary(args.log, ["FORMAT_SUMMARY final replay:"] + format_summaries)

    print(args.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
