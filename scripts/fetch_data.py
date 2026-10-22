"""Fetch the immutable public RTS-GMLC inputs; no API key is required."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "3ece0d3725c844056132393ee252b3083dd4eab4"
BASE = f"https://raw.githubusercontent.com/GridMod/RTS-GMLC/{COMMIT}/"
FILES = {
    "upstream_README.md": "README.md",
    "source_schema.md": "RTS_Data/SourceData/README.md",
    "timeseries_schema.md": "RTS_Data/timeseries_data_files/README.md",
    **{f"{n}.csv": f"RTS_Data/SourceData/{n}.csv" for n in ("bus", "branch", "gen")},
    **{
        f"{kind}_{mode}.csv": f"RTS_Data/timeseries_data_files/{folder}/{mode}_{name}.csv"
        for kind, folder, name in [
            ("load", "Load", "regional_Load"),
            ("wind", "WIND", "wind"),
            ("pv", "PV", "pv"),
            ("rtpv", "RTPV", "rtpv"),
        ]
        for mode in ("DAY_AHEAD", "REAL_TIME")
    },
    "hydro_DAY_AHEAD.csv": "RTS_Data/timeseries_data_files/Hydro/DAY_AHEAD_hydro.csv",
}


def main() -> None:
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "data/source_manifest.json"
    expected = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    manifest = {"repository": "https://github.com/GridMod/RTS-GMLC", "commit": COMMIT, "files": {}}
    for name, source in FILES.items():
        path = raw / name
        if not path.exists():
            print(f"Downloading {source}", flush=True)
            with urlopen(BASE + source, timeout=120) as response:
                path.write_bytes(response.read())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected is not None and digest != expected["files"][name]["sha256"]:
            raise ValueError(f"Source checksum mismatch: {name}; remove the corrupt file and retry")
        manifest["files"][name] = {"url": BASE + source, "sha256": digest, "bytes": path.stat().st_size}
    if expected is None:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("All source files available and checksummed.")


if __name__ == "__main__":
    main()
