import time

# Lista de colores posibles (BGR para OpenCV)
COLORS = [
    (0, 0, 0),        # Negro
    (0, 0, 255),      # Rojo
    (0, 255, 0),      # Verde
    (255, 0, 0),      # Azul
    (0, 255, 255),    # Amarillo
    (255, 0, 255),    # Magenta
    (255, 255, 0),    # Cian
]

# Nombres legibles para mostrar en pantalla
COLOR_NAMES = [
    "Negro",
    "Rojo",
    "Verde",
    "Azul",
    "Amarillo",
    "Magenta",
    "Cian",
]

# Variables de estado
current_color_index = 0
color_select_mode = False
last_color_change_time = 0
ROTATION_SECONDS = 1.5  # segundos entre cambios automáticos


def start_color_selection():
    """
    Activa el modo de selección de color (rotativo).
    """
    global color_select_mode, last_color_change_time
    color_select_mode = True
    last_color_change_time = time.time()
    print("🎨 Entrando en modo selección de color...")


def stop_color_selection():
    """
    Sale del modo de selección de color (mantiene el color actual).
    """
    global color_select_mode
    color_select_mode = False
    print("✅ Color final seleccionado:", COLORS[current_color_index])


def update_color_rotation():
    """
    Si estamos en modo de selección, cambia el color cada ROTATION_SECONDS.
    Devuelve el color actual (BGR).
    """
    global last_color_change_time, current_color_index

    if not color_select_mode:
        return COLORS[current_color_index]

    now = time.time()
    if now - last_color_change_time > ROTATION_SECONDS:
        current_color_index = (current_color_index + 1) % len(COLORS)
        last_color_change_time = now
        print(f"🎨 Color cambiado automáticamente a: {COLORS[current_color_index]} ({get_current_color_name()})")

    return COLORS[current_color_index]


def get_current_color():
    """Devuelve el color actual (B, G, R)."""
    return COLORS[current_color_index]


def get_current_color_name():
    """Devuelve el nombre legible del color actual."""
    return COLOR_NAMES[current_color_index]
