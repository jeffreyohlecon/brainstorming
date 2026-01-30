#!/usr/bin/env python3
"""
Covariate validation OLS for synth matching variables.

Aggregates ZIP3×month panel to ZIP3-level pre-period totals and
regresses log(pre-period transactions) on demographics (and price).

Outputs to the exploratory output directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import get_exploratory_dir, log


PRE_START_MONTH = 3  # Mar 2023
PRE_END_MONTH = 9    # Sep 2023


DEMO_VARS = [
    "pct_college",
    "pct_hh_100k",
    "pct_young",
    "median_age",
    "median_income",
    "pct_stem",
    "pct_broadband",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run covariate validation OLS on pre-period totals."
    )
    parser.add_argument(
        "--lasso",
        action="store_true",
        help="Run LASSO CV for variable selection."
    )
    return parser.parse_args()


def _check_log_outcome(series: pd.Series, name: str) -> pd.Series:
    if (series <= 0).any():
        n_bad = int((series <= 0).sum())
        raise ValueError(
            f"{name} has {n_bad} non-positive values; "
            "cannot take log."
        )
    return np.log(series)


def _tidy_ols(res, model_name: str) -> pd.DataFrame:
    rows = []
    for var in res.params.index:
        rows.append(
            {
                "model": model_name,
                "variable": var,
                "coef": res.params[var],
                "se": res.bse[var],
                "t": res.tvalues[var],
                "p": res.pvalues[var],
            }
        )
    out = pd.DataFrame(rows)
    out["n"] = int(res.nobs)
    out["r2"] = res.rsquared
    return out


def _wide_table(tidy: pd.DataFrame) -> pd.DataFrame:
    wide = (
        tidy.pivot(index="variable", columns="model", values="coef")
        .rename_axis(None, axis=1)
        .reset_index()
    )
    for model in tidy["model"].unique():
        se = (
            tidy.loc[tidy["model"] == model]
            .set_index("variable")["se"]
        )
        wide[f"{model}_se"] = wide["variable"].map(se)
    return wide


def _univariate_correlations(
    df: pd.DataFrame,
    y_col: str,
    covars: list[str],
    out_dir: Path,
) -> None:
    rows = []
    for var in covars:
        x = df[var]
        y = df[y_col]
        corr = x.corr(y)
        rows.append({"variable": var, "corr": corr})
    out = pd.DataFrame(rows).sort_values("corr", key=np.abs,
                                         ascending=False)
    out_path = out_dir / "covariate_validation_correlations.csv"
    out.to_csv(out_path, index=False)
    log(f"Saved correlations: {out_path}")


def _scatterplots(
    df: pd.DataFrame,
    y_col: str,
    covars: list[str],
    out_dir: Path,
) -> None:
    n = len(covars)
    nrows = 2
    ncols = 4
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 6))
    axes = axes.flatten()
    for i, var in enumerate(covars):
        ax = axes[i]
        ax.scatter(df[var], df[y_col], s=12, alpha=0.6)
        ax.set_title(var)
        ax.set_xlabel(var)
        ax.set_ylabel(y_col)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.tight_layout()
    out_path = out_dir / "covariate_validation_scatterplots.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    log(f"Saved scatterplots: {out_path}")


def _partial_r2(
    df: pd.DataFrame,
    y_col: str,
    covars: list[str],
    out_dir: Path,
) -> None:
    import statsmodels.api as sm

    X_full = sm.add_constant(df[covars])
    y = df[y_col]
    res_full = sm.OLS(y, X_full).fit()
    r2_full = res_full.rsquared

    rows = []
    for var in covars:
        reduced = [v for v in covars if v != var]
        X_red = sm.add_constant(df[reduced])
        res_red = sm.OLS(y, X_red).fit()
        r2_red = res_red.rsquared
        rows.append(
            {
                "variable": var,
                "r2_full": r2_full,
                "r2_reduced": r2_red,
                "delta_r2": r2_full - r2_red,
            }
        )
    out = pd.DataFrame(rows).sort_values("delta_r2",
                                         ascending=False)
    out_path = out_dir / "covariate_validation_partial_r2.csv"
    out.to_csv(out_path, index=False)
    log(f"Saved partial R2: {out_path}")


def run_lasso(
    df: pd.DataFrame,
    y: pd.Series,
    covars: list[str],
    out_dir: Path,
) -> None:
    try:
        from sklearn.linear_model import LassoCV
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        raise SystemExit(
            "scikit-learn not installed. Install it or rerun "
            "without --lasso."
        )

    X = df[covars].to_numpy()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    lasso = LassoCV(cv=10, random_state=0)
    lasso.fit(Xs, y.to_numpy())

    coefs = pd.Series(lasso.coef_, index=covars)
    out = pd.DataFrame(
        {
            "variable": coefs.index,
            "coef_std": coefs.values,
            "selected": (coefs != 0).astype(int),
        }
    )
    out_path = out_dir / "covariate_validation_lasso.csv"
    out.to_csv(out_path, index=False)
    log(f"Saved LASSO results: {out_path}")


def main() -> None:
    args = parse_args()

    panel_path = Path(__file__).parent.parent.parent / "data" / "synth_panel.dta"
    log(f"Loading panel: {panel_path}")
    panel = pd.read_stata(panel_path)

    pre_mask = (panel["month_num"] >= PRE_START_MONTH) & (
        panel["month_num"] <= PRE_END_MONTH
    )
    pre = panel.loc[pre_mask].copy()

    keep_cols = ["zip3", "pre_mean_price", "population"] + DEMO_VARS
    agg = (
        pre.groupby("zip3")
        .agg(
            pre_n_trans=("n_trans", "sum"),
            pre_n_users=("n_users", "sum"),
            **{c: (c, "first") for c in keep_cols if c != "zip3"},
        )
        .reset_index()
    )

    agg["log_pre_n_trans"] = _check_log_outcome(
        agg["pre_n_trans"], "pre_n_trans"
    )

    covars_base = DEMO_VARS.copy()
    covars_price = DEMO_VARS + ["pre_mean_price"]

    out_dir = get_exploratory_dir()

    import statsmodels.api as sm

    rows = []
    for name, covars in [
        ("demo_only", covars_base),
        ("demo_plus_price", covars_price),
    ]:
        df = agg.dropna(subset=covars + ["log_pre_n_trans"]).copy()
        X = sm.add_constant(df[covars])
        y = df["log_pre_n_trans"]
        res = sm.OLS(y, X).fit(cov_type="HC1")
        rows.append(_tidy_ols(res, name))

    tidy = pd.concat(rows, ignore_index=True)
    wide = _wide_table(tidy)

    tidy_path = out_dir / "covariate_validation_ols_tidy.csv"
    wide_path = out_dir / "covariate_validation_ols.csv"
    tidy.to_csv(tidy_path, index=False)
    wide.to_csv(wide_path, index=False)
    log(f"Saved OLS tidy table: {tidy_path}")
    log(f"Saved OLS wide table: {wide_path}")

    _univariate_correlations(
        agg.dropna(subset=covars_price + ["log_pre_n_trans"]),
        y_col="log_pre_n_trans",
        covars=covars_price,
        out_dir=out_dir,
    )

    _scatterplots(
        agg.dropna(subset=covars_price + ["log_pre_n_trans"]),
        y_col="log_pre_n_trans",
        covars=covars_price,
        out_dir=out_dir,
    )

    _partial_r2(
        agg.dropna(subset=covars_price + ["log_pre_n_trans"]),
        y_col="log_pre_n_trans",
        covars=covars_price,
        out_dir=out_dir,
    )

    if args.lasso:
        run_lasso(agg.dropna(subset=covars_price), y=agg["log_pre_n_trans"],
                  covars=covars_price, out_dir=out_dir)


if __name__ == "__main__":
    main()
