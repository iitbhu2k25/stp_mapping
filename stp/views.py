from django.http import HttpResponse
from django.template import loader
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from typing import List
import json
import geopandas as gpd
from .models import Villages,District,Sub_district,State
from shapely.geometry import mapping
from .service import weight_redisturb,normalize_data,rank_process,process_geometries,fix_geometry
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
import shapely.ops as ops
def stp_home(request):
    return render(request, 'stp/prediction.html')

@csrf_exempt
def GetStatesView(request):
    states=State.objects.values('state_id','state_name')
    states=[{'id': state['state_id'],'name':state['state_name']} for state in states]
    return JsonResponse(list(states),safe=False)

@csrf_exempt
def GetDistrictView(request):
    if request.method == 'POST':
        state_id=int(json.loads(request.body).get('state'))
        print("state id is ",state_id)
        districts=District.objects.values('district_id','district_name').filter(state_id=state_id)
        districts=[{'id': district['district_id'],'name':district['district_name']} for district in districts]
        return JsonResponse(list(districts),safe=False)
@csrf_exempt
def GetSubDistrictView(request):
    if request.method == 'POST':
        district_id=(json.loads(request.body).get('districts'))
        sub_districts=list(Sub_district.objects.values('subdistrict_id','subdistrict_name').filter(district_id__in=district_id))
        sub_districts=[{'id': sub_district['subdistrict_id'],'name':sub_district['subdistrict_name']} for sub_district in sub_districts]
        return JsonResponse(list(sub_districts),safe=False)

@csrf_exempt
def  GetVillageView(request):
    if request.method == 'POST':
        sub_district_id=(json.loads(request.body).get('subDistricts'))
        villages=list(Villages.objects.values('village_id','village_name').filter(subdistrict_id_id__in=sub_district_id))
        villages=[{'id': village['village_id'],'name':village['village_name']} for village in villages]
        return JsonResponse(list(villages),safe=False)

@csrf_exempt
def GetTableView(request):
    if request.method == 'POST':
        request=json.loads(request.body)
        main_data=request.get('main_data')
        vig_data=main_data['villages']
        table_id=[]
        for i in vig_data:
            table_id.append(int(i[8:]))
        categories=request.get('categories')
        ans=Data.objects.values('name',*categories).filter(id__in=table_id)
        ans=list(ans)
        for i in ans:
            print(i)
        return JsonResponse(ans,safe=False)
    

@csrf_exempt
def GetRankView(request):
    if request.method == 'POST':
        request=json.loads(request.body)
        table_data=request.get('tableData')
        headings=[]
        for i in table_data[0]:
            headings.append(i)        
        headings.remove('name')
        weight_key=weight_redisturb(headings)
        table_data=normalize_data(table_data)
        ans=rank_process(table_data,weight_key,headings)
        print('main ans',ans)
        return JsonResponse(ans,safe=False)

