"""Build notebooks/01_overperformance.ipynb from a declarative cell list.

Keeping the notebook generator under version control means the .ipynb JSON
round-trips cleanly and the source of truth for each cell is a readable Python
string. Run:

    uv run python scripts/build_notebook.py
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "01_overperformance.ipynb"


CELLS: list[tuple[str, str]] = [
    (
        "markdown",
        """
# Alaska 2024: Peltola overperformance vs. Harris

This notebook is the end-to-end pipeline for v1 of the `ak-electoral-map`
project. It fetches the 2024 general election data from the Alaska Division
of Elections and the precinct shapefile from the AK GIS portal, joins them,
computes Peltola-vs-Harris overperformance per precinct (and per House-District
absentee cohort), and writes the static maps and top-N tables published in the
repo.

Running this notebook top-to-bottom reproduces everything under `outputs/` and
`docs/`. It is safe to re-run — fetch is idempotent.
        """.strip(),
    ),
    (
        "code",
        """
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from ak_electoral_map import clean, fetch, metrics

REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUTS = REPO_ROOT / "outputs"
MAPS = OUTPUTS / "maps"
TABLES = OUTPUTS / "tables"
DOCS = REPO_ROOT / "docs"
for d in (MAPS, TABLES, DOCS):
    d.mkdir(parents=True, exist_ok=True)
        """.strip(),
    ),
    (
        "markdown",
        """
## 1. Fetch raw data

Downloads `ENRbyPrecinct.csv`, `ElectionSummaryReport.pdf`, and
`precincts.geojson` into `data/raw/`. Cached on subsequent runs.
        """.strip(),
    ),
    (
        "code",
        """
manifest = fetch.fetch_all()
pd.DataFrame(manifest).T[["filename", "bytes", "retrieved_at"]]
        """.strip(),
    ),
    (
        "markdown",
        """
## 2. Clean and join

Produces a unified GeoDataFrame with 441 rows: 401 geographic precincts
(election-day ballots) + 40 HD-absentee pseudo-precincts (Absentee + Early
Voting + Question ballots aggregated per House District). HD-absentee rows use
the dissolved HD polygon as their geometry.
        """.strip(),
    ),
    (
        "code",
        """
raw_gdf = clean.clean()
clean.write_processed(raw_gdf)
gdf = metrics.with_metrics(raw_gdf)
gdf["row_type"].value_counts()
        """.strip(),
    ),
    (
        "markdown",
        """
## 3. Statewide sanity check

Summed precinct + HD-absentee totals should match DoE certified totals within
~400 votes (the HD99 "Fed Overseas" ballots are dropped — they have no home HD).
        """.strip(),
    ),
    (
        "code",
        """
summary = metrics.statewide_summary(gdf)
pd.Series(summary).to_frame("value")
        """.strip(),
    ),
    (
        "markdown",
        """
## 4. Static maps

Two views:

- **Map A — `overperformance_pp`**: Peltola R1 share minus Harris share, in
  percentage points. Diverging colormap centered on 0. Rows with no ballots
  cast (empty precincts) are shown in grey.
- **Map B — `splitticket_lb`**: lower-bound count of Peltola-Trump crossover
  voters per unit. Sequential colormap, raw count.

The HD-absentee rows are rendered as translucent polygons over the underlying
precincts — visually distinct from the 401 precinct rows, which are drawn
opaquely.
        """.strip(),
    ),
    (
        "code",
        """
# Project to Alaska Albers (EPSG:3338) so Aleutians don't crash into the
# antimeridian and squish Alaska into a sliver. The raw shapefile is WGS84.
gdf_ak = gdf.to_crs("EPSG:3338")
precincts_ak = gdf_ak[gdf_ak["row_type"] == "precinct"]

def render_map(df, column, title, cmap, *, diverging=False, outfile):
    fig, ax = plt.subplots(figsize=(12, 9))
    kwargs = dict(
        column=column, ax=ax, cmap=cmap,
        edgecolor="white", linewidth=0.1,
        legend=True, legend_kwds={"label": title, "shrink": 0.6},
        missing_kwds={"color": "lightgrey"},
    )
    if diverging:
        bound = max(abs(df[column].min()), abs(df[column].max()))
        kwargs.update(vmin=-bound, vmax=bound)
    df.plot(**kwargs)
    ax.set_axis_off()
    ax.set_title(title, fontsize=13, pad=12)
    fig.tight_layout()
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    plt.show()

render_map(
    precincts_ak, "overperformance_pp",
    "Peltola (2024 US House R1) minus Harris (2024 Pres), percentage points",
    cmap="RdBu", diverging=True,
    outfile=MAPS / "overperformance_pp.png",
)
        """.strip(),
    ),
    (
        "code",
        """
render_map(
    precincts_ak, "splitticket_lb",
    "Lower-bound Peltola-Trump crossover voters per precinct (count)",
    cmap="viridis", diverging=False,
    outfile=MAPS / "splitticket_density.png",
)
        """.strip(),
    ),
    (
        "markdown",
        """
