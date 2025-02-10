from django.http import HttpResponse
from django.template import loader
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from .models import Data
import json
import geopandas as gpd
from shapely.geometry import mapping
from .service import weight_redisturb,normalize_data,rank_process 
def stp_home(request):
    return render(request, 'stp/prediction.html')

@csrf_exempt
def GetStatesView(request):
    states=Data.objects.values('id','name','state','district','subdistrict','village').filter(district=0,subdistrict=0,village=0).distinct()
    print(states)
    return JsonResponse(list(states),safe=False)

@csrf_exempt
def GetDistrictView(request):
    if request.method == 'POST':
        request=json.loads(request.body)
        print("request of dis ",request)
        state = request.get('state') ## fetch the state id
        districts=Data.objects.values('name','id','state','district','subdistrict','village').filter(state=state,subdistrict=0,village=0)
        districts=list(districts)
        state_name=Data.objects.values('name').filter(state=state,subdistrict=0,village=0,district=0)
        new_district=[d for d in districts if d['name']!=state_name[0]['name']]
        new_district.sort(key=lambda x: x['name'])
        return JsonResponse(new_district,safe=False)
@csrf_exempt
def GetSubDistrictView(request):
    if request.method == 'POST':
        request=json.loads(request.body)
        print("request of sub dis",request)
        state=request.get('state')
        district=request.get('district')
        sub_district=Data.objects.values('name','id','state','district','subdistrict','village').filter(state=state,district=district,village=0)
        new_sub_district=[d for d in sub_district if d['subdistrict']!=0]
        new_sub_district.sort(key=lambda x: x['name'])
        print("sub dis",list(new_sub_district))
        return JsonResponse(list(new_sub_district),safe=False)

@csrf_exempt
def  GetVillageView(request):
    if request.method == 'POST':
        request=json.loads(request.body)
        state=request.get('state')
        district=request.get('district')
        sub_district=request.get('sub_district')
        village=Data.objects.values('name','id','state','district','subdistrict','village').filter(state=state,district=district,subdistrict=sub_district)
        new_village=[d for d in village if d['village']!=0]
        new_village.sort(key=lambda x: x['name'])
        print("village",list(new_village))
        return JsonResponse(list(new_village),safe=False)

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
def GetBoundry(request):
    if request.method == 'GET':
        try:
            gdf = gpd.read_file('media/shapefile/all_district/States_Sub_District.shp')
            coordinates = []
            
            for geometry in gdf.geometry:
                if geometry.geom_type == 'Polygon':
                    coords = [[[float(x), float(y)] for x, y in geometry.exterior.coords]]
                    coordinates.extend(coords)
                elif geometry.geom_type == 'MultiPolygon':
                    multi_coords = []
                    for polygon in geometry.geoms:  # Use .geoms for MultiPolygon
                        coords = [[float(x), float(y)] for x, y in polygon.exterior.coords]
                        multi_coords.append(coords)
                    coordinates.extend(multi_coords)
                    
            return JsonResponse({'coordinates': coordinates})
        except Exception as e:
            print(str(e))
            return JsonResponse({'error': str(e)}, status=500)
            

