from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry
import geopandas as gpd
import zipfile
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class SpatialVector(models.Model):
   name = models.CharField(max_length=100)
   description = models.TextField(blank=True)
   upload_date = models.DateTimeField(auto_now_add=True)
   geometry = models.GeometryField(srid=4326)
   shapefile = models.FileField(upload_to='shapefiles/')
   attributes = models.JSONField(default=dict)

   def __str__(self):
       return self.name

   def save(self, *args, **kwargs):
        if self.shapefile:
            self.shapefile.seek(0)
           
            with tempfile.TemporaryDirectory() as tmpdir:
               # Save and extract ZIP
                zip_path = os.path.join(tmpdir, 'upload.zip')
                with open(zip_path, 'wb') as zip_file:
                   zip_file.write(self.shapefile.read())

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                   zip_ref.extractall(tmpdir)

               # Find shapefile
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                if not shp_files:
                   raise ValueError("No .shp file found in ZIP")

                dbf_files = [f for f in os.listdir(tmpdir) if f.endswith('.dbf')]
                if not dbf_files:
                   raise ValueError("No .dbf file found in ZIP")
                
               # Read shapefile with geopandas
                gdf = gpd.read_file(os.path.join(tmpdir, shp_files[0]))

               # Read DBF file with geopandas
                dbf_path = os.path.join(tmpdir, dbf_files[0])
                dbf_gdf = gpd.read_file(dbf_path)

               # Store DBF attributes
                attributes_dict = {}
                for index, row in gdf.iterrows():
                   attributes_dict[str(index)] = {
                       col: str(val) if not isinstance(val, (int, float)) else val
                       for col, val in row.drop('geometry').items()
                   }
                self.attributes = attributes_dict

               # Process geometry
                if gdf.crs is None:
                   gdf.set_crs(epsg=4326, inplace=True)
                elif gdf.crs != 'EPSG:4326':
                   gdf = gdf.to_crs(epsg=4326)

                if len(gdf) == 0:
                   raise ValueError("Empty shapefile")

                from shapely.ops import unary_union
                combined_geom = unary_union(gdf.geometry.values) if len(gdf) > 1 else gdf.iloc[0].geometry
                self.geometry = GEOSGeometry(combined_geom.wkt)

        super().save(*args, **kwargs)

   def get_attributes(self, feature_id='0'):
       """Get attributes for a specific feature"""
       return self.attributes.get(str(feature_id), {})

   def get_attribute(self, feature_id='0', field_name=None):
       """Get specific attribute value for a feature"""
       attrs = self.get_attributes(feature_id)
       return attrs.get(field_name) if field_name else attrs
