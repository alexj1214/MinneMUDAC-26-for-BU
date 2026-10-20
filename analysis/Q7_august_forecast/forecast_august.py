"""August 2026 county forecast for MinneMUDAC question 7, graduate division.

Target
    For each of the 87 Minnesota counties in August 2026: visits
    (HouseholdsReg), pounds distributed (PoundsReg), and children, adults,
    and seniors served (ChildrenReg, AdultsReg, SeniorsReg). Individuals
    (IndividualsReg) is forecast too, for the narrative, and equals the sum
    of the three age groups in the source data.

    Wilkin County has no reporting food shelf in the extract. It is kept in
    the output with a forecast of zero so the submission has all 87 rows.

Information set
    Cleaned food-shelf stats from January 2022 through July 2026.
    One public series: BLS LAUS county unemployment rates, kept only through
    July 2026. Any later month returned by the API is dropped before the
    series is stored or used. If forecast/unemployment_through_july2026.csv
    already exists it is read instead of calling the API.

The forecast is chosen by a backtest that copies the real task: predict an
August using only data through that July. August 2023 and August 2024 pick
the model. August 2025 is scored once and is not used to pick the model.
The selection metric is RMSE across counties, which is how the organizers
score question 7. WAPE and bias are reported alongside it.

Output
    forecast/august_2026_by_county.csv       full table with bands
    forecast/Grad_Team_XX_TFG_MinneMUDAC.xlsx  organizers' template, filled
    forecast/Grad_Team_XX_TFG_MinneMUDAC.csv   same rows as CSV
    forecast/summary.json, backtest_metrics.csv, statewide history
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from clean_extracts import MN_COUNTIES

ROOT = Path(".")
OUT = Path("forecast")
TEMPLATE = (
    Path(__file__).resolve().parent.parent.parent
    / "By Organizers" / "PredictionFile" / "Grad_Team_XX_TFG_MinneMUDAC.xlsx"
)
CUTOFF = pd.Timestamp("2026-07-01")
TARGETS = ("households", "pounds", "individuals", "children", "adults", "seniors")
SOURCE_COLS = {
    "households": "HouseholdsReg",
    "pounds": "PoundsReg",
    "individuals": "IndividualsReg",
    "children": "ChildrenReg",
    "adults": "AdultsReg",
    "seniors": "SeniorsReg",
}
# Organizers' template columns, in order, and the metric that fills each.
SUBMISSION = [
    ("Visits", "households"),
    ("Pounds", "pounds"),
    ("Children", "children"),
    ("Adults", "adults"),
    ("Seniors", "seniors"),
]

# Census 2020 county FIPS, Minnesota. Names match the cleaned extracts.
COUNTY_FIPS = {
    "Aitkin": "001", "Anoka": "003", "Becker": "005", "Beltrami": "007",
    "Benton": "009", "Big Stone": "011", "Blue Earth": "013", "Brown": "015",
    "Carlton": "017", "Carver": "019", "Cass": "021", "Chippewa": "023",
    "Chisago": "025", "Clay": "027", "Clearwater": "029", "Cook": "031",
    "Cottonwood": "033", "Crow Wing": "035", "Dakota": "037", "Dodge": "039",
    "Douglas": "041", "Faribault": "043", "Fillmore": "045", "Freeborn": "047",
    "Goodhue": "049", "Grant": "051", "Hennepin": "053", "Houston": "055",
    "Hubbard": "057", "Isanti": "059", "Itasca": "061", "Jackson": "063",
    "Kanabec": "065", "Kandiyohi": "067", "Kittson": "069", "Koochiching": "071",
    "Lac Qui Parle": "073", "Lake": "075", "Lake of the Woods": "077",
    "Le Sueur": "079", "Lincoln": "081", "Lyon": "083", "McLeod": "085",
    "Mahnomen": "087", "Marshall": "089", "Martin": "091", "Meeker": "093",
    "Mille Lacs": "095", "Morrison": "097", "Mower": "099", "Murray": "101",
    "Nicollet": "103", "Nobles": "105", "Norman": "107", "Olmsted": "109",
    "Otter Tail": "111", "Pennington": "113", "Pine": "115", "Pipestone": "117",
    "Polk": "119", "Pope": "121", "Ramsey": "123", "Red Lake": "125",
    "Redwood": "127", "Renville": "129", "Rice": "131", "Rock": "133",
    "Roseau": "135", "St. Louis": "137", "Scott": "139", "Sherburne": "141",
    "Sibley": "143", "Stearns": "145", "Steele": "147", "Stevens": "149",
    "Swift": "151", "Todd": "153", "Traverse": "155", "Wabasha": "157",
    "Wadena": "159", "Waseca": "161", "Washington": "163", "Watonwan": "165",
    "Wilkin": "167", "Winona": "169", "Wright": "171", "Yellow Medicine": "173",
}


def load_panel() -> pd.DataFrame:
    fs = pd.read_csv(ROOT / ".." / "EDA" / "cleaned" / "org_FSStats.csv", parse_dates=["DateForSearch"])
    mn = fs[fs["County"].isin(MN_COUNTIES)].copy()
    panel = (
        mn.groupby(["County", "DateForSearch"], as_index=False)
        .agg(
            **{m: (col, "sum") for m, col in SOURCE_COLS.items()},
            sites=("_id_site", "nunique"),
        )
        .sort_values(["County", "DateForSearch"])
    )
    return panel


def wide(panel: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Months by county, all 87 counties. A county-month with no reporting
    site is zero, which is what the organizers' actuals will show too."""
    return (
        panel.pivot(index="DateForSearch", columns="County", values=metric)
        .sort_index()
        .reindex(columns=MN_COUNTIES)
        .fillna(0.0)
    )


