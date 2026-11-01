# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""yarrow.tiepolicy — a deterministic rule for ties between equally fitting states (draft).

Status: the rule below is *proposed* plan ruling 33 (register item 56) and is not yet ruled. It is
shipped as documented code so it can be reviewed and tested; its version changes with the ruling.

The fit objective ties often (several states can share the maximum under one outer trigram). The
tie is broken by a harness rule, never by the model, and the rule holds no threshold:

1. **Between canons.** Prefer a decision state (upper canon) while no decision artefact exists for
   the current task, and an execution state (lower canon) once one does.
2. **Within a canon.** Prefer the candidate whose inner trigram is reachable from the current
   standpoint by the cheapest route-valid relation: staying put, then one changed inner line, then
   the inner complement, then one step along an arrangement circle. A candidate no route-valid
   relation reaches is dropped.
3. **Otherwise hold.** If candidates remain tied after (1) and (2), or none is reachable, the result
   is ``"hold"``.
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

from yarrow import hexmath as H

__all__ = ["break_tie", "route_cost", "POLICY_VERSION"]

POLICY_VERSION = "0.1-proposed"
_COST = {"stay": 0, "changing_inner": 1, "inner_complement": 2, "arrangement_step": 3}


def route_cost(current_inner: int, target_inner: int) -> Optional[int]:
    """Cost of the cheapest route-valid relation from ``current_inner`` to ``target_inner``;
    None when no route-valid relation connects them."""
    if current_inner == target_inner:
        return _COST["stay"]
    best = None
    for rel in H._route_relations():
        if H.route_valid(current_inner, target_inner, rel):
            if rel.startswith("changing_inner:"):
                c = _COST["changing_inner"]
            elif rel == "inner_complement":
                c = _COST["inner_complement"]
            else:
                c = _COST["arrangement_step"]
            best = c if best is None else min(best, c)
    return best


def break_tie(candidates: Sequence[Tuple[int, int]], current: Tuple[int, int],
              artefact_exists: bool) -> Union[Tuple[int, int], str]:
    """Choose one of ``candidates`` (equally fitting states) or return ``"hold"``."""
    H._check_hex(current)
    cands = list(dict.fromkeys(candidates))
    for c in cands:
        H._check_hex(c)
    if not cands:
        return "hold"
    want = "lower" if artefact_exists else "upper"
    preferred = [c for c in cands if H.canon(c) == want]
    pool = preferred or cands
    costed = [(route_cost(current[0], c[0]), c) for c in pool]
    costed = [(k, c) for k, c in costed if k is not None]
    if not costed:
        return "hold"
    low = min(k for k, _ in costed)
    best = [c for k, c in costed if k == low]
    return best[0] if len(best) == 1 else "hold"
