"""Walk an engine function and its callees (read-only): absolute memory operands and calls, to judge whether a blit
loop touches globals. python scan_engine_fn.py 0x443180 [depth]
"""
import sys
from pathlib import Path

import capstone
import pefile

EXE = Path(__file__).resolve().parents[1] / 'runtime-play' / 'レコンキスタ.exe'
pe = pefile.PE(str(EXE))
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True
text = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.text')
lo, hi = base + text.VirtualAddress, base + text.VirtualAddress + text.Misc_VirtualSize


def walk(start, limit=4000):
    """Linear-sweep the function body, following local branches, until every reachable ret."""
    seen, todo, out, calls = set(), [start], [], set()
    while todo:
        a = todo.pop()
        while lo <= a < hi and a not in seen:
            code = img[a - base:a - base + 16]
            ins = next(md.disasm(code, a), None)
            if ins is None:
                break
            seen.add(a)
            out.append(ins)
            if ins.mnemonic == 'call':
                op = ins.operands[0]
                if op.type == capstone.x86.X86_OP_IMM:
                    calls.add(op.imm)
            if ins.mnemonic.startswith('j'):
                op = ins.operands[0]
                if op.type == capstone.x86.X86_OP_IMM and lo <= op.imm < hi:
                    todo.append(op.imm)
                if ins.mnemonic == 'jmp':
                    break
            if ins.mnemonic in ('ret', 'retn') or len(seen) > limit:
                break
            a += ins.size
    return sorted(out, key=lambda i: i.address), calls


def absmem(ins):
    hits = []
    for op in ins.operands:
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp:
            hits.append(op.mem.disp & 0xffffffff)
    return hits


IAT = {i.address: d.dll.decode() + '!' + i.name.decode() for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports if i.name}


def apis(body):
    """Windows functions called through the import table."""
    out = []
    for ins in body:
        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type == capstone.x86.X86_OP_MEM and ins.operands[0].mem.base == 0:
            out.append(IAT.get(ins.operands[0].mem.disp & 0xffffffff, hex(ins.operands[0].mem.disp & 0xffffffff)))
    return out


if __name__ == '__main__':
    start = int(sys.argv[1], 16)
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    only_api = '--api' in sys.argv
    done, frontier = set(), [(start, 0)]
    while frontier:
        fn, d = frontier.pop(0)
        if fn in done:
            continue
        done.add(fn)
        body, calls = walk(fn)
        mems = [(i.address, i.mnemonic, i.op_str, absmem(i)) for i in body if absmem(i)]
        writes = [m for m in mems if m[1].startswith(('mov', 'add', 'sub', 'inc', 'dec', 'and', 'or', 'xor')) and m[2].split(',')[0].strip().startswith(('dword ptr [0x', 'word ptr [0x', 'byte ptr [0x'))]
        used = apis(body)
        if not only_api or used:
            print(f'fn {fn:#x} depth {d}: {len(body)} ins, calls {[hex(c) for c in sorted(calls)]}' + (f' api {sorted(set(used))}' if used else ''))
        if not only_api:
            for a, mn, ops, h in mems:
                tag = 'WRITE' if (a, mn, ops, h) in writes else 'read '
                print(f'   {tag} {a:#x} {mn} {ops}')
        if d < depth:
            frontier += [(c, d + 1) for c in sorted(calls)]
