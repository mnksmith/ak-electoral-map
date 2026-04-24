"""Parse the DoE precinct results and join them to precinct geometry.

Produces ``data/processed/precincts_2024.geojson`` and ``.parquet``, containing
two kinds of row:

- ``row_type == "precinct"`` (401 rows): one per geographic precinct, with
  election-day ballot totals and the precinct polygon as geometry.
- ``row_type == "hd_absentee"`` (40 rows): one per Alaska state House District,
  aggregating that HD's Absentee + Early Voting + Question ballot totals, with
  geometry equal to the dissolved union of the HD's precincts.

Together these capture ~100% of certified statewide ballots (minus the small
"HD99 Fed Overseas Absentee" bucket, which has no home HD and is dropped).

Candidate vote columns are named by a canonical short key (``peltola_votes``,
``harris_votes``, etc.) regardless of row type, so downstream metrics code can
operate uniformly on both.
"""

from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

PRES_CONTEST_ID = 4
HOUSE_CONTEST_ID = 7

# Canonical short key → DoE candidate_name string.
PRES_CANDIDATES: dict[str, str] = {
    "harris": "Harris/Walz",
    "trump": "Trump/Vance",
    "kennedy": "Kennedy/Shanahan",
    "oliver": "Oliver/Maat",
    "sonski": "Sonski/Onak",
    "stein": "Stein/Ware",
    "terry": "Terry/Broden",
    "west": "West/Abdullah",
}
HOUSE_CANDIDATES: dict[str, str] = {
    "peltola": "Peltola, Mary S.",
    "begich": "Begich, Nick",
    "howe": "Howe, John Wayne",
    "hafner": "Hafner, Eric",
}

# DoE splits each House District's non-election-day ballots across three
# pseudo-precinct rows: "District N - Absentee", "District N - Early Voting",
# and "District N - Question". These aggregate to ~50% of statewide ballots.
# "HD99 Fed Overseas Absentee" is overseas ballots with no home HD — dropped.
_HD_PSEUDO_RE = re.compile(
    r"^District\s+(?P<hd>\d+)\s*-\s*(?:Absentee|Early Voting|Question)\s*$",
    re.IGNORECASE,
)
_EXCLUDED_MARKERS = ("Fed Overseas",)

_NO_SUFFIX_RE = re.compile(r"\s+No\.\s*\d+\s*$", re.IGNORECASE)

# Known 2022-vintage-shapefile vs 2024-CSV renames / splits. Left side is the
# precinct name in ENRbyPrecinct.csv; right side is the 2022 shapefile's
# Precinct_Name. Add rows here as discrepancies surface.
_CSV_TO_GEO_OVERRIDE = {
    "18-556 JBER No.2": "18-555 JBER",
}


def _canonical_name(name: str) -> str:
    # DoE uses "Pelican-Elfin Cove"; the GIS shapefile uses "Pelican/Elfin Cove".
    return name.replace("/", "-")


def _join_key(name: str) -> str:
    """Case- and sub-precinct-insensitive key for joining results to geometry."""
    name = _CSV_TO_GEO_OVERRIDE.get(name, name)
    return _NO_SUFFIX_RE.sub("", _canonical_name(name)).lower().strip()


def _hd_from_pseudo(name: str) -> int | None:
    m = _HD_PSEUDO_RE.match(name.strip())
    return int(m["hd"]) if m else None


def _is_excluded(name: str) -> bool:
    return any(m in name for m in _EXCLUDED_MARKERS)


# --------------------------------------------------------------------------- #
# Results extraction
# --------------------------------------------------------------------------- #

def _raw_results() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "ENRbyPrecinct.csv")
    df = df[df["Contest_Id"].isin([PRES_CONTEST_ID, HOUSE_CONTEST_ID])]
    df = df[~df["Precinct_name"].map(_is_excluded)].copy()
    return df


def _pivot_contest(
    df: pd.DataFrame,
    contest_id: int,
    candidates: dict[str, str],
    index_col: str,
) -> pd.DataFrame:
    sub = df[df["Contest_Id"] == contest_id]
    wide = sub.pivot_table(
        index=index_col,
        columns="candidate_name",
        values="total_votes",
        aggfunc="sum",
        fill_value=0,
    )
    out = pd.DataFrame(index=wide.index)
    for canonical, source in candidates.items():
        out[f"{canonical}_votes"] = wide.get(source, 0).astype(int)
    return out


def _with_totals(wide: pd.DataFrame) -> pd.DataFrame:
    wide = wide.copy()
    wide["pres_total"] = wide[[f"{k}_votes" for k in PRES_CANDIDATES]].sum(axis=1)
    wide["house_r1_total"] = wide[[f"{k}_votes" for k in HOUSE_CANDIDATES]].sum(axis=1)
    return wide


