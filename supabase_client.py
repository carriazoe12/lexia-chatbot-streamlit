from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Asegúrate que esta es tu ANON KEY

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error al inicializar Supabase client: {e}")
    supabase = None

def sign_up_user(email, password):
    """Registra un nuevo usuario."""
    if not supabase:
        return None, "Supabase client no inicializado."
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        # response tiene .user, .session, .error
        if response.user and response.user.id: # Éxito si hay un usuario y tiene ID
            return response.user, None
        elif response.error:
            return None, response.error.message
        else: # Caso inesperado
            return None, "Error desconocido durante el registro."
    except Exception as e:
        return None, f"Excepción durante el registro: {str(e)}"

def sign_in_user(email, password):
    """Inicia sesión de un usuario existente."""
    if not supabase:
        return None, "Supabase client no inicializado."
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user and response.user.id:
            return response.user, None
        elif response.error:
            return None, response.error.message
        else: # Caso inesperado
            return None, "Error desconocido durante el inicio de sesión."
    except Exception as e:
        return None, f"Excepción durante el inicio de sesión: {str(e)}"

def sign_out_user():
    """Cierra la sesión del usuario actual."""
    if not supabase:
        return "Supabase client no inicializado."
    try:
        error = supabase.auth.sign_out() # Devuelve None en éxito, o un AuthError
        if error: 
            if hasattr(error, 'message'):
                return error.message
            return "Error desconocido durante el cierre de sesión."
        return None # Éxito
    except Exception as e:
        return f"Excepción durante el cierre de sesión: {str(e)}"

def get_current_user():
    """Obtiene el usuario actualmente autenticado."""
    if not supabase:
        return None, "Supabase client no inicializado."
    try:
        # get_user() intentará refrescar el token si es necesario y está presente.
        # Si no hay sesión válida (token expirado o no presente), response.user será None.
        response = supabase.auth.get_user()
        if response and response.user: # Asegurarse de que response no es None antes de acceder a .user
            return response.user, None
        # Si response.user es None, puede no haber error explícito, simplemente no hay sesión.
        # Devolveremos None, None para indicar "no usuario, no error de operación".
        return None, None
    except Exception as e:
        return None, f"Excepción al obtener usuario: {str(e)}"