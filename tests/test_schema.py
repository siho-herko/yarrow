# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Tests for yarrow.schema v0.2: valid responses pass; each deliberately broken response fails."""
import copy
import unittest

from yarrow import hexmath as H
from yarrow import schema as S


def make_response(ps, state, next_choice="hold", cited=None, artefact="auto"):
    """A valid response whose heads are exact products of the line probabilities ``ps``."""
    def tri(p3):
        d = S._trigram_product(tuple(p3))
        c = max(d, key=d.get)
        return {"distribution": d, "choice": c, "confidence": d[c]}
    inner, outer = tri(ps[:3]), tri(ps[3:])
    hexd = {}
    for i in range(8):
        for o in range(8):
            hexd[str(H.kingwen(i, o))] = inner["distribution"][str(i)] * outer["distribution"][str(o)]
    hc = str(H.kingwen(int(inner["choice"]), int(outer["choice"])))
    nxt = {k: 0.0 for k in [str(t) for t in range(8)] + ["hold", "escalate"]}
    nxt[next_choice] = 1.0
    r = {f"line_{k + 1}": {"p": p} for k, p in enumerate(ps)}
    r.update({
        "inner_trigram": inner, "outer_trigram": outer,
        "hexagram": {"distribution": hexd, "choice": hc, "confidence": hexd[hc]},
        "next_standpoint": {"distribution": nxt, "choice": next_choice, "confidence": 1.0},
        "out_of_scope": {"p": 0.05}, "needs_deliberation": {"p": 0.1}, "role_conflict": {"p": 0.02},
    })
    if cited is not None:
        r["cited_relation"] = cited
    if artefact == "auto":
        if H.canon(state) == "upper":
            r["decision_artefact"] = {
                "options": [{"id": "a", "description": "request the order record"},
                            {"id": "b", "description": "ask the principal"}],
                "disposition": "choose", "choice": "a", "timing": "before any action this turn",
                "confidence": 0.7,
            }
    return r


TAI = (7, 0)    # 11 Tai — Peace: upper canon (decision state)
SUN = (6, 1)    # 41: lower canon (execution state)
PS_TAI = [0.9, 0.8, 0.95, 0.1, 0.2, 0.15]
PS_SUN = [0.9, 0.8, 0.1, 0.1, 0.2, 0.85]


class TestSchemaFile(unittest.TestCase):
    def test_loads_and_names_every_question(self):
        s = S.load()
        self.assertEqual(s["version"], S.SCHEMA_VERSION)
        ids = [q["id"] for q in s["questions"]]
        for q in ["line_1", "line_6", "inner_trigram", "outer_trigram", "hexagram",
                  "next_standpoint", "out_of_scope", "needs_deliberation", "role_conflict",
                  "deliberation_outcome"]:
            self.assertIn(q, ids)
        self.assertIn("escalate_target", [d["id"] for d in s["deferred"]])

    def test_canon_of_fixtures(self):
        self.assertEqual(H.canon(TAI), "upper")
        self.assertEqual(H.canon(SUN), "lower")


class TestValid(unittest.TestCase):
    def test_decision_state_with_artefact(self):
        self.assertEqual(S.validate(make_response(PS_TAI, TAI), TAI), [])

    def test_execution_state_without_artefact(self):
        self.assertEqual(S.validate(make_response(PS_SUN, SUN), SUN), [])

    def test_route_valid_transition(self):
        r = make_response(PS_TAI, TAI, next_choice="0", cited="inner_complement")
        self.assertEqual(S.validate(r, TAI), [])

    def test_escalate_needs_no_relation(self):
        r = make_response(PS_TAI, TAI, next_choice="escalate")
        self.assertEqual(S.validate(r, TAI), [])

    def test_abstain_artefact(self):
        r = make_response(PS_TAI, TAI)
        r["decision_artefact"].update({"disposition": "abstain", "choice": None})
        self.assertEqual(S.validate(r, TAI), [])


class TestBroken(unittest.TestCase):
    """Mutation tests: each check must fail on input broken in exactly that way."""

    def assertRejected(self, r, state, fragment):
        problems = S.validate(r, state)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_missing_question(self):
        r = make_response(PS_TAI, TAI); del r["role_conflict"]
        self.assertRejected(r, TAI, "role_conflict: missing")

    def test_probability_out_of_range(self):
        r = make_response(PS_TAI, TAI); r["out_of_scope"]["p"] = 1.2
        self.assertRejected(r, TAI, "out_of_scope")

    def test_distribution_not_summing_to_one(self):
        r = make_response(PS_TAI, TAI); r["next_standpoint"]["distribution"]["hold"] = 0.5
        self.assertRejected(r, TAI, "sum to 1")

    def test_trigram_not_product_of_lines(self):
        r = make_response(PS_TAI, TAI); r["line_1"]["p"] = 0.2
        self.assertRejected(r, TAI, "inner_trigram: distribution is not the product")

    def test_flat_hexagram_head(self):
        r = make_response(PS_TAI, TAI)
        r["hexagram"]["distribution"] = {str(n): 1 / 64 for n in range(1, 65)}
        self.assertRejected(r, TAI, "8 x 8 product")

    def test_hexagram_choice_disagrees_with_trigrams(self):
        r = make_response(PS_TAI, TAI); r["hexagram"]["choice"] = "12"
        self.assertRejected(r, TAI, "King Wen number")

    def test_transition_without_relation(self):
        r = make_response(PS_TAI, TAI, next_choice="0")
        self.assertRejected(r, TAI, "route-valid")

    def test_transition_citing_reading_only_relation(self):
        r = make_response(PS_TAI, TAI, next_choice="0", cited="opposite")
        self.assertRejected(r, TAI, "route-valid")

    def test_transition_citing_wrong_relation(self):
        r = make_response(PS_TAI, TAI, next_choice="3", cited="inner_complement")
        self.assertRejected(r, TAI, "route-valid")

    def test_decision_state_without_artefact(self):
        r = make_response(PS_TAI, TAI, artefact=None)
        self.assertRejected(r, TAI, "required in a decision state")

    def test_execution_state_with_artefact(self):
        r = make_response(PS_SUN, SUN)
        r["decision_artefact"] = copy.deepcopy(make_response(PS_TAI, TAI)["decision_artefact"])
        self.assertRejected(r, SUN, "forbidden in an execution state")

    def test_artefact_choice_not_an_option(self):
        r = make_response(PS_TAI, TAI); r["decision_artefact"]["choice"] = "z"
        self.assertRejected(r, TAI, "decision_artefact.choice")

    def test_escalation_without_reason(self):
        r = make_response(PS_TAI, TAI)
        r["decision_artefact"].update({"disposition": "escalate", "choice": None})
        self.assertRejected(r, TAI, "escalate_reason")

    def test_deliberation_outcome_before_s2_design(self):
        r = make_response(PS_TAI, TAI); r["deliberation_outcome"] = {"choice": "x"}
        self.assertRejected(r, TAI, "deliberation_outcome")


if __name__ == "__main__":
    unittest.main()
