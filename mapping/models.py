from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
import os
import zipfile
import tempfile
import geopandas as gpd
import logging

logger = logging.getLogger(__name__)

class SpatialVector(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    geometry = models.GeometryField(srid=4326)
    shapefile = models.FileField(upload_to='shapefiles/', help_text='Upload a ZIP file containing the Shapefile (.shp, .shx, .dbf, .prj)')

    def __str__(self):
        return self.name

    def clean(self):
        if not self.shapefile and not self.geometry:
            raise ValidationError("Either a shapefile or geometry must be provided")
        
        if self.shapefile:
            try:
                self._process_shapefile()
            except Exception as e:
                logger.error(f"Error processing shapefile: {str(e)}")
                raise ValidationError(f"Error processing shapefile: {str(e)}")

    def _process_shapefile(self):
        """Process the uploaded shapefile and extract geometry."""
        logger.info(f"Processing shapefile: {self.shapefile.name}")
        
    def save(self, *args, **kwargs):
        if self.shapefile:
            # Reset file pointer
            self.shapefile.seek(0)
            
            # Create a temporary directory to extract the ZIP file
            with tempfile.TemporaryDirectory() as tmpdir:
                # Save the uploaded ZIP file
                zip_path = os.path.join(tmpdir, 'upload.zip')
                with open(zip_path, 'wb') as zip_file:
                    zip_file.write(self.shapefile.read())

                # Extract the ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # Find the .shp file
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                if not shp_files:
                    raise ValueError("No .shp file found in the ZIP archive")
                
                shp_file = os.path.join(tmpdir, shp_files[0])
                
                try:
                    # Read the shapefile using geopandas
                    gdf = gpd.read_file(shp_file)
                    
                    # Ensure the CRS is WGS84 (EPSG:4326)
                    if gdf.crs is None:
                        gdf.set_crs(epsg=4326, inplace=True)
                    elif gdf.crs != 'EPSG:4326':
                        gdf = gdf.to_crs(epsg=4326)

                    if len(gdf) == 0:
                        raise ValueError("Shapefile contains no features")

                    # Convert to multi-geometry if multiple features exist
                    if len(gdf) > 1:
                        from shapely.ops import unary_union
                        combined_geom = unary_union(gdf.geometry.values)
                        self.geometry = GEOSGeometry(combined_geom.wkt)
                    else:
                        self.geometry = GEOSGeometry(gdf.iloc[0].geometry.wkt)
                
                except Exception as e:
                    raise ValueError(f"Error processing shapefile: {str(e)}")

        super().save(*args, **kwargs)