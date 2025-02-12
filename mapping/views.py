from django.shortcuts import render, redirect
from django.contrib.gis.geos import GEOSGeometry
from django.contrib import messages
import geopandas as gpd
from .forms import VectorFileUploadForm
from .models import SpatialVector

def upload_vector(request):
    if request.method == 'POST':
        form = VectorFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Read the vector file using geopandas
                gdf = gpd.read_file(request.FILES['file'])
                
                # Ensure the CRS is WGS84 (EPSG:4326)
                if gdf.crs is None:
                    gdf.set_crs(epsg=4326, inplace=True)
                elif gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs(epsg=4326)

                # Save each feature to the database
                for _, row in gdf.iterrows():
                    geom = GEOSGeometry(row.geometry.wkt)
                    SpatialVector.objects.create(
                        name=form.cleaned_data['name'],
                        description=form.cleaned_data['description'],
                        geometry=geom
                    )
                messages.success(request, 'Vector file uploaded successfully!')
                return redirect('map_view')
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
    else:
        form = VectorFileUploadForm()
    return render(request, 'mapping/upload.html', {'form': form})

def map_view(request):
    print("inside the mapping")
    vectors = SpatialVector.objects.all()
    return render(request, 'mapping/map_view.html', {'vectors': vectors})

def spatial_query(request):
    # Example spatial query
    if request.method == 'POST':
        query_type = request.POST.get('query_type')
        vector_id = request.POST.get('vector_id')
        
        try:
            base_vector = SpatialVector.objects.get(id=vector_id)
            if query_type == 'intersects':
                results = SpatialVector.objects.filter(
                    geometry__intersects=base_vector.geometry
                ).exclude(id=vector_id)
            elif query_type == 'contains':
                results = SpatialVector.objects.filter(
                    geometry__contains=base_vector.geometry
                ).exclude(id=vector_id)
            elif query_type == 'within':
                results = SpatialVector.objects.filter(
                    geometry__within=base_vector.geometry
                ).exclude(id=vector_id)
            else:
                results = []
            
            return render(request, 'mapping/query.html', {
                'results': results,
                'vectors': SpatialVector.objects.all()
            })
        except SpatialVector.DoesNotExist:
            messages.error(request, 'Vector not found')
    
    return render(request, 'mapping/query.html', {
        'vectors': SpatialVector.objects.all()
    })