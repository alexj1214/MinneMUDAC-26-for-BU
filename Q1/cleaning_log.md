# Q1 cleaning log — need estimates vs. observed activity

Every decision that changes a number, with the evidence behind it and its effect on the
totals. Built from the raw workbooks; nothing inherited from earlier work.

**Window: 2022 thru 2024**, per the challenge brief's change log entry of 2026-09-22
("Updated notes section in Q1 to reflect actual data range from 2022 thru 2024") and
John Hogue in Zoom 2: *"the data sets that you need to compare and contrast are 2022
forward... 2022 is why we have selected going forward, as things kind of stabilize"* —
2022 is the cutoff because COVID confounds anything earlier.

Sources of record:
- `Data/org_FSStats.xlsx` (28,287 x 58)
- `Data/Organization.xlsx` (1,202 x 68)
- `MMG_County_MN_2021_2024.xlsx` — teammate-built, MN only, 348 rows (87 counties x 4
  years), 2021–2023 from the MMG2025 edition, 2024 from MMG2026. Verified against the
  source workbooks: 87 counties every year, food-insecure persons 342,640 / 509,450 /
  581,270 / 636,610 and median rates 0.069 / 0.100 / 0.111 / 0.123 for 2021–2024.

Field names are fixed by the brief (change log 2026-09-29): Visits = `HouseholdsReg`,
Pounds distributed = `PoundsReg`, Individuals served = `IndividualsReg`.

## Baseline — raw, no cleaning

| Year | Households | Individuals | Pounds |
|---|---:|---:|---:|
| 2022 | 1,970,104 | 5,662,630 | 119,160,466.37 |
| 2023 | 2,790,625 | 7,743,201 | 141,451,399.50 |
| 2024 | 2,918,714 | 9,146,694 | 157,816,787.54 |

MMG food-insecure persons: 509,450 (2022), 581,270 (2023), 636,610 (2024).

Window: 18,756 rows, 634 sites, 36 months, 90 raw county labels, 120 rows with a null
county.

---

## Decision 1 — `DateForSearch` is the date of record; `_Year` and `_Month` are dropped
**Status: confirmed (Brian, 2026-10-05)**

Two fields could date a row: `DateForSearch` (a real date) and the `_Year`/`_Month`
pair. They disagree on 26 rows in the window:

- 25 rows carry `_Month = 0`, which resolves to December of the prior year. They sit in
  a contiguous index block across St. Louis, Carlton, Lake and Cook — one Arrowhead
  submission batch filed during the 2023 reporting cycle for December 2022 activity.
- 1 row carries `_Month = 15`, the same overflow upward: month 12 + 3 = March of the
  following year.

`_Month` runs off both ends of the calendar; `DateForSearch` resolves correctly in all
26 cases, is populated on all 28,287 rows of the raw file, and arrives already typed as
`datetime64`. There is no row where `DateForSearch` is missing and `_Year`/`_Month`
would be the only date information. So the pair carries nothing `DateForSearch` lacks
and is partly wrong — both columns are dropped at load.

**Effect of the choice.** All 26 rows stay in the analysis either way; only the year
they are filed under changes. 430,053 lbs land in 2022 rather than 2023, and 2,043 lbs
land in 2024 rather than 2023. By county: St. Louis 345,313 lbs, Carlton 44,326, Lake
25,426, Cook 14,988, Polk 2,043. This matters because Q1 compares years — St. Louis's
2022 pounds move about 8% on this choice alone.

Note for anyone comparing against earlier work: on the old 2023–2024 window these 25
rows fell *outside* the window, so choosing `DateForSearch` dropped them from the
analysis entirely. Widening to 2022 removed that consequence.

```python
fs = fs.drop(columns=['_Year','_Month'])
fsq1 = fs[fs.DateForSearch.dt.year.isin([2022, 2023, 2024])].copy()   # 18,756 rows
```

---

## Decision 2 — duplicate `(site, month)` keys: keep the larger row
**Status: confirmed (Brian, 2026-10-05)**

`org_FSStats` is documented as one row per site per month. In the window, 63
`(_id_site, DateForSearch)` combinations appear more than once — 127 rows across 38
sites. 65 of those rows are in 2022, 6 in 2023, 56 in 2024; 2022 is the worst year.

Of the 63 keys, **8 are value-identical** (dropping either row changes nothing) and
**55 differ**, so the rule decides a number 55 times.

**Rule adopted.** Keep one row per key, ordered by `IndividualsReg` desc, then
`PoundsReg` desc, then `__ID` desc (latest filed). No summing anywhere. Window goes
18,756 -> 18,692 rows.

