"""
Background job orchestration for triggering simulation runs.

Wraps BOTH simulation engines behind one call so main.py never has to
care which one is running -- both conform exactly to the shared
simulation/sim_result.py::SimResult contract.

After a successful run, also converts the max-depth raster into vector
format (.shp) via analysis/raster_to_vector.py and attaches the result
path back onto the SimResult -- this is what makes flood_extent_vector
non-null for the frontend's download button, and satisfies the project's
explicit .shp/.kml export deliverable.

Deliberately a plain in-memory dict + FastAPI BackgroundTasks for the
hackathon, not Celery/Redis: the SWE fallback is sub-second and even a
DualSPHysics demo run is short enough for a single job at a time. Swap
this for a real queue only if runs start queuing up during the demo.

NOTE: this process must be started with the repo root as the working
directory / on PYTHONPATH, e.g.:
    uvicorn dashboard.backend.main:app --reload
run from the repo root -- otherwise `from simulation... import ...` below
won't resolve (there's no setup.py/pyproject.toml pinning this yet).
"""

import uuid
from dataclasses import replace
from pathlib import Path
from typing import Literal, Optional

from simulation.sim_result import SimResult
from simulation.sph.dualsphysics_wrapper import run_sph_simulation
from simulation.delft3d.delft3d_runner import run_second_model
from analysis.raster_to_vector import export_both_formats

Engine = Literal["dualsphysics", "swe_fallback"]

ENGINE_FUNCS = {
    "dualsphysics": run_sph_simulation,
    "swe_fallback": run_second_model,
}

JOBS: dict[str, dict] = {}

OUTPUT_ROOT = Path("analysis/outputs")


def create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"status": "queued", "result": None, "error": None}
    return job_id


def run_job(
    job_id: str,
    engine: Engine,
    dem_path: str,
    breach_hydrograph_csv: str,
    case_name: str,
    config: Optional[dict] = None,
) -> None:
    JOBS[job_id]["status"] = "running"
    engine_fn = ENGINE_FUNCS[engine]
    output_dir = OUTPUT_ROOT / case_name / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result: SimResult = engine_fn(
            dem_path=dem_path,
            breach_hydrograph_csv=breach_hydrograph_csv,
            case_name=case_name,
            output_dir=str(output_dir),
            config=config,
        )

        if result.status == "success" and result.max_depth_raster:
            try:
                vector_paths = export_both_formats(
                    raster_path=result.max_depth_raster,
                    output_dir=str(output_dir),
                    base_name=f"{case_name}_flood_extent",
                )
                result = replace(result, flood_extent_vector=vector_paths.get("shp"))
            except Exception as e:
                result = replace(result, extra={**result.extra, "vector_export_error": str(e)})

        JOBS[job_id]["result"] = result
        JOBS[job_id]["status"] = "success" if result.status == "success" else "failed"
        if result.status != "success":
            JOBS[job_id]["error"] = result.error_message
    except Exception as exc:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = f"{type(exc).__name__}: {exc}"


def get_job(job_id: str) -> Optional[dict]:
    return JOBS.get(job_id)
