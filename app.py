import streamlit as st
import sys
import os
from pathlib import Path
import logging
import time
import uuid # For unique chat session IDs
from typing import Optional, Dict, List, Any # Added Optional, Dict, List, Any here

# --- Basic Logging Setup ---
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
APP_LOG_FILE = LOG_DIR / "app_osint_system.log"

# Ensure handlers are not added multiple times if script reruns
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(APP_LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
logger = logging.getLogger(__name__)

# --- Environment Setup for Imports ---
try:
    APP_DIR = Path(__file__).resolve().parent
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    SRC_PATH = APP_DIR / "src"
    if str(SRC_PATH.absolute()) not in sys.path:
        sys.path.insert(0, str(SRC_PATH.absolute()))
    
    logger.info(f"Application directory (project root): {APP_DIR}")
    logger.info(f"SRC directory added to path: {SRC_PATH.absolute()}")
    logger.info("App environment setup for imports seems okay.")
except Exception as e:
    logger.error(f"Error during app environment setup: {e}", exc_info=True)
    st.error(f"Critical setup error during path configuration: {e}. Check logs.")
    st.stop()

# --- Import System Components AFTER Path Setup ---
try:
    from osint_cli import initialize_system 
except ImportError as e:
    logger.error(f"Failed to import 'initialize_system' from 'osint_cli.py': {e}", exc_info=True)
    logger.error(f"Current sys.path: {sys.path}")
    st.error(f"Failed to import system components: {e}. Ensure 'osint_cli.py' is in the project root and 'src' directory is correctly structured.")
    st.stop()
except Exception as e:
    logger.error(f"An unexpected error occurred while importing 'initialize_system': {e}", exc_info=True)
    st.error(f"Unexpected error setting up imports: {e}. Check logs.")
    st.stop()

# --- Function to Initialize System Components (Cached) ---
@st.cache_resource
def load_osint_system():
    logger.info("Attempting to initialize OSINT system for Streamlit app...")
    try:
        system_components = initialize_system(kb_path="data") 
        
        if isinstance(system_components, dict) and "chatbot_manager" in system_components:
            chatbot_manager = system_components["chatbot_manager"]
        elif hasattr(system_components, 'process_query'): 
            chatbot_manager = system_components
        else:
            logger.error("Failed to initialize OSINT system: 'chatbot_manager' not found in components or incorrect return type.")
            return None
            
        logger.info("OSINT system initialized successfully for Streamlit app.")
        return chatbot_manager
    except Exception as e:
        logger.error(f"Error during OSINT system initialization in load_osint_system: {e}", exc_info=True)
        return None

# --- Custom CSS for Styling ---
def local_css(file_name: str): # Added type hint
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        logger.info(f"Successfully loaded CSS from {file_name}")
    except FileNotFoundError:
        logger.warning(f"CSS file '{file_name}' not found. Skipping custom styles.")
    except Exception as e:
        logger.error(f"Error loading CSS from {file_name}: {e}", exc_info=True)

# --- Streamlit-Specific Response Formatter (Enhanced for Source Details) ---
def display_formatted_response(response_data: Dict[str, Any]): # Used Dict from typing
    response_text = response_data.get("response", "No response content.")
    response_type = response_data.get("type", "unknown")
    confidence = response_data.get("confidence", 0.0)
    sources = response_data.get("sources", [])

    type_icons = {
        "rag": "🔍", "agent": "🤖", "fallback": "ℹ️",
        "claude_fallback": "🧠", "error": "⚠️", "unknown": "❓",
        "agent_incomplete": "🤖⚠️", "greeting": "👋", "system_message": "⚙️"
    }
    type_icon = type_icons.get(response_type, "❓")

    try:
        confidence_float = float(confidence)
    except (ValueError, TypeError):
        confidence_float = 0.0

    confidence_stars_count = int(round(confidence_float * 5))
    confidence_stars = "★" * confidence_stars_count + "☆" * (5 - confidence_stars_count)

    st.markdown(response_text) 

    if sources and response_type not in ["greeting", "fallback", "claude_fallback", "system_message", "error"]:
        with st.expander("📚 **Sources**", expanded=False):
            for i, source_info in enumerate(sources):
                if isinstance(source_info, dict):
                    title = source_info.get('title', 'Unknown Title')
                    file_identifier = source_info.get('file_path', source_info.get('id', 'N/A')) 
                    display_source_name = source_info.get('name', source_info.get('source_name', 'N/A'))
                    
                    score_val = source_info.get('score', source_info.get('similarity'))
                    score_text = f", Relevance: {score_val:.2f}" if isinstance(score_val, (float, int)) else ""
                    
                    st.markdown(f"**{i+1}. {title}**")
                    st.markdown(f"   <small>Source File/ID: `{file_identifier}` (Display: {display_source_name}{score_text})</small>", unsafe_allow_html=True)
                elif isinstance(source_info, str):
                    st.markdown(f"- {source_info}")
                else:
                    st.markdown(f"- {str(source_info)}") 
    
    if response_type not in ["greeting", "system_message"]:
        st.markdown(f"--- \n<small>{type_icon} Type: {response_type} | Confidence: {confidence_stars} ({confidence_float:.2f})</small>", unsafe_allow_html=True)

# --- Chat Session Management ---
def initialize_session_state():
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "next_chat_idx" not in st.session_state:
        st.session_state.next_chat_idx = 1

    if not st.session_state.chat_sessions or not st.session_state.current_chat_id:
        create_new_chat(activate=True)

def create_new_chat(activate: bool = True) -> str: # Added type hints
    idx = st.session_state.next_chat_idx
    new_chat_id = f"chat_{int(time.time())}_{idx}" # Ensure unique IDs
    st.session_state.chat_sessions[new_chat_id] = {
        "id": new_chat_id,
        "name": f"Chat {idx}", # Initial name
        "messages": [{
            "role": "assistant",
            "content": "New chat started. How can OSINT CyberVision assist you?",
            "data": {
                "response": "New chat started. How can OSINT CyberVision assist you?",
                "type": "greeting", "confidence": 1.0, "sources": []
            }
        }]
    }
    if activate:
        st.session_state.current_chat_id = new_chat_id
    st.session_state.next_chat_idx += 1
    logger.info(f"Created new chat session: {new_chat_id}")
    return new_chat_id

def get_current_chat_messages() -> List[Dict[str, Any]]: # Used List, Dict, Any from typing
    if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chat_sessions:
        return st.session_state.chat_sessions[st.session_state.current_chat_id]["messages"]
    return []

def add_message_to_current_chat(role: str, content: str, data: Optional[Dict[str, Any]] = None): # Used Optional, Dict, Any
    if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chat_sessions:
        message = {"role": role, "content": content}
        if data:
            message["data"] = data # Store the full data structure
        st.session_state.chat_sessions[st.session_state.current_chat_id]["messages"].append(message)

# --- Main Streamlit App Logic ---
def main_ui():
    st.set_page_config(page_title="OSINT CyberVision", layout="wide", initial_sidebar_state="expanded")
    
    css_file_path = os.path.join(Path(__file__).parent, "style.css")
    if os.path.exists(css_file_path):
        local_css(css_file_path)
    else:
        logger.info("'style.css' not found. Using default styles.")

    initialize_session_state() # Initialize session state for chat management
    
    chatbot_manager = load_osint_system()
    if not chatbot_manager:
        st.error("Fatal Error: OSINT Chatbot Manager could not be initialized. Application cannot start. Please check the logs.")
        logger.critical("Chatbot Manager failed to load in main_ui. Stopping app execution path.")
        st.stop()
    
    # --- Sidebar for Chat Management ---
    with st.sidebar:
        st.markdown("<div style='text-align: center;'><img src='https://img.icons8.com/fluency/96/cyber-security.png' alt='CyberVision Logo' width='80'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #00A2FF;'>OSINT CyberVision</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9em;'>Advanced OSINT for Cybersecurity</p>", unsafe_allow_html=True)
        st.markdown("---")

        if st.button("➕ New Chat", key="new_chat_button", use_container_width=True):
            create_new_chat(activate=True)
            if hasattr(chatbot_manager, 'get_chatbot') and hasattr(chatbot_manager.get_chatbot(), 'clear_conversation'):
                 chatbot_manager.get_chatbot().clear_conversation()
            st.rerun()

        st.markdown("---")
        st.markdown("**Chat History**")
        
        sorted_chat_ids = sorted(
            st.session_state.chat_sessions.keys(),
            key=lambda chat_id: int(chat_id.split('_')[1]), 
            reverse=True
        )

        for session_id in sorted_chat_ids:
            session = st.session_state.chat_sessions[session_id]
            button_label = session["name"][:30] + "..." if len(session["name"]) > 30 else session["name"]
            button_key = f"chat_button_{session_id}"
            button_type = "primary" if st.session_state.current_chat_id == session_id else "secondary"
            
            if st.button(button_label, key=button_key, use_container_width=True, type=button_type):
                if st.session_state.current_chat_id != session_id:
                    st.session_state.current_chat_id = session_id
                    logger.info(f"Switched to chat: {session_id}")
                    if hasattr(chatbot_manager, 'get_chatbot') and hasattr(chatbot_manager.get_chatbot(), 'clear_conversation'):
                        chatbot_manager.get_chatbot().clear_conversation()
                        # Re-initialize chatbot context with messages from the selected chat
                        active_chat_messages = get_current_chat_messages()
                        for msg_data in active_chat_messages[:-1]: 
                            if msg_data["role"] == "user":
                                 chatbot_manager.get_chatbot().add_message("user", msg_data["content"])
                            elif msg_data["role"] == "assistant" and "data" in msg_data:
                                 chatbot_manager.get_chatbot().add_message("assistant", msg_data["data"].get("response", ""))
                    st.rerun()

        st.markdown("---")
        if st.button("Clear Current Chat", key="clear_current_chat_button", use_container_width=True):
            if st.session_state.current_chat_id:
                current_chat_session = st.session_state.chat_sessions[st.session_state.current_chat_id]
                current_chat_session["messages"] = [{
                    "role": "assistant",
                    "content": "Chat history cleared. How can I assist you next?",
                    "data": {"response": "Chat history cleared. How can I assist you next?", "type": "system_message", "confidence": 1.0, "sources": []}
                }]
                # Reset chat name using parts from its unique ID
                current_chat_session["name"] = f"Chat {current_chat_session['id'].split('_')[-1]}" 
                logger.info(f"Cleared current chat: {st.session_state.current_chat_id}")
                if hasattr(chatbot_manager, 'get_chatbot') and hasattr(chatbot_manager.get_chatbot(), 'clear_conversation'):
                    chatbot_manager.get_chatbot().clear_conversation()
                st.rerun()
        
        st.markdown("---")
        st.markdown("**How to Use:**")
        st.info("- Type your query in the chat input below.\n- Use '➕ New Chat' or `/clear` (in chat) to reset.\n- Use `/help` for more commands.")
        st.markdown("---")
        st.caption("OSINT Thesis Project")

    # --- Main Chat Area ---
    st.header("🤖 OSINT CyberVision Assistant")
    
    active_chat_messages = get_current_chat_messages()
    for message in active_chat_messages:
        with st.chat_message(message["role"]):
            # "data" key is now consistently expected for assistant messages if they have structured info
            if message["role"] == "assistant" and "data" in message and isinstance(message["data"], dict):
                display_formatted_response(message["data"])
            else:
                st.markdown(message["content"]) # For user messages or simple assistant content

    if prompt := st.chat_input("Ask CyberVision about threats, vulnerabilities, or OSINT tasks..."):
        add_message_to_current_chat("user", prompt)
        
        current_chat_session = st.session_state.chat_sessions[st.session_state.current_chat_id]
        user_messages_count = sum(1 for msg in current_chat_session["messages"] if msg["role"] == "user")
        if user_messages_count == 1 and (current_chat_session["name"].startswith("New Chat") or current_chat_session["name"].startswith("Chat ")):
            current_chat_session["name"] = prompt[:30] + "..." if len(prompt) > 30 else prompt

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response_data = None
            
            try:
                # Special command handling
                if prompt.strip().lower() == "/clear":
                    current_chat_session["messages"] = [{
                        "role": "assistant", "content": "Chat cleared. How can I help you next?",
                        "data": {"response": "Chat cleared. How can I help you next?", "type": "system_message", "confidence": 1.0, "sources": []}
                    }]
                    current_chat_session["name"] = f"Chat {current_chat_session['id'].split('_')[-1]}"
                    if hasattr(chatbot_manager, 'get_chatbot') and hasattr(chatbot_manager.get_chatbot(), 'clear_conversation'):
                        chatbot_manager.get_chatbot().clear_conversation()
                    logger.info(f"Chat history cleared for {st.session_state.current_chat_id} via /clear command.")
                    st.rerun()
                
                elif prompt.strip().lower() == "/help":
                    help_text = """**Available Commands & Usage:**
                    - `/clear`: Clears the current conversation history.
                    - `/help`: Shows this help message.
                    - Use the sidebar to switch between chats or start a new one.
                    \nTo analyze OSINT data, simply type your question or request."""
                    message_placeholder.info(help_text)
                    full_response_data = {
                        "response": help_text, "type": "system_message", 
                        "confidence": 1.0, "sources": []
                    }
                    add_message_to_current_chat("assistant", help_text, data=full_response_data)
                
                # Regular query processing
                else:
                    with st.spinner("🧠 CyberVision is analyzing..."):
                        start_time = time.time()
                        # Pass the current chat's messages (excluding the latest user prompt for context)
                        history_for_processing = get_current_chat_messages()[:-1]
                        response_data = chatbot_manager.process_query(prompt, conversation_history=history_for_processing)
                        
                        processing_time = time.time() - start_time
                        logger.info(f"Query processed in {processing_time:.2f}s. Response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                        full_response_data = response_data
                    
                    message_placeholder.empty() 
                    if full_response_data and isinstance(full_response_data, dict):
                        display_formatted_response(full_response_data)
                        st.caption(f"Processing time: {processing_time:.2f} seconds")
                        add_message_to_current_chat("assistant", full_response_data.get("response", "..."), data=full_response_data)
                    else:
                        err_msg = "Received an invalid response structure from the backend."
                        st.error(err_msg)
                        logger.error(f"Invalid response_data structure: {full_response_data}")
                        add_message_to_current_chat("assistant", err_msg, data={"response": err_msg, "type": "error", "confidence": 0.0, "sources": []})
            
            except Exception as e:
                logger.error(f"Error processing query in Streamlit app: {e}", exc_info=True)
                error_msg = f"An error occurred: {str(e)}"
                message_placeholder.error(error_msg)
                full_response_data = {
                    "response": error_msg, "type": "error", 
                    "confidence": 0.0, "sources": []
                }
                add_message_to_current_chat("assistant", error_msg, data=full_response_data)
        
        if prompt.strip().lower() not in ["/clear", "/help"]: # Avoid rerunning immediately after these commands if they are handled within the loop
            st.rerun()

if __name__ == "__main__":
    main_ui()