```python
fsq1 = (fsq1
    .sort_values(['_id_site','DateForSearch','IndividualsReg','PoundsReg','__ID'],
                 ascending=[True, True, False, False, False])
    .drop_duplicates(['_id_site','DateForSearch'], keep='first')
    .copy())
```

### Evidence

Two readings are possible: two separate programs at one site (add the rows) or one
filing superseding another (keep the larger). They predict different monthly totals, so
each duplicated month is benchmarked against that site's own single-row months. 61 of
the 63 keys have at least three single-row months to compare against.

| | Median vs. a typical month at that site | Keys in 0.5–1.5x of typical |
|---|---:|---:|
| Keep the max | **0.99** | 48 of 61 |
| Sum the rows | 1.73 | 22 of 61 |

For the 30 benchmarkable 2022 keys alone: 25 of 30 for keep-max, 6 of 30 for summing.
The original version of this decision rested on five sites; it now rests on 61 keys and
points the same way.

**Worked examples.**

*Site 1148 (Polk), 2024-03 — a correction filed seven months later.*

| `__ID` | Households | Individuals | Pounds | Created |
|---|---:|---:|---:|---|
| 23361 | 33 | 69 | 2,043 | 2023-09-18 |
| 26579 | 43 | 97 | 2,902 | 2024-04-15 |

Typical month at this site: 35 / 75 / 2,180. Keep-max = 1.33x typical; summing = 2.27x,
which reads as two months in one. The creation timestamps are seven months apart. This
is the same record that carried `_Month = 15` in Decision 1.

*Site 1088 (St. Louis), 2022-12 — same pattern, a year apart.*

| Households | Individuals | Pounds | Created |
|---:|---:|---:|---|
| 565 | 974 | 36,595 | 2023-01-13 |
| 691 | 1,106 | 40,515 | 2024-01-16 |

Typical month: 766 / 1,332 / 44,646. Keep-max = 0.91x typical; summing = 1.73x.

*Site 1088 (St. Louis), 2022-02 — a plain double-entry, one of the 8 identical pairs.*
Both rows read 501 / 1,078 / 56,647, submitted 13 days apart.

*Site 1365 (Ogilvie, Kanabec), 2024-04 — the tie-break, and the case the data cannot
settle.* Both rows were created in the same second (2025-02-06T14:28:05Z), so there is
no "filed later" signal. Pounds are identical at 1,772 but households read 36 and 89.
The tie-break keeps the 89-household row. This site's typical month is 4,666 lbs, so
both candidate answers sit far below its normal level — 0.38x for keep-max, 0.76x for
summing.

Sites 1103 (Chisholm, St. Louis) and 1365 (Ogilvie, Kanabec) have duplicates in 13 and
11 months respectively, so neither has a within-year baseline to test against.

**Honest limitation.** This is inference from each site's own level, not direct
evidence. No field states that one row supersedes another. It would misread a genuine
program that started and ended alongside the duplicate period. The only definitive
answer is from The Food Group.

### Effect on totals

How much higher Minnesota's totals would be if the rows were summed instead:

| Year | Households | Individuals | Pounds |
|---|---:|---:|---:|
| 2022 | +0.255% | +0.213% | +0.324% |
| 2023 | +0.001% | +0.002% | +0.003% |
| 2024 | +0.065% | +0.049% | +0.065% |

Statewide the rule is immaterial. At county level it is not:

| County | Year | Keep-max pounds | Summed | Change |
|---|---|---:|---:|---:|
| **Kanabec** | 2024 | 223,930 | 271,538 | **+21.3%** |
| **Lake** | 2022 | 185,529 | 204,521 | **+10.2%** |
| **Cook** | 2022 | 151,731 | 165,411 | **+9.0%** |
| **St. Louis** | 2022 | 4,251,798 | 4,578,412 | **+7.7%** |
| **Carlton** | 2022 | 448,509 | 473,615 | **+5.6%** |
| Jackson | 2023 | 280,080 | 285,018 | +1.8% |
| St. Louis | 2024 | 5,072,313 | 5,100,533 | +0.6% |
| Ramsey-Suburbs | 2024 | 4,236,820 | 4,259,219 | +0.5% |
| Norman | 2022 | 30,215 | 30,373 | +0.5% |
| Polk | 2024 | 640,253 | 642,296 | +0.3% |

**These ten county-years are flagged rule-sensitive and must be disclosed wherever
county results are reported.** Counties outside this list are unaffected by the rule.
Kanabec's entire sensitivity comes from site 1365, the one case the data could not
settle.

