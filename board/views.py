from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Drawing
from django.http import StreamingHttpResponse
from .opencv_scripts.video_stream import generate_frames, generate_camera_frames

@csrf_exempt
def save_drawing(request):
    if request.method == "POST":
        payload = json.loads(request.body)
        name = payload.get("name", "Untitled")
        strokes = payload.get("strokes", [])
        d = Drawing.objects.create(name=name, strokes=strokes)
        return JsonResponse({"id": d.id})
    return JsonResponse({"error":"invalid method"}, status=400)

def list_drawings(request):
    qs = Drawing.objects.order_by("-created_at").values("id","name","created_at")
    return JsonResponse(list(qs), safe=False)

def get_drawing(request, pk):
    try:
        d = Drawing.objects.get(pk=pk)
        return JsonResponse({
            "id": d.id,
            "name": d.name,
            "strokes": d.strokes,
            "created_at": d.created_at.isoformat(),
        })
    except Drawing.DoesNotExist:
        return JsonResponse({"error":"not found"}, status=404)

def home(request):
    return render(request, 'board/home.html')

def canvas_view(request):
    return render(request, 'board/canvas.html')

def gallery(request):
    return render(request, 'board/gallery.html')

def canvas_view(request):
    return render(request, 'board/canvas.html')

def video_feed(request):
    return StreamingHttpResponse(generate_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

def camera_feed(request):
    return StreamingHttpResponse(generate_camera_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

current_mode = "brush"

def set_mode(request, mode):
    global current_mode
    current_mode = mode
    print(f"🟢 Modo cambiado a: {mode}")
    return JsonResponse({"status": "ok", "mode": mode})
