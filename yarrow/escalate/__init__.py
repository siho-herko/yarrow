# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""yarrow.escalate — the escalation invariants, enforced at the tool layer (contract draft v0.2).

The invariants (Hexis plan ruling 30 and the engineering rules of the programme):

1. **Canon.** An *action* executes only in an execution state (lower canon, King Wen 33–64). In a
   decision state (upper canon) only *evidence requests* pass.
2. **Evidence versus action** (proposed plan ruling 32, not yet ruled). An evidence request is a
   read-only retrieval the harness performs on the agent's behalf, permitted from any state and
   logged with its provenance; an action is anything with an effect outside the agent's context. The
   class of each tool is declared in a versioned manifest and never inferred from the call. A tool
   missing from the manifest is refused.
3. **Escalation blocks action.** While an escalation is open, no action executes. Evidence
   requests still pass, so the escalation can be resolved.
4. **Stop is honoured at transport.** A stop request is checked again immediately before a call
   leaves the gate, so a stop raised mid-generation, mid-swap or mid-escalation prevents dispatch.
5. **Transitions at turn boundaries only.** A standpoint change cites a route-valid relation
   (``hexmath.route_valid``); it is refused inside a turn and while an adapter swap is under way.
6. **Replay log.** Every authorisation, refusal, transition, escalation and stop is appended to a
   replay log with the state, the canon, the cited relation and caller-supplied router
   probabilities, read-path state, compute and latency.

Resolution of escalations (DQ-15, open): an escalation records its reason and whether it needs
*authority*. Evidence, deliberation or a model may resolve a fact-finding escalation; one that needs
authority is resolved only by a person. Model review is recorded as model review and never counts
as human authority. This rule is the proposal under DQ-15 and is marked as such until ruled.

What is not here: thresholds, the read path's rule for when a state changes, and any model. The
gate is deterministic code; it enforces boundaries the harness can see and does not protect
actions that bypass it.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from yarrow import hexmath as H

__all__ = ["ToolManifest", "Gate", "Decision", "ReplayLog", "Refused", "UnknownTool",
           "guarded_stream", "RESOLVER_KINDS", "CONTRACT_VERSION"]

CONTRACT_VERSION = "0.2-draft"
RESOLVER_KINDS = ("evidence", "deliberation", "model", "person")
_KINDS = ("evidence", "action")


class Refused(Exception):
    """The gate refused an operation; the reason is in the message and in the replay log."""


class UnknownTool(Refused):
    """A tool absent from the manifest. Its class is never inferred."""


@dataclass(frozen=True)
class ToolManifest:
    """Versioned declaration of every tool's class: 'evidence' or 'action'."""
    version: str
    tools: Dict[str, str]

    def __post_init__(self):
        if not self.version:
            raise ValueError("a manifest carries a version")
        bad = {k: v for k, v in self.tools.items() if v not in _KINDS}
        if bad:
            raise ValueError(f"tool classes are {_KINDS}; got {bad}")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolManifest":
        return cls(version=str(d["version"]), tools=dict(d["tools"]))

    def classify(self, tool: str) -> str:
        if tool not in self.tools:
            raise UnknownTool(f"tool {tool!r} is not in manifest {self.version}")
        return self.tools[tool]


class ReplayLog:
    """Append-only list of records; optionally mirrored to a JSON-lines file."""

    def __init__(self, path: Optional[str] = None):
        self.records: List[Dict[str, Any]] = []
        self.path = path

    def append(self, record: Dict[str, Any]) -> None:
        r = dict(record)
        r["seq"] = len(self.records)
        self.records.append(r)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, default=str) + "\n")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    kind: Optional[str]
    reason: str


@dataclass
class _Escalation:
    reason: str
    needs_authority: bool
    open: bool = True
    resolution: Optional[Dict[str, str]] = None


