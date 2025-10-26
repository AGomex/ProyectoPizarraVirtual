import cv2
import numpy as np
import math

def enhance_stroke(points):
    if len(points) < 5:
        return to_pylist(points)

    # 🔸 Verificar si la figura está cerrada visualmente
    dist = np.linalg.norm(np.array(points[0]) - np.array(points[-1]))
    if dist > 40:  # Si el inicio y el final no se tocan, no procesar como figura
        print("⚪ Trazo abierto, no se detectará figura.")
        return to_pylist(points)

    pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
    min_x, min_y = np.min(pts[:, 0, :], axis=0)
    max_x, max_y = np.max(pts[:, 0, :], axis=0)

    mask = np.zeros((max_y + 10, max_x + 10), dtype=np.uint8)
    cv2.polylines(mask, [pts], isClosed=True, color=255, thickness=3)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return to_pylist(points)

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)

    if area < 100:
        return to_pylist(points)

    epsilon = 0.04 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)

    if len(approx) == 2:
        x1, y1 = approx[0][0]
        x2, y2 = approx[1][0]
        enhanced = interpolate_line(x1, y1, x2, y2)
        print("✨ Línea detectada y corregida.")
        return to_pylist(enhanced)

    elif len(approx) == 3:
        enhanced = [tuple(p[0]) for p in approx] + [tuple(approx[0][0])]
        print("✨ Triángulo detectado y perfeccionado.")
        return to_pylist(enhanced)

    elif len(approx) == 4:
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        enhanced = [tuple(p) for p in box] + [tuple(box[0])]
        print("✨ Rectángulo detectado y perfeccionado.")
        return to_pylist(enhanced)

    else:
        (x, y), radius = cv2.minEnclosingCircle(contour)
        circle_area = math.pi * (radius ** 2)
        if 0.6 < area / circle_area < 1.4:
            enhanced = generate_circle_points(int(x), int(y), int(radius))
            print("✨ Círculo detectado y perfeccionado.")
            return to_pylist(enhanced)

    print("⚪ Figura no reconocida, manteniendo trazo original.")
    return to_pylist(points)


def interpolate_line(x1, y1, x2, y2, num_points=50):
    return [[int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)] for t in np.linspace(0, 1, num_points)]

def generate_circle_points(cx, cy, r, num_points=100):
    return [[int(cx + r * math.cos(a)), int(cy + r * math.sin(a))] for a in np.linspace(0, 2 * math.pi, num_points)]

def to_pylist(points):
    return [[int(x), int(y)] for x, y in points]
