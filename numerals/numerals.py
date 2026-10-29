#!/usr/bin/env python3
"""Armenian alphabetic numerals: encode/decode 1..9999 and self-tests. Additive notation, letters in descending value.
Era conversion is the standard Armenian Era offset (AD = AE + 551 for most of the year); approximate, flagged as such."""
from letters import LET, value

VAL = {LET[i]: value(i) for i in range(36)}
BY_VAL = {v: c for c, v in VAL.items()}

def encode(n):
    assert 1 <= n <= 9999
    return "".join(BY_VAL[int(d) * 10 ** p] for p, d in enumerate(reversed(str(n))) if d != "0")[::-1]
    # built units-first then reversed so the thousands letter leads

def decode(s):
    vals = [VAL[c] for c in s]
    assert vals == sorted(vals, reverse=True), "letters must descend in value"
    return sum(vals)

def ad_from_ae(ae): return ae + 551

if __name__ == "__main__":
    seen = set()
    for n in range(1, 10000):
        s = encode(n); assert decode(s) == n and s not in seen; seen.add(s)
    assert len(seen) == 9999
    assert encode(36) == "ԼԶ" and encode(405) == "ՆԵ" and encode(1000) == "Ռ" and encode(9999) == "ՔՋՂԹ"
    print("1..9999 round-trip: 9999 unique strings; 36=%s  405=%s (the year the alphabet is traditionally dated)" % (encode(36), encode(405)))