## 5. Top-N tables

Top 25 units by each metric, saved as CSV under `outputs/tables/`.
        """.strip(),
    ),
    (
        "code",
        """
tables = {
    "top25_overperformance_pp_precincts.csv":
        metrics.top_n(gdf, "overperformance_pp", n=25, row_type="precinct"),
    "top25_splitticket_lb_precincts.csv":
        metrics.top_n(gdf, "splitticket_lb", n=25, row_type="precinct"),
    "top25_overperformance_pp_hd_absentee.csv":
        metrics.top_n(gdf, "overperformance_pp", n=25, row_type="hd_absentee"),
    "top25_splitticket_lb_hd_absentee.csv":
        metrics.top_n(gdf, "splitticket_lb", n=25, row_type="hd_absentee"),
}
for name, df in tables.items():
    df.to_csv(TABLES / name, index=False, float_format="%.3f")
    print(f"wrote {name} ({len(df)} rows)")

tables["top25_overperformance_pp_precincts.csv"].head(10)
        """.strip(),
    ),
    (
        "code",
        """
tables["top25_splitticket_lb_precincts.csv"].head(10)
        """.strip(),
    ),
    (
        "markdown",
        """
## 6. Interactive folium map

Single choropleth layer of precinct `overperformance_pp`, with each
precinct's tooltip also showing the HD-wide mail-in (absentee + early +
question) Peltola/Harris shares for context. Saved to `docs/index.html`.
        """.strip(),
    ),
    (
        "code",
        """
import branca.colormap as cm
import folium

# Pull the HD-absentee rows out of the combined frame and reshape them into a
# lookup table keyed on house_district, so each precinct's tooltip can surface
# the mail-in numbers for its HD without needing a separate polygon layer.
hd_absentee = gdf[gdf["row_type"] == "hd_absentee"].set_index("house_district")
hd_mailin = hd_absentee[["peltola_pct_r1", "harris_pct", "overperformance_pp"]].rename(
    columns={
        "peltola_pct_r1": "hd_mailin_peltola_pct",
        "harris_pct": "hd_mailin_harris_pct",
        "overperformance_pp": "hd_mailin_overperformance_pp",
    }
).round(2)

# Precinct rows only — the HD-absentee polygons are redundant with HD-wide
# tooltip fields and were visually obscuring the precinct layer.
precincts = gdf[gdf["row_type"] == "precinct"].merge(
    hd_mailin, left_on="house_district", right_index=True, how="left"
)

# Simplify in a planar CRS (EPSG:3338, meters) so the tolerance is meaningful;
# 200 m is fine at web zoom levels and cuts the HTML from ~55 MB to ~3 MB.
wgs = precincts.to_crs("EPSG:3338")
wgs["geometry"] = wgs.geometry.simplify(200, preserve_topology=True)
wgs = wgs.to_crs("EPSG:4326")
wgs = wgs[~wgs.geometry.is_empty & wgs.geometry.notna()].copy()
for col in ["peltola_pct_r1", "harris_pct", "trump_pct", "overperformance_pp"]:
    wgs[col] = wgs[col].round(2)

bound_pp = max(abs(wgs["overperformance_pp"].min()),
               abs(wgs["overperformance_pp"].max()))
pp_scale = cm.LinearColormap(
    ["#b2182b", "#f7f7f7", "#2166ac"],
    vmin=-bound_pp, vmax=bound_pp,
    caption="Peltola R1 % − Harris % (percentage points)",
)

def style_fn(feature):
    v = feature["properties"].get("overperformance_pp")
    return {
        "fillColor": "#bbbbbb" if v is None else pp_scale(v),
        "color": "#ffffff",
        "weight": 0.3,
        "fillOpacity": 0.75,
    }

tooltip_fields = [
    "precinct_name", "house_district",
    "peltola_votes", "harris_votes",
    "peltola_pct_r1", "harris_pct", "trump_pct",
    "overperformance_pp",
    "hd_mailin_peltola_pct", "hd_mailin_harris_pct",
    "hd_mailin_overperformance_pp",
]
tooltip_aliases = [
    "Precinct:", "House District:",
    "Peltola R1 votes:", "Harris votes:",
    "Peltola R1 %:", "Harris %:", "Trump %:",
    "Peltola − Harris (pp):",
    "HD mail-in Peltola R1 %:", "HD mail-in Harris %:",
    "HD mail-in Peltola − Harris (pp):",
]

m = folium.Map(location=[63.0, -152.0], zoom_start=4, tiles="cartodbpositron")
folium.GeoJson(
    wgs,
    style_function=style_fn,
    tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True),
).add_to(m)
pp_scale.add_to(m)

m.save(str(DOCS / "index.html"))
print(f"wrote {DOCS / 'index.html'} ({(DOCS / 'index.html').stat().st_size // 1024} KB)")
m
        """.strip(),
    ),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(src) if kind == "markdown" else nbf.v4.new_code_cell(src)
        for kind, src in CELLS
    ]
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK_PATH)
    print(f"wrote {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
