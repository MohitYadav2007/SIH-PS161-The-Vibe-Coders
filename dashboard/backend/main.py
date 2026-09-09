"""
FastAPI orchestration layer -- triggers either simulation engine and
serves back a SimResult once the run completes.

Both simulation/sph/dualsphysics_wrapper.py::run_sph_simulation() and
simulation/delft3d/delft3d_runner.py::run_second_model() share the exact
same signature (dem_path, breach_hydrograph_csv, case_name, output_dir,
config) and both return simulation/sim_result.py::SimResult -- that
shared shape is what makes them swappable behind one API.

Run from the repo root:
    pip install fastapi "uvicorn[standard]"
    uvicorn dashboard.backend.main:app --reload
"""

from dataclasses import asdict
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dashboard.backend.tasks import create_job, run_job, get_job, ENGINE_FUNCS

app = FastAPI(title="fuzzy-train simulation API")

# Widened for the hackathon since the frontend's exact dev port wasn't
# confirmed across everyone's machines -- tighten to the real frontend
# origin before any real deployment, this is demo-only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data so the pipeline is runnable end-to-end before the real
# Rishiganga DEM/hydrograph land -- see docs/architecture.md.
SAMPLE_DEM = "data/sample/sample_dem.tif"
SAMPLE_HYDROGRAPH = "data/sample/sample_breach_hydrograph.csv"


class SimulationRequest(BaseModel):
    engine: Literal["dualsphysics", "swe_fallback"]
    dem_path: Optional[str] = None                # defaults to sample DEM
    breach_hydrograph_csv: Optional[str] = None    # defaults to sample hydrograph
    case_name: str = "rishiganga_glof_2021"
    config: Optional[dict] = None


@app.get("/engines")
def list_engines():
    return {"engines": list(ENGINE_FUNCS.keys())}


@app.post("/simulate")
def trigger_simulation(req: SimulationRequest, background_tasks: BackgroundTasks):
    dem_path = req.dem_path or SAMPLE_DEM
    hydrograph_path = req.breach_hydrograph_csv or SAMPLE_HYDROGRAPH

    if not Path(dem_path).exists():
        raise HTTPException(400, f"DEM not found: {dem_path}")
    if not Path(hydrograph_path).exists():
        raise HTTPException(400, f"Breach hydrograph not found: {hydrograph_path}")

    job_id = create_job()
    background_tasks.add_task(
        run_job,
        job_id=job_id,
        engine=req.engine,
        dem_path=dem_path,
        breach_hydrograph_csv=hydrograph_path,
        case_name=req.case_name,
        config=req.config,
    )
    return {"job_id": job_id, "status": "queued"}


@app.get("/simulate/{job_id}/status")
def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job_id")
    return {"job_id": job_id, "status": job["status"], "error": job["error"]}


@app.get("/simulate/{job_id}/result")
def get_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job_id")
    if job["status"] not in ("success", "failed"):
        raise HTTPException(409, f"Job not finished yet (status: {job['status']})")
    if job["result"] is None:
        raise HTTPException(500, "Job finished but produced no SimResult")
    return asdict(job["result"])