Lake, Cook, St. Louis and Carlton in 2022 are all Arrowhead counties — the same region
as Decision 1's `_Month = 0` batch and the same region as the structural reporting gaps
in Decision 4. Three separate defects point at one upstream reporting practice in
northeastern Minnesota.

**Why this matters for Q1.** Statewide totals barely move, but Q1 asks for a ranking of
87 counties against the Feeding America estimates and a list of the counties that break
the pattern. A county 21% off is enough to move in or out of that list. The stake is the
county ranking, not the state total.

**Open question for The Food Group:** what does a second row for the same site and month
mean in the FileMaker export — a separate distribution program, or a re-filing?
Specifically site 1365 (Ogilvie, Kanabec) across 2024 and site 1103 (Chisholm, St.
Louis) across 2022.

---

## Decision 3 — `HouseholdsReg > IndividualsReg`: 98 impossible rows
**Status: implemented in the notebook, NOT yet confirmed**

A household contains at least one person, so a monthly household count can never exceed
the individual count at the same site. 98 rows in the deduplicated window break that —
45 in 2022, 23 in 2023, 30 in 2024. They are handled three ways, unchanged in method
from the version validated on the 2023–2024 window:

| Route | Rows | Basis |
|---|---:|---|
| Set by hand | 1 | Site 1197 (Waseca) 2023-07: 273,385 households against 646 individuals. June is 285 and August is 338, so 311, the midpoint. The ratio rule would give 353, above every 2023 month this site reports. Flagged `hh_imputed` so the ratio rule never overwrites it. |
| Rebuilt from a ratio | 93 | `IndividualsReg / r`, where `r` is persons per household — the site's own clean months (56 rows), else its county's (36), else statewide 3.0697 (1). Ratios below 1.5 are impossible as an average and fall to the next tier. |
| Left as received | 4 | `IndividualsReg = 0` with pounds distributed, so no denominator exists. Sites 13836 and 14621 (McLeod, 2024-01) and site 14919 twice (Beltrami, 2023-03 and 2023-04). Deferred to Decision 4. |

`hh_adjusted` is True on all 98; `hh_imputed` on Waseca alone. 98 = 1 + 93 + 4.

### Effect on household totals

| Year | After decision 2 | After decision 3 | Change |
|---|---:|---:|---:|
| 2022 | 1,965,092 | 1,937,451 | −1.41% |
| 2023 | 2,790,586 | 2,506,996 | **−10.16%** |
| 2024 | 2,916,809 | 2,900,331 | −0.57% |

The 2023 change is the largest single cleaning effect in the pipeline and almost all of
it is the one Waseca row. Any 2023 household figure taken from the raw file is overstated
by about 11%.

Counties moved more than 2% by this decision: Waseca 2023 −98.1%, Polk 2023 −22.0%,
Lincoln 2022 −18.6%, Grant 2024 −7.8%, Hennepin-Suburbs 2022 −7.7%, Traverse 2024
−4.7%, Ramsey 2023 −4.7%, Koochiching 2022 −4.3% and 2024 −4.2%, Wright 2023 −4.0%,
Dakota 2022 −3.1% and 2024 −2.8%, Le Sueur 2022 −2.6%, Todd 2022 −2.6%,
Hennepin-Suburbs 2024 −2.5%.

**Honest limitation.** For the 93 ratio rows this reconstructs a plausible household
count, not the true one. Pounds and individuals at those sites are untouched, so any Q1
result resting on Visits inherits this reconstruction while results on pounds or
individuals do not. That is a reason to report all three metrics rather than lead with
Visits.

### Open item before this can be confirmed

14 sites account for 55 of the 98 rows — site 1267 has 8, site 14763 has 8, site 1263
has 7, site 14378 has 5. That is a recurring site-level reporting fault rather than
scattered typos, and it weakens the repair basis: a site with 8 bad months out of 36 has
thin clean history to take a ratio from.

A households/individuals column swap was tested as an explanation and **the test does
not work** — the sites it appears to confirm are the ones whose clean-month ratio is
already near 1.0, so a swapped ratio landing near that value is close to guaranteed and
carries no information. The recurring-site pattern is real; the swap explanation needs a
different test.

---

---

## Decision 8 — county label standardization and the name-to-FIPS map
**Status: confirmed (Brian, 2026-10-05)**

`org_FSStats.County` carries 90 distinct labels for Minnesota's 87 counties. Seven do
not match a county name in MMG, and together they hold **43.1% of all pounds** and
**41.8% of all households** — because two of the three largest counties are among them.

