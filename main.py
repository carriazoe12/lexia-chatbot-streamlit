import streamlit as st
from supabase_client import (
    supabase, sign_up_user, sign_in_user, sign_out_user
)
from chat_utils import (
    get_llm_response, SYSTEM_PROMPT,
    save_message, get_messages_for_conversation,
    create_conversation, get_user_conversations, 
    delete_conversation_and_messages, rename_conversation
)

# --- Page Configuration ---
st.set_page_config(page_title="LexIA Chatbot", layout="wide", initial_sidebar_state="auto")

# --- Session State Initialization (General Auth) ---
if "user_session" not in st.session_state: st.session_state.user_session = None
if "show_signup_form" not in st.session_state: st.session_state.show_signup_form = False
if "auth_error_message" not in st.session_state: st.session_state.auth_error_message = None
if "auth_info_message" not in st.session_state: st.session_state.auth_info_message = None


# --- Constants ---
DEFAULT_NEW_CONVERSATION_TITLE = "Nueva Conversación" 
MAX_TITLE_LENGTH = 50 

# --- Session State Initialization (Chat & Conversation Specific) ---
def initialize_chat_states():
    st.session_state.conversations_list = []
    st.session_state.active_conversation_id = None
    st.session_state.active_conversation_title = "LexIA"
    st.session_state.messages = [] 
    st.session_state.history_loaded_for_active_conv = False
    st.session_state.api_key = st.session_state.get("api_key", None) 
    st.session_state.selected_provider = st.session_state.get("selected_provider", "openai") 
    st.session_state.conversations_loaded = False

def clear_active_conversation_messages():
    st.session_state.messages = []
    st.session_state.history_loaded_for_active_conv = False

# --- Authentication Callbacks ---
def app_login(email, password):
    user, error = sign_in_user(email, password)
    if user:
        current_api_key = st.session_state.get("api_key", None)
        current_provider = st.session_state.get("selected_provider", "openai")
        st.session_state.user_session = user
        st.session_state.auth_error_message = None
        st.session_state.auth_info_message = "Inicio de sesión exitoso."
        initialize_chat_states() 
        if current_api_key: st.session_state.api_key = current_api_key
        if current_provider: st.session_state.selected_provider = current_provider
        st.rerun()
    else:
        st.session_state.user_session = None
        st.session_state.auth_error_message = f"{error}"
        st.session_state.auth_info_message = None
        st.rerun()

def app_signup(email, password): 
    user, error = sign_up_user(email, password)
    if user:
        st.session_state.auth_info_message = "¡Registro exitoso! Por favor, inicia sesión para continuar."
        st.session_state.auth_error_message = None
        st.session_state.show_signup_form = False
        st.rerun()
    else: 
        st.session_state.user_session = None
        st.session_state.auth_error_message = f"{error}"
        st.session_state.auth_info_message = None
        st.rerun()

def app_logout(): 
    api_key_before_logout = st.session_state.get("api_key", None)
    provider_before_logout = st.session_state.get("selected_provider", "openai")
    error = sign_out_user()
    st.session_state.user_session = None 
    initialize_chat_states() 
    st.session_state.api_key = api_key_before_logout
    st.session_state.selected_provider = provider_before_logout
    if error: 
        st.session_state.auth_error_message = f"Error al cerrar sesión en Supabase: {error}. Sesión local finalizada."
    else:
        st.session_state.auth_info_message = "Has cerrado sesión exitosamente."
    st.session_state.show_signup_form = False
    st.rerun()

# --- UI Rendering ---
if st.session_state.user_session is None:
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        st.title("LexIA")
        st.subheader("Tu Asistente Jurídico")
        st.caption("Por favor, inicia sesión o regístrate para continuar.")
        if st.session_state.auth_error_message:
            st.error(st.session_state.auth_error_message)
            st.session_state.auth_error_message = None
        if st.session_state.auth_info_message:
            st.info(st.session_state.auth_info_message)
            st.session_state.auth_info_message = None
        if st.session_state.show_signup_form:
            st.header("Crear Nueva Cuenta")
            with st.form("signup_form"):
                signup_email = st.text_input("Email", key="signup_email_main")
                signup_password = st.text_input("Contraseña", type="password", key="signup_password_main")
                signup_confirm_password = st.text_input("Confirmar Contraseña", type="password", key="signup_confirm_password_main")
                submitted_signup = st.form_submit_button("Registrarse")
                if submitted_signup:
                    if not signup_email or not signup_password:
                        st.session_state.auth_error_message = "El email y la contraseña no pueden estar vacíos."
                    elif signup_password != signup_confirm_password:
                        st.session_state.auth_error_message = "Las contraseñas no coinciden."
                    else:
                        app_signup(signup_email, signup_password)
                    if st.session_state.auth_error_message: st.rerun()
            if st.button("¿Ya tienes una cuenta? Inicia Sesión"):
                st.session_state.show_signup_form = False
                st.session_state.auth_error_message = None 
                st.session_state.auth_info_message = None
                st.rerun()
        else: # Login form
            st.header("Iniciar Sesión")
            with st.form("login_form"):
                login_email = st.text_input("Email", key="login_email_main")
                login_password = st.text_input("Contraseña", type="password", key="login_password_main")
                submitted_login = st.form_submit_button("Entrar")
                if submitted_login:
                    if not login_email or not login_password:
                        st.session_state.auth_error_message = "El email y la contraseña no pueden estar vacíos."
                    else:
                        app_login(login_email, login_password)
                    if st.session_state.auth_error_message: st.rerun()
            if st.button("¿No tienes cuenta? Regístrate"):
                st.session_state.show_signup_form = True
                st.session_state.auth_error_message = None
                st.session_state.auth_info_message = None
                st.rerun()

