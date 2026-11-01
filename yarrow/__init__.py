# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Simon Herko and Chris Pidcock
"""Yarrow: the open-source components of the Hexis programme.

Modules: ``yarrow.hexmath`` (the arithmetic of the sixty-four-state structure, contract v0.1);
``yarrow.schema`` (the Hexis-S1 question set, schema v0.2, and its validator); ``yarrow.seal``
(commit-before-read sealing with salt, third-party anchor and an append-only registry);
``yarrow.escalate`` (the escalation invariants at the tool layer); ``yarrow.tiepolicy`` (a proposed
deterministic tie rule). Modules marked draft or proposed in their docstrings wait on a recorded
ruling before the 0.2.0 tag.
"""
__version__ = "0.2.0rc1"
PAPER_DOI = "10.5281/zenodo.23393632"