| Raw label | Rows | Sites | Households | Pounds | Mapped to |
|---|---:|---:|---:|---:|---|
| Hennepin-Minneapolis | 2,687 | 89 | 1,470,531 | 75,397,482 | Hennepin |
| Hennepin-Suburbs | 951 | 31 | 829,140 | 58,623,213 | Hennepin |
| Ramsey-Saint Paul | 1,137 | 35 | 591,265 | 30,183,083 | Ramsey |
| Ramsey-Suburbs | 517 | 16 | 211,412 | 11,149,124 | Ramsey |
| Lac Qui Parle | 36 | 1 | 1,583 | 116,595 | Lac qui Parle |
| Saint Louis | 1 | 1 | 35 | 4,362 | St. Louis |
| *(null)* | 120 | 42 | 100,361 | 4,542,667 | see Decision 6 |

**Ramsey is split three ways, not two.** A plain `Ramsey` label also exists (154 rows, 5
sites, 2,847 households, 132,910 lbs) and was easy to miss precisely because it matches a
real county name. It is small enough to read as a third data-entry convention rather than
a meaningful subdivision.

Collapsed totals, against MMG's 2024 need estimate for the same county:

| County | Rows | Sites | Households | Pounds | MMG food insecure (2024) |
|---|---:|---:|---:|---:|---:|
| Hennepin | 3,638 | 120 | 2,299,671 | 134,020,695 | 143,160 |
| Ramsey | 1,808 | 56 | 805,524 | 41,465,117 | 71,270 |

The four sub-county labels alone are 42.0% of state pounds, 40.5% of households and 176
sites. **Until they were collapsed there was no county-level correlation to compute for
the two largest counties in Minnesota**, which is why this decision blocked the rest of
Q1.

### Rule adopted

Six label fixes, applied to a new `county` column. The original label is preserved in
`county_detail` rather than overwritten.

```python
FIX = {'Hennepin-Minneapolis': 'Hennepin', 'Hennepin-Suburbs': 'Hennepin',
       'Ramsey-Saint Paul':    'Ramsey',   'Ramsey-Suburbs':   'Ramsey',
       'Lac Qui Parle':        'Lac qui Parle',
       'Saint Louis':          'St. Louis'}
fsq1['county_detail'] = fsq1.County            # Hennepin-Suburbs
fsq1['county']        = fsq1.County.replace(FIX)   # Hennepin
```

Result: **86 distinct counties, zero labels unmatched against MMG.** 86 with activity
plus Wilkin with none accounts for all 87.

### FIPS needs no external source

MMG carries its own `FIPS` column, so the name-to-FIPS map comes out of a file already
being cited. Every non-null county resolves — 100.0% of rows.

```python
fips = (mmg.assign(c=mmg['County, State'].str.replace(' County, Minnesota', '', regex=False))
            .drop_duplicates('c').set_index('c').fips5)
fsq1['county_fips'] = fsq1.county.map(fips)
```

Worth stating to a judge: using MMG's own FIPS avoids a Census vintage mismatch and
removes a source that would otherwise need documenting and defending.

### Why `county_detail` is kept rather than discarded

Collapsing is required for the MMG join, but the sub-county labels are the only
within-county urban/suburban contrast anywhere in The Food Group data:

| Label | Sites | Pounds per household |
|---|---:|---:|
| Hennepin-Minneapolis | 89 | 51.0 |
| Hennepin-Suburbs | 31 | **71.0** |
| Ramsey-Saint Paul | 35 | 51.0 |
| Ramsey-Suburbs | 16 | 53.0 |
| Ramsey | 5 | 47.0 |

Hennepin's suburban sites move 39% more food per household visit than its Minneapolis
sites. Whether that is density, site type or bulk distribution is not established here —
but Q1 asks about rural share and distance to the nearest shelf, and Q8 is about the
reach of the network, so the column is retained for both.

### Wilkin County — zero activity, measurable need

**Wilkin County has 0 rows in the entire 28,287-row file**, not merely in the 2022–2024
window. MMG puts 810 food-insecure residents there at a 12.8% rate, above the state
median. It is the only Minnesota county with need and no demand signal of any kind, and
no log-based model can score it, so it must be reported separately rather than dropped.

---

## Decision 6 — rows with no county: recover 30, carry 90 as a named residual
**Status: confirmed (Brian, 2026-10-06)**

120 rows in the deduplicated window have a blank `County`. Feeding America's estimates
are county-level, so a row with no county cannot enter any county comparison. The
decision is what happens to those 120 rows.

