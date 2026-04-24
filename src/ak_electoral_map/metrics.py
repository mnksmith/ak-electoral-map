"""Compute split-ticket overperformance metrics on the cleaned precinct data.

All metrics operate on a GeoDataFrame whose rows include ``harris_votes``,
``trump_votes``, ``peltola_votes``, ``begich_votes``, ``pres_total``, and
``house_r1_total`` columns — i.e. the output of ``clean.clean()``.

The map shows two primary metrics:

- ``overperformance_pp`` = Peltola R1 share − Harris share, in percentage
  points. Positive means Peltola outran the Democratic Presidential ticket.
- ``splitticket_lb`` = max(0, peltola_votes − harris_votes). Lower bound on the
  count of voters in a precinct who picked Peltola for House and someone other
  than Harris for President. Third-party Presidential share going to Peltola
  first-choice voters is small enough statewide (~1%) to make this a useful
  approximation of the Peltola-Trump crossover population.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd


def _safe_share(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return 100 * numerator / denominator, or NaN where denominator is 0."""
    denom = denominator.where(denominator > 0)
    return 100.0 * numerator / denom


def with_metrics(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Append Peltola-vs-Harris overperformance columns to ``gdf``."""
    out = gdf.copy()
    out["peltola_pct_r1"] = _safe_share(out["peltola_votes"], out["house_r1_total"])
    out["harris_pct"] = _safe_share(out["harris_votes"], out["pres_total"])
    out["trump_pct"] = _safe_share(out["trump_votes"], out["pres_total"])
    out["begich_pct_r1"] = _safe_share(out["begich_votes"], out["house_r1_total"])
    out["overperformance_pp"] = out["peltola_pct_r1"] - out["harris_pct"]
    out["splitticket_lb"] = np.maximum(
        0, out["peltola_votes"].astype(int) - out["harris_votes"].astype(int)
    )
    return out


def statewide_summary(gdf: gpd.GeoDataFrame) -> dict[str, float]:
    """Statewide aggregates (across both precincts and HD-absentee rows)."""
    harris = int(gdf["harris_votes"].sum())
    peltola = int(gdf["peltola_votes"].sum())
    trump = int(gdf["trump_votes"].sum())
    begich = int(gdf["begich_votes"].sum())
    pres_total = int(gdf["pres_total"].sum())
    house_total = int(gdf["house_r1_total"].sum())
    return {
        "harris_votes": harris,
        "trump_votes": trump,
        "peltola_r1_votes": peltola,
        "begich_r1_votes": begich,
        "pres_total": pres_total,
        "house_r1_total": house_total,
        "harris_pct": 100.0 * harris / pres_total,
        "trump_pct": 100.0 * trump / pres_total,
        "peltola_pct_r1": 100.0 * peltola / house_total,
        "begich_pct_r1": 100.0 * begich / house_total,
        "overperformance_pp": 100.0 * (peltola / house_total - harris / pres_total),
        "splitticket_lb": max(0, peltola - harris),
    }


def top_n(
    gdf: gpd.GeoDataFrame,
    column: str,
    n: int = 25,
    row_type: str | None = None,
    ascending: bool = False,
) -> pd.DataFrame:
    """Return the top ``n`` rows by ``column`` (drops geometry), optionally
    filtered to a single ``row_type`` ("precinct" or "hd_absentee")."""
    sub = gdf if row_type is None else gdf[gdf["row_type"] == row_type]
    display_cols = [
        "row_type",
        "precinct_name",
        "house_district",
        "peltola_votes",
        "harris_votes",
        "peltola_pct_r1",
        "harris_pct",
        "overperformance_pp",
        "splitticket_lb",
    ]
    return (
        sub.sort_values(column, ascending=ascending)
        .head(n)
        .loc[:, display_cols]
        .reset_index(drop=True)
    )
