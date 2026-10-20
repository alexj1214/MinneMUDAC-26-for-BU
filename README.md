# MinneMUDAC 2026 — Boston University (Graduate Division)

Team working repository for the **MinneMUDAC 2026 Student Data Challenge**, run by
MinneAnalytics for **The Food Group**, a Minnesota hunger-relief organization. The
competition was held on **October 17, 2026** at St. Catherine University, St. Paul.

The Food Group allocates food to food shelves based on visits. Visits measure demand,
not need. The challenge asks teams to compare need estimates against observed food
shelf activity, build a need-versus-demand divergence measure, relate activity to
prices and SNAP, forecast August 2026 activity by county, and assess whether the
network reaches low-income, low-access (LILA) areas.

Graduate teams answer **Q1, Q4, Q5, Q6 (+ addendum), Q7 (+ addendum) and Q8**. Each
question has its own folder under `analysis/`.

---

## Repository layout

```
.
├── README.md
├── By Organizers/                 Everything the organizers distributed (unchanged layout)
│   ├── TFG_MinneMUDAC_Challenge_Brief_2026_10_01.pdf   the questions and rules
│   ├── TFG_MinneMUDAC_Data_Question_SlideDeck.pdf       kickoff deck
│   ├── Glossary_of_Terms.docx, Division Descriptions.docx
│   ├── Rubrics/                   draft judging rubrics per division
│   ├── PredictionFile/            Q7 submission template + instructions
│   ├── Zoom Summaries/            AI summaries of the three organizer calls
│   └── Data/                      Data_Dictionary.xlsx + MDE school-meal data
│                                  (the five Food Group extracts are NOT in the repo, see below)
├── MMG2026_Data_To_Share/         Feeding America Map the Meal Gap FAQ
│                                  (the MMG workbooks are NOT in the repo, see below)
├── docs/                          Team-authored project docs
│   ├── MinneMUDAC_2026_Team_Roadmap.pdf          4-week plan, Sept 19 → Oct 17
│   ├── MinneMUDAC 26 Rules of Engagement.docx    consolidated rules with sources
│   ├── MinneMUDAC_2026_Meeting_Summary_Sept29.docx   judging / rubric call notes
│   └── EDA Review.docx
├── deliverables/                  Slide deck, v1 → v3 (v3 is the presented version)
└── analysis/
    ├── EDA/                       Profiling of the four extracts; writes cleaned/ CSVs
    ├── Q1_county_panel/           Cleaning pipeline + master county-month panel (Q1 foundation)
    ├── Q1_need_vs_activity/       Q1 analysis + cleaning_log.md (every cleaning decision)
    ├── Q4_Q5_prices_and_snap/     Q4 (CPI) and Q5 (SNAP); older versions in archive/
    ├── Q6_divergence_measure/     Q6 need index and divergence measure
    ├── Q7_august_forecast/        Q7 county forecasts for August 2026 + submission file
    └── Q8_lila_reach/             Q8 tract-level LILA reach analysis, maps and figures
```

---

## Questions → folders → owners

| Q | Question (short) | Folder | Main files | Owner |
|---|---|---|---|---|
| — | Exploratory data analysis of the four extracts | `analysis/EDA/` | `EDA.ipynb` (profiles every table, flags quality issues, writes `cleaned/*.csv`). `EDA_early_draft.ipynb` is an earlier 36-cell draft of the same notebook. | Alex |
| 1 | Clean, join and build the county panel | `analysis/Q1_county_panel/` | `Data Clean.ipynb`, `county_crosswalk.csv`, `master_panel_v2_dictionary.*` (the panel itself is excluded, see below) | Brian |
| 1 | Need estimates vs. observed activity | `analysis/Q1_need_vs_activity/` | `Q1_clean_and_analysis.ipynb`, `cleaning_log.md`, `q1_county_panel.csv`, `q1_unassigned_residual.csv`, `q1_scatter_2024.png` | Brian |
| 4 | Food prices and food shelf activity | `analysis/Q4_Q5_prices_and_snap/` | `✨Q4_FINAL✨.ipynb`, data in `Data/Q4/` | Suji |
| 5 | SNAP enrollment and food shelf use | `analysis/Q4_Q5_prices_and_snap/` | `✨Q5_FINAL✨.ipynb`, data in `Data/Q5/` | Suji |
| 6 | Divergence measure for need and demand (+ grad addendum) | `analysis/Q6_divergence_measure/` | `Q6_need_divergence.ipynb`, `q6_county_year_with_need_index.csv`, `q6_county_summary.csv`, `q6_persistent_divergers.csv`, `q6_divergence_chart.png` | Akbar |
| 7 | Forecast August 2026 activity by county (+ grad addendum) | `analysis/Q7_august_forecast/` | `forecast_august.py` + `forecast_august_steps.ipynb` → `forecast/` (Alex); `Q7_Forecast.ipynb` (Brian) | Alex, Brian |
| 8 | LILA areas and the reach of the network | `analysis/Q8_lila_reach/` | `Q8_01_build_tract_table.ipynb`, `Q8_02_analysis.ipynb`, `Q8_block_relationship_to_csv.ipynb`, outputs in `Q8_outputs/` | VG |

