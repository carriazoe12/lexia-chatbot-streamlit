# LexIA - Chatbot Jurídico con Streamlit y Supabase

LexIA es un prototipo de chatbot jurídico especializado en Derecho español y europeo. Permite a los usuarios interactuar con modelos de lenguaje como GPT (OpenAI) o Gemini (Google) utilizando sus propias claves de API. La aplicación gestiona la autenticación de usuarios, múltiples conversaciones y el historial de mensajes mediante Supabase.


## Características Principales

*   Interfaz de chat interactiva construida con Streamlit.
*   Autenticación de usuarios (registro e inicio de sesión) con Supabase Auth.
*   Gestión de múltiples conversaciones por usuario.
*   Los títulos de las conversaciones se generan automáticamente a partir del primer mensaje del usuario.
*   Almacenamiento seguro del historial de conversaciones en Supabase Database, vinculado a cada usuario y conversación.
*   Permite al usuario introducir su propia API Key de OpenAI o Google Gemini.
*   Selección entre proveedores LLM (OpenAI/Gemini) a través de la interfaz.
*   Prompt del sistema fijo para especializar al asistente en Derecho.
*   Memoria conversacional (últimos 5 turnos de usuario/asistente).
*   Opción para borrar conversaciones individuales.

## Estructura del Proyecto

```text
lexia_chatbot/
├── main.py                # Aplicación principal de Streamlit (UI, flujo de chat, gestión de conversaciones)
├── supabase_client.py     # Cliente y funciones de autenticación de Supabase
├── chat_utils.py          # Lógica de LLM (OpenAI, Gemini), gestión de historial, prompt, operaciones de BD para chat
├── requirements.txt       # Dependencias del proyecto
├── .env.example           # Ejemplo de archivo de variables de entorno (NO subir .env)
└── README.md              # Este archivo
```

## Configuración de Supabase (Base de Datos y Auth)

Se utiliza Supabase para la autenticación y el almacenamiento de datos.

### Tablas

1.  **`conversations`**: Almacena las conversaciones de los usuarios.
    *   `id` (uuid, primary key, default: `uuid_generate_v4()`)
    *   `user_id` (uuid, foreign key a `auth.users.id`, ON DELETE CASCADE)
    *   `title` (text)
    *   `created_at` (timestamptz, default: `now()`)
    *   `updated_at` (timestamptz, default: `now()`)

2.  **`messages`**: Almacena los mensajes de cada conversación.
    *   `id` (uuid, primary key, default: `uuid_generate_v4()`)
    *   `user_id` (uuid, foreign key a `auth.users.id`)
    *   `conversation_id` (uuid, foreign key a `conversations.id`, ON DELETE CASCADE)
    *   `role` (text, ej: "user", "assistant")
    *   `content` (text)
    *   `created_at` (timestamp with time zone, default: `now()`)

### Políticas de Seguridad a Nivel de Fila (RLS)

Asegúrate de que RLS está habilitado para las tablas `conversations` y `messages`.

**Para la tabla `conversations`:**

*   **SELECT**:
    *   Target roles: `authenticated`
    *   USING expression: `auth.uid() = user_id`
*   **INSERT**:
    *   Target roles: `authenticated`
    *   WITH CHECK expression: `auth.uid() = user_id`
*   **UPDATE**:
    *   Target roles: `authenticated`
    *   USING expression: `auth.uid() = user_id`
    *   WITH CHECK expression: `auth.uid() = user_id`
*   **DELETE**:
    *   Target roles: `authenticated`
    *   USING expression: `auth.uid() = user_id`

**Para la tabla `messages`:**
*(Estas políticas verifican la propiedad a través de la tabla `conversations`)*

*   **SELECT**:
    *   Target roles: `authenticated`
    *   USING expression:
        ```sql
        (SELECT c.user_id FROM public.conversations c WHERE c.id = messages.conversation_id) = auth.uid()
        ```
*   **INSERT**:
    *   Target roles: `authenticated`
    *   WITH CHECK expression:
        ```sql
        (SELECT c.user_id FROM public.conversations c WHERE c.id = messages.conversation_id) = auth.uid()
        ```
        *(Nota: Para INSERT, la referencia a `messages.conversation_id` en la subconsulta se refiere al valor que se está intentando insertar para `conversation_id` en la nueva fila).*
*   **DELETE**:
    *   Target roles: `authenticated`
    *   USING expression:
        ```sql
        (SELECT c.user_id FROM public.conversations c WHERE c.id = messages.conversation_id) = auth.uid()
        ```

