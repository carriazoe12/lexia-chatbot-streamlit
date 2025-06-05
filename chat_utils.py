from supabase_client import supabase 
from openai import OpenAI 
import google.generativeai as genai 
import os


SYSTEM_PROMPT = "Eres LexIA, asistente jurídico especializado en Derecho español y europeo. Responde con lenguaje claro y, cuando proceda, menciona la norma o jurisprudencia aplicable."
MAX_CONTEXT_MESSAGES = 10

# --- Conversation Management ---

def create_conversation(user_id, title="Nueva Conversación"):
    """Crea una nueva conversación para un usuario."""
    try:
        response = supabase.table("conversations").insert({
            "user_id": user_id,
            "title": title
            # created_at y updated_at tienen valores por defecto
        }).execute()
        if response.data:
            return response.data[0] # Devuelve la conversación creada
        return None
    except Exception as e:
        print(f"Error creando conversación para user_id {user_id}: {str(e)}")
        return None

def get_user_conversations(user_id):
    """Obtiene todas las conversaciones de un usuario, ordenadas por última actualización."""
    try:
        response = supabase.table("conversations") \
            .select("id, title, created_at, updated_at") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error obteniendo conversaciones para user_id {user_id}: {str(e)}")
        return []

def update_conversation_timestamp(conversation_id):
    """Actualiza el campo updated_at de una conversación."""
    try:
        supabase.table("conversations") \
            .update({"updated_at": "now()"}) \
            .eq("id", conversation_id) \
            .execute()
    except Exception as e:
        print(f"Error actualizando timestamp para conversation_id {conversation_id}: {str(e)}")

def delete_conversation_and_messages(conversation_id):
    """Borra una conversación y sus mensajes (ON DELETE CASCADE está configurado)."""
    try:
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        return None # Éxito
    except Exception as e:
        print(f"Error borrando conversación {conversation_id}: {str(e)}")
        return str(e) 

def rename_conversation(conversation_id, new_title):
    """Renombra una conversación."""
    try:
        supabase.table("conversations") \
            .update({"title": new_title, "updated_at": "now()"}) \
            .eq("id", conversation_id) \
            .execute()
        return None
    except Exception as e:
        print(f"Error renombrando conversación {conversation_id}: {str(e)}")
        return str(e)

# --- Message Management ---

def save_message(user_id, conversation_id, role, content): 
    """Guarda un mensaje en una conversación específica."""
    try:
        supabase.table("messages").insert({
            "user_id": user_id, 
            "conversation_id": conversation_id,
            "role": role,
            "content": content
        }).execute()
        # Después de guardar el mensaje, actualiza el timestamp de la conversación
        update_conversation_timestamp(conversation_id)
        return None
    except Exception as e:
        print(f"Error guardando mensaje en conv {conversation_id}: {str(e)}")
        return str(e)

def get_messages_for_conversation(conversation_id):
    """Obtiene todos los mensajes de una conversación específica, ordenados cronológicamente."""
    try:
        response = supabase.table("messages") \
            .select("role, content, created_at") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=False) \
            .execute()
        # Devolvemos solo role y content para mantener la estructura que espera la UI
        return [{"role": msg["role"], "content": msg["content"]} for msg in response.data] if response.data else []
    except Exception as e:
        print(f"Error obteniendo mensajes para conv {conversation_id}: {str(e)}")
        return []


# --- LLM Interaction ---

def _get_openai_response(chat_history_for_llm, api_key):
    client = OpenAI(api_key=api_key)
    messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}]
    start_index = max(0, len(chat_history_for_llm) - MAX_CONTEXT_MESSAGES)
    messages_to_send.extend(chat_history_for_llm[start_index:])
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages_to_send,
            temperature=0.4,
            max_tokens=4096 #8000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error en _get_openai_response: {str(e)}")
        return f"Error con OpenAI: {str(e)}"

def _get_gemini_response(chat_history_for_llm, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=4096 #8000
            )
        )
        gemini_formatted_history = []
        start_index = max(0, len(chat_history_for_llm) - MAX_CONTEXT_MESSAGES)
        relevant_history = chat_history_for_llm[start_index:]
        for msg in relevant_history:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            gemini_formatted_history.append({"role": role, "parts": [msg["content"]]})
        
        if not gemini_formatted_history and not chat_history_for_llm : # Si no hay historial Y el prompt original está vacío (no debería pasar en el flujo normal)
             return "Error: El historial inicial está vacío, no se puede generar respuesta."

        response = model.generate_content(gemini_formatted_history)
        return response.text
    except Exception as e:
        print(f"Error en _get_gemini_response: {str(e)}")
        # ... (manejo de errores de API key) ...
        if "API_KEY_INVALID" in str(e).upper() or "API KEY NOT VALID" in str(e).upper():
             return "Error con Gemini: API Key inválida o no configurada."
        if "PERMISSION_DENIED" in str(e).upper():
            return "Error con Gemini: Permiso denegado."
        return f"Error con Gemini: {str(e)}"

def get_llm_response(chat_history_for_llm, api_key, provider="openai"):
    if provider == "openai":
        return _get_openai_response(chat_history_for_llm, api_key)
    elif provider == "gemini":
        return _get_gemini_response(chat_history_for_llm, api_key)
    else:
        return f"Proveedor LLM '{provider}' no soportado."