class Gate:
    """The tool-layer gate for one agent session."""

    def __init__(self, manifest: ToolManifest, state: Tuple[int, int], log: Optional[ReplayLog] = None):
        H._check_hex(state)
        self.manifest = manifest
        self.state = state
        self.log = log if log is not None else ReplayLog()
        self.turn = 0
        self._in_turn = False
        self._swapping = False
        self._stop = False
        self._escalations: Dict[int, _Escalation] = {}

    # ------------------------------------------------------------ bookkeeping
    def _record(self, event: str, **kw: Any) -> None:
        self.log.append({"turn": self.turn, "event": event, "state": list(self.state),
                         "kingwen": H.kingwen(*self.state), "canon": H.canon(self.state), **kw})

    @property
    def open_escalations(self) -> List[int]:
        return [i for i, e in self._escalations.items() if e.open]

    @property
    def stopped(self) -> bool:
        return self._stop

    # ------------------------------------------------------------ turns, swaps, transitions
    def begin_turn(self, router: Optional[Dict[str, Any]] = None, readpath: Any = None) -> None:
        if self._in_turn:
            raise Refused("a turn is already open")
        self.turn += 1
        self._in_turn = True
        self._record("turn_begin", router=router, readpath=readpath)

    def end_turn(self, compute: Any = None, latency_ms: Optional[float] = None) -> None:
        if not self._in_turn:
            raise Refused("no turn is open")
        self._in_turn = False
        self._record("turn_end", compute=compute, latency_ms=latency_ms)

    def begin_swap(self) -> None:
        self._swapping = True
        self._record("swap_begin")

    def end_swap(self) -> None:
        self._swapping = False
        self._record("swap_end")

    def transition(self, new_state: Tuple[int, int], cited_relation: Optional[str] = None) -> None:
        """Move to ``new_state`` between turns. A change of inner trigram cites a route-valid relation;
        a change of outer trigram is a reading of the situation and cites nothing."""
        H._check_hex(new_state)
        why = None
        if self._in_turn:
            why = "transitions occur only at turn boundaries"
        elif self._swapping:
            why = "an adapter swap is under way"
        elif self._stop:
            why = "stop requested"
        elif new_state[0] != self.state[0] and not (
                cited_relation and H.route_valid(self.state[0], new_state[0], cited_relation)):
            why = "a change of standpoint must cite a route-valid relation"
        if why:
            self._record("transition_refused", to=list(new_state), cited_relation=cited_relation, reason=why)
            raise Refused(why)
        old = self.state
        self.state = new_state
        self._record("transition", **{"from": list(old)}, cited_relation=cited_relation)

    # ------------------------------------------------------------ escalation
    def open_escalation(self, reason: str, needs_authority: bool) -> int:
        if not reason:
            raise ValueError("an escalation states its reason")
        i = len(self._escalations) + 1
        self._escalations[i] = _Escalation(reason, bool(needs_authority))
        self._record("escalation_open", escalation=i, reason=reason, needs_authority=bool(needs_authority))
        return i

    def resolve_escalation(self, i: int, resolver_kind: str, by: str, outcome: str) -> None:
        """Close escalation ``i``. One that needs authority is closed only by a person (DQ-15, proposed);
        a model's review of it is recorded as model review and leaves it open."""
        e = self._escalations.get(i)
        if e is None or not e.open:
            raise Refused(f"no open escalation {i}")
        if resolver_kind not in RESOLVER_KINDS:
            raise ValueError(f"resolver kinds are {RESOLVER_KINDS}")
        if e.needs_authority and resolver_kind != "person":
            self._record("model_review" if resolver_kind == "model" else "resolution_refused",
                         escalation=i, resolver_kind=resolver_kind, by=by, outcome=outcome,
                         reason="authority can be supplied only by a person")
            raise Refused("this escalation needs authority; only a person can resolve it")
        e.open = False
        e.resolution = {"resolver_kind": resolver_kind, "by": by, "outcome": outcome}
        self._record("escalation_resolved", escalation=i, resolver_kind=resolver_kind, by=by, outcome=outcome)

    # ------------------------------------------------------------ stop
    def request_stop(self, by: str = "principal") -> None:
        self._stop = True
        self._record("stop", by=by)

    # ------------------------------------------------------------ tools
    def authorise(self, tool: str) -> Decision:
        """Decide whether ``tool`` may run now. Never raises for a refusal; logs every decision."""
        try:
            kind = self.manifest.classify(tool)
        except UnknownTool as exc:
            d = Decision(False, None, str(exc))
            self._record("tool_refused", tool=tool, kind=None, reason=d.reason, manifest=self.manifest.version)
            return d
        reason = None
        if self._stop:
            reason = "stop requested"
        elif not self._in_turn:
            reason = "tools run inside a turn"
        elif self._swapping:
            reason = "an adapter swap is under way"
        elif kind == "action":
            if H.canon(self.state) != "lower":
                reason = "actions execute only in execution states (lower canon)"
            elif self.open_escalations:
                reason = "an escalation is open"
        d = Decision(reason is None, kind, reason or "allowed")
        self._record("tool_allowed" if d.allowed else "tool_refused", tool=tool, kind=kind,
                     reason=d.reason, manifest=self.manifest.version)
        return d

    def dispatch(self, tool: str, fn: Callable[..., Any], *args: Any, provenance: str = "", **kwargs: Any) -> Any:
        """Authorise, re-check stop at transport, call ``fn``, and log the result's provenance."""
        d = self.authorise(tool)
        if not d.allowed:
            raise Refused(d.reason)
        if self._stop:  # transport check: a stop raised after authorisation still prevents dispatch
            self._record("tool_refused", tool=tool, kind=d.kind, reason="stop requested at transport")
            raise Refused("stop requested at transport")
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        self._record("tool_done", tool=tool, kind=d.kind, provenance=provenance,
                     latency_ms=round((time.perf_counter() - t0) * 1000, 3))
        return result


def guarded_stream(gate: Gate, chunks: Iterator[Any]) -> Iterator[Any]:
    """Yield generated chunks until a stop is requested; a stop mid-generation ends the stream."""
    for c in chunks:
        if gate.stopped:
            gate._record("generation_stopped")
            return
        yield c
