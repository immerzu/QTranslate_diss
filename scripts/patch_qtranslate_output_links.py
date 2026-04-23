from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(r"F:\Codex\QTranslate_diss")
DEFAULT_INPUT = ROOT / "QTranslate.6.9.0" / "QTranslate.accessibility.default_uia.exe"
DEFAULT_OUTPUT = ROOT / "QTranslate.6.9.0" / "QTranslate.output_links.exe"
ASM = ROOT / "asm" / "format_output_links.s"
CLANG = Path(r"C:\Program Files\LLVM\bin\clang.exe")

ORIG_RICHEDIT_SET_TEXT_VA = 0x00408924
RICHTEXT_MODE_PATCH_VA = 0x00408C27
AUTOURL_DETECT_PATCH_VA = 0x00408C51
POSTPROCESS_HOOK_VA = 0x0042EE5C
FINAL_RESULT_HOOK_VA = 0x0042EF8F
POPUP_RENDER_RICHEDIT_SETTEXT_CALLSITE_VA = 0x00438D53
EXPECTED_PLAINTEXT_PUSH = bytes.fromhex("6A 01")
PATCH_RICHTEXT_PUSH = bytes.fromhex("6A 02")
EXPECTED_AUTOURL_ENABLE_PUSH = bytes.fromhex("6A 01")
PATCH_AUTOURL_DISABLE_PUSH = bytes.fromhex("6A 01")
EXPECTED_POSTPROCESS_HOOK = bytes.fromhex("FF 0D AC 41 58 00")
EXPECTED_FINAL_RESULT_HOOK = bytes.fromhex("FF 0D AC 41 58 00")
DEFAULT_CALLSITE_WHITELIST = {
    # Proven by cdb trace on the real popup hotkey path:
    #   module base 0x00540000
    #   QT_SET_TEXT caller 0x00578D58 -> preferred return 0x00438D58
    #   callsite 0x00438D53 writes the final visible popup result text into the
    #   RichEdit wrapper at object+0x54. After this, msftedit draws the URL via
    #   ExtTextOutW, so formatting must be applied here.
    POPUP_RENDER_RICHEDIT_SETTEXT_CALLSITE_VA,
}