They hold 100,361 households, 287,757 individuals and 4,542,667 lbs — about 1% of the
window on each measure — and span 42 sites. By year: 6 rows in 2022, 50 in 2023, 64 in
2024.

### Recovery attempted

The roster (`Organization.xlsx`) is the only file that could supply a location.
It joins on `org_FSStats._id_site` -> `Organization.__ID`, which matches on 99.8% of
window rows.

| Route | Rows recovered |
|---|---:|
| Site reports a county in another month (checked against all 28,287 raw rows) | 12 |
| `Organization.County` | 12 (same two sites) |
| `Organization.block_geoid` -> first 5 characters = county FIPS | 30 |

**30 rows recovered, 3 sites.** Each is a lookup with multiple agreeing sources, not an
inference:

| Site | Rows | County | Evidence |
|---|---:|---|---|
| 15362 | 6 | Rice | own months (Rice in 7 of 13), roster City Northfield / Zip 55057 / County Rice, `block_geoid` 271310705032009 -> FIPS 27131, Region Southern Minnesota |
| 15363 | 6 | Rice | own months (Rice in 7 of 13), roster City Faribault / Zip 55021 / County Rice, `block_geoid` 271310709011016 -> FIPS 27131, Region Southern Minnesota |
| 15218 | 18 | Cass | `block_geoid` 270219606001067 -> FIPS 27021. Files zeros in all 18 months, so it adds no activity, but it belongs in Cass's site count |

```python
RECOVER = {15362.0: 'Rice', 15363.0: 'Rice', 15218.0: 'Cass'}
fsq1['county']            = fsq1.county.fillna(fsq1._id_site.map(RECOVER))
fsq1['county_unassigned'] = fsq1.county.isna()      # 90 rows, 39 sites
```

### Why the remaining 90 rows cannot be recovered

Of the 42 blank-county sites, only 8 appear in the roster at all, and of those 8 only 3
have any geography filled in. The pattern is two distinct failures:

- **Four roster records opened and never completed.** Site IDs 15361, 15364, 15365 and
  15366 all have roster rows created in the same second — `2023-08-07T09:29:08Z`, a bulk
  import — with `isDistributionSite = 1` and City, State, Zip, County, `block_geoid` and
  Region all blank. All four are now `Inactive`. They filed July 2023 through July 2024.
  Each points to an `_id_Agency` in the range 16898–16903, and **none of those agency
  records exist in the roster**. All hang off `_id_Bank = 3`, which does resolve: Second
  Harvest Heartland, Brooklyn Park, Hennepin County — the food bank, not the sites.
- **34 sites with no roster row whatsoever**, the February 2024 batch. One row each,
  317,627 lbs in total.

The four incomplete records hold **3,379,840 lbs, 91% of the unrecoverable pounds.**
Site 15366 alone averages 4,058 households per month, the 98.9th percentile of the 592
sites that do have a county, and larger than any single site in Rice County.

**Those figures are real, not an artifact.** The Food Group's own system stores a
12-month average per site on the otherwise-blank roster rows, and it matches the activity
file: site 15366 at 4,104 households and 173,959 lbs per month against 4,058 and 169,917
computed from `org_FSStats`; site 15365 at 881 and 54,230 against 871 and 53,164. The
small gaps are 12 months versus the 13 filed. A rollup or a double-count would not carry
a per-site average. Pounds per household (41.9) and month-to-month stability (sd/mean
0.14, tighter than established sites at 0.22–0.23) are both consistent with one real
operation on a regular schedule.

### Every other avenue, and why each fails

| Checked | Result |
|---|---|
| All fields on an unlocatable activity row | 27 populated: counts, dates, derived ratios, `FoodBank = Second Harvest Heartland`, and an `id_agency` that echoes the site's own ID. No name, address, city, zip, census block, FIPS or EIN |
| `Incoming Call.xlsx` | No site identifier of any kind. It carries the *caller's* county, not a destination site |
| `marketbucksUsage.xlsx` | No reference. Apparent matches are its own row-id column `_ID` (range 7,621–21,798) |
| Every xlsx / docx / pdf / csv / pptx in the competition folder, searched for these IDs | Only `org_FSStats` and `Organization`. All other hits are coincidental digit matches inside MMG count columns |
| Public data, by join | Impossible. A join needs a shared key; these rows have none that exists publicly. "Site 15366" is an internal FileMaker record number |
| Public data, by triangulation against independent county totals | Not available. The Food Group's own *2024 Minnesota Food Shelf Visits* report (published with the MN Department of Children, Youth and Family) gives statewide figures only, with county content limited to the top 10 by percentage change 2019–2024. thefoodgroupmn.org/news/hunger-data offers statewide PDFs for 2017–2025, no county download or dashboard |

