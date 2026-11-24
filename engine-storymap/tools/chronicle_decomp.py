"""chronicle.mjo as statements (10-27, for the new 연표's two looks): a stack walk per function that turns pushes and pops back
into expressions, so each engine call reads as name(arg1, arg2, ...) (the top of the stack is the first argument). Branches
stay as goto; nothing is restructured. Korean put back as in chronicle_dump.py.
python chronicle_decomp.py [script.mjo] [out]   -> F:/AI/reconquista-qa/chronicle-new/<script>.decomp.txt
Holds 연표 text (spoilers): for Claude's reading only.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chronicle_dump as D

BIN = {'add.i': '+', 'add.r': '+', 'add.s': '+', 'sub.i': '-', 'sub.r': '-', 'mul.i': '*', 'mul.r': '*', 'div.i': '/', 'div.r': '/',
       'rem': '%', 'and': '&', 'or': '|', 'xor': '^', 'shl': '<<', 'shr': '>>', 'andl': '&&', 'orl': '||',
       'ceq.i': '==', 'ceq.r': '==', 'ceq.s': '==', 'cne.i': '!=', 'cne.r': '!=', 'cne.s': '!=', 'clt.i': '<', 'clt.r': '<',
       'cle.i': '<=', 'cle.r': '<=', 'cgt.i': '>', 'cgt.r': '>', 'cge.i': '>=', 'cge.r': '>=', 'cle.s': '<=', 'clt.s': '<'}
UN = {'notl': '!', 'neg.i': '-', 'neg.r': '-', 'not': '~'}


SCOPE = {0: 'P', 1: 'S', 2: 'T', 3: 'L'}   # persistent, savefile, thread, local (mjotool MjoScope)


def name_of(x):
    """a known name, else scope.hash (locals without a known name by their slot)"""
    if x.hash in D.KNOWN:
        return D.KNOWN[x.hash]
    if x.is_call or x.is_syscall:
        return f'${x.hash:08x}'
    sc = SCOPE.get(int(x.flags.scope), '?')
    return f'L{x.var_offset}' if sc == 'L' else f'{sc}.{x.hash:08x}'


def decomp(s, out):
    starts = sorted((f.offset, f.name_hash) for f in s.functions)
    lines, cur, stack = [], None, []
    for x in s.instructions:
        owner = max((p for p in starts if p[0] <= x.offset), default=(0, 0))[1]
        if owner != cur:
            cur, stack = owner, []
            lines.append(f'\n===== function {owner:08x}')
        mn = x.opcode.mnemonic
        at = f'{x.offset:05x}'
        pop = lambda: stack.pop() if stack else '?'  # noqa: E731
        if mn in ('line', 'nop'):
            continue
        if mn in ('argcheck', 'alloca'):
            lines.append(f'{at}  {D.korean(x.format_instruction())[7:]}')
        elif mn.startswith('ldc'):
            stack.append(repr(x.int_value) if mn == 'ldc.i' else repr(x.float_value))
        elif mn == 'ldstr':
            stack.append('"' + D.korean(x.string or '') + '"')
        elif mn == 'ld':
            t = D.korean(x.format_instruction())
            mod = next((m for m in ('postinc', 'postdec', 'preinc', 'predec', 'notl', 'neg') if f' {m} ' in t), '')
            v = name_of(x)
            stack.append({'postinc': f'{v}++', 'postdec': f'{v}--', 'preinc': f'++{v}', 'predec': f'--{v}', 'notl': f'!{v}', 'neg': f'-{v}'}.get(mod, v))
        elif mn == 'ldelem':
            n = int(re.search(r'dim(\d)', D.korean(x.format_instruction()))[1])
            idx = [pop() for _ in range(n)][::-1]
            stack.append(name_of(x) + ''.join(f'[{i}]' for i in idx))
        elif mn.startswith('stelem'):
            n = int(re.search(r'dim(\d)', D.korean(x.format_instruction()))[1])
            idx = [pop() for _ in range(n)][::-1]   # the value goes on first, then the indices
            val = pop()
            lines.append(f'{at}  {name_of(x)}{"".join(f"[{i}]" for i in idx)} = {val}')
            stack.append(val)
        elif mn.startswith('st'):
            val = pop()
            parts = mn.split('.')   # st.i, or with an operator: st.add.i -> +=
            op = {'add': '+', 'sub': '-', 'mul': '*', 'div': '/', 'rem': '%', 'and': '&', 'or': '|', 'xor': '^', 'shl': '<<', 'shr': '>>'}.get(parts[1], '') if len(parts) == 3 else ''
            lines.append(f'{at}  {name_of(x)} {op}= {val}')
            stack.append(val)
        elif mn == 'pop':
            pop()
        elif mn in BIN:
            b, a = pop(), pop()
            stack.append(f'({a} {BIN[mn]} {b})')
        elif mn in UN:
            stack.append(f'{UN[mn]}{pop()}')
        elif x.is_call or x.is_syscall:
            args = [pop() for _ in range(x.argument_count)]
            call = f'{name_of(x)}({", ".join(args)})'
            if mn.endswith('p'):
                lines.append(f'{at}  {call}')
            else:
                stack.append(call)
        elif mn in ('brfalse', 'brtrue'):
            lines.append(f'{at}  if {"!" if mn == "brfalse" else ""}({pop()}) goto {x.offset + x.size + x.jump_offset:05x}')
        elif mn == 'br':
            lines.append(f'{at}  goto {x.offset + x.size + x.jump_offset:05x}')
        elif mn == 'br.case':
            lines.append(f'{at}  case-goto {x.offset + x.size + x.jump_offset:05x}')
        elif mn == 'bne.case':
            v = pop()
            lines.append(f'{at}  case {v}: else goto {x.offset + x.size + x.jump_offset:05x}')
            stack.append('_sel')
        elif mn == 'switch':
            lines.append(f'{at}  switch {pop()} -> {[f"{x.offset + x.size + o:05x}" for o in (x.switch_cases or [])]}')
        elif mn == 'ret':
            lines.append(f'{at}  return {pop() if stack else ""}')
        else:
            lines.append(f'{at}  ?{mn} {D.korean(x.format_instruction())[7:]}  stack={stack[-3:]}')
    out.write_text('\n'.join(lines), 'utf-8')
    return len(lines)


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'chronicle.mjo'
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r'F:\AI\reconquista-qa\chronicle-new') / (name + '.decomp.txt')
    s, _ = D.core.b.decode(D.entries()[name])
    print(decomp(s, out), 'lines ->', out)
