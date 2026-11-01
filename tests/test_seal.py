# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Tests for yarrow.seal: commit, anchor, read gate, reveal, abandonment and tamper detection.

The configuration values below are placeholders chosen for the tests; they are not programme
thresholds.
"""
import hashlib
import itertools
import json
import os
import tempfile
import unittest

from yarrow import seal as S

CONFIG = {"example.margin": 0.07, "example.dwell": 2}   # test placeholders only
NULL_CODE = b"def derive(seed):\n    return 'null distribution'\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "registry.jsonl")
        self.reg = S.Registry(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def sealed(self):
        return self.reg.seal(CONFIG, purpose="test read", null_code=NULL_CODE,
                             null_code_ref="tests/null.py", seed=20261101)


class TestLifecycle(Base):
    def test_seal_writes_no_value_and_no_salt(self):
        sec = self.sealed()
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("0.07", text)
        self.assertNotIn(sec.salt_hex, text)
        e = self.reg.entries()[0]
        self.assertEqual(e["null_derivation"]["code_sha256"], hashlib.sha256(NULL_CODE).hexdigest())
        self.assertEqual(e["null_derivation"]["seed"], 20261101)

    def test_read_gate_waits_for_confirmed_anchor(self):
        sec = self.sealed()
        self.assertFalse(self.reg.may_read(sec.seal_id))
        self.reg.record_anchor(sec.seal_id, "opentimestamps", b"pending proof", confirmed=False)
        self.assertFalse(self.reg.may_read(sec.seal_id))
        self.reg.record_anchor(sec.seal_id, "opentimestamps", b"upgraded proof", confirmed=True)
        self.assertTrue(self.reg.may_read(sec.seal_id))

    def test_reveal_after_anchor(self):
        sec = self.sealed()
        self.reg.record_anchor(sec.seal_id, "rfc3161", b"tsr", confirmed=True)
        self.reg.reveal(sec, CONFIG)
        self.assertEqual(self.reg.fates()[sec.seal_id], "revealed")
        self.assertFalse(self.reg.may_read(sec.seal_id))
        S.Registry(self.path).verify()

    def test_abandoned_seals_stay_listed(self):
        a, b = self.sealed(), self.reg.seal({"x": 1}, purpose="second", null_code=NULL_CODE,
                                            null_code_ref="tests/null.py", seed=1)
        self.reg.abandon(a.seal_id, "design changed before any read")
        self.assertEqual(self.reg.fates(), {a.seal_id: "abandoned", b.seal_id: "sealed"})

    def test_anchor_instructions(self):
        sec = self.sealed()
        commit = self.reg.entries()[0]["commitment"]
        self.assertTrue(any("ots stamp" in c for c in S.anchor_instructions(commit)))
        self.assertTrue(any("openssl ts" in c for c in S.anchor_instructions(commit, "rfc3161")))
        self.assertTrue(sec.seal_id)


class TestRefusals(Base):
    """Mutation tests: each rule must fail on input broken in exactly that way."""

    def test_reveal_before_anchor_refused(self):
        sec = self.sealed()
        with self.assertRaises(S.RegistryError):
            self.reg.reveal(sec, CONFIG)

    def test_reveal_with_wrong_configuration_refused(self):
        sec = self.sealed()
        self.reg.record_anchor(sec.seal_id, "opentimestamps", b"p", confirmed=True)
        with self.assertRaises(S.RegistryError):
            self.reg.reveal(sec, {"example.margin": 0.08, "example.dwell": 2})

    def test_reveal_with_wrong_salt_refused(self):
        sec = self.sealed()
        self.reg.record_anchor(sec.seal_id, "opentimestamps", b"p", confirmed=True)
        with self.assertRaises(S.RegistryError):
            self.reg.reveal(S.SealSecret(sec.seal_id, "00" * 32), CONFIG)

    def test_no_events_after_abandonment(self):
        sec = self.sealed()
        self.reg.abandon(sec.seal_id, "superseded")
        with self.assertRaises(S.RegistryError):
            self.reg.record_anchor(sec.seal_id, "opentimestamps", b"p", confirmed=True)

    def test_seal_requires_null_derivation(self):
        with self.assertRaises(ValueError):
            self.reg.seal(CONFIG, purpose="x", null_code=NULL_CODE, null_code_ref="", seed=1)

    def _rewrite(self, transform):
        with open(self.path, encoding="utf-8") as f:
            lines = transform(f.read().splitlines())
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def test_altered_line_detected(self):
        sec = self.sealed()
        self.reg.abandon(sec.seal_id, "reason one")
        self._rewrite(lambda ls: [ls[0], ls[1].replace("reason one", "reason two")])
        with self.assertRaises(S.RegistryError):
            S.Registry(self.path)

    def test_removed_line_detected(self):
        a = self.sealed()
        self.reg.seal({"x": 2}, purpose="second", null_code=NULL_CODE, null_code_ref="r", seed=2)
        self.reg.abandon(a.seal_id, "quietly dropped")
        self._rewrite(lambda ls: [ls[0], ls[1]])   # remove the abandonment
        S.Registry(self.path)                       # a truncated tail is still a valid prefix …
        self._rewrite(lambda ls: [ls[1]])           # … but removing an earlier line is not
        with self.assertRaises(S.RegistryError):
            S.Registry(self.path)

    def test_reordered_lines_detected(self):
        self.sealed()
        self.reg.seal({"x": 3}, purpose="second", null_code=NULL_CODE, null_code_ref="r", seed=3)
        self._rewrite(lambda ls: [ls[1], ls[0]])
        with self.assertRaises(S.RegistryError):
            S.Registry(self.path)


class TestSaltMatters(unittest.TestCase):
    def test_unsalted_hash_is_recoverable_salted_is_not(self):
        """Why the salt exists: a few values on known scales are found by enumeration from a bare hash."""
        grid = [round(0.01 * i, 2) for i in range(101)]
        target = {"example.margin": 0.07, "example.dwell": 2}
        bare = hashlib.sha256(S.canonical(target)).hexdigest()
        salted = S.commitment(os.urandom(32), target)

        def search(h):
            for m, d in itertools.product(grid, range(10)):
                if hashlib.sha256(S.canonical({"example.margin": m, "example.dwell": d})).hexdigest() == h:
                    return (m, d)
            return None
        self.assertEqual(search(bare), (0.07, 2))
        self.assertIsNone(search(salted))

    def test_canonical_is_order_independent(self):
        self.assertEqual(S.canonical({"a": 1, "b": 2}), S.canonical(json.loads('{"b": 2, "a": 1}')))


if __name__ == "__main__":
    unittest.main()
