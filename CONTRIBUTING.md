<!-- PLACEMENT: circulation-safe -->
# Contributing to Yarrow

Thank you for helping. A few rules keep the project checkable.

## Sign-off (Developer Certificate of Origin)

Every commit must carry a sign-off line certifying that you wrote the change or otherwise have the right to submit it under the project's licence, as set out in the Developer Certificate of Origin 1.1 (https://developercertificate.org/):

```
Signed-off-by: Your Name <you@example.com>
```

`git commit -s` adds it. Contributions are licensed under Apache 2.0, the project's licence.

## What a change needs

- Tests. Every function in `hexmath` is covered by `tests/`; a new property needs a test, and a new check needs a mutation test that shows it fails on broken input.
- Regenerated tables. Never edit `yarrow/canon/*.json` by hand; change the code and run `python tools/regenerate.py`.
- No thresholds or tuned parameters. `hexmath` holds structure only.

## Changes that need a ruling

The canon partition, the fit rule's form and the relation table define the programme's registered tests. Changes to them are proposed as an issue with the evidence (for the relation table, an ablation result); the project lead records a ruling before a pull request is merged.

## Conduct

Be courteous and specific. We follow the Contributor Covenant, version 2.1 (https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Report problems to simon.herko@trigrammatic.com.
