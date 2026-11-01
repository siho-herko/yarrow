<!-- PLACEMENT: circulation-safe -->
# Yarrow

When a language-model agent is allowed to act, nothing in the usual stack records *how* it is approaching the situation, or stops it acting before a decision exists. Hexis proposes a fixed sixty-four-state structure for that: eight configurations of planning, monitoring and recall on the agent side, paired with eight descriptions of what the situation already supplies, with typed relations between states and a boundary between deciding and executing.

Yarrow is the open-source part of that programme. Version 0.1 shipped `yarrow.hexmath`, the exact arithmetic of the structure, so anyone can check the paper's structural results and build on the same definitions. Version 0.2 (release candidate) adds the router's question schema, a sealing tool for pre-registered configuration, and the escalation invariants enforced at the tool layer.

**Paper:** Herko, S. and Pidcock, C. (2026). *Hexis: a fixed 64-state structure for governing cognitive disposition in language-model agents — definitions, structural results and a pre-registered programme.* Version 1.0. Zenodo. https://doi.org/10.5281/zenodo.23393632

## Status

| Component | State |
| --- | --- |
| `yarrow.hexmath` | **v0.1, released.** Representation, King Wen lookup, the 32/32 canon partition, transformations, the three trigram arrangements, the fit rule, relation typing and the cast distributions, with tests. |
| `tools/check_structure.py` | The standalone checker that accompanies the paper (also deposited with it on Zenodo). |
| `yarrow.schema` | **v0.2, release candidate.** The Hexis-S1 question set as data and a validator for router responses. |
| `yarrow.seal` | **v0.2, release candidate.** Salted commitments, third-party anchors (OpenTimestamps or RFC 3161), an append-only hash-chained registry that lists abandoned seals, and the null-derivation code and seed published with every seal. |
| `yarrow.escalate` | **Contract draft v0.2, release candidate.** Tool manifest (evidence or action), canon enforcement, escalation blocks action, stop at transport, turn-boundary transitions, replay log. Two rules wait on recorded rulings (see the module docstring). |
| `yarrow.tiepolicy` | **Proposed.** A deterministic rule for ties between equally fitting states, shipped for review; it changes with the ruling. |
| `yarrow-s1` (router), `yarrow-tai` (instrument) | Planned; each ships only after it passes its registered gate. |

Nothing in this repository is a result of running an agent. The behavioural claims in the paper are registered tests that have not yet been run.

## Install

```bash
pip install yarrow-ai          # once published; until then:
git clone https://github.com/siho-herko/yarrow && cd yarrow && pip install .
```

Python 3.9 or later; no dependencies.

## Use

```python
from yarrow import hexmath as H

# A state is (inner, outer): the agent's trigram and the context's trigram, as Fuxi indices 0–7.
tai = (7, 0)                      # ☰ Heaven [111] over ☷ Earth [000]
H.kingwen(*tai)                   # 11
H.canon(tai)                      # 'upper'  — a decision state: no tool may execute
H.executable(6, 1)                # True     — 41, an execution state
H.fit(*tai)[1]                    # Fraction(7, 1) at the default centrality weight

# Standpoint transitions must cite a route-valid relation.
H.route_valid(0, 7, "inner_complement")   # True
H.route_valid(0, 7, "inversion")          # False: inversion is reading-only
H.relation((0, 0), (5, 0))                # every tabled relation from 2 to 36
```

## Validate a router response

```python
from yarrow import schema

problems = schema.validate(response, state=(7, 0))   # [] when the response is valid
```

The validator checks form (every question present, probabilities in range, distributions complete) and four structural rules: the trigram heads are the product of the line heads; the hexagram head is the 8 × 8 product of the trigram heads; a change of standpoint cites a route-valid relation; and the state's canon requires a decision artefact (decision states) or forbids one (execution states). It scores nothing.

## Seal before you read

```python
from yarrow.seal import Registry

reg = Registry("seals.jsonl")
secret = reg.seal(config, purpose="R0 gate", null_code=code_bytes,
                  null_code_ref="https://…/null.py", seed=20261101)   # keep `secret` private
# obtain a third-party timestamp (seal.anchor_instructions), then:
reg.record_anchor(secret.seal_id, "opentimestamps", proof_bytes, confirmed=True)
assert reg.may_read(secret.seal_id)
# … run the read …
reg.reveal(secret, config)   # publishes the salt and the configuration
```

## Gate tool calls

```python
from yarrow.escalate import Gate, ToolManifest

gate = Gate(ToolManifest("v1", {"read_order": "evidence", "refund": "action"}), state=(7, 0))
gate.begin_turn()
gate.authorise("read_order").allowed   # True: evidence passes in a decision state
gate.authorise("refund").allowed       # False: actions execute only in execution states
```

## Verify

```bash
python -m unittest discover -s tests -t . -v   # unit, regeneration and mutation tests
python tools/check_structure.py                # the paper's standalone checker
python tools/regenerate.py --check             # committed tables equal a fresh regeneration
```

The mutation tests feed a wrong King Wen table, a flipped line order and a corrupted relation table to `hexmath.verify()` and require each to fail. The tables in `yarrow/canon/` are generated, never edited by hand.

## What is deliberately not here

Thresholds, the read-path rule that decides when a state change is warranted, calibration procedures and any learned parameter. In the programme these are sealed configuration: committed by hash before a test is read and revealed afterwards (paper, chapter L2) — `yarrow.seal` is the tool that does it, and holds no value itself. `hexmath` holds structure only; it carries no interpretation of the figures beyond trigram names and glyphs, and no I Ching text. `yarrow.escalate` enforces boundaries the harness can see; it does not protect actions that bypass the harness.

See `ROADMAP.md` for what comes next and the open design questions.

The Jeongyeok circle is taken from a secondary source and will be checked against a pinned scholarly edition before `hexmath` reaches v1.0.

## Contributing

Issues and pull requests are welcome. Contributions are accepted under Apache 2.0 with a Developer Certificate of Origin sign-off on each commit (`git commit -s`); see [CONTRIBUTING.md](CONTRIBUTING.md). Changes to the relation table follow the programme's rule: they come from an ablation result and a recorded ruling, not from preference.

## Licence and citation

Code: Apache License 2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)). The paper is CC BY 4.0. Please cite the paper; [CITATION.cff](CITATION.cff) gives both the paper and this software.

Contact: Simon Herko, simon.herko@trigrammatic.com.