@csrf_exempt
def GetVillage_UP(request):
    try:
        try:
            request_data = json.loads(request.body)
            villages_list=request_data.get('village_name')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        try:
            gdf = gpd.read_file('media/shapefile/villages/Basin_Villages.shp')

        except Exception as e:
            print('erris is ',str(e))
            return JsonResponse({'error': 'Error reading geographic data'}, status=500)

        # Filter geodataframe
        print("village_list",villages_list)
        filtered_gdf = gdf[gdf['NAME_1'].isin(villages_list)]
        print("filtered_gdf",filtered_gdf)
        coordinates = process_geometries(filtered_gdf)
        print("coor",coordinates)
        if not coordinates:
            return JsonResponse({'error': 'Failed to extract valid coordinates'}, status=500)

        if len(coordinates) > 1:
            coordinates = [coordinates]

        return JsonResponse({'coordinates': coordinates})

    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def GetBoundry(request):
    if request.method == 'GET':
        try:
            gdf = gpd.read_file('media/shapefile/WFSServer/subdistrict_updated.shp')
            coordinates = []
            
            for geometry in gdf.geometry:
                if geometry.geom_type == 'Polygon':
                    coords = [[[float(x), float(y)] for x, y in geometry.exterior.coords]]
                    coordinates.extend(coords)
                elif geometry.geom_type == 'MultiPolygon':
                    multi_coords = []
                    for polygon in geometry.geoms:  
                        coords = [[float(x), float(y)] for x, y in polygon.exterior.coords]
                        multi_coords.append(coords)
                    coordinates.extend(multi_coords)
                    
            return JsonResponse({'coordinates': coordinates})
        except Exception as e:
            print(str(e))
            return JsonResponse({'error': str(e)}, status=500)
        
    if request.method == 'POST':
        try:
            # Read the shapefile
            gdf = gpd.read_file('media/shapefile/WFSServer/subdistrict_updated.shp')
            coordinates = []
            request_data = json.loads(request.body)
            
            def fix_geometry(geometry):
                """Fix invalid geometries and handle topology exceptions"""
                try:
                    # Check if geometry is valid
                    if not geometry.is_valid:
                        # Try to make the geometry valid
                        geometry = make_valid(geometry)
                    
                    # Handle empty geometries
                    if geometry.is_empty:
                        return None
                        
                    # Ensure we have the right geometry type
                    if isinstance(geometry, (Polygon, MultiPolygon)):
                        return geometry
                    else:
                        # If we got a different geometry type, try to convert it
                        return ops.unary_union(geometry)
                        
                except Exception as e:
                    print(f"Error fixing geometry: {str(e)}")
                    return None

            def process_geometry(geometry):
                """Process and extract coordinates from geometry"""
                try:
                    # Fix any topology issues first
                    fixed_geometry = fix_geometry(geometry)
                    if fixed_geometry is None:
                        return
                    
                    if isinstance(fixed_geometry, Polygon):
                        # Process single polygon
                        coords = []
                        # Get exterior coordinates
                        for x, y in fixed_geometry.exterior.coords:
                            coords.append([float(y), float(x)])  # [longitude, latitude]
                        coordinates.append(coords)
                        
                    elif isinstance(fixed_geometry, MultiPolygon):
                        # Process each polygon in the MultiPolygon
                        for polygon in fixed_geometry.geoms:
                            poly_coords = []
                            # Get exterior coordinates for each polygon
                            for x, y in polygon.exterior.coords:
                                poly_coords.append([float(y), float(x)])  # [longitude, latitude]
                            coordinates.append(poly_coords)
                            
                except Exception as e:
                    print(f"Error processing geometry coordinates: {str(e)}")
            
            # Filter data based on request
            try:
                print("request data is ",request_data)
                if request_data.get('villages'):
                    village_list = request_data['villages']
                    filtered_gdf = gdf[gdf['village'].isin(village_list)]
                
                elif request_data.get('subDistricts'):
                    subdistrict = request_data['subDistricts']
                    subdistrict=list(map(int,subdistrict))
                    filtered_gdf = gdf[(gdf['Subdistric'].isin(subdistrict))]
                    print(filtered_gdf)
                
                elif request_data.get('districts'):
                    district = request_data['districts']
                    print("district_data ",district)
                    district= list(map(int, district))
                    filtered_gdf = gdf[(gdf['District_1'].isin(district))]
                    print("filtered_gdf is",filtered_gdf)
                
                elif request_data.get('state'):
                    state_code=int(request_data['stateId'])
                    filtered_gdf = gdf[gdf['state_co_1'] == state_code]
                    print("filtered_gdf is",filtered_gdf)
                
                else:
                    return JsonResponse({'error': 'No valid geographic criteria provided'}, status=400)

                if filtered_gdf.empty:
                    return JsonResponse({'error': 'No matching geographic features found'}, status=404)
                    
                # Dissolve geometries if multiple features exist
                try:
                    if len(filtered_gdf) > 1:
                        filtered_gdf = filtered_gdf.dissolve()
                        # Ensure the dissolved geometry is valid
                        filtered_gdf.geometry = filtered_gdf.geometry.apply(fix_geometry)
                except Exception as e:
                    print(f"Error during dissolve operation: {str(e)}")
                    # If dissolve fails, try processing individual geometries
                    pass
                
                # Process each geometry
                for geometry in filtered_gdf.geometry:
                    if geometry is not None:
                        process_geometry(geometry)
                
                # Ensure we have some coordinates
                if not coordinates:
                    return JsonResponse({'error': 'Failed to extract valid coordinates'}, status=500)

                if len(coordinates) > 1:
                    coordinates = [coordinates]
                
                return JsonResponse({'coordinates': coordinates})
                
            except Exception as e:
                print(f"Error filtering or processing data: {str(e)}")
                return JsonResponse({'error': 'Error processing geographic data'}, status=500)
                
        except Exception as e:
            print(f"Error reading shapefile or processing request: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)