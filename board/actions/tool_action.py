import cv2
import numpy as np

# 🔹 Variables globales
brush_size = 5
MIN_BRUSH = 1
MAX_BRUSH = 50
panel_visible = False
tool_select_mode = False
last_wrist_y = None

SENSITIVITY = 1.5 # más sensible

def open_brush_panel():
    global panel_visible, tool_select_mode
    panel_visible = True
    tool_select_mode = True

def close_brush_panel():
    global panel_visible, tool_select_mode, last_wrist_y
    panel_visible = False
    tool_select_mode = False
    last_wrist_y = None

def update_brush_size(hand_landmarks, frame_height, fingers):
    global brush_size, last_wrist_y
    if not panel_visible:
        return

    # 🔹 Cerrar panel con 5 dedos levantados
    if sum(fingers) == 5:
        close_brush_panel()
        return

    wrist_y = hand_landmarks.landmark[0].y * frame_height
    if last_wrist_y is None:
        last_wrist_y = wrist_y

    delta = last_wrist_y - wrist_y
    change = int(delta / SENSITIVITY)

    if change != 0:
        brush_size += change
        brush_size = max(MIN_BRUSH, min(MAX_BRUSH, brush_size))
        last_wrist_y = wrist_y

def draw_brush_panel(frame):
    global brush_size
    if not panel_visible:
        return

    h, w, _ = frame.shape
    panel_w, panel_h = 120, 30
    x, y = w - panel_w - 20, 100

    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (200, 200, 200), -1)
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (100, 100, 100), 2)

    fill_w = int(panel_w * (brush_size / MAX_BRUSH))
    cv2.rectangle(frame, (x, y), (x + fill_w, y + panel_h), (0, 150, 0), -1)

    percent = int((brush_size / MAX_BRUSH) * 100)
    cv2.putText(frame, f"{percent}%", (x + panel_w//2 - 20, y + panel_h//2 + 7),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

def get_brush_size():
    return brush_size