### Key conventions (from the brief and the organizer calls)

- **Metrics.** Visits = `HouseholdsReg`, Pounds = `PoundsReg`, Individuals = `IndividualsReg`
  (= `ChildrenReg` + `AdultsReg` + `SeniorsReg`). Deprecated fields in the data dictionary
  are not used.
- **Window.** Food shelf data is used from **2022 onward**; the extract ends **July 2026**.
- **Date of record** is `DateForSearch`; the `_Year`/`_Month` pair is dropped
  (see `cleaning_log.md`, Decision 1). All cleaning decisions and their effect on the
  totals are documented in `analysis/Q1_need_vs_activity/cleaning_log.md`.
- **Q7 hard rule.** No August 2026 data from any source was used; using it is a
  disqualification. The forecast cutoff is `2026-07-01`.
- **Map the Meal Gap editions.** The 2025 report carries 2023 data; the 2026 report
  carries 2024 data. `MMG_County_MN_2021_2024.xlsx` is a team-built Minnesota-only
  extract (87 counties × 2021–2024) verified against the source workbooks.

---

## Data

### Provided by the organizers (The Food Group)

| File | Grain | In repo? |
|---|---|---|
| `org_FSStats.xlsx` | food shelf site × month: visits, pounds, individuals (children / adults / seniors) | **No** |
| `Organization.xlsx` | one row per partner organization / site, with county | **No** |
| `Incoming Call.xlsx` | one row per helpline call: city, county, reason, referral | **No** |
| `marketbucksUsage.xlsx` | Market Bucks participation at farmers markets | **No** |
| `Data_Dictionary.xlsx` | field definitions and deprecation flags | Yes |
| `Data/MDE School Meal Data/` | MN Dept. of Education monthly school-meal claims (optional, public) | Yes |

### Feeding America — Map the Meal Gap

Annual county-level food-insecurity estimates (persons, rate, child rate, cost per
meal). Access is requested from Feeding America by each team and approved manually.
**Cite Feeding America explicitly** when using it; the citation for each year is in
that year's workbook. Required for Q1 and Q6. Not in the repo.

### Public sources added by the team

| Source | Used in | Publisher / series | Grain |
|---|---|---|---|
| FRED — CPI, Midwest urban (`Q4-FRED-CPI-Midwest*.xlsx`) | Q4, Q5 | Federal Reserve Bank of St. Louis / BLS | monthly, region |
| MN DHS SNAP dashboard (`Q5-snap-dashboard-*.xlsx`) | Q5 | Minnesota Dept. of Human Services | monthly, county + statewide |
| Census county population estimates (`co-est2025-alldata.csv`) | Q5 | U.S. Census Bureau, Vintage 2025 | annual, county |
| County unemployment rate (`forecast/unemployment_through_july2026.csv`) | Q7 (tested as a regressor, not selected) | BLS Local Area Unemployment Statistics, via the BLS public API | monthly, county |
| USDA Food Access Research Atlas 2019 | Q8 | USDA ERS | tract |
| USDA SRAM 2025 (driving / straight-line distance, tract characteristics) | Q8 | USDA ERS | tract |
| TIGER/Line 2024 Minnesota tracts and blocks | Q8 | U.S. Census Bureau | tract / block geometry |
| 2010→2020 tract/block relationship files, `CenPop2020_Mean_TR27.txt` | Q8 | U.S. Census Bureau | tract / block |
| Historical SNAP Retailer Locator 2005–2025 | Q8 | USDA FNS | store |
| USDA Rural-Urban Continuum Codes, 2013 and 2023 (`rucc` in the Q1 panel) | Q1, Q6 | USDA ERS | county |

Each notebook states the exact series, grain and reason for choosing it, as the brief
requires.

### Files deliberately kept out of the public repo

