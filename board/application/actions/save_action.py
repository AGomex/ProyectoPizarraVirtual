from board.infrastructure.django.models import Drawing
from django.utils import timezone
import cv2
import numpy as np
import os

# Estado en memoria para la sesión actual
current_strokes = []
current_drawing = None
unsaved_changes = False

# ===============================
# 🔹 RESET Y GESTIÓN DE ESTADO
# ===============================

def reset_strokes():
    """Limpia los trazos sin eliminar el dibujo actual."""
    global current_strokes
    current_strokes = []


def reset_globals():
    """Reinicia todo el estado global."""
    global current_drawing, current_strokes
    current_drawing = None
    current_strokes = []


# ===============================
# 🔹 CREAR O CARGAR DIBUJOS
# ===============================

def start_new_drawing(name="Untitled", width=640, height=480):
    """
    Prepara un nuevo lienzo temporal sin crear registro en la base de datos todavía.
    """
    global current_strokes, current_drawing
    current_strokes = []
    current_drawing = None
    print("[INFO] Nuevo lienzo temporal creado (sin guardar aún).")
    return None


def load_drawing(drawing_id):
    """Carga un dibujo existente y sus trazos en memoria."""
    global current_drawing, current_strokes
    try:
        current_drawing = Drawing.objects.get(id=drawing_id)
        current_strokes = current_drawing.strokes or []
        print(f"[INFO] Dibujo cargado: {current_drawing.name} (ID: {current_drawing.id}) con {len(current_strokes)} trazos.")
    except Drawing.DoesNotExist:
        print(f"[ERROR] No se encontró el dibujo con ID {drawing_id}")
        current_drawing = None
        current_strokes = []


# ===============================
# 🔹 TRAZOS Y GUARDADO
# ===============================

def add_stroke(points, color, thickness):
    global current_strokes, current_drawing, unsaved_changes

    stroke = {
        "points": points,
        "color": [int(c) for c in color],
        "thickness": int(thickness),
    }
    current_strokes.append(stroke)
    unsaved_changes = True

    print(f"[TRACE] Trazo agregado: total {len(current_strokes)} trazos.")
    return stroke


def save_current_drawing(name="Untitled", width=640, height=480):
    """
    Guarda el dibujo actual en la base de datos solo si hay trazos.
    Si no existe un Drawing aún, lo crea.
    """
    global current_drawing, current_strokes, unsaved_changes

    if not current_strokes:
        print("[⚠️] Dibujo vacío, no se guardará.")
        return None

    # 🔹 Crear nuevo dibujo si no existe
    if current_drawing is None:
        current_drawing = Drawing.objects.create(
            name=name,
            width=width,
            height=height,
            strokes=current_strokes,
        )
        print(f"[SAVE] Dibujo nuevo creado (ID={current_drawing.id})")
    else:
        # 🔹 Actualizar dibujo existente
        current_drawing.strokes = current_strokes
        current_drawing.save(update_fields=["name", "strokes", "updated_at"])
        print(f"[UPDATE] Dibujo existente actualizado (ID={current_drawing.id})")

    # 🔹 Generar miniatura
    try:
        img = render_strokes(current_strokes, current_drawing.width, current_drawing.height)
        thumb_path = os.path.join("media/thumbs", f"thumb_{current_drawing.id}.jpg")
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        cv2.imwrite(thumb_path, img)

        # Asignar ruta relativa para que Django pueda servirla
        current_drawing.thumbnail = f"thumbs/thumb_{current_drawing.id}.jpg"
        current_drawing.save(update_fields=["thumbnail"])
        print(f"[🖼️] Miniatura generada: {current_drawing.thumbnail}")
    except Exception as e:
        print(f"[ERROR] No se pudo generar miniatura: {e}")

    unsaved_changes = False

    print(f"[💾] Dibujo guardado correctamente: '{current_drawing.name}' (ID={current_drawing.id})")
    return current_drawing


# ===============================
# 🔹 RENDERIZADO DE TRAZOS
# ===============================

def render_strokes(strokes, width, height):
    """Crea una imagen desde los trazos guardados."""
    if not strokes:
        return np.ones((height, width, 3), np.uint8) * 255

    canvas = np.ones((height, width, 3), np.uint8) * 255
    for stroke in strokes:
        color = tuple(int(c) for c in stroke["color"])
        thickness = int(stroke["thickness"])
        pts = stroke["points"]
        for i in range(1, len(pts)):
            cv2.line(canvas, tuple(pts[i - 1]), tuple(pts[i]), color, thickness)
    return canvas