### The rule, and why not to guess

The 90 rows stay in the table behind `county_unassigned`. Every county aggregation filters
them out; a reconciliation check proves that county totals plus the residual equal the
window total, so no figure quoted from this panel is unexplained against the source file.

| | Counties (86) | Unassigned | Window |
|---|---:|---:|---:|
| Households | 7,591,460 | 81,027 | 7,672,487 |
| Individuals | 22,309,847 | 226,024 | 22,535,871 |
| Pounds | 414,239,263.29 | 3,697,467.12 | 417,936,730.41 |

Residual share: 1.06% of households, 1.00% of individuals, **0.88% of pounds**, across 39
sites. Zero in 2022; 1,461,149 lbs in 2023 and 2,236,318 lbs in 2024.

The consecutive IDs, the shared food bank and the two locatable members all point at
Rice, and that inference was rejected. Second Harvest Heartland is the Twin Cities food
bank and operates across most of Minnesota, while Rice County's own regional food bank is
Channel One, which supplies five of Rice's seven sites — so Second Harvest appearing in
Rice is already the unusual thing, and four more of its sites created the same month
could be anywhere in its territory. Assigning the block to Rice would raise that county's
pounds 50%, from 8.5M to 12.7M, on a county already third-highest in the state at 379 lbs
per food-insecure person against a median of 133. Q1's deliverable is a list of counties
that diverge from the need estimates; manufacturing one is the worst available error.

**Stated limitation for the writeup:** the source data contains no geographic identifier
for 39 sites holding 0.88% of pounds. They are reported as unassigned rather than
allocated or deleted, and statewide totals include them.

---

---

## Sensitivity test — how much does the remaining cleaning change the answer?
**Run 2026-10-06**

Decisions 3 and 4 both touch `HouseholdsReg` only; Pounds and Individuals are untouched by
either. So the question is narrow: does Visits move enough to change Q1's answer? Q1's answer
is two things — which metric correlates best with the Feeding America estimate, and which
counties break the pattern. Both were computed four times.

| Variant | `HouseholdsReg` |
|---|---|
| V0 | Decision 3 applied (Waseca by hand + 93 by ratio), no decision 4 fill — **the adopted pipeline** |
| V1 | Decision 3 *not* applied — households exactly as received |
| V2 | Decision 3 = delete the 98 impossible rows instead of repairing them |
| V3 | Decision 3 + decision 4 variant B (fill 49 sporadic rows from site history) |

### Result 1 — the metric ranking never changes

Log-log correlation with number of food insecure persons:

| Variant | 2022 | 2023 | 2024 |
|---|---|---|---|
| V0 | V .922 / I .925 / **P .940** | V .913 / I .919 / **P .930** | V .918 / I .921 / **P .933** |
| V1 | V .921 / I .925 / **P .940** | V **.872** / I .919 / **P .930** | V .918 / I .921 / **P .933** |
| V2 | identical to V0 to three decimals | | |
| V3 | identical to V0 to three decimals | | |

Pounds ranks highest in every year under every variant. Largest change in any correlation
across all four: **0.041**, and it occurs only in V1.

### Result 2 — how decision 3 is implemented, and all of decision 4, change nothing

The outlier county list is identical across V0, V2 and V3 in all three years, for all three
metrics. Repairing the 98 rows and deleting them outright give the same answer. Filling 49
missing rows gives the same answer.

### Result 3 — but decision 3 itself changes the answer completely

2023, counties off-trend on visits:

| | Counties flagged |
|---|---|
| With decision 3 (V0) | Nicollet, Nobles, Pope, Renville, Rice, Steele, Washington |
| Without it (V1) | Nobles, Steele, **Waseca** |

One uncorrected row puts Waseca on the list and **masks five genuine counties**. This table is
the justification for decision 3 in a single comparison and belongs in the writeup.

### What it settles

Further cleaning of `HouseholdsReg` has no return for Q1. Decision 3's open item and decision
4 are closed on this evidence rather than on further investigation. Decisions 5 and 7 touch
site counts and supply-side variables, not these figures.

What it does **not** settle: all of the above is the levels specification, which is largely a
population artifact. The rate results are reported separately and are the substantive finding.


## Decision 4 — missingness: no imputation, carry per-metric coverage instead
**Status: confirmed (Brian, 2026-10-06)**

Of the 18,692 rows in the window:

