#!/usr/bin/env python3
"""Compute Exergy Factor summaries from the cloned XAI4HEAT dataset."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KELVIN_OFFSET = 273.15
FIXED_SINK_C = 20.0
DEFAULT_TEMP_ERROR_C = 0.5
PDF_METADATA = {
    "Creator": "quantity-and-quality scripts/analyze_xai4heat.py",
    "CreationDate": datetime(2026, 5, 19, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 5, 19, tzinfo=timezone.utc),
}


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


def carnot_factor(source_k: pd.Series, sink_k: pd.Series | float) -> pd.Series:
    """Constant-temperature thermal Exergy Factor."""
    values = 1.0 - (sink_k / source_k)
    valid = (source_k > 0) & (sink_k > 0) & (source_k >= sink_k)
    return values.where(valid)


def integrated_water_factor(
    supply_k: pd.Series,
    return_k: pd.Series,
    sink_k: pd.Series | float,
) -> pd.Series:
    """Exergy fraction for sensible heat from water cooling from supply to return."""
    delta_t = supply_k - return_k
    log_ratio = np.log(supply_k / return_k)
    logarithmic_mean = delta_t / log_ratio
    valid = (
        (supply_k > return_k)
        & (return_k > 0)
        & (sink_k > 0)
        & np.isfinite(logarithmic_mean)
        & (logarithmic_mean >= sink_k)
    )
    values = pd.Series(np.nan, index=supply_k.index, dtype=float)
    values.loc[valid] = (
        1.0
        - (sink_k.loc[valid] if isinstance(sink_k, pd.Series) else sink_k)
        * np.log(supply_k.loc[valid] / return_k.loc[valid])
        / delta_t.loc[valid]
    )
    return values


def integrated_water_factor_from_kelvin(
    supply_k: pd.Series,
    return_k: pd.Series,
    sink_k: pd.Series | float,
) -> pd.Series:
    """Alias with explicit Kelvin inputs for uncertainty perturbations."""
    return integrated_water_factor(supply_k, return_k, sink_k)


def load_station(path: Path) -> pd.DataFrame:
    station = path.stem.split("_")[-1]
    df = pd.read_csv(path, parse_dates=["datetime"])
    t_sup_prim_k = df["t_sup_prim"] + KELVIN_OFFSET
    t_ret_prim_k = df["t_ret_prim"] + KELVIN_OFFSET
    t_sup_sec_k = df["t_sup_sec"] + KELVIN_OFFSET
    t_ret_sec_k = df["t_ret_sec"] + KELVIN_OFFSET
    amb_k = df["t_amb"] + KELVIN_OFFSET
    fixed_k = FIXED_SINK_C + KELVIN_OFFSET
    fx_supply_ambient = carnot_factor(t_sup_prim_k, amb_k)

    df = df.assign(
        station=station,
        qizm_weight=df["qizm"].clip(lower=0),
        fx_dynamic=fx_supply_ambient,
        fx_fixed_20c=carnot_factor(t_sup_prim_k, fixed_k),
        fx_supply_ambient=fx_supply_ambient,
        fx_primary_integrated_ambient=integrated_water_factor(t_sup_prim_k, t_ret_prim_k, amb_k),
        fx_primary_integrated_fixed_20c=integrated_water_factor(
            t_sup_prim_k, t_ret_prim_k, fixed_k
        ),
        fx_secondary_integrated_ambient=integrated_water_factor(t_sup_sec_k, t_ret_sec_k, amb_k),
        fx_return_sink=carnot_factor(t_sup_prim_k, t_ret_prim_k),
    )
    return df


def summarize_station(df: pd.DataFrame) -> dict[str, object]:
    valid = df["fx_dynamic"].notna() & df["fx_fixed_20c"].notna()
    positive = valid & (df["qizm_weight"] > 0)
    peak_idx = df.loc[valid, "fx_dynamic"].idxmax()
    return {
        "station": df["station"].iloc[0],
        "date_start": df["datetime"].min().date().isoformat(),
        "date_end": df["datetime"].max().date().isoformat(),
        "intervals": int(valid.sum()),
        "positive_qizm_intervals": int(positive.sum()),
        "qizm_sum": float(df.loc[valid, "qizm_weight"].sum()),
        "mean_t_sup_prim_c": float(df.loc[valid, "t_sup_prim"].mean()),
        "mean_t_amb_c": float(df.loc[valid, "t_amb"].mean()),
        "simple_mean_fx_dynamic": float(df.loc[valid, "fx_dynamic"].mean()),
        "qizm_weighted_fx_dynamic": weighted_average(df["fx_dynamic"], df["qizm_weight"]),
        "qizm_weighted_fx_fixed_20c": weighted_average(df["fx_fixed_20c"], df["qizm_weight"]),
        "qizm_weighted_fx_primary_integrated_ambient": weighted_average(
            df["fx_primary_integrated_ambient"], df["qizm_weight"]
        ),
        "qizm_weighted_fx_primary_integrated_fixed_20c": weighted_average(
            df["fx_primary_integrated_fixed_20c"], df["qizm_weight"]
        ),
        "qizm_weighted_fx_secondary_integrated_ambient": weighted_average(
            df["fx_secondary_integrated_ambient"], df["qizm_weight"]
        ),
        "qizm_weighted_fx_return_sink": weighted_average(df["fx_return_sink"], df["qizm_weight"]),
        "peak_fx_dynamic": float(df.loc[peak_idx, "fx_dynamic"]),
        "peak_fx_datetime": df.loc[peak_idx, "datetime"].isoformat(),
        "min_fx_dynamic": float(df.loc[valid, "fx_dynamic"].min()),
        "negative_fx_count": int((df.loc[valid, "fx_dynamic"] < 0).sum()),
    }


def daily_weighted(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (station, date), group in df.groupby(["station", df["datetime"].dt.date]):
        weight = group["qizm_weight"]
        rows.append(
            {
                "station": station,
                "date": pd.Timestamp(date),
                "qizm_sum": float(weight.sum()),
                "fx_dynamic": weighted_average(group["fx_dynamic"], weight),
                "fx_fixed_20c": weighted_average(group["fx_fixed_20c"], weight),
                "fx_primary_integrated_ambient": weighted_average(
                    group["fx_primary_integrated_ambient"], weight
                ),
                "fx_secondary_integrated_ambient": weighted_average(
                    group["fx_secondary_integrated_ambient"], weight
                ),
                "fx_return_sink": weighted_average(group["fx_return_sink"], weight),
                "t_sup_prim_c": weighted_average(group["t_sup_prim"], weight),
                "t_amb_c": weighted_average(group["t_amb"], weight),
            }
        )
    return pd.DataFrame(rows)


def portfolio_daily(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, group in daily.groupby("date"):
        weight = group["qizm_sum"]
        rows.append(
            {
                "date": date,
                "qizm_sum": float(weight.sum()),
                "fx_dynamic": weighted_average(group["fx_dynamic"], weight),
                "fx_fixed_20c": weighted_average(group["fx_fixed_20c"], weight),
                "fx_primary_integrated_ambient": weighted_average(
                    group["fx_primary_integrated_ambient"], weight
                ),
                "fx_secondary_integrated_ambient": weighted_average(
                    group["fx_secondary_integrated_ambient"], weight
                ),
                "fx_return_sink": weighted_average(group["fx_return_sink"], weight),
                "t_sup_prim_c": weighted_average(group["t_sup_prim_c"], weight),
                "t_amb_c": weighted_average(group["t_amb_c"], weight),
            }
        )
    return pd.DataFrame(rows).sort_values("date")


def interval_count(values: pd.Series) -> int:
    return int(values.notna().sum())


def uncertainty_carnot(
    source_k: pd.Series,
    sink_k: pd.Series | float,
    weights: pd.Series,
    temp_error_c: float,
    perturb_sink: bool = True,
) -> tuple[float, float, float]:
    """Return base, low, and high weighted factors under temperature perturbation."""
    base = weighted_average(carnot_factor(source_k, sink_k), weights)
    low_sink = sink_k + temp_error_c if perturb_sink else sink_k
    high_sink = sink_k - temp_error_c if perturb_sink else sink_k
    low = weighted_average(carnot_factor(source_k - temp_error_c, low_sink), weights)
    high = weighted_average(carnot_factor(source_k + temp_error_c, high_sink), weights)
    return base, low, high


def uncertainty_integrated(
    supply_k: pd.Series,
    return_k: pd.Series,
    sink_k: pd.Series | float,
    weights: pd.Series,
    temp_error_c: float,
    perturb_sink: bool = True,
) -> tuple[float, float, float]:
    """Return base plus min/max weighted factors across conservative perturbation corners."""
    base_series = integrated_water_factor_from_kelvin(supply_k, return_k, sink_k)
    base = weighted_average(base_series, weights)
    values = []
    sink_signs = [-1, 1] if perturb_sink else [0]
    for supply_sign in [-1, 1]:
        for return_sign in [-1, 1]:
            for sink_sign in sink_signs:
                perturbed_sink = sink_k + sink_sign * temp_error_c if perturb_sink else sink_k
                values.append(
                    weighted_average(
                        integrated_water_factor_from_kelvin(
                            supply_k + supply_sign * temp_error_c,
                            return_k + return_sign * temp_error_c,
                            perturbed_sink,
                        ),
                        weights,
                    )
                )
    finite = [value for value in values if np.isfinite(value)]
    return base, min(finite), max(finite)


def make_uncertainty_table(
    all_data: pd.DataFrame,
    temp_error_c: float,
) -> pd.DataFrame:
    weights = all_data["qizm_weight"]
    t_sup_prim_k = all_data["t_sup_prim"] + KELVIN_OFFSET
    t_ret_prim_k = all_data["t_ret_prim"] + KELVIN_OFFSET
    t_sup_sec_k = all_data["t_sup_sec"] + KELVIN_OFFSET
    t_ret_sec_k = all_data["t_ret_sec"] + KELVIN_OFFSET
    amb_k = all_data["t_amb"] + KELVIN_OFFSET
    fixed_k = FIXED_SINK_C + KELVIN_OFFSET

    rows = []
    specs = [
        (
            "primary_supply_ambient_carnot",
            all_data["fx_supply_ambient"],
            uncertainty_carnot(t_sup_prim_k, amb_k, weights, temp_error_c),
        ),
        (
            "primary_supply_return_integrated_ambient",
            all_data["fx_primary_integrated_ambient"],
            uncertainty_integrated(t_sup_prim_k, t_ret_prim_k, amb_k, weights, temp_error_c),
        ),
        (
            "secondary_supply_return_integrated_ambient",
            all_data["fx_secondary_integrated_ambient"],
            uncertainty_integrated(t_sup_sec_k, t_ret_sec_k, amb_k, weights, temp_error_c),
        ),
        (
            "primary_return_sink_carnot",
            all_data["fx_return_sink"],
            uncertainty_carnot(t_sup_prim_k, t_ret_prim_k, weights, temp_error_c),
        ),
        (
            "primary_supply_fixed_20c_carnot",
            all_data["fx_fixed_20c"],
            uncertainty_carnot(
                t_sup_prim_k,
                fixed_k,
                weights,
                temp_error_c,
                perturb_sink=False,
            ),
        ),
    ]
    for model, base_series, (base, low, high) in specs:
        abs_uncertainty = max(abs(base - low), abs(high - base))
        rows.append(
            {
                "model": model,
                "temperature_error_c": temp_error_c,
                "portfolio_fx": base,
                "low_fx": low,
                "high_fx": high,
                "abs_uncertainty_fx": abs_uncertainty,
                "relative_uncertainty_percent": (
                    100.0 * abs_uncertainty / abs(base) if base else float("nan")
                ),
                "valid_intervals": interval_count(base_series),
            }
        )
    return pd.DataFrame(rows)


def make_figure(daily: pd.DataFrame, portfolio: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8.8, 6.8), constrained_layout=True)

    ax = axes[0]
    for station, group in daily.groupby("station"):
        ax.plot(
            group["date"],
            group["fx_dynamic"],
            linewidth=0.85,
            alpha=0.55,
            label=f"{station} dynamic",
        )
    ax.plot(
        portfolio["date"],
        portfolio["fx_dynamic"],
        color="black",
        linewidth=1.8,
        label="Portfolio dynamic",
    )
    ax.plot(
        portfolio["date"],
        portfolio["fx_fixed_20c"],
        color="#a45a00",
        linewidth=1.5,
        linestyle="--",
        label=r"Portfolio fixed $20^\circ$C",
    )
    ax.set_ylabel("Daily weighted $f_X$")
    ax.set_title("XAI4HEAT 2024-25 processed substation files")
    ax.grid(True, alpha=0.25)
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        ncol=1,
        fontsize=7.5,
        frameon=False,
        borderaxespad=0.0,
    )

    zoom = portfolio[
        (portfolio["date"] >= pd.Timestamp("2025-02-17"))
        & (portfolio["date"] <= pd.Timestamp("2025-02-22"))
    ]
    ax2 = axes[1]
    ax2.plot(
        zoom["date"],
        zoom["fx_dynamic"],
        color="black",
        linewidth=2.0,
        marker="o",
        label="Dynamic $f_X$",
    )
    ax2.plot(
        zoom["date"],
        zoom["fx_fixed_20c"],
        color="#a45a00",
        linewidth=1.8,
        linestyle="--",
        marker="s",
        label=r"Fixed $20^\circ$C $f_X$",
    )
    ax2.set_ylabel("Portfolio $f_X$")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.25)

    ax3 = ax2.twinx()
    ax3.plot(
        zoom["date"],
        zoom["t_sup_prim_c"],
        color="#2364aa",
        linewidth=1.5,
        alpha=0.85,
        label=r"Primary supply ($^\circ$C)",
    )
    ax3.plot(
        zoom["date"],
        zoom["t_amb_c"],
        color="#3b7a57",
        linewidth=1.5,
        alpha=0.85,
        label=r"Ambient ($^\circ$C)",
    )
    ax3.set_ylabel(r"Temperature ($^\circ$C)")

    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(
        lines + lines2,
        labels + labels2,
        loc="center left",
        bbox_to_anchor=(1.11, 0.5),
        ncol=1,
        fontsize=7.5,
        frameon=False,
        borderaxespad=0.0,
    )

    for axis in axes:
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        axis.tick_params(axis="x", rotation=25)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xai4heat-root",
        type=Path,
        default=Path("runtime/external/xai4heat"),
        help="Path to a clone of https://github.com/xai4heat/xai4heat",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("paper/generated/xai4heat_f3_summary.csv"),
    )
    parser.add_argument(
        "--daily",
        type=Path,
        default=Path("paper/generated/xai4heat_f3_daily.csv"),
    )
    parser.add_argument(
        "--model-sensitivity",
        type=Path,
        default=Path("paper/generated/xai4heat_f3_model_sensitivity.csv"),
    )
    parser.add_argument(
        "--uncertainty",
        type=Path,
        default=Path("paper/generated/xai4heat_f3_uncertainty.csv"),
    )
    parser.add_argument(
        "--temp-error-c",
        type=float,
        default=DEFAULT_TEMP_ERROR_C,
        help="Symmetric temperature uncertainty for empirical sensitivity table.",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=Path("paper/f3_district_heat_backcast.pdf"),
    )
    args = parser.parse_args()

    data_dir = args.xai4heat_root / "datasets"
    files = sorted(data_dir.glob("xai4heat_2024-25_L*.csv"))
    if not files:
        raise SystemExit(f"No processed station files found in {data_dir}")

    frames = [load_station(path) for path in files]
    all_data = pd.concat(frames, ignore_index=True)
    summary = pd.DataFrame(summarize_station(frame) for frame in frames).sort_values("station")
    summary["dynamic_minus_fixed_20c"] = (
        summary["qizm_weighted_fx_dynamic"] - summary["qizm_weighted_fx_fixed_20c"]
    )

    daily = daily_weighted(all_data)
    portfolio = portfolio_daily(daily)
    portfolio_summary = {
        "station": "portfolio",
        "date_start": all_data["datetime"].min().date().isoformat(),
        "date_end": all_data["datetime"].max().date().isoformat(),
        "intervals": int(all_data["fx_dynamic"].notna().sum()),
        "positive_qizm_intervals": int((all_data["qizm_weight"] > 0).sum()),
        "qizm_sum": float(all_data["qizm_weight"].sum()),
        "mean_t_sup_prim_c": weighted_average(all_data["t_sup_prim"], all_data["qizm_weight"]),
        "mean_t_amb_c": weighted_average(all_data["t_amb"], all_data["qizm_weight"]),
        "simple_mean_fx_dynamic": float(all_data["fx_dynamic"].mean()),
        "qizm_weighted_fx_dynamic": weighted_average(
            all_data["fx_dynamic"], all_data["qizm_weight"]
        ),
        "qizm_weighted_fx_fixed_20c": weighted_average(
            all_data["fx_fixed_20c"], all_data["qizm_weight"]
        ),
        "qizm_weighted_fx_primary_integrated_ambient": weighted_average(
            all_data["fx_primary_integrated_ambient"], all_data["qizm_weight"]
        ),
        "qizm_weighted_fx_primary_integrated_fixed_20c": weighted_average(
            all_data["fx_primary_integrated_fixed_20c"], all_data["qizm_weight"]
        ),
        "qizm_weighted_fx_secondary_integrated_ambient": weighted_average(
            all_data["fx_secondary_integrated_ambient"], all_data["qizm_weight"]
        ),
        "qizm_weighted_fx_return_sink": weighted_average(
            all_data["fx_return_sink"], all_data["qizm_weight"]
        ),
        "peak_fx_dynamic": float(all_data["fx_dynamic"].max()),
        "peak_fx_datetime": all_data.loc[all_data["fx_dynamic"].idxmax(), "datetime"].isoformat(),
        "min_fx_dynamic": float(all_data["fx_dynamic"].min()),
        "negative_fx_count": int((all_data["fx_dynamic"] < 0).sum()),
    }
    portfolio_summary["dynamic_minus_fixed_20c"] = (
        portfolio_summary["qizm_weighted_fx_dynamic"]
        - portfolio_summary["qizm_weighted_fx_fixed_20c"]
    )
    summary = pd.concat([summary, pd.DataFrame([portfolio_summary])], ignore_index=True)

    model_sensitivity = pd.DataFrame(
        [
            {
                "model": "primary_supply_ambient_carnot",
                "formula": "1 - T_amb/T_sup_prim",
                "portfolio_fx": weighted_average(
                    all_data["fx_supply_ambient"], all_data["qizm_weight"]
                ),
                "valid_intervals": int(all_data["fx_supply_ambient"].notna().sum()),
            },
            {
                "model": "primary_supply_return_integrated_ambient",
                "formula": "1 - T_amb ln(T_sup_prim/T_ret_prim)/(T_sup_prim-T_ret_prim)",
                "portfolio_fx": weighted_average(
                    all_data["fx_primary_integrated_ambient"],
                    all_data["qizm_weight"],
                ),
                "valid_intervals": int(all_data["fx_primary_integrated_ambient"].notna().sum()),
            },
            {
                "model": "secondary_supply_return_integrated_ambient",
                "formula": "1 - T_amb ln(T_sup_sec/T_ret_sec)/(T_sup_sec-T_ret_sec)",
                "portfolio_fx": weighted_average(
                    all_data["fx_secondary_integrated_ambient"],
                    all_data["qizm_weight"],
                ),
                "valid_intervals": int(all_data["fx_secondary_integrated_ambient"].notna().sum()),
            },
            {
                "model": "primary_return_sink_carnot",
                "formula": "1 - T_ret_prim/T_sup_prim",
                "portfolio_fx": weighted_average(
                    all_data["fx_return_sink"], all_data["qizm_weight"]
                ),
                "valid_intervals": int(all_data["fx_return_sink"].notna().sum()),
            },
            {
                "model": "primary_supply_fixed_20c_carnot",
                "formula": "1 - T_20C/T_sup_prim",
                "portfolio_fx": weighted_average(all_data["fx_fixed_20c"], all_data["qizm_weight"]),
                "valid_intervals": int(all_data["fx_fixed_20c"].notna().sum()),
            },
        ]
    )
    uncertainty = make_uncertainty_table(all_data, args.temp_error_c)

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary, index=False)
    daily.to_csv(args.daily, index=False)
    model_sensitivity.to_csv(args.model_sensitivity, index=False)
    uncertainty.to_csv(args.uncertainty, index=False)
    make_figure(daily, portfolio, args.figure)

    display_cols = [
        "station",
        "intervals",
        "qizm_sum",
        "mean_t_sup_prim_c",
        "mean_t_amb_c",
        "qizm_weighted_fx_dynamic",
        "qizm_weighted_fx_fixed_20c",
        "qizm_weighted_fx_primary_integrated_ambient",
        "qizm_weighted_fx_secondary_integrated_ambient",
        "qizm_weighted_fx_return_sink",
        "dynamic_minus_fixed_20c",
        "peak_fx_dynamic",
    ]
    print(summary[display_cols].round(4).to_string(index=False))
    print()
    print(model_sensitivity.round(4).to_string(index=False))
    print()
    print(uncertainty.round(5).to_string(index=False))
    print(f"Wrote {args.summary}")
    print(f"Wrote {args.daily}")
    print(f"Wrote {args.model_sensitivity}")
    print(f"Wrote {args.uncertainty}")
    print(f"Wrote {args.figure}")


if __name__ == "__main__":
    main()
