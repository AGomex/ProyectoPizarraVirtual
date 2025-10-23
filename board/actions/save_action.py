from board.models import Drawing
from django.utils import timezone
import cv2
import numpy as np
import os

# Estado en memoria para la sesión actual
current_strokes = []
current_drawing = None


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
    Crea un nuevo Drawing **solo si no existe uno activo**.
    Devuelve current_drawing.
    """
    global current_strokes, current_drawing

    if current_drawing is not None:
        print(f"[INFO] Ya existe un dibujo activo (ID={current_drawing.id}), no se crea uno nuevo.")
        return current_drawing

    current_strokes = []
    current_drawing = Drawing.objects.create(name=name, width=width, height=height)
    print(f"[SAVE] Nuevo dibujo creado -> ID={current_drawing.id}")
    return current_drawing


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
    """Agrega un trazo al dibujo actual y guarda en DB sin bloquear el flujo."""
    global current_strokes, current_drawing

    if not current_drawing:
        print("[ERROR] No hay dibujo activo para agregar trazo.")
        return None  # importante: devolver None si no hay dibujo

    # 🔸 Asegurar que el color se guarde como lista (no numpy)
    stroke = {
        "points": points,
        "color": [int(c) for c in color],
        "thickness": int(thickness),
    }

    current_strokes.append(stroke)
    current_drawing.strokes = current_strokes
    current_drawing.save(update_fields=["strokes"])

    print(f"[TRACE] Trazo agregado: total {len(current_strokes)} trazos.")
    return stroke  



def save_current_drawing():
    """Guarda el dibujo actual y actualiza la miniatura."""
    global current_drawing, current_strokes

    if current_drawing is None:
        print("[⚠️] No hay dibujo activo para guardar.")
        return None

    if not current_strokes:
        print(f"[⚠️] Dibujo vacío '{current_drawing.name}' (ID: {current_drawing.id}), no se guardará.")
        return None

    # 🔹 Guardar trazos
    current_drawing.strokes = current_strokes
    current_drawing.updated_at = timezone.now()
    current_drawing.save()

    # 🔹 Generar o actualizar miniatura
    try:
        img = render_strokes(current_strokes, current_drawing.width, current_drawing.height)
        thumb_path = os.path.join("media/thumbs", f"thumb_{current_drawing.id}.jpg")
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        cv2.imwrite(thumb_path, img)
        current_drawing.thumbnail = f"thumbs/thumb_{current_drawing.id}.jpg"
        current_drawing.save(update_fields=["thumbnail"])
        print(f"[🖼️] Miniatura actualizada para dibujo ID {current_drawing.id}")
    except Exception as e:
        print(f"[ERROR] No se pudo generar miniatura: {e}")

    print(f"[💾] Dibujo guardado correctamente: '{current_drawing.name}' (ID: {current_drawing.id})")
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
