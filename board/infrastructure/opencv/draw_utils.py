import cv2
import numpy as np
from board.application.use_cases.ui_config import BUTTONS
import os
from django.conf import settings

def draw_grid_background(h, w, spacing=20):
    """Dibuja una cuadrícula suave como fondo."""
    bg = np.ones((h, w, 3), np.uint8) * 255
    color_line = (220, 220, 220)
    for y in range(0, h, spacing):
        cv2.line(bg, (0, y), (w, y), color_line, 1)
    for x in range(0, w, spacing):
        cv2.line(bg, (x, 0), (x, h), color_line, 1)
    return bg

def draw_toolbar(frame, h, w, active_index=None, current_color=(0, 0, 0)):
    """Dibuja la barra de herramientas con íconos centrados."""
    toolbar_height = int(h * 0.18)
    section_width = w // len(BUTTONS)

    for i, (icon_file, action_name) in enumerate(BUTTONS):
        # Zona del botón
        x1 = i * section_width
        x2 = x1 + section_width
        color_box = (215, 235, 255) if i == active_index else (245, 245, 245)
        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), color_box, -1)
        cv2.rectangle(frame, (x1, 0), (x2, toolbar_height), (180, 180, 180), 2)

        center_x = x1 + section_width // 2
        center_y = toolbar_height // 2

        # Si es el botón de color, dibujar recuadro
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

        # Ruta del icono
        icon_path = os.path.join(settings.STATICFILES_DIRS[0], "board", "icons", icon_file)
        if not os.path.exists(icon_path):
            cv2.putText(frame, "?", (center_x - 10, center_y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            continue

        # Leer icono
        icon = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
        if icon is None:
            continue

        # Redimensionar
        icon_size = 45
        icon = cv2.resize(icon, (icon_size, icon_size))
        x_offset = center_x - icon_size // 2
        y_offset = center_y - icon_size // 2

        # Dibujar con transparencia
        if icon.shape[2] == 4:
            alpha = icon[:, :, 3] / 255.0
            for c in range(3):
                frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size, c] = (
                    alpha * icon[:, :, c] +
                    (1 - alpha) * frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size, c]
                )
        else:
            frame[y_offset:y_offset + icon_size, x_offset:x_offset + icon_size] = icon