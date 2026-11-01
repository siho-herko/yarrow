# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Tests for yarrow.escalate: the tool-layer invariants and their mutation tests."""
import unittest

from yarrow import hexmath as H
from yarrow import escalate as E

MANIFEST = E.ToolManifest("test-1", {"read_order": "evidence", "refund": "action", "send_email": "action"})
DECISION = (7, 0)   # 11 Tai — Peace, upper canon
EXECUTION = (6, 1)  # 41, lower canon


def gate(state=DECISION):
    g = E.Gate(MANIFEST, state)
    g.begin_turn(router={"hexagram": "11"})
    return g


class TestCanon(unittest.TestCase):
    def test_states(self):
        self.assertEqual(H.canon(DECISION), "upper")
        self.assertEqual(H.canon(EXECUTION), "lower")

    def test_evidence_allowed_in_decision_state(self):
        self.assertTrue(gate().authorise("read_order").allowed)

    def test_action_refused_in_decision_state(self):
        d = gate().authorise("refund")
        self.assertFalse(d.allowed)
        self.assertIn("execution states", d.reason)

    def test_action_allowed_in_execution_state(self):
        self.assertTrue(gate(EXECUTION).authorise("refund").allowed)

    def test_dispatch_runs_and_logs_provenance(self):
        g = gate()
        out = g.dispatch("read_order", lambda: {"order": 1}, provenance="orders-db v3")
        self.assertEqual(out, {"order": 1})
        self.assertEqual(g.log.records[-1]["event"], "tool_done")
        self.assertEqual(g.log.records[-1]["provenance"], "orders-db v3")


class TestManifest(unittest.TestCase):
    def test_unknown_tool_refused_not_inferred(self):
        d = gate(EXECUTION).authorise("delete_everything")
        self.assertFalse(d.allowed)
        self.assertIsNone(d.kind)

    def test_manifest_rejects_unknown_class(self):
        with self.assertRaises(ValueError):
            E.ToolManifest("bad", {"x": "maybe"})

    def test_manifest_needs_version(self):
        with self.assertRaises(ValueError):
            E.ToolManifest("", {"x": "evidence"})


class TestEscalation(unittest.TestCase):
    def test_open_escalation_blocks_action_not_evidence(self):
        g = gate(EXECUTION)
        g.open_escalation("refund above delegated authority", needs_authority=True)
        self.assertFalse(g.authorise("refund").allowed)
        self.assertTrue(g.authorise("read_order").allowed)

    def test_person_resolves_authority_escalation(self):
        g = gate(EXECUTION)
        i = g.open_escalation("refund above delegated authority", needs_authority=True)
        g.resolve_escalation(i, "person", by="account owner", outcome="approved")
        self.assertTrue(g.authorise("refund").allowed)

    def test_model_review_never_counts_as_authority(self):
        g = gate(EXECUTION)
        i = g.open_escalation("refund above delegated authority", needs_authority=True)
        with self.assertRaises(E.Refused):
            g.resolve_escalation(i, "model", by="larger checkpoint", outcome="approve")
        self.assertEqual(g.open_escalations, [i])
        self.assertIn("model_review", [r["event"] for r in g.log.records])
        self.assertFalse(g.authorise("refund").allowed)

    def test_fact_escalation_resolved_by_evidence(self):
        g = gate(EXECUTION)
        i = g.open_escalation("order status unknown", needs_authority=False)
        g.resolve_escalation(i, "evidence", by="read_order", outcome="shipped")
        self.assertTrue(g.authorise("refund").allowed)


class TestStop(unittest.TestCase):
    def test_stop_refuses_everything(self):
        g = gate(EXECUTION)
        g.request_stop()
        self.assertFalse(g.authorise("read_order").allowed)
        self.assertFalse(g.authorise("refund").allowed)

    def test_stop_honoured_at_transport(self):
        """A stop raised between authorisation and dispatch still prevents the call."""
        g = gate(EXECUTION)
        called = []

        class Racing(E.Gate):
            def authorise(self, tool):
                d = super().authorise(tool)
                self.request_stop(by="principal, during authorisation")
                return d
        r = Racing(MANIFEST, EXECUTION)
        r.begin_turn()
        with self.assertRaises(E.Refused):
            r.dispatch("refund", lambda: called.append(1))
        self.assertEqual(called, [])
        self.assertTrue(g.authorise("refund").allowed)

    def test_stop_mid_generation(self):
        g = gate()

        def chunks():
            for k in range(10):
                if k == 3:
                    g.request_stop()
                yield k
        self.assertEqual(list(E.guarded_stream(g, chunks())), [0, 1, 2])

    def test_stop_mid_escalation(self):
        g = gate(EXECUTION)
        i = g.open_escalation("needs approval", needs_authority=True)
        g.request_stop()
        g.resolve_escalation(i, "person", by="owner", outcome="approved")
        self.assertFalse(g.authorise("refund").allowed)

    def test_stop_mid_swap(self):
        g = gate(EXECUTION)
        g.begin_swap()
        g.request_stop()
        g.end_swap()
        self.assertFalse(g.authorise("refund").allowed)


class TestTransitions(unittest.TestCase):
    def test_transition_at_boundary_with_route_valid_relation(self):
        g = E.Gate(MANIFEST, DECISION)
        g.transition(EXECUTION, cited_relation="changing_inner:3")
        self.assertEqual(g.state, EXECUTION)

    def test_transition_inside_turn_refused(self):
        g = gate()
        with self.assertRaises(E.Refused):
            g.transition(EXECUTION, cited_relation="changing_inner:3")

    def test_transition_without_route_valid_relation_refused(self):
        g = E.Gate(MANIFEST, DECISION)
        with self.assertRaises(E.Refused):
            g.transition(EXECUTION, cited_relation="inversion")

    def test_transition_during_swap_refused(self):
        g = E.Gate(MANIFEST, DECISION)
        g.begin_swap()
        with self.assertRaises(E.Refused):
            g.transition(EXECUTION, cited_relation="changing_inner:3")

    def test_situation_change_needs_no_relation(self):
        g = E.Gate(MANIFEST, DECISION)
        g.transition((7, 1))
        self.assertEqual(g.state, (7, 1))

    def test_tools_only_inside_a_turn(self):
        g = E.Gate(MANIFEST, EXECUTION)
        self.assertFalse(g.authorise("refund").allowed)


class TestReplayLog(unittest.TestCase):
    def test_every_decision_is_logged_with_state_and_canon(self):
        g = gate(EXECUTION)
        g.authorise("refund"); g.authorise("nope")
        g.end_turn(compute={"tokens": 10}, latency_ms=12.5)
        events = [r["event"] for r in g.log.records]
        self.assertEqual(events, ["turn_begin", "tool_allowed", "tool_refused", "turn_end"])
        for r in g.log.records:
            self.assertIn("canon", r); self.assertIn("kingwen", r); self.assertIn("seq", r)


class TestGateCapture(unittest.TestCase):
    """Mutation test: a gate that ignores the canon must fail the canon test."""

    def test_always_allow_gate_is_caught(self):
        class Captured(E.Gate):
            def authorise(self, tool):
                return E.Decision(True, self.manifest.tools.get(tool), "allowed")
        g = Captured(MANIFEST, DECISION)
        g.begin_turn()
        self.assertTrue(g.authorise("refund").allowed)   # the broken gate lets it through …
        self.assertFalse(gate(DECISION).authorise("refund").allowed)   # … the real gate does not


if __name__ == "__main__":
    unittest.main()
