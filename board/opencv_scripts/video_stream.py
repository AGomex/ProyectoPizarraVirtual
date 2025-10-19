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
from board.actions.home_action import execute_home_action
from board.actions.color_action import execute_color_action

mp_hands = mp.solutions.hands

color = (0, 0, 0)
thickness = 5
prev_point = None
mode = "draw"
canvas = None
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
lock = Lock()

last_frame = None
last_canvas = None
pointer_data = {"x": 0, "y": 0, "mode": "draw", "action": None}

# Lista de botones (solo Home y Color activos)
BUTTONS = [
    ("home.png", "home"),
    ("brush.png", "brush"),
    ("color.png", "color"),
    ("shapes.png", "shapes"),
    ("enhance.png", "enhance"),
    ("eraser.png", "eraser"),
    ("download.png", "download"),
    ("save.png", "save")
]


# ---------------------- Funciones auxiliares ----------------------

def get_finger_status(hand_landmarks):
    fingers = []
    tip_ids = [4, 8, 12, 16, 20]
    fingers.append(1 if hand_landmarks.landmark[tip_ids[0]].x < hand_landmarks.landmark[tip_ids[0] - 1].x else 0)
    for i in range(1, 5):
        fingers.append(1 if hand_landmarks.landmark[tip_ids[i]].y < hand_landmarks.landmark[tip_ids[i] - 2].y else 0)
    return fingers


def draw_grid_background(h, w, spacing=50):
    bg = np.ones((h, w, 3), np.uint8) * 255
    color_line = (220, 220, 220)
    for y in range(0, h, spacing):
        cv2.line(bg, (0, y), (w, y), color_line, 1)
    for x in range(0, w, spacing):
        cv2.line(bg, (x, 0), (x, h), color_line, 1)
    return bg


def draw_toolbar(frame, h, w, active_index=None):
    toolbar_height = int(h * 0.18)
    section_width = w // len(BUTTONS)

    for i, (icon_file, _) in enumerate(BUTTONS):
        x1 = i * section_width
        x2 = x1 + section_width
        color_box = (215, 235, 255) if i == active_index else (245, 245, 245)
        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), color_box, -1)
        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), (180, 180, 180), 2)

        icon_path = os.path.join(settings.BASE_DIR, "board", "static", "board", "icons", icon_file)
        if os.path.exists(icon_path):
            icon = cv2.imread(icon_path)
            if icon is not None:
                icon = cv2.resize(icon, (40, 40))
                y_offset = int(toolbar_height * 0.35)
                x_offset = x1 + section_width // 2 - 20
                frame[y_offset:y_offset + 40, x_offset:x_offset + 40] = icon


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
                    elif mode == "select":
                        prev_point = None
                        toolbar_height = int(h * 0.18)
                        if cy < toolbar_height:
                            section_width = w // len(BUTTONS)
                            button_index = cx // section_width
                            if 0 <= button_index < len(BUTTONS):
                                active_button = button_index
                                action_name = BUTTONS[button_index][1]
                                action_detected = action_name

                                # --- Ejecutar acción ---
                                if action_name == "home":
                                    pointer_data.update({"redirect": True, "url": "/"})
                                elif action_name == "color":
                                    color = execute_color_action(color)
                                    pointer_data.update({"redirect": False})
            else:
                prev_point = None

            output = canvas.copy()
            draw_toolbar(output, h, w, active_index=active_button)

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
last_redirect_time = None

def get_pointer_data(request):
    global pointer_data, last_redirect_time

    # Si fue redirección hace más de 1 segundo, resetea automáticamente
    if pointer_data.get("redirect"):
        if last_redirect_time and (timezone.now() - last_redirect_time).total_seconds() > 1:
            pointer_data["redirect"] = False
            pointer_data["url"] = None

    return JsonResponse(pointer_data)


@csrf_exempt
def reset_redirect(request):
    """Permite al frontend resetear manualmente el flag redirect después de redirigir."""
    global pointer_data
    pointer_data["redirect"] = False
    pointer_data["url"] = None
    return JsonResponse({"status": "ok"})


