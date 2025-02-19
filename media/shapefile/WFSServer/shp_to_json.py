import geopandas as gpd
import os

def shapefile_to_geojson(input_shapefile, output_geojson):

    try:
        # Read the shapefile
        gdf = gpd.read_file(input_shapefile)
        
        # Ensure the CRS is set to WGS84 (standard for GeoJSON)
        if gdf.crs is not None and gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        
        # Convert to GeoJSON
        gdf.to_file(output_geojson, driver='GeoJSON')
        
        print(f"Successfully converted {input_shapefile} to {output_geojson}")
        
    except Exception as e:
        print(f"Error converting shapefile: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Replace these paths with your actual file paths
    input_file = "./subdistrict_updated.shp"
    output_file = "subdistrict_updated.geojson"
    
    shapefile_to_geojson(input_file, output_file)