import cv2
import mediapipe as mp
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from board.application.actions import (
    color_action,
    save_action,
    undo_redo_action,
    tool_action,
    shape_action,
)

from board.application.use_cases.pointer_state import pointer_data
from board.infrastructure.opencv.draw_utils import draw_grid_background, draw_toolbar
from board.application.use_cases.sync import lock
from board.infrastructure.opencv.video_capture_manager import cap
from board.application.use_cases.ui_config import BUTTONS

from board.application.actions.enhance_action import EnhanceStrokeService


mp_hands = mp.solutions.hands

# Variables globales
color = color_action.get_current_color()
thickness = 5
prev_point = None
mode = "draw"
canvas = None
current_points = []

last_frame = None
last_canvas = None
enhancer = EnhanceStrokeService()

# ---------------------- Funciones auxiliares ----------------------

def get_finger_status(hand_landmarks, handedness="Right"):
    fingers = []
    tip_ids = [4, 8, 12, 16, 20]

    # 👍 Pulgar (diferente para izquierda/derecha)
    if handedness == "Right":
        fingers.append(1 if hand_landmarks.landmark[tip_ids[0]].x <
                        hand_landmarks.landmark[tip_ids[0] - 1].x else 0)
    else:
        fingers.append(1 if hand_landmarks.landmark[tip_ids[0]].x >
                        hand_landmarks.landmark[tip_ids[0] - 1].x else 0)

    # ☝ Resto de dedos (igual para ambas manos)
    for i in range(1, 5):
        fingers.append(
            1 if hand_landmarks.landmark[tip_ids[i]].y <
            hand_landmarks.landmark[tip_ids[i] - 2].y else 0
        )

    return fingers



# ---------------------- Flujo principal ----------------------

