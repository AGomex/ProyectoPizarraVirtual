import cv2
import mediapipe as mp
import numpy as np
from threading import Lock

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

color = (0, 0, 0)
thickness = 5
drawing = False
prev_point = None

canvas = None
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # ✅ se usa una sola cámara
lock = Lock()

last_frame = None
last_canvas = None


def generate_frames():
    """Stream del lienzo procesado con dibujo."""
    global drawing, prev_point, canvas, last_frame, last_canvas

    with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.5) as hands:
        while True:
            with lock:
                success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            if canvas is None or canvas.shape[:2] != (h, w):
                canvas = np.ones((h, w, 3), np.uint8) * 255

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    index_finger = hand_landmarks.landmark[8]
                    middle_finger = hand_landmarks.landmark[12]
                    cx, cy = int(index_finger.x * w), int(index_finger.y * h)

                    if index_finger.y < middle_finger.y - 0.02:
                        drawing = True
                    else:
                        drawing = False
                        prev_point = None

                    if drawing:
                        if prev_point is not None:
                            cv2.line(canvas, prev_point, (cx, cy), color, thickness)
                        prev_point = (cx, cy)

            combined = canvas.copy()

            with lock:
                last_frame = frame.copy()
                last_canvas = combined.copy()

            ret, buffer = cv2.imencode('.jpg', combined)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def generate_camera_frames():
    """Stream de la cámara sin procesar (mini cámara)."""
    global last_frame

    while True:
        if last_frame is None:
            continue
        with lock:
            frame = last_frame.copy()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
