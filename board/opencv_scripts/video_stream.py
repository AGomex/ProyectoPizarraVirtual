import cv2
import mediapipe as mp
import numpy as np
from threading import Lock
from django.http import JsonResponse
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

# 🔹 Importar acciones
from board.actions import color_action
from board.actions.home_action import execute_home_action  # si lo usas, mantenlo

mp_hands = mp.solutions.hands

color = color_action.get_current_color()
thickness = 5
prev_point = None
mode = "draw"
canvas = None
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
lock = Lock()

last_frame = None
last_canvas = None

pointer_data = {"x": 0, "y": 0, "mode": "draw", "action": None, "redirect": False, "url": None}

BUTTONS = [
    ("home.png", "home"),
    ("brush.png", "brush"),
    ("color.png", "color"),   # el recuadro reemplazará este icono
    ("shapes.png", "shapes"),
    ("enhance.png", "enhance"),
    ("eraser.png", "eraser"),
    ("download.png", "download"),
    ("save.png", "save")
]


# ---------------------- Funciones auxiliares ----------------------

def get_finger_status(hand_landmarks):
    """Devuelve lista [pulgar, índice, medio, anular, meñique] (1=levantado)."""
    fingers = []
    tip_ids = [4, 8, 12, 16, 20]
    fingers.append(1 if hand_landmarks.landmark[tip_ids[0]].x < hand_landmarks.landmark[tip_ids[0] - 1].x else 0)
    for i in range(1, 5):
        fingers.append(1 if hand_landmarks.landmark[tip_ids[i]].y < hand_landmarks.landmark[tip_ids[i] - 2].y else 0)
    return fingers


def draw_grid_background(h, w, spacing= 20):
    bg = np.ones((h, w, 3), np.uint8) * 255
    color_line = (220, 220, 220)
    for y in range(0, h, spacing):
        cv2.line(bg, (0, y), (w, y), color_line, 1)
    for x in range(0, w, spacing):
        cv2.line(bg, (x, 0), (x, h), color_line, 1)
    return bg


def draw_toolbar(frame, h, w, active_index=None, current_color=(0, 0, 0)):
    """Dibuja la barra de herramientas con los íconos perfectamente centrados."""
    toolbar_height = int(h * 0.18)
    section_width = w // len(BUTTONS)

    for i, (icon_file, action_name) in enumerate(BUTTONS):
        # --- Zona del botón ---
        x1 = i * section_width
        x2 = x1 + section_width
        color_box = (215, 235, 255) if i == active_index else (245, 245, 245)

        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), color_box, -1)
        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), (180, 180, 180), 2)

        # --- Coordenadas centradas ---
        center_x = x1 + section_width // 2
        center_y = toolbar_height // 2

        # 🔹 Si es el botón de color, dibujar cuadro centrado
        if action_name == "color":
            box_size = 45
            x_offset = center_x - box_size // 2
            y_offset = center_y - box_size // 2
            cv2.rectangle(frame, (x_offset, y_offset),
                          (x_offset + box_size, y_offset + box_size),
                          current_color, -1)
            cv2.rectangle(frame, (x_offset, y_offset),
                          (x_offset + box_size, y_offset + box_size),
                          (80, 80, 80), 2)
            continue

        # --- Ruta del icono ---
        icon_path = os.path.join(settings.BASE_DIR, "board", "static", "board", "icons", icon_file)
        if not os.path.exists(icon_path):
            cv2.putText(frame, "?", (center_x - 10, center_y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            continue

        # --- Leer icono ---
        icon = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
        if icon is None:
            continue

        # --- Redimensionar ---
        icon_size = 45
        icon = cv2.resize(icon, (icon_size, icon_size))

        # --- Coordenadas centradas ---
        x_offset = center_x - icon_size // 2
        y_offset = center_y - icon_size // 2

        # --- Verificar límites ---
        if y_offset + icon_size > frame.shape[0] or x_offset + icon_size > frame.shape[1]:
            continue

        # --- Renderizado con transparencia ---
        if icon.shape[2] == 4:
            alpha = icon[:, :, 3] / 255.0
            for c in range(3):
                frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size, c] = (
                    alpha * icon[:, :, c] +
                    (1 - alpha) * frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size, c]
                )
        else:
            frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size] = icon


# ---------------------- Flujo principal ----------------------

def generate_frames():
    global prev_point, canvas, mode, color, last_frame, last_canvas, pointer_data

    with mp_hands.Hands(max_num_hands=1,
                        min_detection_confidence=0.7,
                        min_tracking_confidence=0.6) as hands:

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            if canvas is None or canvas.shape[:2] != (h, w):
                canvas = draw_grid_background(h, w)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            cx, cy = None, None
            action_detected = None
            active_button = None
            pointer_visible = False

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    fingers = get_finger_status(hand_landmarks)
                    index_finger = hand_landmarks.landmark[8]
                    cx, cy = int(index_finger.x * w), int(index_finger.y * h)
                    pointer_visible = True

                    if all(fingers):
                        mode = "select"
                    elif fingers[1] and fingers[2] and not any(fingers[3:]):
                        mode = "draw"

                    if mode == "draw" and fingers[1] and not any(fingers[2:]):
                        if prev_point is not None:
                            cv2.line(canvas, prev_point, (cx, cy), color, thickness)
                        prev_point = (cx, cy)

                    else:
                        prev_point = None
                        toolbar_height = int(h * 0.18)
                        if cy < toolbar_height:
                            section_width = w // len(BUTTONS)
                            button_index = cx // section_width
                            if 0 <= button_index < len(BUTTONS):
                                active_button = button_index
                                action_name = BUTTONS[button_index][1]
                                action_detected = action_name

                                if action_name == "home":
                                    pointer_data["redirect"] = True
                                    pointer_data["url"] = "/"
                                elif action_name == "color":
                                    color_action.start_color_selection()
                                    pointer_data["redirect"] = False
            else:
                prev_point = None

            # --- Actualizar color mientras esté en modo selección ---
            if color_action.color_select_mode:
                color = color_action.update_color_rotation()
            else:
                color = color_action.get_current_color()

            # --- Confirmar color al abrir la mano ---
            if results.multi_hand_landmarks and color_action.color_select_mode:
                for hand_landmarks in results.multi_hand_landmarks:
                    fingers = get_finger_status(hand_landmarks)
                    if all(fingers):
                        color_action.stop_color_selection()

            # --- Renderizado final ---
            output = canvas.copy()
            draw_toolbar(output, h, w, active_index=active_button, current_color=color)

            # Puntero visible
            if pointer_visible and cx is not None and cy is not None:
                pointer_color = (0, 0, 255) if mode == "select" else (0, 255, 0)
                cv2.circle(output, (cx, cy), 6, pointer_color, -1)
                pointer_data.update({"x": cx, "y": cy, "mode": mode, "action": action_detected})

            with lock:
                last_frame = frame.copy()
                last_canvas = output.copy()

            ret, buffer = cv2.imencode('.jpg', output)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# ---------------------- Cámara lateral ----------------------

def generate_camera_frames():
    global last_frame
    while True:
        if last_frame is None:
            continue
        with lock:
            frame = last_frame.copy()
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# ---------------------- Datos del puntero ----------------------

def get_pointer_data(request):
    global pointer_data
    return JsonResponse(pointer_data)


@csrf_exempt
def reset_redirect(request):
    global pointer_data
    pointer_data["redirect"] = False
    pointer_data["url"] = None
    return JsonResponse({"status": "ok"})