def u16(buf: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def u32(buf: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def parse_pe(buf: bytes | bytearray):
    pe = u32(buf, 0x3C)
    num_sections = u16(buf, pe + 6)
    opt_size = u16(buf, pe + 20)
    opt = pe + 24
    image_base = u32(buf, opt + 28)
    section_alignment = u32(buf, opt + 32)
    file_alignment = u32(buf, opt + 36)
    sec = opt + opt_size
    sections = []
    for i in range(num_sections):
        off = sec + i * 40
        name = buf[off : off + 8].split(b"\0", 1)[0].decode("ascii")
        vsize = u32(buf, off + 8)
        vaddr = u32(buf, off + 12)
        raw_size = u32(buf, off + 16)
        raw_ptr = u32(buf, off + 20)
        chars = u32(buf, off + 36)
        sections.append(
            {
                "name": name,
                "vaddr": vaddr,
                "vsize": vsize,
                "raw_size": raw_size,
                "raw_ptr": raw_ptr,
                "hdr_off": off,
                "chars": chars,
            }
        )
    return {
        "pe": pe,
        "opt": opt,
        "sec_table": sec,
        "num_sections": num_sections,
        "image_base": image_base,
        "section_alignment": section_alignment,
        "file_alignment": file_alignment,
        "sections": sections,
    }


def va_to_off(image_base: int, sections, va: int) -> int:
    rva = va - image_base
    for section in sections:
        span = max(section["vsize"], section["raw_size"])
        if section["vaddr"] <= rva < section["vaddr"] + span:
            return section["raw_ptr"] + (rva - section["vaddr"])
    raise ValueError(hex(va))


def find_callers(buf: bytes | bytearray, pe_info, target_va: int) -> list[int]:
    text = next(section for section in pe_info["sections"] if section["name"] == ".text")
    text_off = text["raw_ptr"]
    text_size = text["raw_size"]
    text_va = pe_info["image_base"] + text["vaddr"]
    text_bytes = buf[text_off : text_off + text_size]
    callers = []
    for i in range(len(text_bytes) - 5):
        if text_bytes[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", text_bytes, i + 1)[0]
        dest = (text_va + i + 5 + rel) & 0xFFFFFFFF
        if dest == target_va:
            callers.append(text_va + i)
    return callers


def parse_coff_symbols(buf: bytes) -> dict[str, int]:
    ptr_symtab = u32(buf, 8)
    num_symbols = u32(buf, 12)
    if ptr_symtab == 0 or num_symbols == 0:
        return {}
    string_table_off = ptr_symtab + num_symbols * 18
    string_table_size = u32(buf, string_table_off)
    string_table = buf[string_table_off : string_table_off + string_table_size]

    def read_symbol_name(raw: bytes) -> str:
        if raw[:4] == b"\x00\x00\x00\x00":
            off = struct.unpack_from("<I", raw, 4)[0]
            end = string_table.index(0, off)
            return string_table[off:end].decode("ascii")
        return raw.split(b"\0", 1)[0].decode("ascii")

    symbols: dict[str, int] = {}
    idx = 0
    while idx < num_symbols:
        off = ptr_symtab + idx * 18
        raw_name = buf[off : off + 8]
        value = u32(buf, off + 8)
        section_number = struct.unpack_from("<h", buf, off + 12)[0]
        storage_class = buf[off + 16]
        aux_count = buf[off + 17]
        if section_number > 0 and storage_class in (2, 3):
            symbols[read_symbol_name(raw_name)] = value
        idx += 1 + aux_count
    return symbols


def build_shellcode() -> tuple[bytes, dict[str, int]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        obj = Path(tmpdir) / "format_output_links.obj"
        subprocess.run([str(CLANG), "-c", "-m32", str(ASM), "-o", str(obj)], check=True)
        buf = obj.read_bytes()
        symbols = parse_coff_symbols(buf)
        num_sections = u16(buf, 2)
        sec_table = 20
        for i in range(num_sections):
            off = sec_table + i * 40
            name = buf[off : off + 8].split(b"\0", 1)[0].decode("ascii")
            raw_size = u32(buf, off + 16)
            raw_ptr = u32(buf, off + 20)
            reloc_count = u16(buf, off + 32)
            if name == ".text":
                if reloc_count:
                    raise RuntimeError("Output-link shellcode must not contain relocations.")
                return buf[raw_ptr : raw_ptr + raw_size], symbols
        raise RuntimeError("No .text section found in output-link shellcode object.")


def add_executable_section(data: bytearray, name: bytes, payload: bytes) -> tuple[int, int]:
    pe_info = parse_pe(data)
    last = pe_info["sections"][-1]
    new_header_off = pe_info["sec_table"] + pe_info["num_sections"] * 40
    first_raw = min(section["raw_ptr"] for section in pe_info["sections"] if section["raw_ptr"])
    if new_header_off + 40 > first_raw:
        raise RuntimeError("No room for an additional section header.")

    raw_ptr = align_up(len(data), pe_info["file_alignment"])
    raw_size = align_up(len(payload), pe_info["file_alignment"])
    vaddr = align_up(last["vaddr"] + max(last["vsize"], last["raw_size"]), pe_info["section_alignment"])
    vsize = len(payload)

    if len(data) < raw_ptr:
        data.extend(b"\x00" * (raw_ptr - len(data)))
    data.extend(payload)
    data.extend(b"\x00" * (raw_size - len(payload)))

    name = name[:8].ljust(8, b"\x00")
    data[new_header_off : new_header_off + 8] = name
    struct.pack_into("<I", data, new_header_off + 8, vsize)
    struct.pack_into("<I", data, new_header_off + 12, vaddr)
    struct.pack_into("<I", data, new_header_off + 16, raw_size)
    struct.pack_into("<I", data, new_header_off + 20, raw_ptr)
    struct.pack_into("<I", data, new_header_off + 24, 0)
    struct.pack_into("<I", data, new_header_off + 28, 0)
    struct.pack_into("<H", data, new_header_off + 32, 0)
    struct.pack_into("<H", data, new_header_off + 34, 0)
    # The output-link hook stores the RichEdit subclass procedure and a few
    # per-process HWND/proc pointers in this section, so it must be writable.
    struct.pack_into("<I", data, new_header_off + 36, 0xE0000020)

    struct.pack_into("<H", data, pe_info["pe"] + 6, pe_info["num_sections"] + 1)
    size_image = align_up(vaddr + vsize, pe_info["section_alignment"])
    struct.pack_into("<I", data, pe_info["opt"] + 56, size_image)
    return pe_info["image_base"] + vaddr, raw_ptr


def patch_binary(
    src: Path,
    dst: Path,
    *,
    patch_set_text_callers: bool = True,
    patch_all_callers: bool = False,
) -> dict:
    data = bytearray(src.read_bytes())
    pe_info = parse_pe(data)

    richtext_off = va_to_off(pe_info["image_base"], pe_info["sections"], RICHTEXT_MODE_PATCH_VA)
    old_rich = bytes(data[richtext_off : richtext_off + 2])
    if old_rich not in (EXPECTED_PLAINTEXT_PUSH, PATCH_RICHTEXT_PUSH):
        raise RuntimeError(f"Unexpected bytes at richtext mode patch site: {old_rich.hex(' ')}")
    data[richtext_off : richtext_off + 2] = PATCH_RICHTEXT_PUSH

    autourl_off = va_to_off(pe_info["image_base"], pe_info["sections"], AUTOURL_DETECT_PATCH_VA)
    old_autourl = bytes(data[autourl_off : autourl_off + 2])
    if old_autourl not in (EXPECTED_AUTOURL_ENABLE_PUSH, PATCH_AUTOURL_DISABLE_PUSH):
        raise RuntimeError(f"Unexpected bytes at auto-url patch site: {old_autourl.hex(' ')}")
    data[autourl_off : autourl_off + 2] = PATCH_AUTOURL_DISABLE_PUSH

    shellcode, symbols = build_shellcode()
    required_symbols = {
        "output_link_wrapper_start",
        "output_link_postprocess_start",
        "output_link_final_result_start",
    }
    if not required_symbols.issubset(symbols):
        raise RuntimeError("Shellcode object is missing required output-link symbols.")
    section_va, _raw_ptr = add_executable_section(data, b".qtlnk", shellcode)
    wrapper_va = section_va + symbols["output_link_wrapper_start"]
    postprocess_va = section_va + symbols["output_link_postprocess_start"]
    final_result_va = section_va + symbols["output_link_final_result_start"]

    pe_info = parse_pe(data)

    patched_callers = []
    if patch_set_text_callers:
        callers = find_callers(data, pe_info, ORIG_RICHEDIT_SET_TEXT_VA)
        if not callers:
            raise RuntimeError("No RichEdit set-text callers found.")
        if not patch_all_callers:
            callers = [va for va in callers if va in DEFAULT_CALLSITE_WHITELIST]
            missing = sorted(DEFAULT_CALLSITE_WHITELIST.difference(callers))
            if missing:
                raise RuntimeError(f"Missing expected output callsites: {[hex(va) for va in missing]}")

        for caller_va in callers:
            off = va_to_off(pe_info["image_base"], pe_info["sections"], caller_va)
            if data[off] != 0xE8:
                raise RuntimeError(f"Expected call at {caller_va:#x}")
            rel = wrapper_va - (caller_va + 5)
            data[off : off + 5] = b"\xE8" + struct.pack("<i", rel)
            patched_callers.append(caller_va)

    dst.write_bytes(data)
    result = {
        "output": str(dst),
        "wrapper_va": f"0x{wrapper_va:08X}",
        "postprocess_va": f"0x{postprocess_va:08X}",
        "final_result_va": f"0x{final_result_va:08X}",
        "patched_richtext_mode_va": f"0x{RICHTEXT_MODE_PATCH_VA:08X}",
        "patched_autourl_detect_va": f"0x{AUTOURL_DETECT_PATCH_VA:08X}",
        "patched_postprocess_hook_va": None,
        "patched_final_result_hook_va": None,
        "patched_callers": [f"0x{va:08X}" for va in patched_callers],
        "shellcode_size": len(shellcode),
    }
    optional_symbols = {
        "richedit_proc_va": "output_link_richedit_proc",
        "mouseup_charfrompos_va": "output_link_mouseup_charfrompos_done",
        "mouseup_gettext_va": "output_link_mouseup_gettext_done",
        "mouseup_match_ready_va": "output_link_mouseup_match_ready",
        "anchor_visual_va": "output_link_anchor_visual_start",
        "cursor_hit_va": "output_link_cursor_hit",
        "click_ignore_selection_va": "output_link_click_ignore_selection",
        "click_ignore_drag_va": "output_link_click_ignore_drag",
        "click_open_va": "output_link_click_open",
        "apply_format_va": ".Lapply_format",
    }
    for key, symbol in optional_symbols.items():
        if symbol in symbols:
            result[key] = f"0x{section_va + symbols[symbol]:08X}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch QTranslate.exe output RichEdit path to allow hidden URL link rendering."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument(
        "--skip-set-text-callers",
        action="store_true",
        help="Do not patch the selected popup RichEdit set-text callsite.",
    )
    parser.add_argument(
        "--patch-all-callers",
        action="store_true",
        help="Patch every call to the RichEdit set-text helper. Default patches only the main translation result callsites.",
    )
    args = parser.parse_args()

    src = args.input
    if not src.exists():
        print(f"Input file not found: {src}", file=sys.stderr)
        return 1

    dst = src if args.in_place else args.output
    if args.in_place:
        backup = src.with_suffix(src.suffix + ".output-links.bak")
        if not backup.exists():
            shutil.copy2(src, backup)

    result = patch_binary(
        src,
        dst,
        patch_set_text_callers=not args.skip_set_text_callers,
        patch_all_callers=args.patch_all_callers,
    )
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
