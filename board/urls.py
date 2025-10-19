from django.urls import path
from . import views
from board.opencv_scripts.video_stream import get_pointer_data , reset_redirect

urlpatterns = [
    path("api/save/", views.save_drawing, name="save_drawing"),
    path("api/list/", views.list_drawings, name="list_drawings"),
    path("api/<int:pk>/", views.get_drawing, name="get_drawing"),
    path('', views.home, name='home'),
    path('canvas/', views.canvas_view, name='canvas'),
    path('gallery/', views.gallery, name='gallery'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('camera_feed/', views.camera_feed, name='camera_feed'),
    path('pointer-data/', get_pointer_data, name='pointer_data'),
    path("set_mode/<str:mode>/", views.set_mode, name="set_mode"),
    path('reset_redirect/', reset_redirect, name='reset_redirect'),

    # vistas HTML: home, canvas, galería
]
