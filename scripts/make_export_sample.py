"""Make a small, real sample of the public export for building the site offline (export/sample/).

Usage: .venv/bin/python scripts/make_export_sample.py <extracted export dir>
Picks seven real series (with a forecast and a data-error flag; in alert or crisis; reporting irregularly; without
enough data; in a market that stopped reporting; far above the national price; in Niger), filters the indexes to them and rebuilds the manifest with the hashes of the sample files.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(__file__).parents[1] / "export" / "sample"
index = json.loads((src / "index.json").read_text())


def series(sid):
    return json.loads((src / "series" / f"{sid}.json").read_text())


rows = index["series"]
flagged = next(r["id"] for r in rows if r["eligible"] and r["status"] == "stress"
               and any(h["flag"] == "data_error" for h in series(r["id"])["history"]))
severe = next(r["id"] for r in rows if r["eligible"] and r["status"] in ("alert", "crisis"))
irregular = next(r["id"] for r in rows if r["eligible"] and r.get("irregular_reporting") and r["id"] not in (flagged, severe))
too_short = next(r["id"] for r in rows if not r["eligible"] and not r.get("silent_months"))
silent = next(r["id"] for r in rows if r.get("silent_months"))  # 1.4: a market that stopped reporting
far = next(r["id"] for r in rows if r.get("far_above_usual") and r["id"] not in (flagged, severe, irregular))
niger = next(r["id"] for r in rows if r["country"] == "niger" and r["eligible"])  # 1.5: a newly added country
picked = [flagged, severe, irregular, too_short, silent, far, niger]

if dst.exists():
    shutil.rmtree(dst)
(dst / "series").mkdir(parents=True)
(dst / "index").mkdir()
(dst / "downloads").mkdir()
dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
files = {f"series/{sid}.json": (src / "series" / f"{sid}.json").read_bytes() for sid in picked}
files["index.json"] = dump({**index, "series": [r for r in rows if r["id"] in picked]})
for p in sorted((src / "index").glob("*.json")):
    country_index = json.loads(p.read_text())
    keep = [r for r in country_index["series"] if r["id"] in picked]
    if keep:
        files[f"index/{p.name}"] = dump({**country_index, "series": keep})
for name in ["countries.json", "track_record.json", "downloads/README.txt"]:
    files[name] = (src / name).read_bytes()
csv_path = next((src / "downloads").glob("forecasts_*.csv"))
lines = csv_path.read_text().splitlines()
files[f"downloads/{csv_path.name}"] = ("\n".join([lines[0]] + [l for l in lines[1:] if l.split(",")[0] in picked])
                                       + "\n").encode()
manifest = json.loads((src / "manifest.json").read_text())
manifest["counts"] = {"series": len(picked),
                      "series_with_forecast": sum(r["eligible"] for r in rows if r["id"] in picked)}
manifest["files"] = [{"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                     for p, b in sorted(files.items())]
files["manifest.json"] = dump(manifest)
for path, data in files.items():
    (dst / path).write_bytes(data)
(dst / "README.md").write_text(
    "# Export sample\n\n"
    f"A small, real sample of the public export ({len(picked)} series), for building the public site offline. Contract:\n"
    "`docs/export-contract.md`; schemas: `export/schema/`. Regenerate with `scripts/make_export_sample.py`.\n\n"
    "Source: World Food Programme (WFP), food prices via the Humanitarian Data Exchange (HDX), licensed CC BY-IGO 3.0.\n"
    "Forecasts: food-price-watch (not an official WFP or FEWS NET assessment).\n")
print("sample:", picked, "->", dst)
