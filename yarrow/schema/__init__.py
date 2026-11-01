# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""yarrow.schema — the Hexis-S1 question set (schema v0.2) and its validator.

``load()`` returns the schema as data. ``validate(response, state, current_inner=None)`` checks a
router response and returns a list of problems (empty when the response is valid). It checks form
(every question present and typed, probabilities in range, distributions complete and summing to
one) and four structural rules:

1. the trigram heads are the product of the line heads (lines 1–3 inner, 4–6 outer);
2. the hexagram head is the 8 × 8 product of the trigram heads, and the reported hexagram is the
   King Wen number of the reported trigrams;
3. a change of standpoint cites a relation that ``hexmath.route_valid`` accepts;
4. the canon of ``state`` requires a decision artefact (upper canon, decision states) or forbids one
   (lower canon, execution states).

It scores nothing and holds no threshold: the read path, calibration and any decision about what a
probability means are sealed configuration outside this package.
"""
from __future__ import annotations

import json
import math
from importlib import resources
from typing import Any, Dict, List, Optional, Tuple

from yarrow import hexmath as H

__all__ = ["load", "validate", "SCHEMA_VERSION", "TOLERANCE"]

SCHEMA_VERSION = "0.2"
# Numerical tolerance for sums and products of probabilities. A floating-point allowance, not a
# decision threshold.
TOLERANCE = 1e-6

_NOULS = ["line_1", "line_2", "line_3", "line_4", "line_5", "line_6",
          "out_of_scope", "needs_deliberation", "role_conflict"]
_TRIGRAM_OPTIONS = [str(t) for t in range(8)]
_HEX_OPTIONS = [str(n) for n in range(1, 65)]
_NEXT_OPTIONS = _TRIGRAM_OPTIONS + ["hold", "escalate"]


def load() -> Dict[str, Any]:
    """The schema v0.2 as data."""
    text = resources.files("yarrow.schema").joinpath("s1_schema_v0.2.json").read_text("utf-8")
    return json.loads(text)


def _is_prob(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0


def _check_noul(name: str, v: Any, out: List[str]) -> Optional[float]:
    if not isinstance(v, dict) or "p" not in v:
        out.append(f"{name}: a Noul is {{'p': probability}}")
        return None
    if not _is_prob(v["p"]):
        out.append(f"{name}: p must be a probability in [0, 1]")
        return None
    return float(v["p"])


def _check_choice(name: str, v: Any, options: List[str], out: List[str]) -> Optional[Dict[str, float]]:
    if not isinstance(v, dict):
        out.append(f"{name}: a Choice is {{'distribution', 'choice', 'confidence'}}")
        return None
    dist = v.get("distribution")
    ok = True
    if not isinstance(dist, dict) or set(map(str, dist)) != set(options):
        out.append(f"{name}: distribution must give every option exactly once")
        ok = False
    elif not all(_is_prob(p) for p in dist.values()):
        out.append(f"{name}: every option probability must be in [0, 1]")
        ok = False
    elif abs(sum(dist.values()) - 1.0) > TOLERANCE:
        out.append(f"{name}: distribution must sum to 1")
        ok = False
    if str(v.get("choice")) not in options:
        out.append(f"{name}: choice must be one of the options")
        ok = False
    if not _is_prob(v.get("confidence")):
        out.append(f"{name}: confidence must be a scalar in [0, 1]")
        ok = False
    return {str(k): float(p) for k, p in dist.items()} if ok else None


def _trigram_product(ps: Tuple[float, float, float]) -> Dict[str, float]:
    out = {}
    for t in range(8):
        bits = H.trigram_bits(t)
        q = 1.0
        for p, b in zip(ps, bits):
            q *= p if b == 1 else (1.0 - p)
        out[str(t)] = q
    return out


def _check_artefact(a: Any, out: List[str]) -> None:
    if not isinstance(a, dict):
        out.append("decision_artefact: must be an object")
        return
    opts = a.get("options")
    ids: List[str] = []
    if not isinstance(opts, list) or not opts:
        out.append("decision_artefact.options: at least one option")
    else:
        for o in opts:
            if not isinstance(o, dict) or not o.get("id") or not isinstance(o.get("description"), str):
                out.append("decision_artefact.options: each option is {id, description}")
                break
            ids.append(str(o["id"]))
        if len(ids) != len(set(ids)):
            out.append("decision_artefact.options: ids must be unique")
    disp = a.get("disposition")
    if disp not in ("choose", "abstain", "escalate"):
        out.append("decision_artefact.disposition: one of choose, abstain, escalate")
    if disp == "choose" and str(a.get("choice")) not in ids:
        out.append("decision_artefact.choice: must name an option when disposition is choose")
    if disp in ("abstain", "escalate") and a.get("choice") is not None:
        out.append("decision_artefact.choice: must be null unless disposition is choose")
    if not isinstance(a.get("timing"), str) or not a["timing"].strip():
        out.append("decision_artefact.timing: a non-empty statement")
    if not _is_prob(a.get("confidence")):
        out.append("decision_artefact.confidence: a scalar in [0, 1]")
    if disp == "escalate" and not (isinstance(a.get("escalate_reason"), str) and a["escalate_reason"].strip()):
        out.append("decision_artefact.escalate_reason: required when disposition is escalate")


def validate(response: Dict[str, Any], state: Tuple[int, int],
             current_inner: Optional[int] = None) -> List[str]:
    """Problems with ``response`` for a turn in ``state`` = (inner, outer); empty list when valid.

    ``current_inner`` is the standpoint in force before this turn's transition; it defaults to the
    inner trigram of ``state``.
    """
    H._check_hex(state)
    cur = state[0] if current_inner is None else current_inner
    H._check_trigram(cur)
    out: List[str] = []
    if not isinstance(response, dict):
        return ["response must be an object"]

    lines: List[Optional[float]] = []
    for q in _NOULS:
        if q not in response:
            out.append(f"{q}: missing")
            if q.startswith("line_"):
                lines.append(None)
            continue
        p = _check_noul(q, response[q], out)
        if q.startswith("line_"):
            lines.append(p)

    heads = {}
    for q, opts in (("inner_trigram", _TRIGRAM_OPTIONS), ("outer_trigram", _TRIGRAM_OPTIONS),
                    ("hexagram", _HEX_OPTIONS), ("next_standpoint", _NEXT_OPTIONS)):
        if q not in response:
            out.append(f"{q}: missing")
            heads[q] = None
        else:
            heads[q] = _check_choice(q, response[q], opts, out)

    # Rule 1: trigram heads are the product of the line heads.
    for q, idx in (("inner_trigram", (0, 1, 2)), ("outer_trigram", (3, 4, 5))):
        ps = [lines[i] for i in idx]
        if heads[q] is not None and all(p is not None for p in ps):
            expect = _trigram_product(tuple(ps))  # type: ignore[arg-type]
            if any(abs(heads[q][k] - expect[k]) > TOLERANCE for k in expect):
                out.append(f"{q}: distribution is not the product of its line probabilities")

    # Rule 2: the hexagram head is the product of the trigram heads; reported choices agree.
    if heads["inner_trigram"] and heads["outer_trigram"] and heads["hexagram"]:
        for i in range(8):
            for o in range(8):
                kw = str(H.kingwen(i, o))
                want = heads["inner_trigram"][str(i)] * heads["outer_trigram"][str(o)]
                if abs(heads["hexagram"][kw] - want) > TOLERANCE:
                    out.append("hexagram: distribution is not the 8 x 8 product of the trigram heads")
                    break
            else:
                continue
            break
        ri, ro = int(response["inner_trigram"]["choice"]), int(response["outer_trigram"]["choice"])
        if str(response["hexagram"]["choice"]) != str(H.kingwen(ri, ro)):
            out.append("hexagram: reported choice is not the King Wen number of the reported trigrams")

    # Rule 3: a change of standpoint cites a route-valid relation.
    if heads["next_standpoint"] is not None:
        nxt = str(response["next_standpoint"]["choice"])
        if nxt in _TRIGRAM_OPTIONS and int(nxt) != cur:
            cited = response.get("cited_relation")
            if not isinstance(cited, str) or not H.route_valid(cur, int(nxt), cited):
                out.append("next_standpoint: a change of standpoint must cite a route-valid relation")

    # Rule 4: the canon decides whether a decision artefact is required or forbidden.
    has_artefact = response.get("decision_artefact") is not None
    if H.canon(state) == "upper":
        if not has_artefact:
            out.append("decision_artefact: required in a decision state (upper canon)")
        else:
            _check_artefact(response["decision_artefact"], out)
    elif has_artefact:
        out.append("decision_artefact: forbidden in an execution state (lower canon)")

    if "deliberation_outcome" in response and response["deliberation_outcome"] is not None:
        out.append("deliberation_outcome: options are deferred to the S2 design; omit until then")
    return out