def template_counties() -> list[str]:
    """County names exactly as the organizers' template spells them."""
    names = pd.read_excel(TEMPLATE)["County"].dropna().astype(str).str.strip().tolist()
    ours = {c.lower(): c for c in MN_COUNTIES}
    unknown = [n for n in names if n.lower() not in ours]
    if unknown or len(names) != 87:
        raise RuntimeError(f"template counties do not match MN_COUNTIES: {unknown}, n={len(names)}")
    return names


def rmse(actual: pd.Series, pred: pd.Series) -> float:
    a = actual.to_numpy(dtype=float)
    p = pred.reindex(actual.index).to_numpy(dtype=float)
    return float(np.sqrt(np.mean((a - p) ** 2)))


def trail3(w: pd.DataFrame, year: int, month: int) -> pd.Series:
    """Mean of the three months before `year-month`. Uses no data from that month."""
    end = pd.Timestamp(year, month, 1)
    window = [end - pd.DateOffset(months=k) for k in (1, 2, 3)]
    return sum(w.loc[t] for t in window) / 3


def wape(actual: pd.Series, pred: pd.Series) -> float:
    a = actual.to_numpy(dtype=float)
    p = pred.reindex(actual.index).to_numpy(dtype=float)
    mask = np.isfinite(a) & np.isfinite(p) & (a > 0)
    return float(np.abs(a[mask] - p[mask]).sum() / a[mask].sum())


def bias(actual: pd.Series, pred: pd.Series) -> float:
    a = actual.to_numpy(dtype=float)
    p = pred.reindex(actual.index).to_numpy(dtype=float)
    mask = np.isfinite(a) & np.isfinite(p) & (a > 0)
    return float((p[mask] - a[mask]).sum() / a[mask].sum())


def load_unemployment() -> pd.DataFrame:
    """Saved BLS series if present, otherwise download it. Either way the
    series ends at July 2026."""
    path = OUT / "unemployment_through_july2026.csv"
    if path.exists():
        unemp = pd.read_csv(path, parse_dates=["DateForSearch"])
        if unemp["DateForSearch"].max() > CUTOFF:
            raise RuntimeError("saved unemployment series goes past July 2026")
        return unemp
    unemp = fetch_unemployment()
    unemp.to_csv(path, index=False)
    return unemp


