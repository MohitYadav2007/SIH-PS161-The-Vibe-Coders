import os
import rasterio
from rasterio.features import shapes
import geopandas as gpd

def convert_raster_to_vector(raster_path: str, output_path: str, threshold: float = 0.1) -> str:
    if not os.path.exists(raster_path):
        raise FileNotFoundError(f"Raster file not found at {raster_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with rasterio.open(raster_path) as src:
        image = src.read(1)
        mask = image > threshold

        results = (
            {'properties': {'water_depth': float(v)}, 'geometry': s}
            for i, (s, v) in enumerate(shapes(image, mask=mask, transform=src.transform))
        )
        geoms = list(results)

    if not geoms:
        gdf = gpd.GeoDataFrame(columns=['water_depth', 'geometry'], crs=src.crs)
    else:
        gdf = gpd.GeoDataFrame.from_features(geoms, crs=src.crs)

    gdf.to_file(output_path, driver="GeoJSON")
    return output_path
