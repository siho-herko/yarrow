# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Tests for yarrow.hexmath (contract v0.1, section 7). Run: python3 -m unittest -v"""
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

from yarrow import hexmath as H

ROOT = Path(__file__).resolve().parents[1]
ALL = [(i, o) for i in range(8) for o in range(8)]


class Representation(unittest.TestCase):
    def test_kingwen_is_a_permutation(self):
        self.assertEqual(sorted(H.kingwen(i, o) for i, o in ALL), list(range(1, 65)))

    def test_round_trips(self):
        for h in ALL:
            self.assertEqual(H.from_lines(H.lines(h)), h)
            self.assertEqual(H.from_kingwen(H.kingwen(*h)), h)

    def test_anchors(self):
        self.assertEqual(H.kingwen(7, 0), 11)   # 11 Tai: inner Heaven, outer Earth
        self.assertEqual(H.kingwen(0, 7), 12)   # 12 Pi
        self.assertEqual(H.kingwen(5, 2), 63)   # 63 Jiji
        self.assertEqual(H.kingwen(2, 5), 64)   # 64 Weiji
        self.assertEqual(H.label(5), "☲ Fire [101]")

    def test_bad_input(self):
        for bad in [(8, 0), (0, -1), (1,), "x"]:
            with self.assertRaises(ValueError):
                H.lines(bad)


class CanonPartition(unittest.TestCase):
    def test_32_32(self):
        self.assertEqual(sum(H.canon(h) == "upper" for h in ALL), 32)
        self.assertEqual(sum(H.canon(h) == "lower" for h in ALL), 32)

    def test_fibre_sizes(self):
        dec = {7: 6, 6: 2, 5: 3, 4: 6, 3: 3, 2: 4, 1: 2, 0: 6}
        for i, n in dec.items():
            self.assertEqual(len(H.decision_fibre(i)), n)
            self.assertEqual(len(H.execution_fibre(i)), 8 - n)

    def test_inversion_keeps_the_canon(self):
        for h in ALL:
            self.assertEqual(H.canon(h), H.canon(H.inversion(h)))

    def test_nuclear_can_cross(self):
        self.assertEqual(H.canon((7, 0)), "upper")
        self.assertEqual(H.kingwen(*H.nuclear((7, 0))), 54)
        self.assertEqual(H.canon(H.nuclear((7, 0))), "lower")

    def test_executable(self):
        self.assertFalse(H.executable(7, 0))   # 11 Tai, decision state
        self.assertTrue(H.executable(6, 1))    # 41 Sun, execution state


class Fit(unittest.TestCase):
    def test_correspondence_inversion_invariant(self):
        for h in ALL:
            self.assertEqual(sum(H.correspondence(h)), sum(H.correspondence(H.inversion(h))))

    def test_wangbi_not_inversion_invariant(self):
        self.assertTrue(any(H.fit(*h)[1] != H.fit(*H.inversion(h))[1] for h in ALL))

    def test_proper_under_inversion(self):
        for h in ALL:
            self.assertEqual(sum(H.proper(H.inversion(h))), 6 - sum(H.proper(h)))

    def test_ordering_properties(self):
        self.assertGreater(H.fit(7, 0)[1], H.fit(0, 7)[1])   # 11 Tai above 12 Pi
        self.assertGreater(H.fit(5, 2)[1], H.fit(2, 5)[1])   # 63 Jiji above 64 Weiji
        doubled = [H.fit(t, t, "match")[1] for t in range(8)]
        self.assertEqual(set(doubled), {max(H.fit(*h, "match")[1] for h in ALL)})

    def test_all_proper_state(self):
        self.assertEqual([h for h in ALL if all(H.proper(h))], [(5, 2)])

    def test_per_line_sums_to_total(self):
        for h in ALL:
            for w in (1, 2, Fraction(3, 2)):
                per, total = H.fit(*h, w_central=w)
                self.assertEqual(sum(per), total)

    def test_weight_below_one_rejected(self):
        with self.assertRaises(ValueError):
            H.fit(0, 0, w_central=Fraction(1, 2))

    def test_worked_examples(self):
        # the refund example and the second example of the paper (U5.2, U7, L4)
        self.assertEqual(H.fit(0, 0)[1], 3)
        best = lambda o: max(H.fit(i, o)[1] for i in range(8))
        tied = lambda o: sorted(H.kingwen(i, o) for i in range(8) if H.fit(i, o)[1] == best(o))
        self.assertEqual((best(0), tied(0)), (7, [11, 36]))
        self.assertEqual(H.fit(7, 1)[1], 5)
        self.assertEqual(best(1), 5)
        self.assertEqual([n for n in tied(1) if n > 32], [41])
        self.assertEqual(H.fit(0, 4)[1], 3)
        self.assertEqual((best(4), tied(4)), (5, [32, 34, 55, 62]))


