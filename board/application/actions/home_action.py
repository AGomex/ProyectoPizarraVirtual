from django.shortcuts import redirect

def execute_home_action(request=None):
    """
    Acción del botón Home.
    Si se ejecuta desde el backend, simplemente devuelve una señal
    para redirigir al usuario al home.
    """
    return {"redirect": True, "url": "/"}  
