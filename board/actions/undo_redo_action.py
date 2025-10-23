import time
from board.actions import save_action

# Control de tiempo para evitar múltiples activaciones seguidas
_last_action_time = 0
_cooldown = 2.0  # segundos

# Pilas para deshacer/rehacer
undo_stack = []
redo_stack = []

def can_perform():
    """Evita ejecuciones repetidas muy rápidas."""
    global _last_action_time
    now = time.time()
    if now - _last_action_time < _cooldown:
        return False
    _last_action_time = now
    return True

def register_stroke(stroke):
    """Registrar un nuevo trazo en el historial (para permitir deshacer)."""
    undo_stack.append(stroke.copy())
    redo_stack.clear()  # limpiar rehacer cada vez que se dibuja algo nuevo

def undo_last_stroke():
    """Deshacer el trazo más reciente."""
    if not can_perform():
        return False

    if not save_action.current_strokes:
        print("[UNDO] No hay trazos para deshacer.")
        return False

    stroke = save_action.current_strokes.pop()  # quitar último trazo
    redo_stack.append(stroke)
    print(f"[UNDO] Deshecho trazo, quedan {len(save_action.current_strokes)} trazos activos.")
    return True

def redo_last_stroke():
    """Rehacer el trazo más recientemente deshecho."""
    if not can_perform():
        return False

    if not redo_stack:
        print("[REDO] No hay trazos para rehacer.")
        return False

    stroke = redo_stack.pop()
    save_action.current_strokes.append(stroke)
    print(f"[REDO] Rehecho trazo, total {len(save_action.current_strokes)} trazos activos.")
    return True

def reset_history():
    """Vaciar las pilas al iniciar o guardar un dibujo."""
    undo_stack.clear()
    redo_stack.clear()
