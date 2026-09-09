"""
Compares two SimResult outputs (e.g. dualsphysics vs swe_fallback) run on
the SAME dem_path + breach_hydrograph_csv -- satisfies the project's
explicit "compare the scenario" deliverable.

Produces:
  - a difference raster (engine_a depth - engine_b depth)
  - summary statistics: peak depth, flooded area, mean depth per engine
  - a JSON summary, directly usable by the dashboard/frontend

Both max_depth_raster files must share the same grid shape for a valid
cell-by-cell diff -- true whenever both engines are run against the same
DEM, since both georeference their output to the input DEM's CRS/transform.
"""

import json
from pathlib import Path

import numpy as np
import rasterio

from simulation.sim_result import SimResult


def compare_results(result_a: SimResult, result_b: SimResult, output_dir: str) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if result_a.status != "success" or result_b.status != "success":
        summary = {
            "comparable": False,
            "reason": f"One or both runs did not succeed (a.status={result_a.status}, b.status={result_b.status})",
            "engine_a": result_a.engine,
            "engine_b": result_b.engine,
        }
        _write_json(summary, output_dir / "comparison_summary.json")
        return summary

    if not result_a.max_depth_raster or not result_b.max_depth_raster:
        summary = {
            "comparable": False,
            "reason": "One or both results have no max_depth_raster",
            "engine_a": result_a.engine,
            "engine_b": result_b.engine,
        }
        _write_json(summary, output_dir / "comparison_summary.json")
        return summary

    with rasterio.open(result_a.max_depth_raster) as src_a:
        depth_a = src_a.read(1)
        nodata_a = src_a.nodata
        transform_a = src_a.transform
        crs_a = src_a.crs
        shape_a = src_a.shape

    with rasterio.open(result_b.max_depth_raster) as src_b:
        depth_b = src_b.read(1)
        nodata_b = src_b.nodata
        shape_b = src_b.shape

    if shape_a != shape_b:
        summary = {
            "comparable": False,
            "reason": (f"Grid shape mismatch: {result_a.engine}={shape_a} vs "
                       f"{result_b.engine}={shape_b}. Both engines must be run "
                       f"against the SAME DEM for a valid cell-by-cell comparison."),
            "engine_a": result_a.engine,
            "engine_b": result_b.engine,
        }
        _write_json(summary, output_dir / "comparison_summary.json")
        return summary

    depth_a_clean = np.where(depth_a == nodata_a, 0.0, depth_a) if nodata_a is not None else depth_a
    depth_b_clean = np.where(depth_b == nodata_b, 0.0, depth_b) if nodata_b is not None else depth_b
    depth_a_clean = np.maximum(depth_a_clean, 0.0)
    depth_b_clean = np.maximum(depth_b_clean, 0.0)

    diff = depth_a_clean - depth_b_clean

    diff_path = output_dir / "comparison_diff.tif"
    with rasterio.open(
        diff_path, "w", driver="GTiff", height=shape_a[0], width=shape_a[1], count=1,
        dtype=diff.dtype, crs=crs_a, transform=transform_a, nodata=-9999.0,
    ) as dst:
        dst.write(diff, 1)

    cell_area = abs(transform_a.a * transform_a.e)

    summary = {
        "comparable": True,
        "engine_a": result_a.engine,
        "engine_b": result_b.engine,
        "engine_a_peak_depth_m": float(depth_a_clean.max()),
        "engine_b_peak_depth_m": float(depth_b_clean.max()),
        "engine_a_flooded_area_m2": float((depth_a_clean > 0.01).sum() * cell_area),
        "engine_b_flooded_area_m2": float((depth_b_clean > 0.01).sum() * cell_area),
        "engine_a_mean_depth_m": float(depth_a_clean[depth_a_clean > 0.01].mean()) if (depth_a_clean > 0.01).any() else 0.0,
        "engine_b_mean_depth_m": float(depth_b_clean[depth_b_clean > 0.01].mean()) if (depth_b_clean > 0.01).any() else 0.0,
        "max_abs_diff_m": float(np.abs(diff).max()),
        "mean_abs_diff_m": float(np.abs(diff).mean()),
        "engine_a_runtime_seconds": result_a.runtime_seconds,
        "engine_b_runtime_seconds": result_b.runtime_seconds,
        "diff_raster": str(diff_path),
    }

    _write_json(summary, output_dir / "comparison_summary.json")
    return summary


def _write_json(data: dict, path: Path) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    from simulation.delft3d.delft3d_runner import run_second_model
    from simulation.sph.dualsphysics_wrapper import run_sph_simulation

    dem_path = "data/sample/sample_dem.tif"
    hydrograph_path = "data/sample/sample_breach_hydrograph.csv"
    shared_config = {"breach_row": 2, "breach_col": 30, "sim_duration_s": 1800}

    result_swe = run_second_model(
        dem_path=dem_path, breach_hydrograph_csv=hydrograph_path,
        case_name="compare_test", output_dir="analysis/outputs/compare_test/swe",
        config=shared_config,
    )
    print("SWE:", result_swe.status)

    result_sph = run_sph_simulation(
        dem_path=dem_path, breach_hydrograph_csv=hydrograph_path,
        case_name="compare_test", output_dir="analysis/outputs/compare_test/sph",
        config={**shared_config, "dp": 2.0},
    )
    print("SPH:", result_sph.status)

    summary = compare_results(result_sph, result_swe, "analysis/outputs/compare_test")
    print(json.dumps(summary, indent=2))
