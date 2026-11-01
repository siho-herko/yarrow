# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Tests for yarrow.tiepolicy (proposed plan ruling 33)."""
import unittest

from yarrow import hexmath as H
from yarrow import tiepolicy as T


def fit_maxima(outer_t):
    scores = {i: H.fit(i, outer_t)[1] for i in range(8)}
    top = max(scores.values())
    return [(i, outer_t) for i, s in scores.items() if s == top]


class TestRouteCost(unittest.TestCase):
    def test_order_of_costs(self):
        self.assertEqual(T.route_cost(7, 7), 0)
        self.assertEqual(T.route_cost(7, 6), 1)      # one changed inner line
        self.assertEqual(T.route_cost(7, 0), 2)      # complement
        self.assertIsNotNone(T.route_cost(7, H.successor(7, "fuxi")))

    def test_every_pair_reachable_or_none(self):
        for a in range(8):
            for b in range(8):
                c = T.route_cost(a, b)
                self.assertTrue(c is None or 0 <= c <= 3)


class TestBreakTie(unittest.TestCase):
    """Fixtures are real fit ties (hexmath.fit, default weight)."""

    def test_fixtures_are_ties(self):
        self.assertEqual(fit_maxima(0), [(5, 0), (7, 0)])          # 36 lower, 11 upper
        self.assertEqual(fit_maxima(3), [(4, 3), (5, 3)])          # 42, 37: both lower
        self.assertIn((4, 1), fit_maxima(1)); self.assertIn((7, 1), fit_maxima(1))

    def test_between_canons_decision_first(self):
        self.assertEqual(T.break_tie(fit_maxima(0), (7, 0), artefact_exists=False), (7, 0))

    def test_between_canons_execution_once_artefact_exists(self):
        self.assertEqual(T.break_tie(fit_maxima(0), (7, 0), artefact_exists=True), (5, 0))

    def test_cheapest_route_wins_within_canon(self):
        self.assertEqual(T.route_cost(7, 5), 1)
        self.assertGreater(T.route_cost(7, 4) or 99, 1)
        self.assertEqual(T.break_tie(fit_maxima(3), (7, 3), artefact_exists=True), (5, 3))

    def test_staying_put_is_cheapest(self):
        self.assertEqual(T.break_tie(fit_maxima(5), (5, 5), artefact_exists=False), (5, 5))

    def test_remaining_tie_holds(self):
        # from ☱ Lake [110]: ☳ Thunder [100] and ☰ Heaven [111] are each one changed line away
        self.assertEqual(T.route_cost(6, 4), 1); self.assertEqual(T.route_cost(6, 7), 1)
        self.assertEqual(T.break_tie(fit_maxima(1), (6, 1), artefact_exists=False), "hold")

    def test_empty_holds(self):
        self.assertEqual(T.break_tie([], (0, 0), False), "hold")

    def test_deterministic_under_reordering(self):
        for o in range(8):
            for cur in range(8):
                for art in (False, True):
                    ties = fit_maxima(o)
                    self.assertEqual(T.break_tie(ties, (cur, o), art),
                                     T.break_tie(list(reversed(ties)), (cur, o), art))

    def test_mutation_model_choice_is_not_the_policy(self):
        """A 'policy' that returns the first candidate fails the canon rule on a real tie."""
        first = lambda cands, cur, art: cands[0]
        self.assertNotEqual(first(fit_maxima(0), (7, 0), False), T.break_tie(fit_maxima(0), (7, 0), False))


if __name__ == "__main__":
    unittest.main()
