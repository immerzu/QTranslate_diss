from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(r"F:\Codex\QTranslate_diss")
EXE = ROOT / "QTranslate.6.9.0" / "QTranslate.exe"
ASM = ROOT / "asm" / "read_html_or_unicode_clipboard.s"

CLANG = Path(r"C:\Program Files\LLVM\bin\clang.exe")
FUNC_CLIP_VA = 0x0043BE7E
CALL_ACC_MAIN_VA = 0x0040531D
CAVE_VA = 0x0053D0A3

EXPECTED_PROLOGUE_CLIP = bytes.fromhex("55 8B EC 51 51 53 8B C1 57")
EXPECTED_CALL_ACC_MAIN = bytes.fromhex("E8 DF F5 FF FF")


def u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def parse_pe(buf: bytes):
    pe = u32(buf, 0x3C)
    num_sections = u16(buf, pe + 6)
    opt_size = u16(buf, pe + 20)
    opt = pe + 24
    image_base = u32(buf, opt + 28)
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
        sections.append((name, vaddr, vsize, raw_ptr, raw_size, off))
    return image_base, file_alignment, sections


def va_to_off(image_base: int, sections, va: int) -> int:
    rva = va - image_base
    for name, vaddr, vsize, raw_ptr, raw_size, _hdr_off in sections:
        span = max(vsize, raw_size)
        if vaddr <= rva < vaddr + span:
            return raw_ptr + (rva - vaddr)
    raise ValueError(hex(va))


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
        tmp = Path(tmpdir)
        obj = tmp / "stub.obj"
        subprocess.run(
            [str(CLANG), "-c", "-m32", str(ASM), "-o", str(obj)],
            check=True,
        )
        buf = obj.read_bytes()
        symbols = parse_coff_symbols(buf)
        # COFF file header
        num_sections = u16(buf, 2)
        sec_table = 20
        for i in range(num_sections):
            off = sec_table + i * 40
            name = buf[off : off + 8].split(b"\0", 1)[0].decode("ascii")
            size = u32(buf, off + 16)
            ptr = u32(buf, off + 20)
            if name == ".text":
                return buf[ptr : ptr + size], symbols
        raise RuntimeError("No .text section found in assembled stub object.")


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def rel32_target(site_va: int, encoded: bytes) -> int:
    return site_va + 5 + struct.unpack_from("<i", encoded, 1)[0]


def resolve_acc_symbol(symbols: dict[str, int], variant: str) -> str:
    mapping = {
        "experimental": "accessibility_shellcode_start",
        "delegate": "accessibility_shellcode_delegate_start",
        "name-only": "accessibility_shellcode_name_only_start",
        "noop": "accessibility_shellcode_noop_start",
        "uia-point": "accessibility_shellcode_uia_point_start",
    }
    try:
        symbol = mapping[variant]
    except KeyError as exc:
        raise RuntimeError(f"Unknown accessibility variant: {variant}") from exc
    if symbol not in symbols:
        raise RuntimeError(f"Assembler output is missing symbol: {symbol}")
    return symbol


