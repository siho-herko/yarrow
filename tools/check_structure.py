# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
# Run: python3 check_structure.py   (Python 3.8+, standard library only; exits non-zero if any stated fact fails)
"""Recompute the structural facts the paper states (v0.2, ruling 30 of 4 Oct 2026: upper canon 1–32 = decision
states, lower canon 33–64 = execution states; the hexmath contract v0.1 carries the earlier form and is to be regenerated).
Lines are bits, 1 yang / 0 yin; a trigram is [b1 b2 b3] bottom to top; Fuxi index has the
bottom line most significant. King Wen numbers are a lookup table (not computed)."""
from itertools import product

NAMES = {7: "☰ Heaven", 6: "☱ Lake", 5: "☲ Fire", 4: "☳ Thunder",
         3: "☴ Wind", 2: "☵ Water", 1: "☶ Mountain", 0: "☷ Earth"}
GLYPH = {k: v.split()[0] for k, v in NAMES.items()}

def bits(t):            # bottom to top
    return [(t >> 2) & 1, (t >> 1) & 1, t & 1]

def from_bits(b):
    return (b[0] << 2) | (b[1] << 1) | b[2]

# Traditional King Wen table: rows = lower (inner) trigram, cols = upper (outer) trigram,
# in the order Qian, Zhen, Kan, Gen, Kun, Xun, Li, Dui.
ORDER = [7, 4, 2, 1, 0, 3, 5, 6]
TABLE = [
    [1, 34, 5, 26, 11, 9, 14, 43],
    [25, 51, 3, 27, 24, 42, 21, 17],
    [6, 40, 29, 4, 7, 59, 64, 47],
    [33, 62, 39, 52, 15, 53, 56, 31],
    [12, 16, 8, 23, 2, 20, 35, 45],
    [44, 32, 48, 18, 46, 57, 50, 28],
    [13, 55, 63, 22, 36, 37, 30, 49],
    [10, 54, 60, 41, 19, 61, 38, 58],
]
KW = {}
for i, inner in enumerate(ORDER):
    for j, outer in enumerate(ORDER):
        KW[(inner, outer)] = TABLE[i][j]
assert sorted(KW.values()) == list(range(1, 65))

def lines(h):           # h = (inner, outer) -> six bits bottom to top
    return bits(h[0]) + bits(h[1])

def from_lines(L):
    return (from_bits(L[:3]), from_bits(L[3:]))

def inversion(h):
    return from_lines(list(reversed(lines(h))))

def nuclear(h):
    L = lines(h)
    return (from_bits(L[1:4]), from_bits(L[2:5]))

def correspondence(h):
    L = lines(h)
    return [L[k] != L[k + 3] for k in range(3)]

def proper(h):
    L = lines(h)
    return [(L[k] == 1) if k % 2 == 0 else (L[k] == 0) for k in range(6)]  # k=0 is line 1

def decision(h):      # upper canon 上經, King Wen 1–32: the standpoint produces a typed decision artefact
    return KW[h] <= 32

def execution(h):     # lower canon 下經, King Wen 33–64: the standpoint carries out; tools may execute only here
    return KW[h] > 32

# --- anchors ---
assert KW[(7, 0)] == 11 and KW[(0, 7)] == 12
assert KW[(5, 2)] == 63 and KW[(2, 5)] == 64
assert KW[(6, 4)] == 54
assert nuclear((7, 0)) == (6, 4), "nuclear of 11 Tai is 54 Guimei"

# D.1 canon partition (ruling 30, 4 Oct 2026): upper canon (1–32) = decision states,
# lower canon (33–64) = execution states; all 64 routable; the canon fixes the kind of output.
dec = [h for h in KW if decision(h)]
exe = [h for h in KW if execution(h)]
assert len(dec) == 32 and len(exe) == 32 and not set(dec) & set(exe)
dfibre = {inner: sorted(o for o in range(8) if decision((inner, o))) for inner in range(8)}
efibre = {inner: sorted(o for o in range(8) if execution((inner, o))) for inner in range(8)}
dsizes = {NAMES[i]: len(f) for i, f in dfibre.items()}
esizes = {NAMES[i]: len(f) for i, f in efibre.items()}
print("decision-fibre sizes:", dsizes)
print("execution-fibre sizes:", esizes)
assert dsizes == {"☰ Heaven": 6, "☱ Lake": 2, "☲ Fire": 3, "☳ Thunder": 6,
                  "☴ Wind": 3, "☵ Water": 4, "☶ Mountain": 2, "☷ Earth": 6}
assert esizes == {"☰ Heaven": 2, "☱ Lake": 6, "☲ Fire": 5, "☳ Thunder": 2,
                  "☴ Wind": 5, "☵ Water": 4, "☶ Mountain": 6, "☷ Earth": 2}
assert all(len(f) >= 2 for f in efibre.values()), "every standpoint executes in at least two contexts"
assert all(dsizes[n] + esizes[n] == 8 for n in NAMES.values())
print("decision fibres:", {NAMES[i]: [GLYPH[o] for o in f] for i, f in dfibre.items()})
print("execution fibres:", {NAMES[i]: [GLYPH[o] for o in f] for i, f in efibre.items()})
assert decision((7, 0)) and decision((0, 7)), "11 Tai and 12 Pi are decision states"
assert execution((5, 2)) and execution((2, 5)), "63 Jiji and 64 Weiji are execution states"
assert execution(nuclear((7, 0))), "the nuclear of 11 Tai, 54 Guimei, is an execution state"

