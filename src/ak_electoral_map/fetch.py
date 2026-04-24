"""Download raw source data for the 2024 Alaska general election analysis.

Pulls three files into ``data/raw/``:

- ``ENRbyPrecinct.csv`` — precinct-level vote totals, Alaska DoE
- ``ElectionSummaryReport.pdf`` — statewide totals, Alaska DoE (for sanity cross-check)
- ``precincts.geojson`` — precinct boundaries, AK state GIS portal

Each run also writes ``data/raw/MANIFEST.json`` with URL, retrieval timestamp,
byte count, and sha256 for every file, so the provenance is reproducible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
import truststore

# The AK DoE web server does not send its TLS intermediate cert. Using the OS
# trust store (which does AIA chasing on macOS and Windows) sidesteps the
# resulting chain-build failure without having to ship our own CA bundle.
truststore.inject_into_ssl()

# Some AK state pages 403 requests without a browser-shaped User-Agent.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) "
    "Gecko/20100101 Firefox/125.0"
)


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    filename: str


SOURCES: tuple[Source, ...] = (
    Source(
        name="precinct_results",
        url="https://www.elections.alaska.gov/results/24GENR/ENRbyPrecinct.csv",
        filename="ENRbyPrecinct.csv",
    ),
    Source(
        name="statewide_summary",
        url="https://www.elections.alaska.gov/results/24GENR/ElectionSummaryReport.pdf",
        filename="ElectionSummaryReport.pdf",
    ),
    Source(
        name="precinct_boundaries",
        url="https://gis.data.alaska.gov/datasets/DCCED::precincts.geojson",
        filename="precincts.geojson",
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "MANIFEST.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(source: Source, dest: Path) -> None:
    with requests.get(
        source.url,
        timeout=120,
        headers={"User-Agent": _USER_AGENT},
        stream=True,
    ) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)


def fetch_all(*, force: bool = False) -> dict[str, dict[str, object]]:
    """Download every source into ``data/raw/`` and refresh the manifest.

    If ``force`` is False and a file already exists, it is kept and only the
    manifest entry is refreshed (bytes + sha256, timestamp from file mtime).
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, object]] = {}
    for src in SOURCES:
        dest = RAW_DIR / src.filename
        if force or not dest.exists():
            print(f"[fetch] {src.name}: downloading {src.url}")
            _download(src, dest)
            retrieved_at = datetime.now(timezone.utc).isoformat()
        else:
            print(f"[fetch] {src.name}: reusing cached {dest.name}")
            retrieved_at = datetime.fromtimestamp(
                dest.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        manifest[src.name] = {
            "url": src.url,
            "filename": src.filename,
            "retrieved_at": retrieved_at,
            "bytes": dest.stat().st_size,
            "sha256": _sha256(dest),
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"[fetch] wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return manifest


if __name__ == "__main__":
    fetch_all()
