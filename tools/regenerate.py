# PLACEMENT: circulation-safe
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the committed tables from yarrow.hexmath. CI byte-compares the output with the
committed files; a difference fails the build, and the committed file is replaced from this
script, never edited by hand.

Usage: python3 tools/regenerate.py [--check]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yarrow import hexmath as H

OUT = Path(__file__).resolve().parents[1] / "yarrow" / "canon" / "hexagrams_v1.json"


def build() -> str:
    states = []
    for n in range(1, 65):
        i, o = H.from_kingwen(n)
        _, total = H.fit(i, o)
        states.append({
            "kingwen": n, "inner": H.label(i), "outer": H.label(o),
            "lines": "".join(map(str, H.lines((i, o)))),
            "canon": H.canon((i, o)), "executable": H.executable(i, o),
            "fit_default": str(total),
        })
    fibres = {H.label(i): {"decision": sorted(H.label(o) for o in H.decision_fibre(i)),
                           "execution": sorted(H.label(o) for o in H.execution_fibre(i))}
              for i in range(8)}
    doc = {"_placement": "circulation-safe", "generated_by": "tools/regenerate.py",
           "lines_note": "bottom to top; 1 yang (explicit), 0 yin (implicit)",
           "fit_note": "rule wangbi at the default centrality weight of 1",
           "states": states, "fibres": fibres}
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text("utf-8") == text
        print("tables match" if ok else "tables differ: run tools/regenerate.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(text, "utf-8"); print("wrote", OUT)