# D.2 correspondence is inversion-invariant, for every hexagram
for h in KW:
    assert sorted(correspondence(h)) == sorted(correspondence(inversion(h)))
    assert sum(correspondence(h)) == sum(correspondence(inversion(h)))
print("correspondence inversion-invariant: all 64")
for h in [(7, 0), (0, 7), (5, 2), (2, 5)]:
    print(KW[h], "correspondence", correspondence(h), "proper", sum(proper(h)))
assert sum(proper((7, 0))) == 4 and sum(proper((0, 7))) == 2
assert sum(proper((5, 2))) == 6 and sum(proper((2, 5))) == 0

# D.3 proper position: inversion maps proper count p -> 6 - p, for every hexagram
for h in KW:
    assert sum(proper(inversion(h))) == 6 - sum(proper(h))
print("proper(inversion(h)) == 6 - proper(h): all 64")

# D.4 the all-proper state
allp = [h for h in KW if all(proper(h))]
print("all six proper:", [(KW[h], lines(h)) for h in allp])
assert allp == [(5, 2)] and lines((5, 2)) == [1, 0, 1, 0, 1, 0]

# inversion keeps the canon: every inversion pair lies on one side
for h in KW:
    assert decision(h) == decision(inversion(h))
print("inversion preserves the canon (decision/execution): all 64")
cross = [KW[h] for h in dec if execution(nuclear(h))]
print("decision states whose nuclear is an execution state:", sorted(cross))

# D.5 fit at the public default weight (U5.2): correspondence (one unit per corresponding pair)
# plus proper position (one unit per proper line); lines 2 and 5 carry the centrality weight,
# whose default is one, so at the default the score is the plain sum. (v0.28: added so that
# the worked-example scores and ties stated in U5.2, U7 and L4 are asserted, not only printed.)
def fit(h, w=1):
    L = lines(h)
    corr = sum((w if k == 1 else 1) for k in range(3) if L[k] != L[k + 3])
    prop = sum((w if k in (1, 4) else 1) for k, ok in enumerate(proper(h)) if ok)
    return corr + prop

def best(outer):
    scores = {inner: fit((inner, outer)) for inner in range(8)}
    m = max(scores.values())
    return m, sorted(KW[(i, outer)] for i, s in scores.items() if s == m)

# refund example, first turn: outer ☷ Earth [000]
assert fit((0, 0)) == 3, "2 Kun scores 3"
assert best(0) == (7, [11, 36]), "max 7 shared by 11 Tai (decision) and 36 Mingyi (execution)"
assert decision((7, 0)) and execution((5, 0))
# second turn: outer ☶ Mountain [001]
assert fit((7, 1)) == 5 and KW[(7, 1)] == 26, "26 Dachu scores 5"
m, tied = best(1)
assert m == 5 and len(tied) == 4 and [n for n in tied if n > 32] == [41], "41 Sun is the one execution state among four tied at 5"
# second example (L4): outer ☳ Thunder [100]
assert fit((0, 4)) == 3 and KW[(0, 4)] == 16, "16 Yu scores 3"
assert best(4) == (5, [32, 34, 55, 62]), "max 5 shared by 32, 34, 55, 62"
assert [n for n in best(4)[1] if n <= 32] == [32], "32 Heng is the one decision state"
print("worked-example fit scores and ties (default weight): all asserted")

# D.7 arrangements (clockwise from top), as tabled in hexmath §4
ARR = {
    "fuxi":      [7, 3, 2, 1, 0, 4, 5, 6],
    "kingwen":   [5, 0, 6, 7, 2, 1, 4, 3],
    "jeongyeok": [0, 5, 6, 4, 7, 2, 1, 3],
}
SHUOGUA_XI = [4, 3, 5, 0, 6, 7, 2, 1]
def same_cycle(a, b):
    i = a.index(b[0]); return [a[(i + k) % 8] for k in range(8)] == b
assert same_cycle(ARR["kingwen"], SHUOGUA_XI)
print("Shuogua XI order is the King Wen circle's cycle: True")
for name, circ in ARR.items():
    assert sorted(circ) == list(range(8))
    pairs = [(circ[i], circ[i + 4]) for i in range(4)]
    comp = [(a ^ 7) == b for a, b in pairs]
    print(name, "opposite pairs:", [(GLYPH[a], GLYPH[b]) for a, b in pairs],
          "complement?", comp, "all:", all(comp))
# Jeongyeok neither rotation nor reflection of Fuxi
fx = ARR["fuxi"]; jy = ARR["jeongyeok"]
dihedral = [[fx[(i + k) % 8] for i in range(8)] for k in range(8)]
dihedral += [list(reversed(d)) for d in dihedral]
assert jy not in dihedral
print("Jeongyeok is a rotation/reflection of Fuxi: False")
for name, circ in ARR.items():
    steps = [bin(circ[i] ^ circ[(i + 1) % 8]).count("1") for i in range(8)]
    print(name, "Hamming step profile (regenerated, not stated in the paper):", steps)

# Standpoint configurations (line 1 future, 2 present, 3 past; yang explicit)
for t in [7, 6, 5, 4, 3, 2, 1, 0]:
    b = bits(t)
    print(NAMES[t], "".join(map(str, b)),
          "plan" if b[0] else "no plan", "monitored" if b[1] else "unmonitored",
          "recall" if b[2] else "pattern")
print("ALL CHECKS PASSED")