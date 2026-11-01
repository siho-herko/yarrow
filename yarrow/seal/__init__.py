# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""yarrow.seal — commit to configuration before a read without revealing it (sealing mechanism v0.2).

A sealed configuration (thresholds, read-path parameters, calibration settings) is committed by a
salted hash before any data are read and revealed after the read. The module answers the three
questions a sceptic asks of a hash:

* *Were the values secret until read?* Every seal carries a fresh 256-bit salt, so a file holding a
  few numbers on known scales cannot be recovered from its hash by enumeration. The salt is returned
  to the caller, never written to the registry until the reveal.
* *Is the date real?* A seal is anchored with a third-party timestamp — OpenTimestamps by default,
  an RFC 3161 timestamp authority as the alternative. ``may_read`` is False until an anchor is
  recorded as confirmed. This module records anchors; obtaining the proof is done with the
  anchoring tool itself (``anchor_instructions`` gives the commands), so the library needs no
  network access.
* *Was this the only seal?* The registry is append-only and hash-chained, and lists every seal and
  its fate — sealed, anchored, revealed or abandoned. ``Registry.verify`` fails if a line is
  altered, removed or reordered.

The one thing a seal cannot show — that a threshold came from a null rather than from a look at the
data — is handled by publishing the null-derivation code (its hash and location) and its random
seed with every seal.

What is not here: any threshold or configuration value. The registry holds commitments until a
reveal; values appear only in reveal events, after the read.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

__all__ = ["canonical", "commitment", "Registry", "SealSecret", "RegistryError",
           "anchor_instructions", "ANCHOR_METHODS", "SALT_BYTES"]

SALT_BYTES = 32
ANCHOR_METHODS = ("opentimestamps", "rfc3161")
_GENESIS = "0" * 64


class RegistryError(Exception):
    """The registry is malformed, or an operation would break its rules."""


def canonical(config: Any) -> bytes:
    """Canonical bytes of a JSON-serialisable configuration: sorted keys, no spaces, UTF-8."""
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def commitment(salt: bytes, config: Any) -> str:
    """SHA-256 of salt || canonical(config), hex."""
    if len(salt) != SALT_BYTES:
        raise ValueError(f"salt must be {SALT_BYTES} bytes")
    return hashlib.sha256(salt + canonical(config)).hexdigest()


