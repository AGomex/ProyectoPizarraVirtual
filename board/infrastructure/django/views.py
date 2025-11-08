from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
import json
import os
import cv2
import numpy as np

from board.infrastructure.django.models import Drawing

from board.application.use_cases.video_stream import (
    generate_frames,
    generate_camera_frames,
)

from board.application.actions import save_action

@require_GET
def check_unsaved_changes(request):
    """
    Devuelve si hay cambios sin guardar en el lienzo actual.
    """
    # Si no hay trazos, no hay nada que guardar
    if not save_action.current_strokes or len(save_action.current_strokes) == 0:
        return JsonResponse({"unsaved": False})
    
    # Si hay trazos, verificar si están sin guardar
    unsaved = getattr(save_action, "unsaved_changes", True)
    
    return JsonResponse({"unsaved": unsaved})

@require_POST
def reset_unsaved(request):
    """
    Marca que ya no hay cambios sin guardar (por ejemplo, tras guardar o salir).
    """
    save_action.unsaved_changes = False
    return JsonResponse({"status": "ok"})

@require_POST
def reset_redirect(request):
    """
    Endpoint auxiliar para resetear la redirección automática
    después de ejecutar una acción con el puntero.
    """
    request.session["redirect"] = None
    request.session["redirect_url"] = None
    return JsonResponse({"status": "ok"})


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

@login_required
def canvas_view(request, drawing_id=None):
    drawing = None

    if drawing_id is not None:
        drawing = get_object_or_404(Drawing, pk=drawing_id)
        print(f"🖼 Cargando dibujo existente: {drawing.id}")
        save_action.load_drawing(drawing.id)
    
    else:
        print("🆕 Creando nuevo dibujo temporal.")
        if save_action.current_drawing is not None and save_action.unsaved_changes:
            print("⚠ Hay cambios sin guardar. Creando nuevo dibujo independiente.")
            save_action.reset_globals()
        save_action.start_new_drawing(name="Nuevo Dibujo")
    
    # 🔹 Obtener los últimos dibujos para mostrar en el panel lateral
    recent_drawings = Drawing.objects.filter(user=request.user).order_by('-updated_at')

    # 🔹 Renderizar plantilla en todos los casos
    return render(request, "board/canvas.html", {
        "drawing": drawing,
        "recent_drawings": recent_drawings
    })

@login_required
def gallery_view(request):
    drawings = Drawing.objects.filter(user=request.user).order_by('-updated_at')[:16]

    for drawing in drawings:
        thumb_dir = os.path.join(settings.MEDIA_ROOT, "thumbs")
        thumb_path = os.path.join(thumb_dir, f"thumb_{drawing.id}.jpg")
        needs_regen = (
            not drawing.thumbnail
            or not os.path.exists(thumb_path)
        )
        if needs_regen:
            print(f"[🖼] Regenerando miniatura para dibujo ID={drawing.id}...")
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

@login_required
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
        print(f"⚠ Reutilizando lienzo temporal existente (ID temporal)")
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

@csrf_exempt
@require_POST
def save_drawing_with_name(request):
    """Guarda el dibujo con el nombre proporcionado por el usuario."""
    try:
        data = json.loads(request.body)
        drawing_name = data.get("name", "Dibujo sin título").strip()
        
        if not drawing_name:
            drawing_name = "Dibujo sin título"
        
        # Verificar si hay trazos
        if not save_action.current_strokes or len(save_action.current_strokes) == 0:
            return JsonResponse({
                "success": False,
                "message": "No se puede guardar un dibujo vacío"
            })
        
        # 🔹 VERIFICAR SI YA EXISTE UN DIBUJO CON ESE NOMBRE (case-insensitive)
        # Obtenemos todos los dibujos y comparamos manualmente en Python
        all_drawings = Drawing.objects.filter(user=request.user)

        # Si estamos editando un dibujo existente, excluirlo
        if save_action.current_drawing and save_action.current_drawing.id:
            all_drawings = all_drawings.exclude(id=save_action.current_drawing.id)

        # Comparar nombres en minúsculas
        for drawing in all_drawings:
            if drawing.name.lower() == drawing_name.lower():
                return JsonResponse({
                    "success": False,
                    "message": f"Ya existe un dibujo con el nombre '{drawing_name}'. Por favor elige otro nombre."
        })
        
        # Guardar
        drawing = save_action.save_current_drawing(name=drawing_name)
        if drawing:
            drawing.user = request.user
            drawing.save(update_fields=["user"])

        if drawing:
            return JsonResponse({
                "success": True,
                "message": f"Dibujo '{drawing_name}' guardado correctamente",
                "drawing_id": drawing.id
            })
        else:
            return JsonResponse({
                "success": False,
                "message": "Error al guardar el dibujo"
            })
            
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)
    
@csrf_exempt
@require_POST
def login_user(request):
    username = request.POST.get("username")
    password = request.POST.get("password")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({"success": True})
    
    return JsonResponse({
        "success": False,
        "message": "Credenciales incorrectas"
    })


def register_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if password != password2:
            return JsonResponse({"success": False, "message": "Las contraseñas no coinciden"})

        if User.objects.filter(username=username).exists():
            return JsonResponse({"success": False, "message": "El usuario ya existe"})

        if User.objects.filter(email=email).exists():
            return JsonResponse({"success": False, "message": "El correo ya está en uso"})

        if len(password) < 8:
            return JsonResponse({"success": False, "message": "La contraseña debe tener al menos 8 caracteres"})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        login(request, user)

        return JsonResponse({"success": True, "message": "Registrado correctamente"})

    return JsonResponse({"success": False, "message": "Método no permitido"})

def logout_user(request):
    logout(request)
    return redirect('home')