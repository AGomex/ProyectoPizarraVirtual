import cv2
import numpy as np
from board.application.actions import save_action

# ----------------------
# 🔹 Estado global del módulo
# ----------------------
panel_visible = False
shape_selected = "rectangle"  # opciones: "rectangle", "circle", etc.
start_point = None
drawing_shape = False
shapes = []  # lista temporal de shapes pendientes de guardar

# Tamaño base del panel
PANEL_X, PANEL_Y = 50, 1 # posición inicial (abajo)
BUTTON_SIZE = 50
BUTTON_MARGIN = 10

# ----------------------
# 🔹 Funciones para panel
# ----------------------
def open_shape_panel():
    global panel_visible
    panel_visible = True

def close_shape_panel():
    global panel_visible
    panel_visible = False

def select_shape(shape_name):
    global shape_selected
    shape_selected = shape_name


# ----------------------
# 🔹 Dibujar panel horizontal (una sola fila)

# ----------------------
# 🔹 Cache de geometría del panel (para reuso en detección de gestos)
# ----------------------
last_panel_geometry = None
# formato: (x_start, y_start, panel_width, panel_height, total_buttons)

# ----------------------
# 🔹 Dibujar panel horizontal (una sola fila) — versión correcta
# ----------------------
def draw_shape_panel(frame):
    """Dibuja el panel de selección de formas en una fila horizontal arriba.
    Además guarda la geometría en last_panel_geometry para que la detección de gestos use exactamente
    la misma posición.
    """
    global last_panel_geometry

    if not panel_visible:
        last_panel_geometry = None
        return

    shapes_list = [
        "rectangle", "square", "circle",
        "line", "triangle", "star",
        "pentagon", "hexagon", "heptagon"
    ]

    total_buttons = len(shapes_list)
    panel_width = total_buttons * (BUTTON_SIZE + BUTTON_MARGIN) + 20
    panel_height = BUTTON_SIZE + 35

    # 🔹 Centrar horizontalmente y ubicar arriba — usar dimensiones reales del frame
    h, w = frame.shape[:2]
    x_start = (w - panel_width) // 2
    y_start = 1 # <-- altura superior (ajústalo si quieres más o menos margen)

    # Guardar geometría para que la detección use exactamente estos valores
    last_panel_geometry = (int(x_start), int(y_start), int(panel_width), int(panel_height), total_buttons)

    # Fondo del panel
    cv2.rectangle(frame, (x_start, y_start),
                  (x_start + panel_width, y_start + panel_height),
                  (240, 240, 240), -1)
    cv2.rectangle(frame, (x_start, y_start),
                  (x_start + panel_width, y_start + panel_height),
                  (180, 180, 180), 2)

    # Dibujar botones en una fila
    for i, name in enumerate(shapes_list):
        x1 = x_start + 10 + i * (BUTTON_SIZE + BUTTON_MARGIN)
        y1 = y_start + 20
        x2 = x1 + BUTTON_SIZE
        y2 = y1 + BUTTON_SIZE

        color = (100, 200, 250) if shape_selected == name else (200, 200, 200)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 2)

        # --- Dibujo de íconos ---
        cx, cy = x1 + BUTTON_SIZE // 2, y1 + BUTTON_SIZE // 2
        s = 12

        if name == "rectangle":
            cv2.rectangle(frame, (cx - s, cy - s//2), (cx + s, cy + s//2), (0, 0, 0), 2)
        elif name == "square":
            cv2.rectangle(frame, (cx - s, cy - s), (cx + s, cy + s), (0, 0, 0), 2)
        elif name == "circle":
            cv2.circle(frame, (cx, cy), s, (0, 0, 0), 2)
        elif name == "line":
            cv2.line(frame, (cx - s, cy + s), (cx + s, cy - s), (0, 0, 0), 2)
        elif name == "triangle":
            pts = np.array([[cx, cy - s], [cx - s, cy + s], [cx + s, cy + s]], np.int32)
            cv2.polylines(frame, [pts], True, (0, 0, 0), 2)
        elif name == "star":
            points = []
            for j in range(10):
                angle = j * np.pi / 5
                r = s if j % 2 == 0 else s // 2
                x = int(cx + r * np.sin(angle))
                y = int(cy - r * np.cos(angle))
                points.append((x, y))
            cv2.polylines(frame, [np.array(points, np.int32)], True, (0, 0, 0), 2)
        elif name in ["pentagon", "hexagon", "heptagon"]:
            sides = {"pentagon": 5, "hexagon": 6, "heptagon": 7}[name]
            pts = []
            for j in range(sides):
                angle = 2 * np.pi * j / sides
                x = int(cx + s * np.cos(angle - np.pi / 2))
                y = int(cy + s * np.sin(angle - np.pi / 2))
                pts.append((x, y))
            cv2.polylines(frame, [np.array(pts, np.int32)], True, (0, 0, 0), 2)


# ----------------------

# ----------------------
# 🔹 Selección con gesto — usa la geometría calculada por draw_shape_panel()
# ----------------------
def handle_shape_selection_by_gesture(cx, cy, fingers):
    """Detecta qué botón fue apuntado por el gesto.
    Usa la geometría cacheada en last_panel_geometry si está disponible.
    """
    global shape_selected, last_panel_geometry

    if not panel_visible or fingers is None:
        return

    if sum(fingers) != 5:
        return

    # Lista de formas (idéntica a la usada por draw_shape_panel)
    shapes_list = [
        "rectangle", "square", "circle",
        "line", "triangle", "star",
        "pentagon", "hexagon", "heptagon"
    ]

    DETECTION_MARGIN = 15

    # Si no hay geometría cacheada, no podemos detectar (evita usar tamaños fijos)
    if last_panel_geometry is None:
        return

    x_start, y_start, panel_width, panel_height, total_buttons = last_panel_geometry

    # Comprobación de seguridad: si el número de botones cambió, recalcular índices
    if total_buttons != len(shapes_list):
        # fallback simple: actualizamos total_buttons localmente
        total_buttons = len(shapes_list)

    for i, name in enumerate(shapes_list):
        x1 = x_start + 10 + i * (BUTTON_SIZE + BUTTON_MARGIN)
        y1 = y_start + 35
        x2 = x1 + BUTTON_SIZE
        y2 = y1 + BUTTON_SIZE

        if (x1 - DETECTION_MARGIN) <= cx <= (x2 + DETECTION_MARGIN) and \
           (y1 - DETECTION_MARGIN) <= cy <= (y2 + DETECTION_MARGIN):
            shape_selected = name
            break


# ----------------------
# 🔹 Dibujar forma
# ----------------------
def draw_shape(canvas, start, end, color, thickness):
    if start is None or end is None:
        return

    x1, y1 = int(start[0]), int(start[1])
    x2, y2 = int(end[0]), int(end[1])
    w, h = x2 - x1, y2 - y1
    cx, cy = (x1 + x2)//2, (y1 + y2)//2
    size = max(abs(w), abs(h)) // 2

    if shape_selected == "rectangle":
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)
    elif shape_selected == "square":
        side = min(abs(w), abs(h))
        cv2.rectangle(canvas, (x1, y1), (x1 + side, y1 + side), color, thickness)
    elif shape_selected == "circle":
        cv2.circle(canvas, (cx, cy), int(size), color, thickness)
    elif shape_selected == "line":
        cv2.line(canvas, (x1, y1), (x2, y2), color, thickness)
    elif shape_selected == "triangle":
        pts = np.array([[cx, cy - size], [cx - size, cy + size], [cx + size, cy + size]], np.int32)
        cv2.polylines(canvas, [pts], True, color, thickness)
    elif shape_selected == "star":
        points = []
        for j in range(10):
            angle = j * np.pi / 5
            r = size if j % 2 == 0 else size // 2
            x = int(cx + r * np.sin(angle))
            y = int(cy - r * np.cos(angle))
            points.append((x, y))
        cv2.polylines(canvas, [np.array(points, np.int32)], True, color, thickness)
    elif shape_selected in ["pentagon", "hexagon", "heptagon"]:
        sides = {"pentagon": 5, "hexagon": 6, "heptagon": 7}[shape_selected]
        pts = []
        for j in range(sides):
            angle = 2 * np.pi * j / sides
            x = int(cx + size * np.cos(angle - np.pi/2))
            y = int(cy + size * np.sin(angle - np.pi/2))
            pts.append((x, y))
        cv2.polylines(canvas, [np.array(pts, np.int32)], True, color, thickness)


# ----------------------
# 🔹 Guardar forma
# ----------------------
def add_shape_to_strokes(start, end, color, thickness):
    if start is None or end is None:
        return

    x1, y1 = start
    x2, y2 = end
    w, h = x2 - x1, y2 - y1
    cx, cy = (x1 + x2)//2, (y1 + y2)//2
    size = max(abs(w), abs(h)) // 2
    points = []

    if shape_selected == "rectangle":
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
    elif shape_selected == "square":
        side = min(abs(w), abs(h))
        points = [(x1, y1), (x1 + side, y1), (x1 + side, y1 + side), (x1, y1 + side), (x1, y1)]
    elif shape_selected == "circle":
        radius = int(max(abs(w), abs(h)) / 2)
        for angle in range(0, 360, 5):
            rad = np.deg2rad(angle)
            x = int(cx + radius * np.cos(rad))
            y = int(cy + radius * np.sin(rad))
            points.append((x, y))
    elif shape_selected == "line":
        points = [start, end]
    elif shape_selected == "triangle":
        points = [(cx, y1), (x1, y2), (x2, y2), (cx, y1)]
    elif shape_selected == "star":
        for i in range(10):
            angle = i * np.pi / 5
            r = size if i % 2 == 0 else size // 2
            x = int(cx + r * np.sin(angle))
            y = int(cy - r * np.cos(angle))
            points.append((x, y))
        points.append(points[0])
    elif shape_selected in ["pentagon", "hexagon", "heptagon"]:
        sides = {"pentagon": 5, "hexagon": 6, "heptagon": 7}[shape_selected]
        for i in range(sides):
            angle = 2 * np.pi * i / sides
            x = int(cx + size * np.cos(angle - np.pi/2))
            y = int(cy + size * np.sin(angle - np.pi/2))
            points.append((x, y))
        points.append(points[0])

    if points:
        save_action.add_stroke(points, color, thickness)


# ----------------------
# 🔹 Vista previa temporal


def draw_temporary_shape(canvas, current_pos, color, thickness):
    global last_panel_geometry

    if start_point is None or current_pos is None:
        return

    # Si hay panel visible, ajustar por su altura
    offset_y = 0
    if last_panel_geometry is not None:
        _, y_start, _, panel_height, _ = last_panel_geometry
        offset_y = panel_height  # compensar toda la altura del panel

    adjusted_start = (start_point[0], start_point[1] - offset_y)
    adjusted_end = (current_pos[0], current_pos[1] - offset_y)

    temp_canvas = canvas.copy()
    draw_shape(temp_canvas, adjusted_start, adjusted_end, color, thickness)
    return temp_canvas