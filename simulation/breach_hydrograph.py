"""
Generates the breach hydrograph (discharge vs. time) that feeds BOTH
simulation engines as the inflow boundary condition.

OUTPUT CONTRACT (this is what dualsphysics_wrapper.py and delft3d_runner.py
both expect as input):

    CSV with exactly two columns, header required:
        time_s,discharge_cms
        0,0
        60,120.5
        120,890.3
        ...

See data/sample/sample_breach_hydrograph.csv for a synthetic placeholder.
Real Rishiganga (Feb 7 2021) values are in
generate_rishiganga_breach_hydrograph() below -- see docs/breach_model.md
for full sourcing/validation.
"""

import csv
import math
from pathlib import Path


def generate_synthetic_hydrograph(
    peak_discharge_cms: float,
    time_to_peak_s: float,
    total_duration_s: float,
    timestep_s: float = 10.0,
) -> list[tuple[float, float]]:
    points = []
    t = 0.0
    while t <= total_duration_s:
        if t <= time_to_peak_s:
            q = peak_discharge_cms * (t / time_to_peak_s) if time_to_peak_s > 0 else peak_discharge_cms
        else:
            decay_const = 3.0 / (total_duration_s - time_to_peak_s)
            q = peak_discharge_cms * math.exp(-decay_const * (t - time_to_peak_s))
        points.append((round(t, 1), round(q, 2)))
        t += timestep_s
    return points


def save_hydrograph_csv(points: list[tuple[float, float]], path: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "discharge_cms"])
        writer.writerows(points)


def generate_rishiganga_breach_hydrograph(
    peak_discharge_cms: float = 12762.0,
    time_to_peak_s: float = 600.0,
    total_duration_s: float = 1800.0,
    baseline_cms: float = 75.0,
    timestep_s: float = 10.0,
) -> list[tuple[float, float]]:
    """
    Real breach hydrograph for the Rishiganga GLOF, Feb 7 2021.
    See docs/breach_model.md for full sourcing and reasoning.
    Peak validated against Pandey et al. 2023 (~12,762 m3/s) and
    Shugar et al. 2021 (range 8,200-14,200 m3/s).
    Rise phase: true exponential rise, normalized to reach exactly
    peak_discharge_cms at t=time_to_peak_s.
    """
    decay_rate_per_s = 0.15 / 60
    rise_k = 3.0

    points = []
    t = 0.0
    while t <= total_duration_s:
        if t <= time_to_peak_s and time_to_peak_s > 0:
            q = peak_discharge_cms * (1 - math.exp(-rise_k * t / time_to_peak_s)) / (1 - math.exp(-rise_k))
        else:
            q = peak_discharge_cms * math.exp(-decay_rate_per_s * (t - time_to_peak_s))
        q = max(q, baseline_cms)
        points.append((round(t, 1), round(q, 2)))
        t += timestep_s
    return points


if __name__ == "__main__":
    pts = generate_rishiganga_breach_hydrograph()
    out_path = "data/processed/rishiganga_breach_hydrograph.csv"
    save_hydrograph_csv(pts, out_path)
    print(f"Wrote {len(pts)} points to {out_path}")
