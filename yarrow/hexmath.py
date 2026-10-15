# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""yarrow.hexmath — the arithmetic of the sixty-four-state structure (contract v0.1).

Representation
--------------
A *line* is a bit: 1 yang (explicit tier), 0 yin (implicit tier). A *trigram* is three lines
bottom to top; its Fuxi index reads the three bits as a binary number with the bottom line most
significant (☷ Earth [000] = 0 … ☰ Heaven [111] = 7). A *hexagram* is a pair ``(inner, outer)`` of
trigram indices: lines 1–3 are the inner (agent) trigram and lines 4–6 the outer (context)
trigram. King Wen numbers are looked up from the received table, never computed from the bits.

Canon partition
---------------
Hexis partitions the King Wen sequence at 32/33 (its ruling of 4 October 2026, departing from the
received division of the text into thirty and thirty-four figures): King Wen 1–32 form the upper
or *decision* canon, 33–64 the lower or *execution* canon. A tool may execute only in an execution
state; every state is routable.

Fit
---
``fit(inner, outer, rule="wangbi")`` scores a state. Under ``wangbi`` each corresponding pair
(lines 1–4, 2–5, 3–6 of opposite polarity) contributes one unit, split between its two lines, and
each properly placed line (yang at 1, 3, 5; yin at 2, 4, 6) contributes one unit; lines 2 and 5
carry a centrality weight ``w_central >= 1`` on both contributions, default 1. ``match`` and
``correspondence`` are named alternatives kept for ablation only.

What is not here: thresholds, any read-path or hysteresis rule, any learned parameter, any
interpretation of a figure beyond trigram names and glyphs, and any I Ching text.

