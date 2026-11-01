<!-- PLACEMENT: circulation-safe -->
# Changelog

## 0.2.0rc1 — November 2026 (release candidate; pre-release tag v0.2.0rc1; 0.2.0 waits on plan rulings 32 and 33 and DQ-15)

- `yarrow.schema` v0.2: the Hexis-S1 question set as data (`s1_schema_v0.2.json`, including the decision artefact v0.2 and the deferred `changing_line_k` and `escalate_target`) and `validate()` with four structural rules: line heads parameterise the trigram heads; the hexagram head is the 8 × 8 product; a change of standpoint cites a route-valid relation; the canon requires or forbids a decision artefact.
- `yarrow.seal` v0.2 (sealing mechanism v0.2): 256-bit salted commitments; OpenTimestamps or RFC 3161 anchors recorded by proof hash; `may_read` false until an anchor is confirmed; reveal checked against the commitment; an append-only, hash-chained registry that lists abandoned seals; the null-derivation code hash, location and seed written with every seal.
- `yarrow.escalate` contract draft v0.2: versioned tool manifest (evidence or action, never inferred); actions only in execution states; open escalations block actions but not evidence; escalations that need authority are resolved only by a person and model review is logged as such (proposal under DQ-15); stop honoured at transport, mid-generation, mid-swap and mid-escalation; transitions only at turn boundaries and only on a route-valid relation; replay log.
- `yarrow.tiepolicy` (proposed plan ruling 33): canon preference by decision-artefact status, then the cheapest route-valid relation, then hold.
- Tests: 108 (36 from 0.1.0 plus 72), including mutation tests for every new check; run on Python 3.9, 3.11 and 3.13.

## 0.1.0 — 15 October 2026

First public release, alongside the Hexis paper v1.0 (https://doi.org/10.5281/zenodo.23393632).

- `yarrow.hexmath` v0.1: trigram and hexagram representation; King Wen lookup; the 32/32 canon partition with decision and execution fibres; changing, derived, opposite, inversion, nuclear and King Wen succession; the Fuxi, King Wen (Later Heaven) and Jeongyeok circles; correspondence, proper position and centrality; `fit` under `wangbi` with `match` and `correspondence` as ablation alternatives; the relation table as versioned data with `route_valid` and `relation`; the yarrow-stalk and coin distributions; `verify()` for mutation testing.
- `tools/check_structure.py`: the paper's standalone checker.
- `tools/regenerate.py` and the generated `yarrow/canon/hexagrams_v1.json`.
