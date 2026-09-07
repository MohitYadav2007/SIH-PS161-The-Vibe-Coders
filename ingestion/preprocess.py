"""
ingestion/preprocess.py

Reprojects the raw DEM from ingestion/dem_fetch.py (Copernicus GLO-30 /
NASADEM, delivered in geographic CRS -- EPSG:4326, lat/lon) into a
PROJECTED CRS in meters (UTM 44N / EPSG:32644), which BOTH simulation
engines require. See simulation/generate_sample_dem.py's docstring and
docs/ for why: a geographic CRS silently breaks Manning's-equation-based
solvers (pixel size ends up ~0.0001 "meters" instead of ~10-30).

Also clips to a focused sub-catchment around the documented Feb 2021
GLOF flow path (avalanche source -> Raini confluence -> Tapovan), since
the full download bbox from dem_fetch.py is deliberately generous and a
smaller extent is both more appropriate for a demo and safer for GPU
memory during the DualSPHysics run.

USAGE:
    python ingestion/preprocess.py
    python ingestion/preprocess.py --in data/raw/rishiganga_dem_raw.tif \
        --out data/processed/rishiganga_dem_utm44n.tif
"""
import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import from_bounds

TARGET_CRS = "EPSG:32644"  # UTM zone 44N -- matches data/sample/sample_dem.tif

# Sub-catchment clip box, in the SAME geographic lon/lat as dem_fetch.py's
# DEFAULT_BBOX, tightened around the actual documented GLOF flow path
# (Ronti Gad avalanche source -> Raini/Dhauliganga confluence -> Tapovan).
# This is intentionally smaller than the raw download bbox.
CLIP_BBOX_LONLAT = {
    "south": 30.24,
    "north": 30.40,
    "west": 79.55,
    "east": 79.75,
}


def reproject_dem(in_path: Path, out_path: Path, target_crs: str = TARGET_CRS) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(in_path) as src:
        if src.crs is None:
            raise ValueError(f"{in_path} has no CRS set -- cannot safely reproject.")

        print(f"Source CRS: {src.crs}, shape: {src.shape}, res: {src.res}")

        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update({
            "crs": target_crs,
            "transform": transform,
            "width": width,
            "height": height,
        })

        with rasterio.open(out_path, "w", **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )

    with rasterio.open(out_path) as check:
        print(f"Reprojected CRS: {check.crs}, shape: {check.shape}, "
              f"res: {check.res[0]:.2f}m x {check.res[1]:.2f}m")

    return out_path


def clip_to_subcatchment(in_path: Path, out_path: Path, bbox_lonlat: dict) -> Path:
    """
    Clips a REPROJECTED (already-UTM) DEM to a sub-catchment extent.
    bbox_lonlat is given in lon/lat for readability (matches dem_fetch.py's
    convention) but is converted to the DEM's own CRS before windowing.
    """
    import pyproj

    with rasterio.open(in_path) as src:
        transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        west_m, south_m = transformer.transform(bbox_lonlat["west"], bbox_lonlat["south"])
        east_m, north_m = transformer.transform(bbox_lonlat["east"], bbox_lonlat["north"])

        window = from_bounds(west_m, south_m, east_m, north_m, transform=src.transform)
        data = src.read(1, window=window)
        clipped_transform = src.window_transform(window)

        kwargs = src.meta.copy()
        kwargs.update({
            "height": data.shape[0],
            "width": data.shape[1],
            "transform": clipped_transform,
        })

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_path, "w", **kwargs) as dst:
            dst.write(data, 1)

    print(f"Clipped to sub-catchment: {data.shape[1]}x{data.shape[0]} cells -> {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="data/raw/rishiganga_dem_raw.tif")
    parser.add_argument("--out", dest="out_path", default="data/processed/rishiganga_dem_utm44n.tif")
    parser.add_argument("--skip-clip", action="store_true",
                         help="Reproject only, skip sub-catchment clipping")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    if not in_path.exists():
        raise FileNotFoundError(
            f"{in_path} not found -- run ingestion/dem_fetch.py first, "
            f"or check --in points to the right raw DEM file."
        )

    reprojected_tmp = out_path.with_suffix(".reprojected_tmp.tif")
    reproject_dem(in_path, reprojected_tmp)

    if args.skip_clip:
        reprojected_tmp.rename(out_path)
    else:
        clip_to_subcatchment(reprojected_tmp, out_path, CLIP_BBOX_LONLAT)
        reprojected_tmp.unlink()

    print(f"Done. Processed DEM ready at: {out_path}")


if __name__ == "__main__":
    main()
