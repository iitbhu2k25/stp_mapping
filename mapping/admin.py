from django.contrib.gis import admin
from .models import SpatialVector

@admin.register(SpatialVector)
class SpatialVectorAdmin(admin.GISModelAdmin):
    list_display = ('name', 'description', 'upload_date')
    search_fields = ('name', 'description')
    fields = ('name', 'description', 'shapefile', 'geometry')
    readonly_fields = ('geometry',)  # Make geometry read-only since it's auto-generated
    
    # Customize the map display
    map_width = 800
    map_height = 500
    
    def save_model(self, request, obj, form, change):
        # Print debugging information
        print("Saving model...")
        if obj.shapefile:
            print(f"Shapefile uploaded: {obj.shapefile.name}")
        
        super().save_model(request, obj, form, change)
        print(f"Geometry after save: {obj.geometry}")
    
    def save_model(self, request, obj, form, change):
        # Print debugging information
        print("Saving model...")
        if obj.shapefile:
            print(f"Shapefile uploaded: {obj.shapefile.name}")
        
        super().save_model(request, obj, form, change)
        print(f"Geometry after save: {obj.geometry}")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['shapefile'].help_text = 'Upload a ZIP file containing the Shapefile (.shp, .shx, .dbf, .prj)'
        return form