# video_stream.py (solo la función generate_frames completa)
def generate_frames(drawing_id=None):
    """
    Stream de video interactivo con detección de gestos, panel de color, pincel,
    panel de formas, modos (select, draw, enhance, eraser) y sincronización con la base de datos.
    """
    global prev_point, canvas, mode, color, last_frame, last_canvas, pointer_data
    global current_points, start_point, drawing_shape, shape_selected, last_active_mode

    # Inicialización
    drawing_shape = False
    canvas = None
    current_points = []
    start_point = None
    shape_selected = "rectangle"
    last_active_mode = None
    SMOOTHING = 3
    recent_index_positions = []
    previous_color = None
    stroke_mode = None
    stroke_color = None
    stroke_size = None

    # Cargar o crear dibujo
    if drawing_id is not None:
        save_action.load_drawing(drawing_id)
    else:
        if save_action.current_drawing is None:
            save_action.start_new_drawing(name="Nuevo Dibujo")
        else:
            save_action.reset_strokes()

    with mp_hands.Hands(max_num_hands=1,
                        min_detection_confidence=0.8,
                        min_tracking_confidence=0.75) as hands:

        while True:
            success, frame = cap.read()
            if not success:
                break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Crear lienzo base
            if canvas is None or canvas.shape[:2] != (h, w):
                canvas = draw_grid_background(h, w)
                if hasattr(save_action, "current_strokes") and save_action.current_strokes:
                    strokes_img = save_action.render_strokes(save_action.current_strokes, w, h)
                    if strokes_img is not None:
                        mask = strokes_img < 250
                        canvas[mask] = strokes_img[mask]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            cx, cy = None, None
            pointer_visible = False
            active_button = None
            action_detected = None
            fingers = [0, 0, 0, 0, 0]

            try:
                if results.multi_hand_landmarks:
                    for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        handedness = results.multi_handedness[hand_idx].classification[0].label
                        fingers = get_finger_status(hand_landmarks, handedness)
                        index_finger = hand_landmarks.landmark[8]
                        cx, cy = int(index_finger.x * w), int(index_finger.y * h)
                        pointer_visible = True

                        # Suavizado
                        recent_index_positions.append([cx, cy])
                        if len(recent_index_positions) > SMOOTHING:
                            recent_index_positions.pop(0)
                        avg_point = np.mean(recent_index_positions, axis=0).astype(int)
                        cx, cy = int(avg_point[0]), int(avg_point[1])

                        # 🔹 Cerrar paneles con gesto de dos dedos levantados
                        if fingers[1] and fingers[2] and not any(fingers[0:1] + fingers[3:]):
                                if tool_action.panel_visible:
                                    tool_action.close_brush_panel()
                                if color_action.panel_visible:
                                    color_action.close_color_panel()
                                if shape_action.panel_visible:
                                    shape_action.close_shape_panel()
                                    drawing_shape = False
                                    start_point = None

                        # Actualizar tamaño del pincel/borrador
                        tool_action.update_brush_size(hand_landmarks, h, fingers)

                        # 🔹 Control de modos por gesto
                        if sum(fingers) == 5:
                            if mode != "select":
                                last_active_mode = mode
                            if mode == "eraser" and tool_action.panel_visible:
                                tool_action.close_brush_panel()
                            mode = "select"

                        elif fingers[1] and fingers[2] and not any(fingers[3:]):
                            if mode not in ["enhance", "eraser"]:
                                mode = "draw"

                        # 🔹 Dibujo de formas
                        if shape_action.panel_visible:
                            if sum(fingers) == 5 and not drawing_shape:
                                shape_action.handle_shape_selection_by_gesture(cx, cy, fingers)

                            if sum(fingers) == 1 and fingers[1] and not drawing_shape:
                                start_point = (cx, cy)
                                drawing_shape = True

                            elif drawing_shape and sum(fingers) == 5:
                                size = tool_action.get_brush_size("brush")
                                shape_action.add_shape_to_strokes(start_point, (cx, cy), color, size)

                                canvas = draw_grid_background(h, w)
                                strokes_img = save_action.render_strokes(save_action.current_strokes, w, h)
                                if strokes_img is not None:
                                    mask = strokes_img < 250
                                    canvas[mask] = strokes_img[mask]

                                start_point = None
                                drawing_shape = False

                        # 🔹 Determinar active_mode
                        if mode == "select":
                            active_mode = "select"
                        else:
                            active_mode = mode
                            last_active_mode = mode

                        drawing_allowed = active_mode in ["draw", "enhance", "eraser"]

                        # 🔹 Inicio o continuación de trazo
                        if drawing_allowed and fingers[1] and not any(fingers[2:]) \
                                and not shape_action.panel_visible and not tool_action.panel_visible:

                            if prev_point is None:
                                # 🔹 Inicio del trazo: se fijan las propiedades del trazo
                                stroke_mode = active_mode
                                stroke_color = (255, 255, 255) if stroke_mode == "eraser" else color
                                stroke_size = tool_action.get_brush_size(
                                    "eraser" if stroke_mode == "eraser" else "brush"
                                )
                                current_points = [[cx, cy]]
                            else:
                                cv2.line(canvas, prev_point, (cx, cy), stroke_color, stroke_size)
                                current_points.append([cx, cy])
                            prev_point = (cx, cy)
                        
                        else:
                            # 🔹 Fin de trazo
                            if len(current_points) > 1 and stroke_mode is not None:
                                if stroke_mode == "enhance":
                                    enhanced, detected_shape = enhancer.enhance_stroke(current_points)
                                    if detected_shape and not pointer_data.get("alert_sent", False):
                                        # pointer_data["alert"] = f"{detected_shape} detectado y perfeccionado."
                                        # pointer_data["alert_sent"] = True
                                        save_action.add_stroke(enhanced, color, stroke_size)
                                    elif detected_shape is None:
                                        # pointer_data["alert"] = "No se encontró similitud con figura básica."
                                        # pointer_data["alert_sent"] = True
                                        # save_action.add_stroke(enhanced, color, stroke_size)
                                        pass

                                elif stroke_mode == "eraser":
                                    save_action.add_stroke(current_points, (255, 255, 255), stroke_size)
                                    if previous_color is not None:
                                        color = previous_color
                                        previous_color = None

                                else:  # draw normal
                                    save_action.add_stroke(current_points, stroke_color, stroke_size)

                                # 🔹 Actualizar lienzo
                                canvas = draw_grid_background(h, w)
                                strokes_img = save_action.render_strokes(save_action.current_strokes, w, h)
                                if strokes_img is not None:
                                    mask = strokes_img < 250
                                    canvas[mask] = strokes_img[mask]

                            current_points = []
                            prev_point = None
                            stroke_mode = None

                        # 🔹 Toolbar principal
                        toolbar_height = int(h * 0.18)
                        if mode == "select" and cy and cy < toolbar_height:
                            if not (color_action.panel_visible or shape_action.panel_visible):
                                section_width = w // len(BUTTONS)
                                button_index = cx // section_width
                                if 0 <= button_index < len(BUTTONS):
                                    active_button = button_index
                                    action_name = BUTTONS[button_index][1]
                                    action_detected = action_name

                                    if action_name == "undo":
                                        if undo_redo_action.undo_last_stroke():
                                            canvas = draw_grid_background(h, w)
                                            strokes_img = save_action.render_strokes(save_action.current_strokes, w, h)
                                            if strokes_img is not None:
                                                mask = strokes_img < 250
                                                canvas[mask] = strokes_img[mask]
                                    elif action_name == "redo":
                                        if undo_redo_action.redo_last_stroke():
                                            canvas = draw_grid_background(h, w)
                                            strokes_img = save_action.render_strokes(save_action.current_strokes, w, h)
                                            if strokes_img is not None:
                                                mask = strokes_img < 250
                                                canvas[mask] = strokes_img[mask]
                                    elif action_name == "color":
                                        if not tool_action.panel_visible and not shape_action.panel_visible:
                                            color_action.open_color_panel()
                                    elif action_name == "brush":
                                        if not color_action.panel_visible and not shape_action.panel_visible:
                                            tool_action.open_brush_panel(tool="brush")
                                    elif action_name == "shapes":
                                        if not color_action.panel_visible and not tool_action.panel_visible:
                                            shape_action.open_shape_panel()
                                    elif action_name == "save":
                                        pointer_data["action"] = "save_requested"
                                    elif action_name == "enhance":
                                        mode = "enhance"
                                    elif action_name == "eraser":
                                        if mode != "eraser":
                                            previous_color = color
                                            color = (255, 255, 255)
                                            mode = "eraser"
                                            tool_action.open_brush_panel(tool="eraser")
                                            pointer_data["waiting_brush_close"] = True
                                        else:
                                            mode = "draw"
                                            if previous_color is not None:
                                                color = previous_color
                                                previous_color = None
                                            last_active_mode = mode
                                            prev_point = None

            except Exception as e:
                print(f"[ERROR en frame]: {e}")
                continue

            # Color actual
            if mode != "eraser":
                color = color_action.get_current_color()

            # 🔹 Dibujar UI y vista previa de la forma
            if drawing_shape and start_point is not None and cx is not None and cy is not None:
                temp_canvas = canvas.copy()
                size = tool_action.get_brush_size("brush")
                shape_action.draw_shape(temp_canvas, start_point, (cx, cy), color, size)
                output = temp_canvas
            else:
                output = canvas.copy()

            # 🔹 Dibujar toolbar y paneles
            draw_toolbar(output, h, w, active_index=active_button, current_color=color)
            tool_action.draw_brush_panel(output)
            if color_action.panel_visible:
                color_action.draw_advanced_color_panel(output, h, w, pointer_x=cx, pointer_y=cy, finger_states=fingers)
            shape_action.draw_shape_panel(output)

            # 🔹 Puntero visual
            if pointer_visible and cx is not None and cy is not None:
                pointer_color = (
                    (0, 0, 255) if mode == "select"
                    else (255, 0, 255) if mode == "enhance"
                    else (255, 255, 255) if mode == "eraser"
                    else (0, 255, 0)
                )
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
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() + b'\r\n')

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