def patch_binary(src: Path, dst: Path, *, with_accessibility_main: bool = False, accessibility_variant: str = "uia-point") -> None:
    data = bytearray(src.read_bytes())
    pe = u32(data, 0x3C)
    opt = pe + 24
    image_base, file_alignment, sections = parse_pe(data)
    clip_off = va_to_off(image_base, sections, FUNC_CLIP_VA)
    acc_main_off = va_to_off(image_base, sections, CALL_ACC_MAIN_VA)
    cave_off = va_to_off(image_base, sections, CAVE_VA)

    clip_bytes = bytes(data[clip_off : clip_off + len(EXPECTED_PROLOGUE_CLIP)])
    clip_is_original = clip_bytes == EXPECTED_PROLOGUE_CLIP
    clip_is_patched = clip_bytes[:1] == b"\xE9" and CAVE_VA <= rel32_target(FUNC_CLIP_VA, clip_bytes[:5]) < CAVE_VA + 0x10000
    if not (clip_is_original or clip_is_patched):
        raise RuntimeError("Unexpected bytes at 0x43BE7E; binary does not match the analyzed build.")

    acc_bytes = bytes(data[acc_main_off : acc_main_off + len(EXPECTED_CALL_ACC_MAIN)])
    acc_is_original = acc_bytes == EXPECTED_CALL_ACC_MAIN
    acc_is_patched = acc_bytes[:1] == b"\xE8" and CAVE_VA <= rel32_target(CALL_ACC_MAIN_VA, acc_bytes[:5]) < CAVE_VA + 0x10000
    if with_accessibility_main and not (acc_is_original or acc_is_patched):
        raise RuntimeError("Unexpected call bytes at 0x40531D; binary does not match the analyzed build.")

    shellcode, symbols = build_shellcode()
    if "shellcode_start" not in symbols:
        raise RuntimeError("Assembler output is missing required entry symbol: shellcode_start.")
    text = next(section for section in sections if section[0] == ".text")
    text_name, text_vaddr, text_vsize, text_raw_ptr, text_raw_size, text_hdr = text
    text_raw_end = text_raw_ptr + text_raw_size
    needed_raw_end = cave_off + len(shellcode)

    if needed_raw_end > text_raw_end:
        growth = align_up(needed_raw_end - text_raw_end, file_alignment)
        data[text_raw_end:text_raw_end] = b"\x00" * growth

        # Shift subsequent section raw pointers in the PE headers.
        for name, vaddr, vsize, raw_ptr, raw_size, hdr_off in sections:
            if raw_ptr > text_raw_ptr:
                struct.pack_into("<I", data, hdr_off + 20, raw_ptr + growth)

        text_raw_size += growth
        struct.pack_into("<I", data, text_hdr + 16, text_raw_size)
        struct.pack_into("<I", data, opt + 4, text_raw_size)

        # Recompute section info after insertion so later VA->file calculations stay honest.
        image_base, file_alignment, sections = parse_pe(data)
        clip_off = va_to_off(image_base, sections, FUNC_CLIP_VA)
        acc_main_off = va_to_off(image_base, sections, CALL_ACC_MAIN_VA)
        cave_off = va_to_off(image_base, sections, CAVE_VA)
        text = next(section for section in sections if section[0] == ".text")
        text_name, text_vaddr, text_vsize, text_raw_ptr, text_raw_size, text_hdr = text

    cave_rva = CAVE_VA - image_base
    needed_vsize = (cave_rva - text_vaddr) + len(shellcode)
    if needed_vsize > text_vsize:
        struct.pack_into("<I", data, text_hdr + 8, needed_vsize)
    struct.pack_into("<I", data, opt + 4, text_raw_size)

    data[cave_off : cave_off + len(shellcode)] = shellcode

    clip_target_va = CAVE_VA + symbols["shellcode_start"]
    clip_rel = clip_target_va - (FUNC_CLIP_VA + 5)
    clip_jmp = b"\xE9" + struct.pack("<i", clip_rel)
    data[clip_off : clip_off + 5] = clip_jmp
    data[clip_off + 5 : clip_off + len(EXPECTED_PROLOGUE_CLIP)] = b"\x90" * (len(EXPECTED_PROLOGUE_CLIP) - 5)

    if with_accessibility_main:
        acc_target_va = CAVE_VA + symbols[resolve_acc_symbol(symbols, accessibility_variant)]
        acc_rel = acc_target_va - (CALL_ACC_MAIN_VA + 5)
        acc_call = b"\xE8" + struct.pack("<i", acc_rel)
        data[acc_main_off : acc_main_off + 5] = acc_call

    dst.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch QTranslate.exe to keep link URLs in clipboard and accessibility capture paths.")
    parser.add_argument(
        "--input",
        type=Path,
        default=EXE,
        help="Source executable. Default: the unpacked QTranslate.exe in this workspace.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination executable. Default: QTranslate.patched.exe, or QTranslate.accessibility.default_uia.exe when accessibility patching is enabled.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Patch the input file in place. A .bak backup is created first.",
    )
    parser.add_argument(
        "--with-accessibility-main",
        action="store_true",
        help="Also patch TaskShowMainWindow(mode=2) to use the accessibility helper.",
    )
    parser.add_argument(
        "--accessibility-variant",
        choices=["experimental", "delegate", "name-only", "noop", "uia-point"],
        default="uia-point",
        help="Which accessibility helper to route TaskShowMainWindow(mode=2) to when accessibility patching is enabled.",
    )
    args = parser.parse_args()

    src = args.input
    if not src.exists():
        print(f"Input file not found: {src}", file=sys.stderr)
        return 1

    if args.in_place:
        backup = src.with_suffix(src.suffix + ".bak")
        if not backup.exists():
            shutil.copy2(src, backup)
        dst = src
    else:
        if args.output is not None:
            dst = args.output
        elif args.with_accessibility_main:
            dst = ROOT / "QTranslate.6.9.0" / "QTranslate.accessibility.default_uia.exe"
        else:
            dst = ROOT / "QTranslate.6.9.0" / "QTranslate.patched.exe"

    patch_binary(
        src,
        dst,
        with_accessibility_main=args.with_accessibility_main,
        accessibility_variant=args.accessibility_variant,
    )
    print(f"Patched file written to: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