## Pasos para Clonar y Desplegar (Localmente)

1.  **Clonar el repositorio:**
    ```bash
    git clone [URL_DEL_REPOSITORIO_GIT_AQUI]
    cd lexia_chatbot
    ```

2.  **Crear y activar un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    # En Linux/macOS:
    source venv/bin/activate
    # En Windows:
    # venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno:**
    *   Crea un archivo llamado `.env` en la raíz del directorio `lexia_chatbot/` (copia y renombra `.env.example`).
    *   Añade tus credenciales de Supabase (obtenidas de tu proyecto en Supabase: Project Settings -> API):
        ```env
        SUPABASE_URL="TU_SUPABASE_URL"
        SUPABASE_KEY="TU_SUPABASE_ANON_KEY"
        ```
    *   **Importante**: Asegúrate de que la `SUPABASE_KEY` es tu `anon key` pública.

5.  **Ejecutar la aplicación Streamlit:**
    ```bash
    streamlit run main.py
    ```
    La aplicación debería abrirse automáticamente en tu navegador web.

## Instrucciones para Cambiar entre ChatGPT y Gemini

1.  **Inicia Sesión**: Accede a la aplicación con tus credenciales.
2.  **Barra Lateral**: Una vez dentro, localiza la barra lateral.
3.  **Introduce tu API Key**: Pega la API Key del proveedor que deseas usar (OpenAI para ChatGPT, Google para Gemini) en el campo "Tu API Key (OpenAI/Gemini)".
4.  **Selecciona el Proveedor**: En el menú desplegable "Selecciona el proveedor LLM", elige "OpenAI" o "Gemini".
5.  **Chatea**: La aplicación usará el proveedor seleccionado para las respuestas. Puedes cambiar de proveedor en cualquier momento durante la misma sesión, incluso durante una conversación, ya que mantiene la memoria conversacional de los últimos 5 turnos, siempre que tengas la API Key correcta para el nuevo proveedor.

## Gestión de la API Key

La aplicación permite a los usuarios utilizar sus propias claves de API de OpenAI o Google Gemini.

*   **Introducción de la Clave**: Se proporciona un campo de tipo `password` en la barra lateral para que el usuario pegue su clave de API de forma segura (oculta visualmente).
*   **Almacenamiento de la Clave**:
    *   En el contexto de esta aplicación Streamlit, la API Key se almacena temporalmente en el estado de la sesión del servidor (`st.session_state`) durante la sesión activa del usuario en el navegador.
    *   **Importante**: La API Key **no se almacena en la base de datos** ni se persiste de forma permanente en el servidor. Se pierde si el usuario cierra la pestaña del navegador o la sesión de Streamlit expira por completo.
    *   *Nota*: La especificación original de la prueba menciona `localStorage`. En una aplicación web frontend tradicional, `localStorage` sería el método preferido para persistir la clave en el navegador del cliente. Streamlit, al ser una framework donde la lógica principal corre en Python en el servidor, no tiene acceso directo a `localStorage` de la misma manera. `st.session_state` es el mecanismo de almacenamiento temporal por sesión utilizado.
*   **Uso de la Clave en Peticiones**:
    *   Las librerías cliente oficiales de OpenAI (`openai-python`) y Google (`google-generativeai`) se utilizan para interactuar con los LLMs.
    *   Estas librerías gestionan internamente la inclusión segura de la API Key en las cabeceras de las solicitudes HTTP (generalmente como `Authorization: Bearer <API_KEY>` o un encabezado específico del proveedor) a sus respectivos servicios, conforme a sus estándares de autenticación.

## Mejoras Pendientes

*   **Edición de Títulos de Conversación**: Permitir al usuario editar manualmente los títulos de las conversaciones.
*   **Manejo de Errores Avanzado**: Mejorar la retroalimentación al usuario para diferentes tipos de errores (API Key inválida, problemas de red, límites de tokens excedidos).
*   **Límite de Contexto Configurable o Más Dinámico**: Permitir ajustar el número de mensajes enviados como contexto o adaptarlo según la longitud.
*   **Funcionalidad "Olvidé mi Contraseña"**: Implementar la opción de recuperación de contraseña de Supabase Auth.
*   **Paginación o Carga Infinita para Historial de Conversaciones**: Si un usuario tiene muchas conversaciones, la carga inicial podría ser lenta.
*   **Internacionalización (i18n)**: Preparar la UI para múltiples idiomas.

---
