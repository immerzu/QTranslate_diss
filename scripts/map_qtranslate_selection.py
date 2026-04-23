from __future__ import annotations

import struct
from pathlib import Path


EXE = Path(r"F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.exe")


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
    sec = opt + opt_size
    sections = []
    for i in range(num_sections):
        off = sec + i * 40
        name = buf[off : off + 8].split(b"\0", 1)[0].decode("ascii")
        vsize = u32(buf, off + 8)
        vaddr = u32(buf, off + 12)
        raw_size = u32(buf, off + 16)
        raw_ptr = u32(buf, off + 20)
        sections.append((name, vaddr, vsize, raw_ptr, raw_size))
    return image_base, sections


def va_to_off(image_base: int, sections, va: int) -> int:
    rva = va - image_base
    for name, vaddr, vsize, raw_ptr, raw_size in sections:
        span = max(vsize, raw_size)
        if vaddr <= rva < vaddr + span:
            return raw_ptr + (rva - vaddr)
    raise ValueError(hex(va))


def read_c_string(buf: bytes, off: int) -> str:
    end = buf.index(0, off)
    return buf[off:end].decode("ascii", "ignore")


def parse_imports(buf: bytes, image_base: int, sections):
    pe = u32(buf, 0x3C)
    opt = pe + 24
    import_rva = u32(buf, opt + 104)
    imp_off = va_to_off(image_base, sections, image_base + import_rva)
    imports = {}
    idx = 0
    while True:
        oft = u32(buf, imp_off + idx * 20)
        name_rva = u32(buf, imp_off + idx * 20 + 12)
        ft = u32(buf, imp_off + idx * 20 + 16)
        if oft == 0 and name_rva == 0 and ft == 0:
            break
        dll = read_c_string(buf, va_to_off(image_base, sections, image_base + name_rva))
        thunk_rva = oft or ft
        t = 0
        while True:
            val = u32(buf, va_to_off(image_base, sections, image_base + thunk_rva + t * 4))
            if val == 0:
                break
            if val & 0x80000000:
                name = f"ORDINAL_{val & 0xFFFF}"
            else:
                name = read_c_string(buf, va_to_off(image_base, sections, image_base + val) + 2)
            imports[image_base + ft + t * 4] = f"{dll}!{name}"
            t += 1
        idx += 1
    return imports


def find_callers(buf: bytes, image_base: int, sections, target: int):
    text = next(s for s in sections if s[0] == ".text")
    text_off = text[3]
    text_size = text[4]
    text_va = image_base + text[1]
    text_bytes = buf[text_off : text_off + text_size]
    result = []
    for i in range(len(text_bytes) - 5):
        if text_bytes[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", text_bytes, i + 1)[0]
        dest = (text_va + i + 5 + rel) & 0xFFFFFFFF
        if dest == target:
            result.append(text_va + i)
    return result


def find_code_caves(buf: bytes, image_base: int, sections, min_len: int = 32):
    text = next(s for s in sections if s[0] == ".text")
    raw_ptr = text[3]
    raw_size = text[4]
    text_va = image_base + text[1]
    blob = buf[raw_ptr : raw_ptr + raw_size]
    caves = []
    i = 0
    while i < len(blob):
        if blob[i] != 0x00:
            i += 1
            continue
        j = i
        while j < len(blob) and blob[j] == 0x00:
            j += 1
        ln = j - i
        if ln >= min_len:
            caves.append((text_va + i, ln))
        i = j
    return sorted(caves, key=lambda item: item[1], reverse=True)


def main():
    buf = EXE.read_bytes()
    image_base, sections = parse_pe(buf)
    imports = parse_imports(buf, image_base, sections)

    print("QTranslate selection map")
    print("exe:", EXE)
    print()

    print("Important imports")
    wanted = [
        "USER32.dll!OpenClipboard",
        "USER32.dll!GetClipboardData",
        "USER32.dll!SetClipboardData",
        "USER32.dll!EnumClipboardFormats",
        "USER32.dll!GetClipboardSequenceNumber",
        "OLEACC.dll!AccessibleObjectFromPoint",
        "KERNEL32.dll!GetProcAddress",
        "KERNEL32.dll!LoadLibraryExA",
    ]
    for va, name in sorted(imports.items()):
        if name in wanted:
            print(f"  {name:<42} 0x{va:08x}")
    print()

    print("Critical functions")
    critical = {
        0x404901: "Accessibility selection reader",
        0x43BE7E: "CF_UNICODETEXT clipboard reader",
        0x43BEFC: "Copy-via-clipboard orchestrator",
        0x43EC71: "Clipboard snapshot",
        0x43EE28: "Clipboard restore",
        0x4147ED: "TaskCopySelection dispatch",
        0x4056CE: "TaskTranslateClipboard clipboard ingest",
    }
    for va, label in critical.items():
        print(f"  0x{va:08x} {label}")
    print()

    print("Callers of the Unicode clipboard reader")
    for caller in find_callers(buf, image_base, sections, 0x43BE7E):
        print(f"  0x{caller:08x}")
    print()

    print("Callers of the accessibility reader")
    for caller in find_callers(buf, image_base, sections, 0x404901):
        print(f"  0x{caller:08x}")
    print()

    print("Largest .text code caves")
    for va, ln in find_code_caves(buf, image_base, sections)[:10]:
        print(f"  0x{va:08x} len={ln}")


if __name__ == "__main__":
    main()
