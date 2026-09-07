"""
Background job orchestration for triggering simulation runs.

Wraps BOTH simulation engines behind one call so main.py never has to
care which one is running -- both conform exactly to the shared
simulation/sim_result.py::SimResult contract.

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
from pathlib import Path
from typing import Literal, Optional

from simulation.sim_result import SimResult
from simulation.sph.dualsphysics_wrapper import run_sph_simulation
from simulation.delft3d.delft3d_runner import run_second_model

Engine = Literal["dualsphysics", "swe_fallback"]

# engine name (matches SimResult.engine values) -> callable with the
# shared (dem_path, breach_hydrograph_csv, case_name, output_dir, config)
# signature both engine modules already implement.
ENGINE_FUNCS = {
    "dualsphysics": run_sph_simulation,
    "swe_fallback": run_second_model,
}

# job_id -> {"status": "queued"|"running"|"success"|"failed", "result": SimResult|None, "error": str|None}
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
    """Runs inside a FastAPI BackgroundTask. Updates JOBS[job_id] in place --
    there's no return value because BackgroundTasks doesn't give you one back."""
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
        JOBS[job_id]["result"] = result
        # Trust the engine's own status field rather than assuming success
        # just because it returned without raising.
        JOBS[job_id]["status"] = "success" if result.status == "success" else "failed"
        if result.status != "success":
            JOBS[job_id]["error"] = result.error_message
    except Exception as exc:
        # An engine raising instead of returning a failed SimResult
        # shouldn't crash the worker or leave the job stuck at "running".
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = f"{type(exc).__name__}: {exc}"


def get_job(job_id: str) -> Optional[dict]:
    return JOBS.get(job_id)