else:
    # --- CHAT INTERFACE (USER LOGGED IN) ---
    user_id = st.session_state.user_session.id
    user_email = st.session_state.user_session.email if hasattr(st.session_state.user_session, 'email') else 'Usuario'

    if "conversations_list" not in st.session_state: initialize_chat_states()
    
    # --- Sidebar ---
    st.sidebar.title(f"Bienvenido/a")
    st.sidebar.write(f"{user_email}")
    st.sidebar.markdown("---")

    # Cargar/Gestionar lista de conversaciones
    if not st.session_state.conversations_loaded:
        st.session_state.conversations_list = get_user_conversations(user_id)
        st.session_state.conversations_loaded = True
        if st.session_state.conversations_list: # Si hay conversaciones, seleccionar la primera
            conv = st.session_state.conversations_list[0]
            st.session_state.active_conversation_id = conv["id"]
            st.session_state.active_conversation_title = conv["title"]
            clear_active_conversation_messages()

        st.rerun() # Rerun para que la UI refleje la carga inicial

    if st.sidebar.button("➕ Nueva Conversación", use_container_width=True):
        created_conv = create_conversation(user_id, DEFAULT_NEW_CONVERSATION_TITLE)
        if created_conv:
            st.session_state.conversations_list.insert(0, created_conv)
            st.session_state.active_conversation_id = created_conv["id"]
            st.session_state.active_conversation_title = created_conv["title"]
            clear_active_conversation_messages()
            st.rerun()
        else: st.sidebar.error("No se pudo crear la conversación.")


    st.sidebar.markdown("#### Mis Conversaciones")
    # Si después de cargar y de la opción de "Nueva conversación", no hay ninguna conversación activa
    # Y la lista de conversaciones está vacía, es el momento de indicar que no hay nada o crear una.
    # Este chequeo se hace ANTES de intentar mostrar la lista.
    if not st.session_state.conversations_list and st.session_state.conversations_loaded:
        st.sidebar.caption("No tienes conversaciones. ¡Crea una nueva!")
        # Opcionalmente, podríamos forzar la creación de una aquí si es la política deseada
        # if st.button("Crear mi primera conversación"): 

    for conv_item in st.session_state.conversations_list: # Iterar sobre la lista actual
        conv_id_item = conv_item["id"]
        conv_title_item = conv_item["title"]
        col1, col2 = st.sidebar.columns([6,1])
        with col1: 
            is_active = (conv_id_item == st.session_state.active_conversation_id)
            conv_button_label = f"💬 {conv_title_item}" if not is_active else f"▶️ **{conv_title_item}**"
            if st.button(conv_button_label, key=f"conv_btn_{conv_id_item}", use_container_width=True, type="secondary" if not is_active else "primary"):
                if not is_active:
                    st.session_state.active_conversation_id = conv_id_item
                    st.session_state.active_conversation_title = conv_title_item
                    clear_active_conversation_messages()
                    st.rerun()
        with col2: 
            if st.button("🗑️", key=f"delete_btn_{conv_id_item}", help="Borrar conversación"):
                error_delete_conv = delete_conversation_and_messages(conv_id_item)
                if error_delete_conv: 
                    st.sidebar.error(f"Error al borrar: {error_delete_conv}")
                else:
                    # Actualizar la lista en session_state ANTES de decidir qué hacer después
                    st.session_state.conversations_list = [c for c in st.session_state.conversations_list if c["id"] != conv_id_item]
                    
                    if st.session_state.active_conversation_id == conv_id_item: # Si se borró la activa
                        st.session_state.active_conversation_id = None
                        st.session_state.active_conversation_title = "LexIA" 
                        clear_active_conversation_messages() # Limpia mensajes de la conv borrada
                        
                        # Si quedan otras conversaciones, seleccionar la primera de la lista actualizada
                        if st.session_state.conversations_list: 
                            new_active_conv = st.session_state.conversations_list[0]
                            st.session_state.active_conversation_id = new_active_conv["id"]
                            st.session_state.active_conversation_title = new_active_conv["title"]
                            # No es necesario clear_active_conversation_messages() aquí porque la historia
                            # de la nueva activa se cargará en el próximo ciclo.
                        # else: # No quedan conversaciones. La UI mostrará "No tienes conversaciones."
                              # Ya no creamos una nueva automáticamente aquí.
                    st.rerun() 
    
    st.sidebar.markdown("---")
    # Configuración API Key, Provider, System Prompt, Cerrar Sesión ...
    st.session_state.api_key = st.sidebar.text_input(
        "Tu API Key (OpenAI/Gemini)", type="password",
        value=st.session_state.api_key if st.session_state.api_key else "",
        key="api_key_input_sidebar_multi"
    )
    provider_options = ["OpenAI", "Gemini"]
    current_provider_display = st.session_state.selected_provider.capitalize()
    try: idx = provider_options.index(current_provider_display)
    except ValueError: idx = 0
    selected_provider_display_sb = st.sidebar.selectbox(
        "Selecciona el proveedor LLM", provider_options, index=idx,
        key="provider_select_sidebar_multi"
    )
    if selected_provider_display_sb.lower() != st.session_state.selected_provider:
        st.session_state.selected_provider = selected_provider_display_sb.lower()
    with st.sidebar.expander("Prompt del Sistema (LexIA)"): st.caption(SYSTEM_PROMPT)
    st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar Sesión", key="logout_button_sidebar_multi", use_container_width=True): app_logout()

    # --- Main Chat Area ---
    st.title(st.session_state.active_conversation_title or "LexIA") # Título por defecto si no hay conv activa
    st.caption(f"Usando: {st.session_state.selected_provider.capitalize()}")

    if st.session_state.active_conversation_id and not st.session_state.history_loaded_for_active_conv:
        with st.spinner("Cargando mensajes..."):
            st.session_state.messages = get_messages_for_conversation(st.session_state.active_conversation_id)
            st.session_state.history_loaded_for_active_conv = True
            st.rerun() 

    if st.session_state.active_conversation_id: # Si hay una conversación activa, mostrar sus mensajes
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    elif st.session_state.conversations_loaded and not st.session_state.conversations_list : # Si se cargaron las conversaciones y no hay ninguna
        st.info("No tienes conversaciones. Crea una nueva desde la barra lateral para comenzar.")
    elif not st.session_state.conversations_loaded: 
        st.info("Cargando conversaciones...")
    else: # Hay conversaciones pero ninguna está activa (no debería pasar, pero como fallback...)
        st.info("Por favor, selecciona una conversación de la barra lateral.")


    # Chat input
    if prompt := st.chat_input("Escribe tu consulta jurídica aquí...", key="main_chat_input_multi", disabled=(not st.session_state.active_conversation_id)):
        if not st.session_state.api_key:
            st.warning("Por favor, introduce tu API Key en la barra lateral para chatear.")
            st.stop()
        if not st.session_state.active_conversation_id:
            st.warning("Por favor, selecciona o crea una conversación para chatear.")
            st.stop()

        is_first_message_in_conv = len(st.session_state.messages) == 0 
        conv_needs_autotitle = st.session_state.active_conversation_title == DEFAULT_NEW_CONVERSATION_TITLE
        rename_succeeded_this_turn = False

        if is_first_message_in_conv and conv_needs_autotitle:
            new_title_from_prompt = prompt[:MAX_TITLE_LENGTH] + ("..." if len(prompt) > MAX_TITLE_LENGTH else "")
            error_rename = rename_conversation(st.session_state.active_conversation_id, new_title_from_prompt)
            if error_rename is None: 
                st.session_state.active_conversation_title = new_title_from_prompt
                for conv_idx, c in enumerate(st.session_state.conversations_list):
                    if c["id"] == st.session_state.active_conversation_id:
                        st.session_state.conversations_list[conv_idx]["title"] = new_title_from_prompt
                        break
                rename_succeeded_this_turn = True
            else:
                st.error(f"No se pudo actualizar el título de la conversación: {error_rename}")
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        save_err_user = save_message(user_id, st.session_state.active_conversation_id, "user", prompt)
        if save_err_user: st.error(f"Error guardando tu mensaje: {save_err_user}")

        with st.spinner("LexIA está pensando..."):
            llm_history = st.session_state.messages
            response_content = get_llm_response(llm_history, st.session_state.api_key, st.session_state.selected_provider)
        
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        with st.chat_message("assistant"): st.markdown(response_content)

        save_err_assistant = save_message(user_id, st.session_state.active_conversation_id, "assistant", response_content)
        if save_err_assistant: st.error(f"Error guardando respuesta de LexIA: {save_err_assistant}")
        
        if rename_succeeded_this_turn: # Solo rerun si se renombró con éxito en este turno
            st.rerun()