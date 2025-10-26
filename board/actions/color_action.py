import cv2
import numpy as np
import colorsys

# ---------------------- Variables globales ----------------------
current_color = (0, 0, 255)   # Color BGR actual
color_select_mode = False
panel_visible = False
color_intensity = 1.0
prev_intensity = None
INTENSITY_SMOOTHING = 0.08
recent_colors = []

# Panel
PALETTE_ROWS, PALETTE_COLS = 5, 12
RECENT_LIMIT = 6
color_mode = "idle"  # 🔸 puede ser "idle" (espera) o "select" (selección)

# Paleta de colores precalculada (HSV -> BGR)
PRECALCULATED_COLORS = []
for j in range(PALETTE_ROWS):
    for i in range(PALETTE_COLS):
        hue = i / (PALETTE_COLS - 1)
        sat = 1.0
        val = 1.0 - (j / (PALETTE_ROWS - 1)) * 0.7
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        PRECALCULATED_COLORS.append((int(b*255), int(g*255), int(r*255)))

# Escala de grises
PRECALCULATED_GRAYS = [(int(255 - (255 / 11) * i),)*3 for i in range(12)]

# ---------------------- Funciones auxiliares ----------------------
def get_current_color():
    """Devuelve el color actual BGR multiplicado por intensidad."""
    b, g, r = current_color
    return (int(b * color_intensity), int(g * color_intensity), int(r * color_intensity))

def open_color_panel():
    global color_select_mode, panel_visible
    color_select_mode = True
    panel_visible = True

def close_color_panel():
    global color_select_mode, panel_visible
    color_select_mode = False
    panel_visible = False

def adjust_intensity_with_pointer(px, py, frame_width, frame_height):
    """Ajusta la intensidad del color según la posición del puntero."""
    global color_intensity, prev_intensity, recent_colors, current_color

    bar_left = 50
    bar_right = 50 + 320
    if px < bar_left or px > bar_right:
        return

    target_intensity = (px - bar_left) / (bar_right - bar_left)
    target_intensity = np.clip(target_intensity, 0.2, 1.0)

    if prev_intensity is None:
        prev_intensity = target_intensity
    else:
        prev_intensity = prev_intensity*(1-INTENSITY_SMOOTHING) + target_intensity*INTENSITY_SMOOTHING

    color_intensity = prev_intensity

    # Guardar color ajustado en recientes
    entry = (current_color, color_intensity)
    if entry not in recent_colors:
        recent_colors.insert(0, entry)
        if len(recent_colors) > RECENT_LIMIT:
            recent_colors.pop()