| | Rows | Share |
|---|---:|---:|
| All three measures populated | 15,990 | 85.5% |
| All three null | 1,297 | 6.9% |
| All three zero | 1,101 | 5.9% |
| Partly null | 270 | 1.4% |
| Partly zero | 34 | 0.2% |

`sum()` in pandas treats null as zero, so null rows and zero rows both contribute nothing to
a county total. Neither category changes a single figure. What they change is whether you
can tell "this county served nobody" from "this county did not report" — which matters for
per-site rates and for knowing which counties have a trustworthy Visits figure.

### Rule adopted: impute nothing

A site-history imputation rule was built and tested (fill the 109 sporadic partly-null rows
from the site's own clean months, requiring at least 6 clean months; it reaches 49 of them).
**The sensitivity test in this log shows it changes nothing in Q1's output** — identical
metric ranking, identical outlier counties, in all three years. The remaining 161 partly-null
rows are structural: 22 sites that never file the missing field in any month, so there is no
site history to impute from at all.

Imputing 49 rows to move no result is unjustifiable invention. The rule is: leave missing as
missing, and carry coverage flags so the gap is visible rather than silently read as zero.

### Coverage is the real output

Share of each county-year's site-months with no household figure at all:

| County | Year | Site-months | No household figure |
|---|---|---:|---:|
| Beltrami | 2022 | 96 | 69.8% |
| Becker | 2022 | 34 | 64.7% |
| Grant | 2022 | 23 | 60.9% |
| Becker | 2023 / 2024 | 48 | 75.0% |
| Beltrami | 2023 / 2024 | 143 | 74.1% / 73.4% |
| Mahnomen | 2024 | 36 | 36.1% |
| Itasca | 2022 | 122 | 31.1% |
| Ramsey | 2022 | 48 | 29.2% |
| St. Louis | 2022 / 2023 | 252 | 28.6% |
| Clay | 2022 | 128 | 25.0% |
| Hubbard | 2023 / 2024 | 48 | 25.0% |
| **Hennepin-Minneapolis** | 2022 | 862 | **19.5%** |
| | 2023 / 2024 | 900 / 925 | 16.3% / 16.5% |

**Becker and Beltrami have no usable Visits figure** — three quarters of their site-months
carry no household count. Any Visits-based result for those two counties is reporting
coverage, not demand. 2022 is the weakest year for household coverage, which matters because
2022 was added to the window late.

Six St. Louis sites (11061, 13457, 13454, 11721, 10887, 11043) report individuals in all 12
of their months and households in none, and all six appear only in 2023. That understates
St. Louis households in 2023 by roughly 11,500 — about 16% — while leaving 2024 untouched,
so the county's apparent household growth into 2024 is partly an artifact. Carried to
decision 5.

### Honest limitation

Coverage flags make the gap visible; they do not fix it. A county-level Visits figure built
on 25% coverage is not comparable to one built on 100%, and no flag changes that. The
defensible use is to exclude the worst counties from Visits-based conclusions and say so.

---

## Decision 3, open item — closed: the 14 repeat-offender sites need no further action
**Status: closed (Brian, 2026-10-06)**

14 sites account for 55 of the 98 impossible rows — site 1267 has 8, 14763 has 8, 1263 has 7,
14378 has 5. That is a recurring site-level reporting fault rather than scattered typos, and
it thins the clean history those sites' repairs are drawn from.

A households/individuals column swap was tested as the explanation and **the test does not
discriminate**: the sites it appears to confirm are those whose clean-month ratio already sits
near 1.0, so a swapped ratio landing near that value is close to guaranteed and carries no
information. Recorded here so the test is not repeated in the belief that it proved something.

**The sensitivity test settles the practical question.** Repairing those rows by ratio (the
adopted rule) and deleting all 98 outright produce *identical* Q1 output — same metric
ranking, same outlier counties, all three years. How the 98 are handled does not matter.
Whether they are handled at all matters a great deal: see the sensitivity test.

No further work. The recurring-site pattern is recorded as a data-quality observation for
The Food Group, not as an open analytical question.

---

## Finding — Steele County and site 1279: a regional hub, attributed to one county
**Status: hypothesis, stated as such. Logged 2026-10-06**

Steele is the single largest divergence between need and activity in Minnesota, on every
metric and in every year, on both the level and the rate basis. What follows is what the data
establishes, then what it does not.

### Established

Steele County, 2024: population 37,273, estimated food insecure 4,100, **59,192 household
visits**. That is 1.6 visits per resident per year, or **14.4 per food-insecure person** —
against a state norm near 2.4.

Fitting visits per 1,000 residents on the food insecurity rate across all 86 counties gives
`514 - 1,415 x FI rate`. Steele's rate of 0.110 predicts 358 visits per 1,000; it records
1,588. The residual is 1,230 against a standard error of 202, so **t = 6.08** — the furthest
off the line of any county in the state.

Counties at the same need rate, for scale: Rice 1,224 visits per 1,000, Hennepin 754, Waseca
387, Goodhue 336, Nicollet 83, Pope 75.

It is not a one-year artifact. Steele has risen every year while the state median barely
moved:

| Year | Steele visits / 1,000 | State median | Steele lbs per food-insecure person | State median |
|---|---:|---:|---:|---:|
| 2022 | 665 | 201 | 388 | 134 |
| 2023 | 1,110 | 255 | 511 | 152 |
| 2024 | 1,588 | 267 | 607 | 144 |

**95% of it is one site.** Steele has three food shelves; site 1279 records 56,546 of the
county's 59,192 household visits and 2,374,049 of its pounds. By volume that makes 1279 the
**fifth-largest food shelf in Minnesota** — behind sites in Washington (pop. 277,531), Anoka
(370,112), Olmsted (164,900) and Hennepin (1,266,903) — operating in the state's 28th-largest
county.

### Hypotheses tested and rejected

**A reporting or counting artifact.** Site 1279's internal ratios are ordinary: 3.05
individuals per household visit against a network median of 2.74 (65th percentile); pounds per
household 41.98 against 55.84 (27th); pounds per individual 13.76 against 20.94 (21st). The
individuals-per-household figure is stable at exactly 3.0 in all three years and the monthly
series is smooth (3,881–5,585 in 2024), so there is no definitional break. More frequent,
smaller pickups would inflate visits while leaving total pounds normal — but Steele is 4.2x
the state norm on **pounds** as well, so frequency alone cannot account for it.

**Drawing clients from adjacent counties, zero-sum.** If Steele were pulling visits that would
otherwise have been recorded next door, its neighbours should sit below the fitted line. None
of them do:

| County | FI rate | Visits / 1,000 | t |
|---|---:|---:|---:|
| Steele | 0.11 | 1,588 | **+6.08** |
| Rice | 0.11 | 1,224 | +3.87 |
| Blue Earth | 0.13 | 646 | +1.33 |
| Dodge | 0.09 | 454 | +0.30 |
| Mower | 0.12 | 449 | +0.44 |
| Waseca | 0.11 | 387 | +0.11 |
| Freeborn | 0.13 | 380 | +0.20 |
| Le Sueur | 0.11 | 293 | −0.29 |

(Adjacency taken as the five bordering counties plus Blue Earth and Le Sueur; **not yet
confirmed against an authoritative county adjacency source** and should be before publication.)

### The hypothesis that survives

**Site 1279 operates a catchment much wider than Steele County, and county-level attribution
assigns all of it to Steele.** Two variants remain consistent with the evidence and the data
cannot separate them:

1. It reaches households that were not visiting any food shelf. Nobody else's count falls, so
   neighbours look normal. This is the condition the brief describes — need that the visit
   data gives no signal of — being met rather than missed.
2. Its catchment is wide and thin, spread across many counties. The scatter around the fitted
   line is 244 visits per 1,000; a county of 20,000 losing 2,000 visits moves by 100 per
   1,000, under half a standard error. Undetectable per county.

### Why it cannot be settled with the data provided

No file contains client geography. Activity is attributed to the site's county
(`org_FSStats.County`), never the household's. The call centre logs were checked as the only
possible route: `ReferralInfoEntry` holds generic categories (`Food Shelf`, `County Office`),
never a named destination, and there are 59 calls from Steele and 338 from its neighbours
across three years — too generic and too thin either way.

### How to state it

Defensible: *"One site records 95% of Steele County's food shelf activity and ranks fifth
largest in Minnesota while sitting in the 28th-largest county. Its internal ratios are normal,
and its neighbours show no depletion, which is consistent with a regional catchment wider than
the county and with reaching households not previously served. The data contains no client
geography, so this cannot be confirmed."*

Not defensible: *"Steele County is over-served."* That is a claim about food insecurity. The
evidence supports a claim about attribution.

**This is the clearest illustration in the dataset of why county-level activity is a measure
of demand and not of need**, and it is the strongest candidate for the structural-divergence
section of the writeup.


## Pending

5. Site reporting continuity — the 32-site Feb-2024 import block and 13 real transitions,
   plus six St. Louis sites that report individuals only and disappear after 2023.
7. Sites absent from `Organization` — 34 in the old window, recount needed.