def fetch_unemployment() -> pd.DataFrame:
    """BLS LAUS unemployment rate by county. Months after July 2026 are discarded."""
    series_ids = [
        f"LAUCN27{fips}0000000003" for fips in COUNTY_FIPS.values()
    ]
    id_to_county = {f"LAUCN27{fips}0000000003": name for name, fips in COUNTY_FIPS.items()}
    rows = []
    for start in range(0, len(series_ids), 25):
        batch = series_ids[start : start + 25]
        body = json.dumps(
            {"seriesid": batch, "startyear": "2022", "endyear": "2026"}
        ).encode()
        req = urllib.request.Request(
            "https://api.bls.gov/publicAPI/v1/timeseries/data/",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(payload.get("message"))
        for series in payload["Results"]["series"]:
            county = id_to_county[series["seriesID"]]
            for point in series["data"]:
                period = point["period"]
                if not period.startswith("M"):
                    continue
                stamp = pd.Timestamp(int(point["year"]), int(period[1:]), 1)
                if stamp > CUTOFF:
                    continue
                value = point["value"]
                if value in {"", "-"}:
                    continue
                rows.append({"County": county, "DateForSearch": stamp, "unemp_rate": float(value)})
        time.sleep(0.3)
    out = pd.DataFrame(rows)
    if out.empty or out["DateForSearch"].max() > CUTOFF:
        raise RuntimeError("unemployment series was not cut at July 2026")
    return out


def unemployment_adjustment(
    w: pd.DataFrame, unemp: pd.DataFrame, fit_end: pd.Timestamp
) -> tuple[float, float, int]:
    """Fit log(actual / trail3) = a + b * year-over-year unemployment change.

    The latest unemployment month allowed in a forecast of month t is t-1.
    `fit_end` is the last month whose actual value may enter the regression.
    """
    rate = unemp.pivot(index="DateForSearch", columns="County", values="unemp_rate").sort_index()
    ys, xs = [], []
    months = w.index[(w.index >= pd.Timestamp("2023-02-01")) & (w.index <= fit_end)]
    for stamp in months:
        prev = stamp - pd.DateOffset(months=1)
        prev_ly = stamp - pd.DateOffset(months=13)
        if prev not in rate.index or prev_ly not in rate.index:
            continue
        base = trail3(w, stamp.year, stamp.month)
        actual = w.loc[stamp]
        du = rate.loc[prev] - rate.loc[prev_ly]
        for county in w.columns:
            b0 = float(base[county])
            y0 = float(actual[county])
            x0 = du.get(county, np.nan)
            if b0 > 0 and y0 > 0 and np.isfinite(x0):
                ys.append(np.log(y0 / b0))
                xs.append(float(x0))
    y = np.asarray(ys)
    x = np.asarray(xs)
    X = np.column_stack([np.ones(len(x)), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma2 = float(resid @ resid) / (len(y) - 2)
    xtx_inv = np.linalg.inv(X.T @ X)
    se_b = float(np.sqrt(sigma2 * xtx_inv[1, 1]))
    return float(beta[0]), float(beta[1]), int(len(y)), se_b


def apply_unemp(
    base: pd.Series, unemp: pd.DataFrame, year: int, month: int, intercept: float, slope: float
) -> pd.Series:
    rate = unemp.pivot(index="DateForSearch", columns="County", values="unemp_rate")
    prev = pd.Timestamp(year, month, 1) - pd.DateOffset(months=1)
    prev_ly = pd.Timestamp(year, month, 1) - pd.DateOffset(months=13)
    du = (rate.loc[prev] - rate.loc[prev_ly]).reindex(base.index)
    factor = np.exp(intercept + slope * du.to_numpy(dtype=float))
    factor = np.where(np.isfinite(factor), factor, 1.0)
    return base * factor


def score_models(panel: pd.DataFrame, unemp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # For each origin, the unemployment slope is fit only on months up to
    # that July. August 2025 always uses the slope fit through July 2024,
    # so the holdout year does not choose the coefficient.
    fit_cache = {}
    for metric in TARGETS:
        w = wide(panel, metric)
        fits = {}
        for year in (2023, 2024):
            intercept, slope, n, se = unemployment_adjustment(
                w, unemp, pd.Timestamp(year, 7, 1)
            )
            fits[year] = {"intercept": intercept, "slope": slope, "n": n, "se": se}
        fit_cache[metric] = fits
        for year in (2023, 2024, 2025):
            actual = w.loc[pd.Timestamp(year, 8, 1)]
            pred_t3 = trail3(w, year, 8)
            used = fits[2024] if year == 2025 else fits[year]
            pred_u = apply_unemp(
                pred_t3, unemp, year, 8, used["intercept"], used["slope"]
            )
            for name, pred in (("trail3", pred_t3), ("trail3_unemp", pred_u)):
                rows.append(
                    {
                        "metric": metric,
                        "year": year,
                        "model": name,
                        "rmse": rmse(actual, pred),
                        "wape": wape(actual, pred),
                        "bias": bias(actual, pred),
                        "pred_total": float(pred.sum()),
                        "actual_total": float(actual.sum()),
                    }
                )
    return pd.DataFrame(rows), fit_cache


def error_bands(panel: pd.DataFrame, metric: str) -> dict:
    """80% empirical bands from August 2023 and 2024 percent errors, by size.

    Coverage is then checked on August 2025, which did not set the band.
    """
    w = wide(panel, metric)
    records = []
    for year in (2023, 2024):
        actual = w.loc[pd.Timestamp(year, 8, 1)]
        pred = trail3(w, year, 8)
        july = w.loc[pd.Timestamp(year, 7, 1)]
        for county in w.columns:
            if actual[county] <= 0 or pred[county] <= 0:
                continue
            records.append(
                {
                    "county": county,
                    "year": year,
                    "july": float(july[county]),
                    "ratio": float(actual[county] / pred[county]),
                }
            )
    err = pd.DataFrame(records)
    err["band"] = pd.qcut(err["july"], 3, labels=["smaller", "mid", "larger"])
    quantiles = {}
    for band, g in err.groupby("band", observed=True):
        quantiles[str(band)] = {
            "p10": float(g["ratio"].quantile(0.10)),
            "p90": float(g["ratio"].quantile(0.90)),
            "n": int(len(g)),
        }
    # edges from the backtest Julys, applied later with 2026 July size
    edges = err.groupby("band", observed=True)["july"].agg(["min", "max"])
    # 2025 coverage
    actual = w.loc[pd.Timestamp("2025-08-01")]
    pred = trail3(w, 2025, 8)
    july = w.loc[pd.Timestamp("2025-07-01")]
    hit = 0
    total = 0
    for county in w.columns:
        if actual[county] <= 0 or pred[county] <= 0:
            continue
        level = float(july[county])
        band = _size_band(level, err)
        q = quantiles[band]
        lo, hi = pred[county] * q["p10"], pred[county] * q["p90"]
        total += 1
        hit += int(lo <= actual[county] <= hi)
    return {
        "quantiles": quantiles,
        "july_edges": {str(k): {"min": float(v["min"]), "max": float(v["max"])} for k, v in edges.iterrows()},
        "holdout_2025_coverage": hit / total if total else None,
        "holdout_2025_n": total,
        "_err": err,
    }


def _size_band(july_value: float, err: pd.DataFrame) -> str:
    # Assign by the tertile cutpoints of the estimation sample, not by re-binning.
    cuts = err["july"].quantile([1 / 3, 2 / 3]).to_numpy()
    if july_value <= cuts[0]:
        return "smaller"
    if july_value <= cuts[1]:
        return "mid"
    return "larger"


def region_map() -> pd.Series:
    orgs = pd.read_csv(ROOT / ".." / "EDA" / "cleaned" / "Organization.csv")
    orgs = orgs[orgs["County"].isin(MN_COUNTIES) & orgs["Region"].notna()]
    mode = (
        orgs.groupby("County")["Region"]
        .agg(lambda s: s.value_counts().index[0])
    )
    return mode


def main() -> None:
    OUT.mkdir(exist_ok=True)
    panel = load_panel()
    print("Step 1. Panel:", panel["County"].nunique(), "counties with rows,", panel["DateForSearch"].min().date(), "to", panel["DateForSearch"].max().date())
    if panel["DateForSearch"].max() != CUTOFF:
        raise RuntimeError("extract does not end in July 2026; stop and check the file")
    missing = sorted(set(MN_COUNTIES) - set(panel["County"]))
    print("Counties with no food-shelf rows (forecast is zero):", missing)

    print("Step 2. BLS unemployment rates, cut at July 2026 (saved file if present, else download).")
    unemp = load_unemployment()
    print(
        "  unemployment rows", len(unemp),
        "counties", unemp["County"].nunique(),
        "through", unemp["DateForSearch"].max().date(),
    )

    print("Step 3. Backtest trail3 against trail3 plus unemployment. Model choice uses 2023 and 2024 only, scored by RMSE.")
    scored, fit_cache = score_models(panel, unemp)
    scored.to_csv(OUT / "backtest_metrics.csv", index=False)
    for metric, fits in fit_cache.items():
        fit = fits[2024]
        print(
            f"  {metric}: slope fit through July 2024 {fit['slope']:+.4f} "
            f"(SE {fit['se']:.4f}), intercept {fit['intercept']:+.4f}, n={fit['n']}"
        )
    choice = {}
    for metric in TARGETS:
        sub = scored[scored["metric"] == metric]
        sel = sub[sub["year"].isin([2023, 2024])].groupby("model")["rmse"].mean()
        winner = sel.idxmin()
        hold = sub[(sub["year"] == 2025) & (sub["model"] == winner)].iloc[0]
        trail_hold = sub[(sub["year"] == 2025) & (sub["model"] == "trail3")].iloc[0]
        choice[metric] = {
            "selected_on_2023_2024": winner,
            "selection_rmse": {k: float(v) for k, v in sel.items()},
            "holdout_2025_rmse": float(hold["rmse"]),
            "holdout_2025_wape": float(hold["wape"]),
            "holdout_2025_bias": float(hold["bias"]),
            "trail3_holdout_2025_rmse": float(trail_hold["rmse"]),
            "trail3_holdout_2025_wape": float(trail_hold["wape"]),
            "trail3_holdout_2025_bias": float(trail_hold["bias"]),
        }
        print(
            f"  {metric}: selected {winner} (mean RMSE 2023-24 {sel[winner]:,.0f}); "
            f"2025 holdout RMSE {hold['rmse']:,.0f}, WAPE {hold['wape']:.3f}, bias {hold['bias']:+.3f}"
        )

    # Unemployment has to win the 2023–2024 selection and then not lose the
    # untouched August 2025 check, on every metric. A gain that reverses on
    # the latest August is not stable enough to publish.
    won_selection = all(v["selected_on_2023_2024"] == "trail3_unemp" for v in choice.values())
    survived_holdout = all(
        v["holdout_2025_rmse"] <= v["trail3_holdout_2025_rmse"] + 1e-9
        for v in choice.values()
    )
    use_unemp = won_selection and survived_holdout
    model_name = "trail3_unemp" if use_unemp else "trail3"
    print(
        "Step 4. Unemployment won 2023–2024 selection:", won_selection,
        "| survived August 2025:", survived_holdout,
        "| published model:", model_name,
    )

    print("Step 5. Empirical 80% bands from August 2023 and 2024, coverage checked on August 2025.")
    bands = {metric: error_bands(panel, metric) for metric in TARGETS}
    for metric, band in bands.items():
        print(
            f"  {metric}: 2025 county coverage of the 80% band "
            f"{band['holdout_2025_coverage']:.1%} (n={band['holdout_2025_n']})"
        )

    print("Step 6. Forecast August 2026 from May–July 2026, all 87 counties.")
    regions = region_map()
    pieces = []
    for metric in TARGETS:
        w = wide(panel, metric)
        base = trail3(w, 2026, 8)
        if use_unemp:
            fit = fit_cache[metric]
            # Refit through July 2026 only after the holdout decision. The
            # published model is still the one that won on 2023–2024.
            intercept, slope, n, se = unemployment_adjustment(w, unemp, CUTOFF)
            forecast = apply_unemp(base, unemp, 2026, 8, intercept, slope)
            fit_cache[metric]["final_intercept"] = intercept
            fit_cache[metric]["final_slope"] = slope
            fit_cache[metric]["final_se"] = se
            fit_cache[metric]["final_n"] = n
        else:
            forecast = base
        july = w.loc[pd.Timestamp("2026-07-01")]
        aug_2025 = w.loc[pd.Timestamp("2025-08-01")]
        err = bands[metric]["_err"]
        qmap = bands[metric]["quantiles"]
        frame = pd.DataFrame(
            {
                "County": forecast.index,
                f"{metric}_forecast": forecast.to_numpy(),
                f"{metric}_july2026": july.reindex(forecast.index).to_numpy(),
                f"{metric}_aug2025": aug_2025.reindex(forecast.index).to_numpy(),
            }
        )
        los, his = [], []
        for county, value, july_value in zip(frame["County"], frame[f"{metric}_forecast"], frame[f"{metric}_july2026"]):
            band_name = _size_band(float(july_value), err)
            q = qmap[band_name]
            los.append(float(value) * q["p10"])
            his.append(float(value) * q["p90"])
        frame[f"{metric}_p10"] = los
        frame[f"{metric}_p90"] = his
        pieces.append(frame.set_index("County"))

    forecast = pieces[0]
    for piece in pieces[1:]:
        forecast = forecast.join(piece)
    sites = (
        panel[panel["DateForSearch"] == CUTOFF]
        .set_index("County")["sites"]
        .reindex(forecast.index)
        .fillna(0)
    )
    # Wilkin has no organization, so no region. Keep the JSON valid.
    forecast.insert(0, "region", regions.reindex(forecast.index).fillna("none").to_numpy())
    forecast.insert(1, "sites_july2026", sites.to_numpy())
    forecast = forecast.reset_index().sort_values("pounds_forecast", ascending=False)

    # Integers for counts. Ranges stay integers too.
    for col in forecast.columns:
        if col in {"County", "region"}:
            continue
        forecast[col] = forecast[col].round(0).astype(int)

    forecast.to_csv(OUT / "august_2026_by_county.csv", index=False)

    print("Step 7. Fill the organizers' template: 87 rows, their spelling, their column order.")
    names = template_counties()
    by_lower = forecast.set_index(forecast["County"].str.lower())
    submission = pd.DataFrame({"County": names})
    for col, metric in SUBMISSION:
        submission[col] = [
            int(by_lower.loc[n.lower(), f"{metric}_forecast"]) for n in names
        ]
    if submission.isna().any().any() or len(submission) != 87:
        raise RuntimeError("submission is incomplete")
    submission.to_excel(OUT / "Grad_Team_XX_TFG_MinneMUDAC.xlsx", index=False)
    submission.to_csv(OUT / "Grad_Team_XX_TFG_MinneMUDAC.csv", index=False)
    age_sum = submission[["Children", "Adults", "Seniors"]].sum(axis=1)
    indiv = pd.Series(
        [int(by_lower.loc[n.lower(), "individuals_forecast"]) for n in names]
    )
    print(
        "  children+adults+seniors vs individuals forecast, statewide:",
        f"{int(age_sum.sum()):,} vs {int(indiv.sum()):,}",
        f"(max county gap {int((age_sum - indiv).abs().max())})",
    )

    state = {
        "model": model_name,
        "counties_forecast": int(len(forecast)),
        "counties_not_in_extract": missing,
        "submission_file": str(OUT / "Grad_Team_XX_TFG_MinneMUDAC.xlsx"),
        "use_unemployment": use_unemp,
        "unemployment_won_selection": won_selection,
        "unemployment_survived_holdout": survived_holdout,
        "unemployment_fit": fit_cache,
        "choice": choice,
        "bands": {
            m: {k: v for k, v in band.items() if k != "_err"}
            for m, band in bands.items()
        },
        "statewide": {
            metric: {
                "forecast": int(forecast[f"{metric}_forecast"].sum()),
                "july2026": int(forecast[f"{metric}_july2026"].sum()),
                "aug2025": int(forecast[f"{metric}_aug2025"].sum()),
                "p10": int(forecast[f"{metric}_p10"].sum()),
                "p90": int(forecast[f"{metric}_p90"].sum()),
            }
            for metric in TARGETS
        },
    }
    # County p10/p90 sums are not a statewide interval (errors are not independent).
    # Replace with a statewide band from the three backtest totals.
    for metric in TARGETS:
        w = wide(panel, metric)
        ratios = []
        for year in (2023, 2024, 2025):
            actual = float(w.loc[pd.Timestamp(year, 8, 1)].sum())
            pred = float(trail3(w, year, 8).sum())
            ratios.append(actual / pred)
        point = state["statewide"][metric]["forecast"]
        state["statewide"][metric]["backtest_actual_over_pred"] = ratios
        state["statewide"][metric]["state_p10"] = int(round(point * min(ratios)))
        state["statewide"][metric]["state_p90"] = int(round(point * max(ratios)))

    # Monthly statewide history for the chart, through July 2026 only.
    history = (
        panel.groupby("DateForSearch")[list(TARGETS)]
        .sum()
        .reset_index()
    )
    history.to_csv(OUT / "statewide_monthly_through_july2026.csv", index=False)
    state["history"] = [
        {"month": r.DateForSearch.strftime("%Y-%m"), **{m: float(getattr(r, m)) for m in TARGETS}}
        for r in history.itertuples(index=False)
    ]
    by_region = (
        forecast.groupby("region")[[f"{m}_forecast" for m in TARGETS]]
        .sum()
        .astype(int)
        .reset_index()
    )
    state["by_region"] = by_region.to_dict(orient="records")
    state["counties"] = forecast.to_dict(orient="records")

    (OUT / "summary.json").write_text(json.dumps(state, indent=2))
    print("Wrote", OUT / "august_2026_by_county.csv")
    print("Statewide forecast", json.dumps(state["statewide"], indent=2))


if __name__ == "__main__":
    main()
