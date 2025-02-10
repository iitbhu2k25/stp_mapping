# mapping/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_vector, name='upload_vector'),
    path('map/', views.map_view, name='map_view'),
    path('query/', views.spatial_query, name='spatial_query'),
    path('', views.map_view, name='index'),  # Default view
]