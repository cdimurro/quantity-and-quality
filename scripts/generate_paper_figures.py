#!/usr/bin/env python3
"""Generate deterministic paper figures that do not depend on external data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PDF_METADATA = {
    "Creator": "quantity-and-quality scripts/generate_paper_figures.py",
    "CreationDate": datetime(2026, 5, 19, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 5, 19, tzinfo=timezone.utc),
}


def save_reference_temp_sensitivity(output: Path) -> None:
    source_c = 80.0
    degree = "\N{DEGREE SIGN}"
    t0_c = np.linspace(0, 35, 141)
    fx = 1.0 - (t0_c + 273.15) / (source_c + 273.15)

    fig, ax = plt.subplots(figsize=(6.4, 3.8), constrained_layout=True)
    ax.plot(t0_c, fx, color="black", linewidth=2)
    for ref_c in [15, 20, 25]:
        ref_fx = 1.0 - (ref_c + 273.15) / (source_c + 273.15)
        ax.scatter([ref_c], [ref_fx], color="#2364aa", zorder=3)
        ax.annotate(
            f"{ref_c}{degree}C: {ref_fx:.3f}",
            xy=(ref_c, ref_fx),
            xytext=(ref_c + 1.2, ref_fx + 0.004),
            fontsize=9,
        )
    ax.set_xlabel(f"Reference sink temperature, $T_0$ ({degree}C)")
    ax.set_ylabel("Thermal Exergy Factor, $f_X$")
    ax.set_title(f"{source_c:.0f}{degree}C Heat: Sensitivity to Reference Sink")
    ax.grid(True, alpha=0.25)
    ax.set_xlim(0, 35)
    ax.set_ylim(0.12, 0.24)
    fig.savefig(output, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)


def save_theta_loss_mapping(output: Path) -> None:
    eta = np.linspace(0.0, 1.0, 401)
    theta = np.degrees(np.arctan2(1 - eta, eta))
    points = np.array([0.93, 0.83, 0.50, 0.192, 0.064])
    point_theta = np.degrees(np.arctan2(1 - points, points))

    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    ax.plot(eta, theta, color="black", linewidth=2)
    ax.scatter(points, point_theta, color="#a45a00", zorder=3)
    label_positions = {
        0.064: (0.15, 82.5),
        0.192: (0.29, 81.0),
        0.50: (0.57, 52.5),
        0.83: (0.67, 31.0),
        0.93: (0.97, 18.0),
    }
    label_alignment = {
        0.93: "right",
    }
    for e, t in zip(points, point_theta):
        text_x, text_y = label_positions[float(e)]
        ax.annotate(
            f"$\\eta_X={e:.3f}$\n${t:.1f}^\\circ$",
            xy=(e, t),
            xytext=(text_x, text_y),
            textcoords="data",
            fontsize=8,
            ha=label_alignment.get(float(e), "left"),
            va="bottom",
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.94,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#555555",
                "linewidth": 0.6,
                "shrinkA": 2,
                "shrinkB": 4,
            },
        )
    ax.set_xlabel("Second-law efficiency, $\\eta_X$")
    ax.set_ylabel("Exergy Loss Angle, $\\theta_{loss}$ (degrees)")
    ax.set_title("Bounded Display Coordinate for Exergy Non-Retention", pad=12)
    ax.grid(True, alpha=0.25)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 90)
    ax.set_yticks([0, 20, 40, 60, 80, 90])
    fig.savefig(output, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)


def save_ece_comparison(output: Path) -> None:
    labels = ["Low-temp\nlarge MWh", "Higher-temp\nsmaller MWh"]
    energy = np.array([1000.0, 300.0])
    fx = np.array([0.04, 0.307])
    capex_musd = np.array([2.0, 1.5])
    mwh_ex = energy * fx
    ece = mwh_ex / capex_musd

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), constrained_layout=True)
    axes[0].bar(labels, energy, color=["#8da0cb", "#66c2a5"])
    axes[0].set_ylabel("Reported energy (MWh)")
    axes[0].set_title("Scalar Energy Screen")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].set_ylim(0, energy.max() * 1.18)

    axes[1].bar(labels, ece, color=["#8da0cb", "#66c2a5"])
    axes[1].set_ylabel("MWh_ex per million dollars")
    axes[1].set_title("Exergy Capital Efficiency")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].set_ylim(0, ece.max() * 1.18)
    for ax, vals in zip(axes, [energy, ece]):
        for i, val in enumerate(vals):
            ax.text(i, val * 1.02, f"{val:.1f}", ha="center", va="bottom", fontsize=9)
    fig.savefig(output, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("paper"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_reference_temp_sensitivity(args.output_dir / "reference_temp_sensitivity.pdf")
    save_theta_loss_mapping(args.output_dir / "theta_loss_mapping.pdf")
    save_ece_comparison(args.output_dir / "ece_comparison.pdf")
    print(f"Wrote figures to {args.output_dir}")


if __name__ == "__main__":
    main()
