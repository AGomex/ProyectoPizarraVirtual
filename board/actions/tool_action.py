import cv2
import numpy as np

# 🔹 Variables globales
brush_size_paint = 5
brush_size_eraser = 20   # tamaño inicial del borrador
MIN_BRUSH = 1
MAX_BRUSH = 50

panel_visible = False
tool_select_mode = False
last_wrist_y = None

SENSITIVITY = 1.5  # sensibilidad del control vertical

# 🔸 Tipo de herramienta activa para el panel
current_tool = "brush"  # "brush" o "eraser"


# ===============================
# 🔹 FUNCIONES DE PANEL Y CONTROL
# ===============================

def open_brush_panel(tool="brush"):
    """Abre el panel de tamaño según la herramienta."""
    global panel_visible, tool_select_mode, current_tool
    panel_visible = True
    tool_select_mode = True
    current_tool = tool  # puede ser "brush" o "eraser"


def close_brush_panel():
    """Cierra el panel."""
    global panel_visible, tool_select_mode, last_wrist_y
    panel_visible = False
    tool_select_mode = False
    last_wrist_y = None


def update_brush_size(hand_landmarks, frame_height, fingers):
    """
    Ajusta el tamaño del pincel o borrador SOLO cuando la mano está en puño.
    fingers: lista de 5 valores (1 si el dedo está extendido, 0 si está cerrado)
    """
    global brush_size_paint, brush_size_eraser, last_wrist_y

    if not panel_visible:
        return

    # 🔸 Solo cambiar si la mano está completamente cerrada (puño)
    if fingers[1] and fingers[2] and not any(fingers[0:1] + fingers[3:]):  # si algún dedo está levantado
        last_wrist_y = None
        return

    # 🔹 Movimiento vertical de la muñeca
    wrist_y = hand_landmarks.landmark[0].y * frame_height
    if last_wrist_y is None:
        last_wrist_y = wrist_y

    delta = last_wrist_y - wrist_y
    change = int(delta / SENSITIVITY)

    if change != 0:
        if current_tool == "eraser":
            brush_size_eraser += change
            brush_size_eraser = max(MIN_BRUSH, min(MAX_BRUSH, brush_size_eraser))
        else:
            brush_size_paint += change
            brush_size_paint = max(MIN_BRUSH, min(MAX_BRUSH, brush_size_paint))

        last_wrist_y = wrist_y




def draw_brush_panel(frame):
    """Dibuja el panel de tamaño para la herramienta activa."""
    global brush_size_paint, brush_size_eraser, current_tool
    if not panel_visible:
        return

    h, w, _ = frame.shape
    panel_w, panel_h = 150, 35
    x, y = w - panel_w - 20, 100

    # Fondo del panel
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (240, 240, 240), -1)
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (80, 80, 80), 2)

    # Determinar tamaño actual según herramienta
    size = brush_size_eraser if current_tool == "eraser" else brush_size_paint
    fill_w = int(panel_w * (size / MAX_BRUSH))
    color = (0, 160, 0) if current_tool == "brush" else (60, 60, 60)  # verde o gris oscuro
    cv2.rectangle(frame, (x, y), (x + fill_w, y + panel_h), color, -1)

    # Texto
    percent = int((size / MAX_BRUSH) * 100)
    label = "PINCEL" if current_tool == "brush" else "BORRADOR"
    cv2.putText(frame, f"{label}: {percent}%", (x + 8, y + panel_h//2 + 7),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)


def get_brush_size(tool="brush"):
    """Obtiene el tamaño de la herramienta actual."""
    return brush_size_eraser if tool == "eraser" else brush_size_paint