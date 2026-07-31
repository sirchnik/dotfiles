import gdb
import os

def _eval_int(expr: str) -> int:
    return int(gdb.parse_and_eval(expr))

def _is_printable(b: int) -> bool:
    return 32 <= b <= 126

def _hexdump_c(data: bytes, base_offset: int = 0, width: int = 16) -> str:
    # kept for optional /c flag
    lines = []
    n = len(data)

    for off in range(0, n, width):
        chunk = data[off:off + width]

        hex_pairs = [f"{b:02x}" for b in chunk]
        padded = hex_pairs + ["  "] * (width - len(hex_pairs))

        left = padded[:8]
        right = padded[8:]

        hex_part = " ".join(left) + "  " + " ".join(right)
        ascii_part = "".join(chr(b) if _is_printable(b) else "." for b in chunk)

        lines.append(f"{base_offset + off:08x}  {hex_part}  |{ascii_part}|")

    return "\n".join(lines) + ("\n" if lines else "")

def _u32_le(b: bytes) -> int:
    # b may be < 4 bytes at end; pad with zeros for display
    bb = b + b"\x00" * (4 - len(b))
    return int.from_bytes(bb, byteorder="little", signed=False)

def _u32_be(b: bytes) -> int:
    bb = b + b"\x00" * (4 - len(b))
    return int.from_bytes(bb, byteorder="big", signed=False)

def _dump32(data: bytes, begin_addr: int, base_offset: int = 0, words_per_line: int = 4,
            show_bytes: bool = True, big_endian: bool = False) -> str:
    """
    32-bit oriented dump: each line shows 4 DWORDs (16 bytes) by default.

    Format example (LE):
      off      addr        dword0      dword1      dword2      dword3     | bytes |
      00000000 0xdeadbeef  11223344    aabbccdd    00000001    7fffffff   | ....... |

    - off is relative to start (base_offset usually 0)
    - addr is absolute address (begin_addr + off)
    """
    lines = []
    n = len(data)
    bytes_per_line = words_per_line * 4
    u32 = _u32_be if big_endian else _u32_le

    # header
    cols = ["off", "addr"] + [f"dword{i}" for i in range(words_per_line)]
    if show_bytes:
        cols.append("bytes")
    lines.append(
        f"{cols[0]:>8} {cols[1]:>10}  " +
        "  ".join(f"{c:>10}" for c in cols[2:2+words_per_line]) +
        (f"   | {cols[-1]} |" if show_bytes else "")
    )

    for off in range(0, n, bytes_per_line):
        chunk = data[off:off + bytes_per_line]

        dwords = []
        for w in range(words_per_line):
            wb = chunk[w*4:(w+1)*4]
            if len(wb) == 0:
                # no more data; keep column alignment
                dwords.append(" " * 10)
            else:
                dwords.append(f"{u32(wb):08x}".rjust(10))

        off_s = f"{base_offset + off:08x}"
        addr_s = f"0x{(begin_addr + off):08x}"

        if show_bytes:
            # show raw bytes in-order for quick pattern spotting
            raw = " ".join(f"{b:02x}" for b in chunk)
            # pad raw bytes area to a stable width (for alignment)
            # each byte => "xx " (3 chars), minus last space
            max_raw_len = bytes_per_line * 3 - 1
            raw = raw.ljust(max_raw_len)

            # also show ascii-ish view at the end (optional but helpful)
            ascii_part = "".join(chr(b) if _is_printable(b) else "." for b in chunk)
            lines.append(
                f"{off_s:>8} {addr_s:>10}  " +
                "  ".join(dwords) +
                f"   | {raw} | {ascii_part}"
            )
        else:
            lines.append(
                f"{off_s:>8} {addr_s:>10}  " + "  ".join(dwords)
            )

    return "\n".join(lines) + ("\n" if lines else "")

