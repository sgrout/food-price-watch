"""Make a small, real sample of the basket export (export/sample-baskets/): one basket with a forecast per country.

Usage: .venv/bin/python scripts/make_basket_sample.py <extracted basket export dir>
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(__file__).parents[1] / "export" / "sample-baskets"
dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
files, picked = {}, []
for p in sorted((src / "index").glob("*.json")):
    idx = json.loads(p.read_text())
    keep = next(r for r in idx["baskets"] if r["eligible"])
    picked.append(keep["id"])
    files[f"index/{p.name}"] = dump({**idx, "baskets": [keep]})
    files[f"basket/{keep['id']}.json"] = (src / "basket" / f"{keep['id']}.json").read_bytes()
files["track_record.json"] = (src / "track_record.json").read_bytes()
manifest = json.loads((src / "manifest.json").read_text())
manifest["counts"] = {"baskets": len(picked), "baskets_with_forecast": len(picked)}
manifest["files"] = [{"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p, b in sorted(files.items())]
files["manifest.json"] = dump(manifest)
if dst.exists():
    shutil.rmtree(dst)
for path, data in files.items():
    (dst / path).parent.mkdir(parents=True, exist_ok=True)
    (dst / path).write_bytes(data)
(dst / "README.md").write_text(
    "# Basket export sample\n\nA small, real sample of the optional basket export (one basket per country). Contract:\n"
    "`docs/export-contract.md` section 4b; schemas: `export/schema/basket_*.schema.json`. Regenerate with\n"
    "`scripts/make_basket_sample.py`.\n\nSource: World Food Programme (WFP), food prices via the Humanitarian Data\n"
    "Exchange (HDX), licensed CC BY-IGO 3.0. Baskets and forecasts: Staple Signals (not an official MEB).\n")
print("basket sample:", picked)