def build_precinct_table() -> pd.DataFrame:
    """Per-geographic-precinct vote totals (election-day ballots)."""
    df = _raw_results()
    df = df[~df["Precinct_name"].str.match(_HD_PSEUDO_RE)]
    df = df.copy()
    df["Precinct_name"] = df["Precinct_name"].map(_canonical_name)
    pres = _pivot_contest(df, PRES_CONTEST_ID, PRES_CANDIDATES, "Precinct_name")
    house = _pivot_contest(df, HOUSE_CONTEST_ID, HOUSE_CANDIDATES, "Precinct_name")
    wide = _with_totals(pres.join(house, how="outer").fillna(0).astype(int))
    wide.index = wide.index.map(_join_key)
    wide.index.name = "join_key"
    return wide.groupby(level=0).sum().reset_index()


def build_hd_absentee_table() -> pd.DataFrame:
    """Per-House-District vote totals from the Absentee+Early Voting+Question
    pseudo-precinct rows. Returns one row per HD (40 rows for HD 1–40)."""
    df = _raw_results()
    df = df[df["Precinct_name"].str.match(_HD_PSEUDO_RE)].copy()
    df["house_district"] = df["Precinct_name"].map(_hd_from_pseudo).astype(int)
    pres = _pivot_contest(df, PRES_CONTEST_ID, PRES_CANDIDATES, "house_district")
    house = _pivot_contest(df, HOUSE_CONTEST_ID, HOUSE_CANDIDATES, "house_district")
    return _with_totals(pres.join(house, how="outer").fillna(0).astype(int)).reset_index()


# --------------------------------------------------------------------------- #
# Geometry extraction
# --------------------------------------------------------------------------- #

def load_precinct_geometry() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(RAW_DIR / "precincts.geojson")
    gdf = gdf.rename(
        columns={
            "Precinct_Name": "precinct_name",
            "HouseDistrict": "house_district",
            "SenateDistrict": "senate_district",
            "ElectionRegion": "election_region",
        }
    )
    gdf["precinct_name"] = gdf["precinct_name"].map(_canonical_name)
    gdf["join_key"] = gdf["precinct_name"].map(_join_key)
    return gdf[
        [
            "precinct_name",
            "join_key",
            "house_district",
            "senate_district",
            "election_region",
            "geometry",
        ]
    ]


def load_hd_geometry(precincts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Dissolve precinct polygons into one polygon per House District."""
    hd = precincts.dissolve(by="house_district", as_index=False)
    return hd[["house_district", "geometry"]]


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #

def _build_precinct_gdf(
    precinct_geom: gpd.GeoDataFrame, precinct_results: pd.DataFrame
) -> gpd.GeoDataFrame:
    merged = precinct_geom.merge(
        precinct_results, on="join_key", how="inner", validate="1:1"
    )
    dropped_res = set(precinct_results["join_key"]) - set(merged["join_key"])
    if dropped_res:
        print(f"[clean] precinct result rows without geometry "
              f"({len(dropped_res)}): {sorted(dropped_res)}")
    merged = merged.drop(columns=["join_key"])
    merged.insert(0, "row_type", "precinct")
    return merged


def _build_hd_absentee_gdf(
    hd_geom: gpd.GeoDataFrame, hd_results: pd.DataFrame
) -> gpd.GeoDataFrame:
    merged = hd_geom.merge(hd_results, on="house_district", how="inner", validate="1:1")
    merged.insert(0, "row_type", "hd_absentee")
    merged.insert(
        1,
        "precinct_name",
        merged["house_district"].map(lambda hd: f"HD {hd} — Absentee+Early+Question"),
    )
    merged["senate_district"] = pd.NA
    merged["election_region"] = pd.NA
    return merged


def clean() -> gpd.GeoDataFrame:
    """Build the unified GeoDataFrame of precincts + HD-absentee pseudo-rows."""
    precinct_geom = load_precinct_geometry()
    hd_geom = load_hd_geometry(precinct_geom)
    precinct_results = build_precinct_table()
    hd_results = build_hd_absentee_table()

    precinct_gdf = _build_precinct_gdf(precinct_geom, precinct_results)
    hd_gdf = _build_hd_absentee_gdf(hd_geom, hd_results)

    column_order = [
        "row_type",
        "precinct_name",
        "house_district",
        "senate_district",
        "election_region",
        *(f"{k}_votes" for k in PRES_CANDIDATES),
        *(f"{k}_votes" for k in HOUSE_CANDIDATES),
        "pres_total",
        "house_r1_total",
        "geometry",
    ]
    combined = gpd.GeoDataFrame(
        pd.concat(
            [precinct_gdf[column_order], hd_gdf[column_order]],
            ignore_index=True,
        ),
        crs=precinct_geom.crs,
    )
    return combined


def write_processed(gdf: gpd.GeoDataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    geojson_path = PROCESSED_DIR / "precincts_2024.geojson"
    parquet_path = PROCESSED_DIR / "precincts_2024.parquet"
    gdf.to_file(geojson_path, driver="GeoJSON")
    gdf.to_parquet(parquet_path)
    print(f"[clean] wrote {geojson_path.relative_to(REPO_ROOT)} "
          f"({geojson_path.stat().st_size // 1024} KB)")
    print(f"[clean] wrote {parquet_path.relative_to(REPO_ROOT)} "
          f"({parquet_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    gdf = clean()
    counts = gdf["row_type"].value_counts()
    print(f"[clean] {len(gdf)} rows: {counts.to_dict()}")
    write_processed(gdf)
