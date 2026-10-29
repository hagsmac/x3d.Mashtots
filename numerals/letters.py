#!/usr/bin/env python3
"""The 36 letters of Mesrop Mashtots's alphabet with Unicode facts and Armenian numeral values.
Everything here is computed from unicodedata + arithmetic, then asserted. Writes letters.json."""
import json, unicodedata

# Unicode block U+0531..U+0556 has 38 capitals. The original alphabet is the first 36 (Օ U+0555 and Ֆ U+0556 were added later).
CODE = [0x531 + i for i in range(36)]
LET = "".join(map(chr, CODE))
assert LET == "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ"      # same order as work/mashtots/reveal_data.py

def value(i):          # i = 0..35: nine letters per decade, 1..9, 10..90, 100..900, 1000..9000
    return (i % 9 + 1) * 10 ** (i // 9)

def table():
    out = []
    for i, cp in enumerate(CODE):
        ch = chr(cp)
        name = unicodedata.name(ch)
        assert name.startswith("ARMENIAN CAPITAL LETTER "), name
        out.append(dict(index=i + 1, char=ch, codepoint="U+%04X" % cp, unicode_name=name,
                        small=ch.lower(), value=value(i), place=10 ** (i // 9), digit=i % 9 + 1,
                        row=i // 9, col=i % 9))
    return out

if __name__ == "__main__":
    t = table()
    assert len(t) == 36 and len({r["value"] for r in t}) == 36
    assert sum(r["value"] for r in t) == 45 * 1111 == 49995
    json.dump(t, open("letters.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("36 letters; values", t[0]["value"], "...", t[-1]["value"], "; sum", sum(r["value"] for r in t))