The repository is public. The competition's Rules of Engagement (`docs/…Rules of
Engagement.docx`, §10) allow findings and methodology in a personal portfolio but
**not the raw data or specific data values**, and Map the Meal Gap access is granted
per requester. The `.gitignore` therefore excludes:

| Excluded | Why | How to get it |
|---|---|---|
| The four Food Group extracts (every copy, in `By Organizers/Data/`, `analysis/Q8_lila_reach/Data for Q8/`, `analysis/Q4_Q5_prices_and_snap/Data/`) | not redistributable | shared team Drive |
| `analysis/EDA/cleaned/*.csv`, `analysis/Q1_county_panel/master_panel_v2*.csv/.xlsx` | cleaned / re-keyed copies of the same data | re-run `EDA.ipynb` / `Data Clean.ipynb` |
| `MMG2026_Data_To_Share/*.xlsx`, `MMG_County_MN_2021_2024.xlsx` | Feeding America access is per-requester | request at feedingamerica.org (Map the Meal Gap data request) |
| `By Organizers/Zoom Summaries/Zoom*_Transcript.txt` | verbatim transcripts of named organizers | team Drive (AI summaries are included) |
| `Data for Q8/tl_2024_27_tabblock20/` (256 MB) | above GitHub's 100 MB file limit | [Census TIGER/Line 2024, blocks, state 27](https://www2.census.gov/geo/tiger/TIGER2024/TABBLOCK20/tl_2024_27_tabblock20.zip) |
| `Data for Q8/Historical SNAP Retailer Locator Data 2005-2025.csv` (91 MB) | above GitHub's 50 MB warning | [USDA FNS SNAP Retailer Locator data](https://www.fns.usda.gov/snap/retailer-locator) |
| `analysis/Q4_Q5_prices_and_snap/Data/trash/` | archived scratch workbooks | — |

Drop the matching files into the same paths and every notebook runs unchanged.

---

## Running the notebooks

- **Working directory.** `Q1_clean_and_analysis.ipynb`, `Data Clean.ipynb` and
  `Q7_Forecast.ipynb` reference `By Organizers/Data/...` and
  `MMG_County_MN_2021_2024.xlsx` **relative to the repo root**; start Jupyter at the
  repo root for those. `forecast_august.py` / `forecast_august_steps.ipynb` run from
  `analysis/Q7_august_forecast/` and read `../EDA/cleaned/` (produced by
  `analysis/EDA/EDA.ipynb`, run from `analysis/EDA/`). The Q8 notebooks run from
  `analysis/Q8_lila_reach/` with `Data for Q8/` and `Q8_outputs/` as siblings.
- **Colab paths.** The Q4/Q5, Q6 and block-relationship notebooks were developed in
  Google Colab and hard-code `/content/drive/MyDrive/MinneMUDAC 26 for BU/...`; edit
  the `DATA_DIR` / `ROOT` line at the top to point at this repo.
- **Environment.** Python 3 with pandas, numpy, scipy, statsmodels, matplotlib,
  seaborn and plotly (plus openpyxl for the Excel files). No geopandas: the Q8
  notebooks read the TIGER `.dbf`/`.shp` files directly.
- **Q7 pipeline.** `forecast_august.py` backtests on 2023 and 2024 holdouts
  (`forecast/backtest_metrics.csv`), picks the model, writes
  `forecast/august_2026_by_county.csv` with prediction bands and fills the organizers'
  template to `forecast/Grad_Team_XX_TFG_MinneMUDAC.xlsx` / `.csv` (87 counties).
  `forecast/summary.json` records the selection. `forecast_august_steps.ipynb` walks
  through the same steps.

### Known gaps

- `forecast_august.py` imports `clean_extracts` (for `MN_COUNTIES`), which is not in
  the folder; the notebook version does not need it.
- Wilkin County has no reporting food shelf in the extract; it is kept in the Q7
  submission with a forecast of zero so all 87 counties are present (see `summary.json`).
- `analysis/EDA/EDA_early_draft.ipynb` is an earlier revision of `EDA.ipynb`, kept for
  reference only.

---

## Team

Boston University MSBA students, Graduate Division: Alex Jiang, Akbar, Brian, Suji
and VG. Questions about the competition go to minnemudac@minneanalytics.org.

## Citations

- The Food Group, MinneMUDAC 2026 Student Data Challenge data extracts (food shelf
  activity, organizations, helpline calls, Market Bucks), 2022–July 2026.
- Feeding America, *Map the Meal Gap* 2025 (2019–2023 data) and 2026 (2024 data).
- U.S. Census Bureau, TIGER/Line Shapefiles 2024; 2010–2020 relationship files;
  Centers of Population 2020; Vintage 2025 county population estimates.
- USDA Economic Research Service, Food Access Research Atlas (2019) and SRAM (2025);
  Rural-Urban Continuum Codes.
- USDA Food and Nutrition Service, SNAP Retailer Locator historical data.
- Minnesota Department of Human Services, SNAP dashboard.
- Minnesota Department of Education, School Nutrition Program claim data.
- Federal Reserve Bank of St. Louis (FRED) / U.S. Bureau of Labor Statistics, CPI-U
  Midwest; BLS Local Area Unemployment Statistics, county unemployment rate.
