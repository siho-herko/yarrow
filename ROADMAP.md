<!-- PLACEMENT: circulation-safe -->
# Roadmap

Dates are targets, not promises. Each row ships only when its gate passes; the gates and their predicates are registered in the paper (https://doi.org/10.5281/zenodo.23393632) and sealed before any read.

| Version | Contents | Gate | Target |
| --- | --- | --- | --- |
| 0.1.0 | `yarrow.hexmath` v0.1; the paper's checker; regeneration and mutation tests | Structural checks pass; tables regenerate byte-for-byte | Released 15 Oct 2026 |
| 0.2.0 | `yarrow.schema` v0.2; `yarrow.seal` v0.2; `yarrow.escalate` contract v0.2; tie-policy helper | Review by a second engineer; the rulings the draft modules name are recorded; every new check has a mutation test | November 2026 |
| 0.3 | Schema v0.3 (escalation target, if DQ-15 is ruled); integration example in one existing agent runtime; replay-log format documented | Integration test in the runtime; replay log reconstructs a session | Early 2027 |
| 0.4 | Release of the evaluation components after the first pre-registered read: reproduction instructions, the read's code and sealed configuration revealed | The read has run and is published, whatever it shows | By 30 June 2027, if funded |
| `yarrow-s1` | The routing model's weights | Its registered gate, release checks and the base model's licence | Only if the gate passes |
| `yarrow-tai` | The decision-timing instrument | Its registered validation, with held-out items released under the stated withholding | Only if validated |

## Open design questions

1. **Escalation target (DQ-15).** An escalation names its resolver — evidence, deliberation, a more capable model, a trusted model or a person. `yarrow.escalate` implements the proposal that an escalation needing authority is resolved only by a person and that model review never counts as human authority; schema v0.3 would carry the field.
2. **Evidence versus action (proposed plan ruling 32).** A read-only retrieval the harness performs is evidence and may be requested from any state; anything with an effect outside the agent's context is an action. The manifest declares which is which.
3. **Ties (proposed plan ruling 33).** The rule in `yarrow.tiepolicy`.
4. **Decision validity before action, recovery after restart, and the mapping of runtime events to turns.** Raised by an external engineering review; to be settled before any general guarantee is claimed.

## Funded work

Work funded by grants ships here under Apache 2.0 (code) and CC BY 4.0 (documents), with two time-limited withholdings: held-out evaluation items are hash-committed at sealing and released on regeneration or twelve months after first use, whichever is first; pre-registered thresholds are sealed before each read and published with their derivation after it.