@dataclass(frozen=True)
class SealSecret:
    """What the sealer keeps privately until the reveal. Never write it to the registry early."""
    seal_id: str
    salt_hex: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _line_hash(entry: Dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(canonical(body)).hexdigest()


def anchor_instructions(commit_hex: str, method: str = "opentimestamps") -> List[str]:
    """Shell commands that obtain a third-party timestamp for a commitment (run outside Python)."""
    if method == "opentimestamps":
        return [f"printf '%s' {commit_hex} > seal_{commit_hex[:12]}.txt",
                f"ots stamp seal_{commit_hex[:12]}.txt",
                f"# after confirmation (hours): ots upgrade seal_{commit_hex[:12]}.txt.ots && ots verify seal_{commit_hex[:12]}.txt.ots"]
    if method == "rfc3161":
        return [f"printf '%s' {commit_hex} > seal_{commit_hex[:12]}.txt",
                f"openssl ts -query -data seal_{commit_hex[:12]}.txt -sha256 -cert -out seal_{commit_hex[:12]}.tsq",
                "# send the .tsq to the chosen timestamp authority and keep the .tsr response"]
    raise ValueError(f"anchor methods are {ANCHOR_METHODS}")


class Registry:
    """An append-only, hash-chained registry of seals, stored as JSON lines.

    Events: ``sealed`` (commitment, purpose, null derivation), ``anchored`` (method, proof hash,
    confirmed), ``revealed`` (salt and configuration, after the read), ``abandoned`` (reason).
    """

    def __init__(self, path: str):
        self.path = path
        if os.path.exists(path):
            self.verify()

    # ------------------------------------------------------------ reading
    def entries(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def verify(self) -> None:
        """Raise RegistryError unless the chain is intact and every event is legal."""
        prev = _GENESIS
        state: Dict[str, str] = {}
        for i, e in enumerate(self.entries()):
            if e.get("seq") != i:
                raise RegistryError(f"line {i}: sequence broken")
            if e.get("prev") != prev:
                raise RegistryError(f"line {i}: chain broken")
            if e.get("hash") != _line_hash(e):
                raise RegistryError(f"line {i}: content altered")
            sid, ev = e.get("seal_id"), e.get("event")
            if ev == "sealed":
                if sid in state:
                    raise RegistryError(f"line {i}: seal {sid} written twice")
                state[sid] = "sealed"
            elif sid not in state:
                raise RegistryError(f"line {i}: event for unknown seal {sid}")
            elif state[sid] in ("revealed", "abandoned"):
                raise RegistryError(f"line {i}: seal {sid} already {state[sid]}")
            elif ev == "anchored":
                if e.get("confirmed"):
                    state[sid] = "anchored"
            elif ev == "revealed":
                if state[sid] != "anchored":
                    raise RegistryError(f"line {i}: seal {sid} revealed before a confirmed anchor")
                sealed = next(x for x in self.entries() if x["seal_id"] == sid and x["event"] == "sealed")
                if commitment(bytes.fromhex(e["salt"]), e["config"]) != sealed["commitment"]:
                    raise RegistryError(f"line {i}: revealed configuration does not match seal {sid}")
                state[sid] = "revealed"
            elif ev == "abandoned":
                state[sid] = "abandoned"
            else:
                raise RegistryError(f"line {i}: unknown event {ev!r}")
            prev = e["hash"]

    def fates(self) -> Dict[str, str]:
        """Seal id → current status: sealed, anchored, revealed or abandoned."""
        self.verify()
        out: Dict[str, str] = {}
        for e in self.entries():
            ev = e["event"]
            if ev == "sealed":
                out[e["seal_id"]] = "sealed"
            elif ev == "anchored" and e.get("confirmed"):
                out[e["seal_id"]] = "anchored"
            elif ev in ("revealed", "abandoned"):
                out[e["seal_id"]] = ev
        return out

    def may_read(self, seal_id: str) -> bool:
        """True only when the seal exists and carries a confirmed anchor and has not been abandoned
        or revealed. A read must not be scheduled before this is True."""
        return self.fates().get(seal_id) == "anchored"

    # ------------------------------------------------------------ writing
    def _require(self, seal_id: str, allowed: Iterable[str]) -> None:
        status = self.fates().get(seal_id)
        if status is None:
            raise RegistryError(f"no seal {seal_id}")
        if status not in allowed:
            raise RegistryError(f"seal {seal_id} is {status}")

    def _append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        self.verify()
        es = self.entries()
        entry = {"seq": len(es), "prev": es[-1]["hash"] if es else _GENESIS, "time": _now(), **event}
        entry["hash"] = _line_hash(entry)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return entry

    def seal(self, config: Any, *, purpose: str, null_code: bytes, null_code_ref: str,
             seed: int, salt: Optional[bytes] = None) -> SealSecret:
        """Commit to ``config``. Returns the secret (keep it private until the reveal).

        ``null_code`` is the exact bytes of the null-derivation code; its SHA-256, ``null_code_ref``
        (where it is published) and ``seed`` are written with the seal.
        """
        if not purpose or not null_code_ref:
            raise ValueError("a seal states its purpose and where its null-derivation code is published")
        if not isinstance(seed, int):
            raise ValueError("the null-derivation seed is an integer")
        salt = secrets.token_bytes(SALT_BYTES) if salt is None else salt
        commit = commitment(salt, config)
        sid = commit[:16]
        self._append({"event": "sealed", "seal_id": sid, "commitment": commit, "purpose": purpose,
                      "null_derivation": {"code_sha256": hashlib.sha256(null_code).hexdigest(),
                                          "code_ref": null_code_ref, "seed": seed}})
        return SealSecret(seal_id=sid, salt_hex=salt.hex())

    def record_anchor(self, seal_id: str, method: str, proof: bytes, confirmed: bool) -> None:
        """Record a third-party timestamp proof for a seal (its SHA-256 is stored, not the proof)."""
        if method not in ANCHOR_METHODS:
            raise ValueError(f"anchor methods are {ANCHOR_METHODS}")
        self._require(seal_id, ("sealed", "anchored"))
        self._append({"event": "anchored", "seal_id": seal_id, "method": method,
                      "proof_sha256": hashlib.sha256(proof).hexdigest(), "confirmed": bool(confirmed)})

    def reveal(self, secret: SealSecret, config: Any) -> None:
        """After the read: publish the salt and the configuration. Fails if they do not match."""
        self._require(secret.seal_id, ("anchored",))
        sealed = next(e for e in self.entries() if e["seal_id"] == secret.seal_id and e["event"] == "sealed")
        if commitment(bytes.fromhex(secret.salt_hex), config) != sealed["commitment"]:
            raise RegistryError("salt and configuration do not match the seal")
        self._append({"event": "revealed", "seal_id": secret.seal_id, "salt": secret.salt_hex,
                      "config": json.loads(canonical(config))})

    def abandon(self, seal_id: str, reason: str) -> None:
        """Record a seal that will never be read. Abandoned seals stay listed."""
        if not reason:
            raise ValueError("an abandoned seal states its reason")
        self._require(seal_id, ("sealed", "anchored"))
        self._append({"event": "abandoned", "seal_id": seal_id, "reason": reason})