Reference: Herko, S. and Pidcock, C. (2026). Hexis: a fixed 64-state structure for governing
cognitive disposition in language-model agents. Version 1.0. https://doi.org/10.5281/zenodo.23393632
"""
from __future__ import annotations

import json
from fractions import Fraction
from importlib import resources
from itertools import product
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

__all__ = [
    "TRIGRAMS", "lines", "inner", "outer", "from_lines", "kingwen", "from_kingwen", "canon",
    "executable", "decision_fibre", "execution_fibre", "changing", "derived", "complement",
    "opposite", "inversion", "nuclear", "kingwen_successor", "arrangement",
    "opposite_is_complement", "successor", "predecessor", "correspondence", "proper", "central",
    "fit", "relation", "route_valid", "relation_table", "cast", "sample", "verify",
]

Hexagram = Tuple[int, int]

# ---------------------------------------------------------------- trigrams
TRIGRAMS: Dict[int, Tuple[str, str]] = {
    0: ("☷", "Earth"), 1: ("☶", "Mountain"), 2: ("☵", "Water"), 3: ("☴", "Wind"),
    4: ("☳", "Thunder"), 5: ("☲", "Fire"), 6: ("☱", "Lake"), 7: ("☰", "Heaven"),
}


def trigram_bits(t: int) -> List[int]:
    """Three lines of trigram ``t``, bottom to top."""
    _check_trigram(t)
    return [(t >> 2) & 1, (t >> 1) & 1, t & 1]


def trigram_from_bits(b: Sequence[int]) -> int:
    if len(b) != 3 or any(x not in (0, 1) for x in b):
        raise ValueError("a trigram is three bits")
    return (b[0] << 2) | (b[1] << 1) | b[2]


def label(t: int) -> str:
    """Notation used in the paper, e.g. '☲ Fire [101]'."""
    g, n = TRIGRAMS[t]
    return f"{g} {n} [{''.join(map(str, trigram_bits(t)))}]"


def _check_trigram(t: int) -> None:
    if not (isinstance(t, int) and 0 <= t <= 7):
        raise ValueError(f"trigram index must be 0–7, got {t!r}")


def _check_hex(h: Hexagram) -> None:
    if not (isinstance(h, tuple) and len(h) == 2):
        raise ValueError(f"a hexagram is an (inner, outer) pair, got {h!r}")
    _check_trigram(h[0]); _check_trigram(h[1])


# ---------------------------------------------------------------- representation
def lines(h: Hexagram) -> List[int]:
    """Six lines bottom to top."""
    _check_hex(h)
    return trigram_bits(h[0]) + trigram_bits(h[1])


def inner(h: Hexagram) -> int:
    _check_hex(h); return h[0]


def outer(h: Hexagram) -> int:
    _check_hex(h); return h[1]


def from_lines(L: Sequence[int]) -> Hexagram:
    if len(L) != 6:
        raise ValueError("a hexagram is six lines")
    return (trigram_from_bits(L[:3]), trigram_from_bits(L[3:]))


# ---------------------------------------------------------------- King Wen table (received order)
# Rows: lower (inner) trigram; columns: upper (outer) trigram; both in the order
# Qian, Zhen, Kan, Gen, Kun, Xun, Li, Dui.
_ORDER = [7, 4, 2, 1, 0, 3, 5, 6]
_TABLE = [
    [1, 34, 5, 26, 11, 9, 14, 43],
    [25, 51, 3, 27, 24, 42, 21, 17],
    [6, 40, 29, 4, 7, 59, 64, 47],
    [33, 62, 39, 52, 15, 53, 56, 31],
    [12, 16, 8, 23, 2, 20, 35, 45],
    [44, 32, 48, 18, 46, 57, 50, 28],
    [13, 55, 63, 22, 36, 37, 30, 49],
    [10, 54, 60, 41, 19, 61, 38, 58],
]


def _build_kingwen(table, order) -> Dict[Hexagram, int]:
    kw = {}
    for i, inn in enumerate(order):
        for j, out in enumerate(order):
            kw[(inn, out)] = table[i][j]
    return kw


_KW: Dict[Hexagram, int] = _build_kingwen(_TABLE, _ORDER)
_FROM_KW: Dict[int, Hexagram] = {n: h for h, n in _KW.items()}


def kingwen(inner_t: int, outer_t: int) -> int:
    """King Wen number of the state (inner, outer)."""
    h = (inner_t, outer_t); _check_hex(h)
    return _KW[h]


def from_kingwen(n: int) -> Hexagram:
    if n not in _FROM_KW:
        raise ValueError("King Wen numbers run 1–64")
    return _FROM_KW[n]


# ---------------------------------------------------------------- canon partition
def canon(h: Hexagram) -> str:
    """'upper' (decision state, King Wen 1–32) or 'lower' (execution state, 33–64)."""
    _check_hex(h)
    return "upper" if _KW[h] <= 32 else "lower"


def executable(inner_t: int, outer_t: int) -> bool:
    """True when a tool may execute: the state is in the lower (execution) canon."""
    return canon((inner_t, outer_t)) == "lower"


def decision_fibre(inner_t: int) -> FrozenSet[int]:
    """Outer trigrams that make a decision state with this inner trigram."""
    _check_trigram(inner_t)
    return frozenset(o for o in range(8) if canon((inner_t, o)) == "upper")


def execution_fibre(inner_t: int) -> FrozenSet[int]:
    _check_trigram(inner_t)
    return frozenset(o for o in range(8) if canon((inner_t, o)) == "lower")


# ---------------------------------------------------------------- transformations
def changing(h: Hexagram, k: int) -> Hexagram:
    """Flip line k (1–6)."""
    if k not in range(1, 7):
        raise ValueError("lines are numbered 1–6")
    L = lines(h); L[k - 1] ^= 1
    return from_lines(L)


def derived(h: Hexagram, ks: Sequence[int]) -> Hexagram:
    """Flip every line in ``ks``."""
    for k in set(ks):
        h = changing(h, k)
    return h


def complement(t: int) -> int:
    _check_trigram(t)
    return t ^ 7


def opposite(h: Hexagram) -> Hexagram:
    """Flip every line (錯)."""
    _check_hex(h)
    return (h[0] ^ 7, h[1] ^ 7)


def inversion(h: Hexagram) -> Hexagram:
    """Reverse the six lines (綜)."""
    return from_lines(list(reversed(lines(h))))


def nuclear(h: Hexagram) -> Hexagram:
    """Inner = lines 2–4, outer = lines 3–5 (互)."""
    L = lines(h)
    return (trigram_from_bits(L[1:4]), trigram_from_bits(L[2:5]))


def kingwen_successor(h: Hexagram) -> Hexagram:
    """n → n + 1 in the received order (64 → 1)."""
    return from_kingwen(_KW[h] % 64 + 1)


# ---------------------------------------------------------------- arrangements
_ARRANGEMENTS: Dict[str, List[int]] = {
    # clockwise from the top position
    "fuxi": [7, 3, 2, 1, 0, 4, 5, 6],        # ☰ ☴ ☵ ☶ ☷ ☳ ☲ ☱
    "kingwen": [5, 0, 6, 7, 2, 1, 4, 3],     # ☲ ☷ ☱ ☰ ☵ ☶ ☳ ☴ (Later Heaven)
    "jeongyeok": [0, 5, 6, 4, 7, 2, 1, 3],   # ☷ ☲ ☱ ☳ ☰ ☵ ☶ ☴ (to be checked against a pinned edition before v1.0)
}


def arrangement(name: str) -> List[int]:
    if name not in _ARRANGEMENTS:
        raise ValueError(f"arrangements are {sorted(_ARRANGEMENTS)}")
    return list(_ARRANGEMENTS[name])


def opposite_is_complement(name: str) -> bool:
    c = arrangement(name)
    return all(c[i] ^ 7 == c[i + 4] for i in range(4))


def successor(t: int, name: str) -> int:
    c = arrangement(name); _check_trigram(t)
    return c[(c.index(t) + 1) % 8]


def predecessor(t: int, name: str) -> int:
    c = arrangement(name); _check_trigram(t)
    return c[(c.index(t) - 1) % 8]


# ---------------------------------------------------------------- line rules
def correspondence(h: Hexagram) -> List[bool]:
    """Per pair (1–4, 2–5, 3–6): True when the two lines have opposite polarity (應)."""
    L = lines(h)
    return [L[k] != L[k + 3] for k in range(3)]


def proper(h: Hexagram) -> List[bool]:
    """Per line 1–6: yang at 1, 3, 5 and yin at 2, 4, 6 (當位)."""
    L = lines(h)
    return [(L[k] == 1) if k % 2 == 0 else (L[k] == 0) for k in range(6)]


def central(h: Hexagram) -> List[bool]:
    """Per line 1–6: lines 2 and 5 are central."""
    _check_hex(h)
    return [k in (1, 4) for k in range(6)]


def fit(inner_t: int, outer_t: int, rule: str = "wangbi", w_central=1):
    """Score the state (inner, outer). Returns (per_line, total) with exact fractions.

    rule="wangbi": correspondence plus proper position, centrality weight on lines 2 and 5
    (default 1; a non-default weight used in any evaluation read is sealed configuration).
    rule="match" and rule="correspondence": named alternatives for ablation only.
    """
    h = (inner_t, outer_t); _check_hex(h)
    w = Fraction(w_central)
    if w < 1:
        raise ValueError("w_central must be at least 1")
    L = lines(h)
    per = [Fraction(0)] * 6
    if rule == "wangbi":
        for k, c in enumerate(correspondence(h)):
            if c:
                weight = w if k == 1 else Fraction(1)
                per[k] += weight / 2
                per[k + 3] += weight / 2
        for k, ok in enumerate(proper(h)):
            if ok:
                per[k] += w if k in (1, 4) else Fraction(1)
    elif rule == "match":
        for k in range(3):
            if L[k] == L[k + 3]:
                per[k] += Fraction(1, 2); per[k + 3] += Fraction(1, 2)
    elif rule == "correspondence":
        for k, c in enumerate(correspondence(h)):
            if c:
                per[k] += Fraction(1, 2); per[k + 3] += Fraction(1, 2)
    else:
        raise ValueError("rules are 'wangbi', 'match', 'correspondence'")
    return per, sum(per)


# ---------------------------------------------------------------- relations
def _load_relation_table() -> Dict[str, str]:
    data = json.loads(resources.files("yarrow.canon").joinpath("relations_v1.json").read_text("utf-8"))
    return {r["relation"]: r["status"] for r in data["relations"]}


def relation_table() -> Dict[str, str]:
    """Relation name → status ('route-valid', 'read-only input' or 'reading-only'), as versioned data."""
    return dict(_load_relation_table())


def _route_relations() -> List[str]:
    out = [f"changing_inner:{k}" for k in (1, 2, 3)] + ["inner_complement"]
    for a in _ARRANGEMENTS:
        out += [f"successor:{a}", f"predecessor:{a}"]
    return out


def _apply_inner(rel: str, t: int) -> Optional[int]:
    if rel.startswith("changing_inner:"):
        k = int(rel.split(":")[1])
        b = trigram_bits(t); b[k - 1] ^= 1
        return trigram_from_bits(b)
    if rel == "inner_complement":
        return t ^ 7
    if rel.startswith("successor:"):
        return successor(t, rel.split(":")[1])
    if rel.startswith("predecessor:"):
        return predecessor(t, rel.split(":")[1])
    return None


def _family(rel: str) -> str:
    """Table key for a concrete relation name, e.g. 'successor:fuxi' → 'successor:<arrangement>'."""
    if rel.startswith("changing_inner:"):
        return "changing_inner"
    if rel.startswith("changing_outer:"):
        return "changing_outer"
    for f in ("successor", "predecessor"):
        if rel.startswith(f + ":"):
            return f + ":<arrangement>"
    return rel


def route_valid(inner_a: int, inner_b: int, cited: str) -> bool:
    """True when the cited relation is route-valid and maps inner_a to inner_b."""
    _check_trigram(inner_a); _check_trigram(inner_b)
    table = _load_relation_table()
    if table.get(_family(cited)) != "route-valid":
        return False
    try:
        return _apply_inner(cited, inner_a) == inner_b
    except (ValueError, IndexError):
        return False


def relation(a: Hexagram, b: Hexagram) -> Set[str]:
    """Every tabled relation under which b follows a."""
    _check_hex(a); _check_hex(b)
    found = set()
    if a[1] == b[1]:
        for rel in _route_relations():
            if _apply_inner(rel, a[0]) == b[0]:
                found.add(rel)
    if a[0] == b[0] and a[1] != b[1]:
        diff = [k for k in range(3) if trigram_bits(a[1])[k] != trigram_bits(b[1])[k]]
        if len(diff) == 1:
            found.add(f"changing_outer:{diff[0] + 4}")
    if opposite(a) == b:
        found.add("opposite")
    if inversion(a) == b:
        found.add("inversion")
    if nuclear(a) == b:
        found.add("nuclear")
    nd = sum(x != y for x, y in zip(lines(a), lines(b)))
    if nd >= 2:
        found.add("derived")
    if kingwen_successor(a) == b:
        found.add("kingwen_successor")
    return found


# ---------------------------------------------------------------- cast distributions
def _division_outcomes(stalks: int) -> List[Tuple[Fraction, int]]:
    """One division of the yarrow-stalk method on ``stalks`` stalks.

    The stalks are split into two heaps; one stalk is taken from the right heap; each heap is
    counted off by fours, leaving a remainder of 1–4. The left heap's residue is taken as uniform
    over 1–4 (the split point is arbitrary); the right heap's residue follows from the total.
    Returns (probability, stalks set aside) pairs.
    """
    out: Dict[int, Fraction] = {}
    for r_left in (1, 2, 3, 4):
        r_right = (stalks - 1 - r_left) % 4 or 4
        aside = 1 + r_left + r_right
        out[aside] = out.get(aside, Fraction(0)) + Fraction(1, 4)
    return sorted((p, a) for a, p in out.items())


def cast(method: str = "yarrow") -> Dict[int, Fraction]:
    """Distribution over the four line outcomes 6, 7, 8, 9 (6 changing yin … 9 changing yang)."""
    if method == "coin":
        dist: Dict[int, Fraction] = {}
        for coins in product((2, 3), repeat=3):
            v = sum(coins)
            dist[v] = dist.get(v, Fraction(0)) + Fraction(1, 8)
        return dict(sorted(dist.items()))
    if method != "yarrow":
        raise ValueError("methods are 'yarrow' and 'coin'")
    dist = {}
    def walk(stalks: int, step: int, p: Fraction):
        if step == 3:
            v = stalks // 4
            dist[v] = dist.get(v, Fraction(0)) + p
            return
        for q, aside in _division_outcomes(stalks):
            walk(stalks - aside, step + 1, p * q)
    walk(49, 0, Fraction(1))
    return dict(sorted(dist.items()))


def sample(method: str = "yarrow", rng=None) -> Tuple[Hexagram, List[int]]:
    """Draw six line outcomes; return the primary hexagram and the changing lines (1–6)."""
    import random
    rng = rng or random.Random()
    d = cast(method)
    vals, weights = list(d), [float(p) for p in d.values()]
    outcomes = rng.choices(vals, weights=weights, k=6)
    primary = from_lines([v % 2 for v in outcomes])  # 7, 9 yang; 6, 8 yin
    moving = [k + 1 for k, v in enumerate(outcomes) if v in (6, 9)]
    return primary, moving


# ---------------------------------------------------------------- self-verification
def verify(table=None, order=None, relations: Optional[Dict[str, str]] = None) -> None:
    """Assert the structural facts the paper states; raises AssertionError on any failure.

    The optional arguments let the mutation tests pass a broken King Wen table, a broken
    line order or a corrupted relation table and confirm that verification fails.
    """
    kw = _build_kingwen(table or _TABLE, order or _ORDER)
    assert sorted(kw.values()) == list(range(1, 65)), "King Wen table is a permutation of 1–64"
    assert kw[(7, 0)] == 11 and kw[(0, 7)] == 12, "11 Tai and 12 Pi"
    assert kw[(5, 2)] == 63 and kw[(2, 5)] == 64, "63 Jiji and 64 Weiji"
    assert kw[(7, 7)] == 1 and kw[(0, 0)] == 2, "1 Qian and 2 Kun"
    dec = {h for h, n in kw.items() if n <= 32}
    assert len(dec) == 32
    sizes = {i: sum(1 for o in range(8) if (i, o) in dec) for i in range(8)}
    assert sizes == {7: 6, 6: 2, 5: 3, 4: 6, 3: 3, 2: 4, 1: 2, 0: 6}, "decision-fibre sizes"
    for h in kw:
        assert ((h in dec) == (inversion(h) in dec)), "inversion keeps the canon"
    assert kw[nuclear((7, 0))] == 54 and kw[nuclear((7, 0))] > 32, "nuclear of 11 Tai is 54 Guimei"
    rel = relations if relations is not None else _load_relation_table()
    route = {k for k, v in rel.items() if v == "route-valid"}
    assert route == {"changing_inner", "inner_complement", "successor:<arrangement>",
                     "predecessor:<arrangement>"}, "route-valid relations"
    for name in ("opposite", "inversion", "nuclear", "derived", "kingwen_successor"):
        assert rel.get(name) == "reading-only", f"{name} is reading-only"