class DumpHex(gdb.Command):
    """Dump memory as 32-bit (DWORD) oriented text into a file.

Usage:
  dumphex BEGIN END
  dumphex /len BEGIN LEN

Output naming options:
  /n NAME     sets output filename prefix (without extension). Default: dumphex
  /o EXT      sets extension, including leading dot. Default: .txt
  /out PATH   full output path override (ignores /n and /o)

Formatting options:
  /c          old hexdump -C style (bytes + ASCII, 16 bytes per line)
  /be         interpret DWORDs as big-endian (default: little-endian)
  /nobytes    don't include raw bytes/ascii column (DWORDs only)
  /w N        words per line (DWORDs). Default: 4 (=> 16 bytes/line)

Examples:
  dumphex 0x401000 0x401080
  dumphex /n stack /len $esp 256
  dumphex /w 8 /len $esp 256
  dumphex /be 0x1000 0x1100
  dumphex /c 0x401000 0x401080
"""

    def __init__(self):
        super(DumpHex, self).__init__("dumphex", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        argv = gdb.string_to_argv(arg)

        len_mode = False
        name_prefix = "dumphex"
        ext = ".txt"
        out_path = None

        # formatting defaults (32-bit optimized)
        use_classic_c = False
        big_endian = False
        show_bytes = True
        words_per_line = 4

        i = 0
        while i < len(argv) and argv[i].startswith("/"):
            flag = argv[i]

            if flag == "/len":
                len_mode = True
                i += 1
                continue

            if flag == "/n":
                if i + 1 >= len(argv):
                    raise gdb.GdbError("dumphex /n requires a NAME (filename prefix)")
                name_prefix = argv[i + 1]
                i += 2
                continue

            if flag == "/o":
                if i + 1 >= len(argv):
                    raise gdb.GdbError("dumphex /o requires an EXT (e.g. .txt, .log)")
                ext = argv[i + 1]
                if not ext.startswith("."):
                    raise gdb.GdbError("EXT must start with a dot, e.g. .txt")
                i += 2
                continue

            if flag == "/out":
                if i + 1 >= len(argv):
                    raise gdb.GdbError("dumphex /out requires a PATH (e.g. mem.txt or /tmp/mem.txt)")
                out_path = argv[i + 1]
                i += 2
                continue

            # new formatting flags
            if flag == "/c":
                use_classic_c = True
                i += 1
                continue

            if flag == "/be":
                big_endian = True
                i += 1
                continue

            if flag == "/nobytes":
                show_bytes = False
                i += 1
                continue

            if flag == "/w":
                if i + 1 >= len(argv):
                    raise gdb.GdbError("dumphex /w requires N (DWORDs per line)")
                words_per_line = int(argv[i + 1], 0)
                if words_per_line <= 0 or words_per_line > 16:
                    raise gdb.GdbError("/w N must be between 1 and 16")
                i += 2
                continue

            raise gdb.GdbError(f"Unknown flag: {flag}")

        if len(argv) - i != 2:
            raise gdb.GdbError("Usage: dumphex [/len] [/n NAME] [/o EXT] [/out PATH] BEGIN END|LEN")

        begin = _eval_int(argv[i])
        end_or_len = _eval_int(argv[i + 1])

        if len_mode:
            length = end_or_len
            if length < 0:
                raise gdb.GdbError("LEN must be >= 0")
            end = begin + length
        else:
            end = end_or_len
            if end < begin:
                raise gdb.GdbError("END must be >= BEGIN")
            length = end - begin

        inferior = gdb.selected_inferior()
        data = inferior.read_memory(begin, length).tobytes()

        if use_classic_c:
            text = _hexdump_c(data, base_offset=0, width=16)
        else:
            text = _dump32(
                data,
                begin_addr=begin,
                base_offset=0,
                words_per_line=words_per_line,
                show_bytes=show_bytes,
                big_endian=big_endian,
            )

        final_path = out_path if out_path is not None else (name_prefix + ext)

        with open(final_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

        fmt = "hexdump -C" if use_classic_c else "32-bit DWORD view"
        gdb.write(
                f"Wrote {fmt} of {length} bytes from 0x{begin:x}..0x{end:x} to {os.path.abspath(final_path)}:0\n"
        )

DumpHex()