class Arrangements(unittest.TestCase):
    def test_permutations(self):
        for a in ("fuxi", "kingwen", "jeongyeok"):
            self.assertEqual(sorted(H.arrangement(a)), list(range(8)))

    def test_opposites(self):
        self.assertTrue(H.opposite_is_complement("fuxi"))
        self.assertFalse(H.opposite_is_complement("kingwen"))
        self.assertTrue(H.opposite_is_complement("jeongyeok"))

    def test_jeongyeok_not_dihedral_image_of_fuxi(self):
        fx = H.arrangement("fuxi")
        images = [[fx[(i + k) % 8] for i in range(8)] for k in range(8)]
        images += [list(reversed(x)) for x in images]
        self.assertNotIn(H.arrangement("jeongyeok"), images)

    def test_shuogua_order_is_kingwen_cycle(self):
        kw = H.arrangement("kingwen")
        order = [4, 3, 5, 0, 6, 7, 2, 1]   # ☳ ☴ ☲ ☷ ☱ ☰ ☵ ☶
        i = kw.index(order[0])
        self.assertEqual([kw[(i + k) % 8] for k in range(8)], order)

    def test_hamming_profiles_reported(self):
        for a in ("fuxi", "kingwen", "jeongyeok"):
            c = H.arrangement(a)
            steps = [bin(c[i] ^ c[(i + 1) % 8]).count("1") for i in range(8)]
            print(f"\n{a} Hamming step profile (reported, not asserted): {steps}", end="")


class Relations(unittest.TestCase):
    def test_route_valid_accepts_route_relations(self):
        self.assertTrue(H.route_valid(0, 7, "inner_complement"))
        self.assertTrue(H.route_valid(0, 5, "predecessor:kingwen"))   # ☷ → ☲ on the Later Heaven circle
        self.assertTrue(H.route_valid(0, 3, "predecessor:jeongyeok"))
        self.assertTrue(H.route_valid(7, 6, "changing_inner:3"))

    def test_route_valid_rejects_reading_relations(self):
        for rel in ("opposite", "inversion", "nuclear", "derived", "kingwen_successor", "changing_outer:4"):
            self.assertFalse(H.route_valid(0, 7, rel))

    def test_route_valid_rejects_wrong_target(self):
        self.assertFalse(H.route_valid(0, 6, "inner_complement"))

    def test_route_relations_map_inner_to_inner(self):
        for a in ALL:
            for b in ALL:
                for rel in H.relation(a, b):
                    if H.relation_table().get(H._family(rel)) == "route-valid":
                        self.assertEqual(a[1], b[1])

    def test_table_is_data(self):
        data = json.loads((ROOT / "yarrow" / "canon" / "relations_v1.json").read_text("utf-8"))
        self.assertEqual(data["version"], 1)


class Cast(unittest.TestCase):
    def test_sums_to_one(self):
        self.assertEqual(sum(H.cast("yarrow").values()), 1)
        self.assertEqual(sum(H.cast("coin").values()), 1)

    def test_asymmetry_differs(self):
        y, c = H.cast("yarrow"), H.cast("coin")
        self.assertNotEqual(y[9] - y[6], c[9] - c[6])

    def test_sample(self):
        import random
        h, moving = H.sample("yarrow", random.Random(0))
        self.assertIn(h, ALL)
        self.assertTrue(all(1 <= k <= 6 for k in moving))


class Mutation(unittest.TestCase):
    """Each deliberately broken input must make verification fail."""

    def test_verify_passes(self):
        H.verify()

    def test_wrong_kingwen_table(self):
        bad = [row[:] for row in H._TABLE]
        bad[0][4], bad[4][0] = bad[4][0], bad[0][4]   # swap 11 and 12
        with self.assertRaises(AssertionError):
            H.verify(table=bad)

    def test_flipped_line_order(self):
        with self.assertRaises(AssertionError):
            H.verify(order=list(reversed(H._ORDER)))

    def test_corrupted_relation_file(self):
        rel = H.relation_table(); rel["inversion"] = "route-valid"
        with self.assertRaises(AssertionError):
            H.verify(relations=rel)


class Regeneration(unittest.TestCase):
    def test_committed_tables_match(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "regenerate.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_standalone_checker_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_structure.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
