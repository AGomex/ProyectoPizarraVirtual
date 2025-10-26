from django.urls import path
from . import views
from board.opencv_scripts.video_stream import get_pointer_data, reset_redirect

urlpatterns = [
    # --- API ---
    path("api/save/", views.save_drawing, name="save_drawing"),
    path("api/list/", views.list_drawings, name="list_drawings"),
    path("api/<int:pk>/", views.get_drawing, name="get_drawing"),

    # --- Vistas principales ---
    path("", views.home, name="home"),
    path("canvas/", views.canvas_view, name="canvas_blank"), 
    path("canvas/<int:drawing_id>/", views.canvas_view, name="canvas"),  
    path("gallery/", views.gallery_view, name="gallery"),
    path("drawing/<int:drawing_id>/", views.edit_drawing_view, name="edit_drawing"),
    path("drawing/<int:drawing_id>/delete/", views.delete_drawing, name="delete_drawing"),
    path("manual/", views.manual, name="manual"),

    # --- Streams ---
    path("video_feed/<int:drawing_id>/", views.video_feed, name="video_feed"),
    path("video_feed/", views.video_feed_blank, name="video_feed_blank"),
    path("camera_feed/", views.camera_feed, name="camera_feed"),

    # --- Control de puntero y modos ---
    path("pointer-data/", get_pointer_data, name="pointer_data"),
    path("set_mode/<str:mode>/", views.set_mode, name="set_mode"),
    path("reset_redirect/", reset_redirect, name="reset_redirect"),
    path("check-unsaved/", views.check_unsaved_changes, name="check_unsaved_changes"),
    path("reset-unsaved/", views.reset_unsaved, name="reset_unsaved"),
    path("reset-redirect/", views.reset_redirect, name="reset_redirect"),

    path('save-with-name/', views.save_drawing_with_name, name='save_with_name'),

]
