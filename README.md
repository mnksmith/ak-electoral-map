# ak-electoral-map

Precinct-level analysis of Alaska's 2024 general election, focused on **where Mary Peltola (US House, D) outperformed Kamala Harris (President, D)** on the same ballot — i.e. the geography of Peltola-Trump split-ticket voters.

> Status: **v1 in progress.** Maps and tables land here as the pipeline is built.

## Why

Alaska's recent elections show unusual split-ticket behavior. In 2024, Peltola lost the US House seat by ~2.5 pts while Harris lost the presidential race by ~13 pts — meaning a large universe of Alaskans picked Peltola for House *and* Trump for President on the same ballot. Those voters are the most addressable persuasion universe for a statewide Democratic campaign.

This repo maps that geography at the most granular level publicly available (the voting precinct), as a starting point for targeting and messaging research.

## Methodology (v1)

- **Source data:** [Alaska Division of Elections 2024 general precinct results](https://www.elections.alaska.gov/results/24GENR/) and [precinct shapefiles from the AK GIS portal](https://gis.data.alaska.gov/).
- **Peltola's share:** Round 1 first-choice votes only (cleanest analog to plurality Presidential share — Alaska uses RCV for US House but plurality for President).
- **Ballot scope:** precinct-reported ballots only. Absentee / Early / Question ballots are reported at the House District level in DoE's data and are **not** included here (see Caveats).
- **Primary metrics:**
  - `overperformance_pp` = Peltola R1 % − Harris % (percentage points)
  - `splitticket_lb` = max(0, Peltola R1 votes − Harris votes), a lower-bound count of Peltola-Trump voters per precinct.

## Reproduce locally

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnksmith/ak-electoral-map.git
cd ak-electoral-map
uv sync
uv run jupyter lab notebooks/01_overperformance.ipynb
```

The notebook fetches all raw data on first run; subsequent runs use the cached copies in `data/raw/`.

## Caveats

- Absentee/Early/Question ballots are reported at House District level by the Division of Elections and are **not** allocated back to precincts here. Statewide totals in this repo will be lower than certified totals by that margin.
- `splitticket_lb` is a lower bound, not a point estimate. Ecological inference refinements are deferred to follow-up work.
- Large rural precincts can visually dominate a choropleth despite having few voters; the raw-count map (`splitticket_lb`) partly corrects for this.
- Precinct boundaries changed after the 2023 redistricting proclamation — this analysis uses the 2024-effective precinct map only.

## Roadmap

- **v1** (this): two precinct-level maps + top-N tables + interactive folium map.
- **v1.1:** allocate absentee/early ballots to precincts.
- **v2:** join ACS demographic and economic covariates (income, education, age, race, employment sector).
- **v3:** model Peltola-Trump split-ticket propensity; report feature importances.

## License

MIT. See [LICENSE](LICENSE).
