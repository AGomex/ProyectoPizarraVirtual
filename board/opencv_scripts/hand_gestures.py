import cv2
import mediapipe as mp
import numpy as np
import requests

# Dirección de tu API Django para guardar trazos
API_URL = "http://127.0.0.1:8000/board/api/save/"

# Inicialización de MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Variables de dibujo
canvas = np.ones((600, 800, 3), np.uint8) * 255  # lienzo blanco
drawing = False
strokes = []
current_stroke = []

# Parámetros del dibujo
color = (0, 0, 0)  # negro
thickness = 5

def enviar_a_django(nombre, trazos):
    """Guarda los trazos en la base Django."""
    data = {"name": nombre, "strokes": trazos}
    try:
        r = requests.post(API_URL, json=data)
        print("Guardado en Django:", r.json())
    except Exception as e:
        print("Error al enviar:", e)

def detectar_gesto(hand_landmarks):
    """
    Retorna el gesto detectado:
    - 'draw': dedo índice arriba
    - 'erase': puño cerrado
    - 'clear': mano abierta
    """
    finger_tips = [8, 12, 16, 20]
    fingers = []

    # y del pulgar y de los otros dedos
    landmarks = hand_landmarks.landmark
    for tip in finger_tips:
        fingers.append(landmarks[tip].y < landmarks[tip - 2].y)

    # índice arriba, los demás abajo → dibujar
    if fingers[0] and not any(fingers[1:]):
        return "draw"
    # todos abajo → borrar
    elif not any(fingers):
        return "erase"
    # todos arriba → limpiar
    elif all(fingers):
        return "clear"
    else:
        return "none"

def main():
    global drawing, current_stroke, strokes

    cap = cv2.VideoCapture(0)
    with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7) as hands:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)  # espejo
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    gesture = detectar_gesto(hand_landmarks)
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    h, w, _ = frame.shape
                    index_finger = hand_landmarks.landmark[8]
                    cx, cy = int(index_finger.x * w), int(index_finger.y * h)

                    if gesture == "draw":
                        drawing = True
                        current_stroke.append([cx, cy])

                        # Dibuja una línea entre el último punto y el nuevo punto
                        if len(current_stroke) > 1:
                            cv2.line(canvas,
                                    tuple(current_stroke[-2]),
                                    tuple(current_stroke[-1]),
                                    color,
                                    thickness)

                    elif gesture == "erase":
                        drawing = False
                        if current_stroke:
                            strokes.append({
                                "color": f"rgb{color}",
                                "width": thickness,
                                "points": current_stroke
                            })
                            current_stroke = []
                        cv2.putText(frame, "BORRAR", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    
                    elif gesture == "clear":
                        drawing = False
                        canvas[:] = 255
                        current_stroke = []
                        strokes = []
                        cv2.putText(frame, "LIMPIAR", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

            cv2.imshow("Camara", frame)
            cv2.imshow("Pizarra", canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                # Guardar trazos actuales
                if current_stroke:
                    strokes.append({
                        "color": f"rgb{color}",
                        "width": thickness,
                        "points": current_stroke
                    })
                enviar_a_django("Dibujo por gestos", strokes)
            elif key == 27:  # ESC
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
