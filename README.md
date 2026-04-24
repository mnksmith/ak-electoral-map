# ak-electoral-map

Precinct-level analysis of Alaska's 2024 general election, focused on **where Mary Peltola (US House, D) outperformed Kamala Harris (US President, D)** on the same ballot — i.e. the geography of Peltola-Trump split-ticket voters.

> **Interactive map:** https://mnksmith.github.io/ak-electoral-map/ (enabled after first Pages build)

## Why

Alaska's recent elections show unusual split-ticket behavior. In 2024, Peltola lost the US House seat by ~2.5 pts while Harris lost the presidential race by ~13 pts — meaning a large universe of Alaskans picked Peltola for House *and* Trump for President on the same ballot. Those voters are the most addressable persuasion universe for a statewide Democratic campaign.

This repo maps that geography at the most granular level publicly available and surfaces the precincts and House Districts where split-ticket behavior is most concentrated.

## Headline findings (2024 general, v1)

| Metric | Value |
| --- | --- |
| Statewide Peltola R1 share | 46.44% |
| Statewide Harris share | 41.36% |
| Statewide Peltola overperformance | **+5.09 pts** |
| Lower-bound Peltola-Trump voter count | **~12,844** |
| Precincts where Peltola R1 > Harris | 387 / 401 |
| Election-day Peltola overperformance (vs Harris) | +10,129 votes |
| Absentee/early Peltola overperformance | +2,715 votes |

Split-ticket signal is materially stronger on election day than among absentee voters — the in-person electorate leaned Peltola-Trump ~4× more than the absentee electorate did.

### Where the overperformance is concentrated

- **By rate (percentage points):** Western Alaska Native villages dominate. Top 5 precincts by `overperformance_pp` are all in HDs 37–40 (Bristol Bay, Yukon-Kuskokwim Delta, North Slope, Northwest Arctic), with deltas of +28 to +52 pts. See `outputs/tables/top25_overperformance_pp_precincts.csv`.
- **By raw vote count:** urban precincts dominate because they're bigger. Top precinct is **40-010 Browerville** (Utqiaġvik, ~128 split-ticket lower bound), followed by several University/Fairbanks precincts (80–100 each) and larger Anchorage/Kodiak precincts. See `outputs/tables/top25_splitticket_lb_precincts.csv`.

Static maps live in `outputs/maps/`:

- [`overperformance_pp.png`](outputs/maps/overperformance_pp.png) — Peltola R1 % minus Harris %, diverging colormap.
- [`splitticket_density.png`](outputs/maps/splitticket_density.png) — lower-bound Peltola-Trump voter count per precinct, sequential colormap.

## Methodology (v1)

**Sources**
- 2024 precinct results: [Alaska Division of Elections, 24GENR `ENRbyPrecinct.csv`](https://www.elections.alaska.gov/results/24GENR/).
- Precinct boundaries: [AK GIS portal, DCCED "Precincts" feature layer](https://gis.data.alaska.gov/datasets/DCCED::precincts/about) (2022-05-24 vintage; see caveats).
- Statewide cross-check: `ElectionSummaryReport.pdf` from the same DoE folder.

All raw downloads are committed to the manifest (`data/raw/MANIFEST.json` with URL + timestamp + sha256) and re-fetchable via `uv run python -m ak_electoral_map.fetch`.

**How Peltola overperformance is computed**
- `peltola_pct_r1` uses Peltola's **Round 1 first-choice** RCV votes — the cleanest analog to plurality Presidential share and the most direct read on baseline preference.
- `harris_pct` uses Harris's Presidential plurality share.
- `overperformance_pp = peltola_pct_r1 − harris_pct` (percentage points).
- `splitticket_lb = max(0, peltola_votes − harris_votes)`: the lower-bound count of Peltola-Trump voters per unit. Treats third-party Presidential votes that went to Peltola-R1 voters as negligible (they are: Stein/Oliver combined ~1% statewide).

**How absentee ballots are handled**
Alaska's DoE reports election-day ballots at the precinct level, but Absentee + Early Voting + Question ballots are only reported at the state House District level (40 HDs, each containing ~10 precincts). Roughly 50% of all statewide ballots fall into the absentee/early bucket.

v1 treats each HD's Absentee + Early + Question ballots as its own **pseudo-precinct** row (40 rows, geometry = dissolved HD polygon). The dataset thus contains:

- 401 geographic precincts (election-day ballots only)
- 40 HD-absentee pseudo-precincts (all non-election-day ballots for that HD)

Together they capture ~100% of certified statewide ballots, minus the small "HD99 Fed Overseas Absentee" bucket (voters with no home HD), which is dropped.

On the interactive map, HD-absentee polygons render with dashed black boundaries and lower opacity to visually distinguish them from real precincts.

## Reproduce locally

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnksmith/ak-electoral-map.git
cd ak-electoral-map
uv sync
uv run jupyter lab notebooks/01_overperformance.ipynb   # interactive
# or run the whole pipeline headlessly:
uv run jupyter nbconvert --to notebook --execute \
    notebooks/01_overperformance.ipynb --output 01_overperformance.ipynb
```

The notebook fetches all raw data on first run and caches it under `data/raw/`. Re-running regenerates `data/processed/`, `outputs/`, and `docs/index.html`.

## Caveats

- **Precinct boundaries are 2022-vintage.** The AK GIS portal's DCCED "Precincts" feature layer has `AsOfDate = 2022-05-24`. The 2023 redistricting proclamation was implemented for 2024 elections, so a small number of precincts were split/renamed (notably the JBER area). Four 2024 precincts without a 2022 polygon are handled via explicit overrides in `src/ak_electoral_map/clean.py`. A v1.1 could upgrade to a 2024-vintage shapefile once the state republishes.
- **`splitticket_lb` is a lower bound**, not a point estimate. It assumes all non-Harris Pres votes by Peltola-R1 voters went to Trump (close to true but not exact). Ecological inference refinements are a modeling task deferred to v3.
- **Large rural precincts can visually dominate a choropleth** despite having few voters. The raw-count map (`splitticket_density.png`) partly corrects this; dot-density rendering is a future enhancement.
- **HD-absentee pseudo-precincts overlap their constituent precincts geographically.** On maps they render with dashed, translucent styling, but the overlap can obscure small precincts — toggle layers in the interactive view to read around this.
- **Cross-cycle comparison is not in v1.** Precinct boundaries changed after 2023, so comparing 2024 precinct-level numbers to 2022 or 2020 requires geometry reconciliation we haven't done.

## Roadmap

- **v1** (this): precinct + HD-absentee overperformance maps, top-N tables, interactive folium map on GitHub Pages.
- **v1.1:** upgrade to a 2024-vintage precinct shapefile; allocate HD-absentee voters down to precincts proportionally for a single unified map.
- **v2:** join ACS demographic and economic covariates (income, education, age, race, employment sector) at the tract-to-precinct level.
- **v3:** model Peltola-Trump split-ticket propensity; report feature importances.

## Repo layout

```
src/ak_electoral_map/
  fetch.py         # download DoE + GIS sources into data/raw/
  clean.py         # parse, join, and produce data/processed/precincts_2024.{geojson,parquet}
  metrics.py       # overperformance and split-ticket lower-bound calcs
notebooks/
  01_overperformance.ipynb   # end-to-end pipeline
scripts/
  build_notebook.py          # regenerates the notebook from declarative cells
outputs/maps/, outputs/tables/, docs/index.html   # published artifacts
```

## License

MIT. See [LICENSE](LICENSE).
