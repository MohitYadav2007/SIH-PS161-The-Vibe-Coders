import os
import rasterio
from rasterio.features import shapes
import geopandas as gpd


def convert_raster_to_vector(
    raster_path: str,
    output_path: str,
    threshold: float = 0.1,
    driver: str = "ESRI Shapefile",
) -> str:
    """
    Converts a max-depth GeoTIFF (from either simulation engine's
    SimResult.max_depth_raster) into a vector polygon file.

    driver: "ESRI Shapefile" (.shp, default) or "KML" (.kml) -- matches
    the project's explicit deliverable requirement (.shp or .Kml output).
    Pick the driver to match output_path's extension.
    """
    if not os.path.exists(raster_path):
        raise FileNotFoundError(f"Raster file not found at {raster_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with rasterio.open(raster_path) as src:
        image = src.read(1)
        mask = image > threshold

        results = (
            {'properties': {'water_depth': float(v)}, 'geometry': s}
            for i, (s, v) in enumerate(shapes(image, mask=mask, transform=src.transform))
        )
        geoms = list(results)
        crs = src.crs

    if not geoms:
        gdf = gpd.GeoDataFrame(columns=['water_depth', 'geometry'], crs=crs)
    else:
        gdf = gpd.GeoDataFrame.from_features(geoms, crs=crs)

    try:
        gdf.to_file(output_path, driver=driver)
    except Exception as e:
        # KML export needs libkml support in the local GDAL/fiona build --
        # not guaranteed to be present. Fail loudly rather than silently
        # writing the wrong format.
        raise RuntimeError(
            f"Failed writing with driver={driver!r}: {e}. "
            f"If this was a KML export, your GDAL build may lack libkml "
            f"support -- try driver='ESRI Shapefile' instead."
        ) from e

    return output_path


def export_both_formats(raster_path: str, output_dir: str, base_name: str, threshold: float = 0.1) -> dict:
    """Convenience wrapper: writes both .shp and .kml from the same raster."""
    shp_path = os.path.join(output_dir, f"{base_name}.shp")
    kml_path = os.path.join(output_dir, f"{base_name}.kml")
    out = {"shp": convert_raster_to_vector(raster_path, shp_path, threshold, driver="ESRI Shapefile")}
    try:
        out["kml"] = convert_raster_to_vector(raster_path, kml_path, threshold, driver="KML")
    except RuntimeError as e:
        out["kml"] = None
        out["kml_error"] = str(e)
    return out
