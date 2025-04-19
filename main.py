import streamlit as st
import os
import json
import openai

# Default configuration
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key-here",
    "api_version": "2023-05-15",
    "model": "gpt-4"
}

# Initialisation de l'état de la session
def init_session_state():
    if 'config' not in st.session_state:
        st.session_state.config = DEFAULT_CONFIG.copy()
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    if 'available_tools' not in st.session_state:
        st.session_state.available_tools = {}

# Fonctions utilitaires partagées
def save_config():
    """Save configuration to file"""
    with open('config.json', 'w') as f:
        json.dump(st.session_state.config, f)

def load_config():
    """Load configuration from file"""
    try:
        with open('config.json', 'r') as f:
            st.session_state.config.update(json.load(f))
    except FileNotFoundError:
        pass

def init_openai():
    """Initialize OpenAI client"""
    openai.api_type = st.session_state.config['api_type']
    openai.api_base = st.session_state.config['api_base']
    openai.api_key = st.session_state.config['api_key']
    openai.api_version = st.session_state.config['api_version']

def ensure_string_content(content: Any) -> str:
    """Ensure the content is a valid string"""
    if content is None:
        return "[No content]"
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float)):
        return str(content)
    if isinstance(content, (dict, list)):
        try:
            return json.dumps(content, ensure_ascii=False)
        except:
            return str(content)
    return str(content)

# Initialisation
init_session_state()
load_config()
init_openai()

# Afficher juste un message d'accueil dans le main
st.title("Application principale")
st.write("Navigation via le menu de gauche")
