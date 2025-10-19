import random

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

current_color_index = 0

def execute_color_action(current_color):
    """
    Cambia al siguiente color de la lista.
    Si se llega al final, vuelve al primero.
    """
    global current_color_index
    current_color_index = (current_color_index + 1) % len(COLORS)
    new_color = COLORS[current_color_index]
    print(f"🎨 Nuevo color: {new_color}")
    return new_color
