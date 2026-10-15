<!-- PLACEMENT: circulation-safe -->
# Yarrow

When a language-model agent is allowed to act, nothing in the usual stack records *how* it is approaching the situation, or stops it acting before a decision exists. Hexis proposes a fixed sixty-four-state structure for that: eight configurations of planning, monitoring and recall on the agent side, paired with eight descriptions of what the situation already supplies, with typed relations between states and a boundary between deciding and executing.

Yarrow is the open-source part of that programme. Version 0.1 ships `yarrow.hexmath`, the exact arithmetic of the structure, so anyone can check the paper's structural results and build on the same definitions.

**Paper:** Herko, S. and Pidcock, C. (2026). *Hexis: a fixed 64-state structure for governing cognitive disposition in language-model agents — definitions, structural results and a pre-registered programme.* Version 1.0. Zenodo. https://doi.org/10.5281/zenodo.23393632

## Status

| Component | State |
| --- | --- |
| `yarrow.hexmath` | **v0.1, released here.** Representation, King Wen lookup, the 32/32 canon partition, transformations, the three trigram arrangements, the fit rule, relation typing and the cast distributions, with tests. |
| `tools/check_structure.py` | The standalone checker that accompanies the paper (also deposited with it on Zenodo). |
| `yarrow.schema`, `yarrow.seal`, `yarrow.escalate` | Planned (paper, chapter L5). |
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

## Verify

```bash
python -m unittest discover -s tests -t . -v   # unit, regeneration and mutation tests
python tools/check_structure.py                # the paper's standalone checker
python tools/regenerate.py --check             # committed tables equal a fresh regeneration
```

The mutation tests feed a wrong King Wen table, a flipped line order and a corrupted relation table to `hexmath.verify()` and require each to fail. The tables in `yarrow/canon/` are generated, never edited by hand.

## What is deliberately not here

Thresholds, the read-path rule that decides when a state change is warranted, calibration procedures and any learned parameter. In the programme these are sealed configuration: committed by hash before a test is read and revealed afterwards (paper, chapter L2). `hexmath` holds structure only; it carries no interpretation of the figures beyond trigram names and glyphs, and no I Ching text.

The Jeongyeok circle is taken from a secondary source and will be checked against a pinned scholarly edition before `hexmath` reaches v1.0.

## Contributing

Issues and pull requests are welcome. Contributions are accepted under Apache 2.0 with a Developer Certificate of Origin sign-off on each commit (`git commit -s`); see [CONTRIBUTING.md](CONTRIBUTING.md). Changes to the relation table follow the programme's rule: they come from an ablation result and a recorded ruling, not from preference.

## Licence and citation

Code: Apache License 2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)). The paper is CC BY 4.0. Please cite the paper; [CITATION.cff](CITATION.cff) gives both the paper and this software.

Contact: Simon Herko, simon.herko@trigrammatic.com.
