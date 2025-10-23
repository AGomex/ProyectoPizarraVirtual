from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Drawing
from django.http import StreamingHttpResponse
from .opencv_scripts.video_stream import generate_frames, generate_camera_frames
from board.actions import save_action
import cv2
import numpy as np
import os
from django.conf import settings

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

def canvas_view(request, drawing_id=None):
    """
    Vista principal del lienzo.
    Si tiene un ID -> carga el dibujo existente.
    Si no tiene ID -> abre un nuevo lienzo vacío (uno solo a la vez).
    """
    drawing = None

    if drawing_id is not None:
        # 🔹 Cargar dibujo existente
        drawing = get_object_or_404(Drawing, pk=drawing_id)
        print(f"🖼️ Cargando dibujo existente: {drawing.id} -> {drawing.name}")
        save_action.load_drawing(drawing.id)
    else:
        # 🔹 Si no hay ID (nuevo lienzo)
        if save_action.current_drawing is None:
            print("🆕 No hay dibujo activo, creando nuevo lienzo vacío.")
            save_action.start_new_drawing(name="Nuevo Dibujo Temporal")
        else:
            print(f"⚠️ Reutilizando lienzo activo (ID: {save_action.current_drawing.id})")

    return render(request, "board/canvas.html", {"drawing": drawing})


def gallery_view(request):
    drawings = Drawing.objects.order_by('-updated_at')[:9]

    for drawing in drawings:
        thumb_dir = os.path.join(settings.MEDIA_ROOT, "thumbs")
        thumb_path = os.path.join(thumb_dir, f"thumb_{drawing.id}.jpg")
        needs_regen = (
            not drawing.thumbnail
            or not os.path.exists(thumb_path)
        )
        if needs_regen:
            print(f"[🖼️] Regenerando miniatura para dibujo ID={drawing.id}...")
            try:
                img = save_action.render_strokes(
                    drawing.strokes,
                    drawing.width,
                    drawing.height
                )

                os.makedirs(thumb_dir, exist_ok=True)
                cv2.imwrite(thumb_path, img)

                drawing.thumbnail = f"thumbs/thumb_{drawing.id}.jpg"
                drawing.save(update_fields=["thumbnail"])
            except Exception as e:
                print(f"[ERROR] No se pudo generar miniatura para dibujo {drawing.id}: {e}")

    return render(request, "board/gallery.html", {"drawings": drawings})

def edit_drawing_view(request, drawing_id):
    drawing = get_object_or_404(Drawing, pk=drawing_id)
    save_action.load_drawing(drawing.id)  
    return redirect("canvas", drawing_id=drawing.id)

def delete_drawing(request, drawing_id):
    """Elimina el dibujo y su miniatura"""
    drawing = get_object_or_404(Drawing, pk=drawing_id)
    if drawing.thumbnail and os.path.exists(drawing.thumbnail.path):
        os.remove(drawing.thumbnail.path)
    drawing.delete()
    return redirect("gallery")

def manual(request):
    return render(request, 'board/manual.html')

def video_feed(request, drawing_id):
    """
    Streaming del dibujo existente.
    Carga el dibujo en memoria y lanza generate_frames con el id.
    """
    print(f"🎥 Solicitado stream para dibujo {drawing_id}")
    return StreamingHttpResponse(
        generate_frames(drawing_id),
        content_type="multipart/x-mixed-replace; boundary=frame"
    )

def video_feed_blank(request):
    """
    Streaming para un lienzo en blanco.
    Si ya existe un lienzo activo sin guardar, lo reutiliza.
    """
    print("🎥 Iniciando stream para lienzo en blanco...")

    # 🔹 Si hay un dibujo cargado desde galería, NO lo reiniciamos
    if save_action.current_drawing is not None and save_action.current_drawing.id is None:
        # Solo si es un nuevo dibujo temporal
        print(f"⚠️ Reutilizando lienzo temporal existente (ID temporal)")
        save_action.reset_strokes()
    else:
        print("🆕 Creando nuevo dibujo temporal.")
        save_action.start_new_drawing(name="Nuevo Dibujo")

    return StreamingHttpResponse(
        generate_frames(None),
        content_type="multipart/x-mixed-replace; boundary=frame"
    )

def camera_feed(request):
    return StreamingHttpResponse(generate_camera_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

current_mode = "brush"

def set_mode(request, mode):
    global current_mode
    current_mode = mode
    print(f"🟢 Modo cambiado a: {mode}")
    return JsonResponse({"status": "ok", "mode": mode})