# ---------------------- Panel de color avanzado ----------------------
def draw_advanced_color_panel(frame, h, w, pointer_x=None, pointer_y=None, finger_states=None):
    """
    Dibuja el panel de color con modo espera (idle) y modo selección (select).
    """
    global current_color, recent_colors, color_intensity, prev_intensity, panel_visible, color_mode

    if not panel_visible:
        return

    if finger_states is None or len(finger_states) != 5:
        finger_states = [0,0,0,0,0]

    num_fingers = sum(finger_states)

    # 🎨 Modo selección: 1 dedo
    # 🕓 Modo espera: 5 dedos
    if num_fingers == 1:
        color_mode = "select"
    elif num_fingers == 5:
        color_mode = "idle"

    block_size = 22
    block_spacing = 3
    padding = 8
    container_w = 320
    container_h = 285
    panel_x = 50
    panel_y = 95

    # Fondo del panel
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x+container_w, panel_y+container_h), (250,250,250), -1)
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x+container_w, panel_y+container_h), (180,180,180), 2)
    cv2.putText(frame, "Colores", (panel_x+5, panel_y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50,50,50), 2)

    start_x = panel_x + padding
    start_y = panel_y + 40
    MARGIN = 2

    # ---- Paleta principal ----
    for idx, color in enumerate(PRECALCULATED_COLORS):
        row = idx // PALETTE_COLS
        col = idx % PALETTE_COLS
        x1 = start_x + col*(block_size+block_spacing)
        y1 = start_y + row*(block_size+block_spacing)
        x2 = x1 + block_size
        y2 = y1 + block_size

        hover = (
            pointer_x is not None and pointer_y is not None and
            (x1 - MARGIN) <= pointer_x <= (x2 + MARGIN) and
            (y1 - MARGIN) <= pointer_y <= (y2 + MARGIN)
        )

        if hover:
            scale = 1.4
            cx, cy = (x1+x2)//2, (y1+y2)//2
            half = int(block_size*scale//2)
            x1_h, y1_h, x2_h, y2_h = cx-half, cy-half, cx+half, cy+half
            cv2.rectangle(frame, (x1_h, y1_h), (x2_h, y2_h), color, -1)
            cv2.rectangle(frame, (x1_h, y1_h), (x2_h, y2_h), (255,255,255), 2)
            cv2.rectangle(frame, (x1_h-1, y1_h-1), (x2_h+1, y2_h+1), (150,150,150), 1)

            # ✅ Solo cambia color si está en modo selección
            if color_mode == "select" and current_color != color:
                current_color = color
                color_intensity = 1.0
                prev_intensity = 1.0
                entry = (color, color_intensity)
                if entry not in recent_colors:
                    recent_colors.insert(0, entry)
                    if len(recent_colors) > RECENT_LIMIT:
                        recent_colors.pop()
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (200,200,200), 1)

    # ---- Escala de grises ----
    gray_y = start_y + PALETTE_ROWS*(block_size+block_spacing) + 10
    for i, gray in enumerate(PRECALCULATED_GRAYS):
        gx1 = start_x + i*(block_size+block_spacing)
        gy1 = gray_y
        gx2 = gx1 + block_size
        gy2 = gy1 + block_size

        hover = (
            pointer_x is not None and pointer_y is not None and
            (gx1 - MARGIN) <= pointer_x <= (gx2 + MARGIN) and
            (gy1 - MARGIN) <= pointer_y <= (gy2 + MARGIN)
        )

        if hover:
            scale = 1.4
            cx, cy = (gx1+gx2)//2, (gy1+gy2)//2
            half = int(block_size*scale//2)
            gx1_h, gy1_h, gx2_h, gy2_h = cx-half, cy-half, cx+half, cy+half
            cv2.rectangle(frame, (gx1_h, gy1_h), (gx2_h, gy2_h), gray, -1)
            cv2.rectangle(frame, (gx1_h, gy1_h), (gx2_h, gy2_h), (255,255,255), 2)
            cv2.rectangle(frame, (gx1_h-1, gy1_h-1), (gx2_h+1, gy2_h+1), (150,150,150), 1)

            if color_mode == "select" and current_color != gray:
                current_color = gray
                color_intensity = 1.0
                prev_intensity = 1.0
                entry = (gray, color_intensity)
                if entry not in recent_colors:
                    recent_colors.insert(0, entry)
                    if len(recent_colors) > RECENT_LIMIT:
                        recent_colors.pop()
        else:
            cv2.rectangle(frame, (gx1, gy1), (gx2, gy2), gray, -1)
            cv2.rectangle(frame, (gx1, gy1), (gx2, gy2), (180,180,180), 1)

    # ---- Color actual ----
    recent_y = gray_y + block_size + 15
    cx1 = start_x
    cy1 = recent_y
    cx2 = cx1 + block_size*2
    cy2 = cy1 + block_size
    cv2.rectangle(frame, (cx1,cy1), (cx2,cy2), get_current_color(), -1)
    cv2.rectangle(frame, (cx1,cy1), (cx2,cy2), (100,100,100), 2)

    # ---- Colores recientes ----
    for i, (col_base, col_int) in enumerate(recent_colors[:RECENT_LIMIT]):
        center_x = start_x + (3+i)*(block_size+6)+10
        center_y = cy1 + block_size//2
        display_color = (int(col_base[0]*col_int), int(col_base[1]*col_int), int(col_base[2]*col_int))
        radius = block_size//2

        hover = (
            pointer_x is not None and pointer_y is not None and
            (center_x-radius-MARGIN) <= pointer_x <= (center_x+radius+MARGIN) and
            (center_y-radius-MARGIN) <= pointer_y <= (center_y+radius+MARGIN)
        )

        if hover:
            radius_hover = int(radius * 1.3)
            cv2.circle(frame, (center_x, center_y), radius_hover, display_color, -1)
            cv2.circle(frame, (center_x, center_y), radius_hover, (255,255,255), 2)
            cv2.circle(frame, (center_x, center_y), radius_hover+1, (150,150,150), 1)

            if color_mode == "select" and (current_color != col_base or abs(color_intensity - col_int) > 0.01):
                current_color, color_intensity = col_base, col_int
                prev_intensity = color_intensity
        else:
            cv2.circle(frame, (center_x, center_y), radius, display_color, -1)
            cv2.circle(frame, (center_x, center_y), radius, (130,130,130), 1)

    # ---- Barra de intensidad ----
    slider_y = cy2 + 35
    bar_left = start_x
    bar_right = start_x + PALETTE_COLS*(block_size+block_spacing)
    cv2.putText(frame, "Intensidad:", (start_x, slider_y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (70,70,70), 1)
    cv2.line(frame, (bar_left, slider_y), (bar_right, slider_y), (160,160,160), 3)
    knob_x = int(bar_left + color_intensity*(bar_right-bar_left))
    cv2.circle(frame, (knob_x, slider_y), 6, (0,0,0), -1)

    # ✅ Ajustar intensidad solo en modo espera
    if color_mode == "idle" and pointer_x is not None and pointer_y is not None and bar_left <= pointer_x <= bar_right and slider_y-10 <= pointer_y <= slider_y+10:
        adjust_intensity_with_pointer(pointer_x, pointer_y, w, h)