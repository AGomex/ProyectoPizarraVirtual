from django.urls import path
from . import views

urlpatterns = [
    path("api/save/", views.save_drawing, name="save_drawing"),
    path("api/list/", views.list_drawings, name="list_drawings"),
    path("api/<int:pk>/", views.get_drawing, name="get_drawing"),
    path('', views.home, name='home'),
    path('canvas/', views.canvas_view, name='canvas'),
    path('gallery/', views.gallery, name='gallery'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('camera_feed/', views.camera_feed, name='camera_feed'),
    # vistas HTML: home, canvas, galería
]
