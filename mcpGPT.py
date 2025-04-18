import streamlit as st
from datetime import datetime
import time
import os
import json
import openai
from typing import Dict, List
import base64
from io import StringIO
import importlib.util
import glob
import ast
import sys
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import pptx

# Configuration initiale
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key-here",
    "api_version": "2023-05-15",
    "model": "gpt-4"
}

# État de l'application
if 'config' not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG.copy()
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'available_tools' not in st.session_state:
    st.session_state.available_tools = {}

# Fonctions utilitaires
def save_config():
    """Sauvegarde la configuration dans un fichier"""
    with open('config.json', 'w') as f:
        json.dump(st.session_state.config, f)

def load_config():
    """Charge la configuration depuis un fichier"""
    try:
        with open('config.json', 'r') as f:
            st.session_state.config.update(json.load(f))
    except FileNotFoundError:
        pass

def init_openai():
    """Initialise le client OpenAI"""
    openai.api_type = st.session_state.config['api_type']
    openai.api_base = st.session_state.config['api_base']
    openai.api_key = st.session_state.config['api_key']
    openai.api_version = st.session_state.config['api_version']

# Fonctions pour les fichiers
def extract_text_from_pdf(file):
    """Extrait le texte d'un PDF"""
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_excel(file):
    """Extrait le texte d'un fichier Excel"""
    df = pd.read_excel(file)
    return df.to_markdown()

def extract_text_from_word(file):
    """Extrait le texte d'un document Word"""
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_ppt(file):
    """Extrait le texte d'une présentation PowerPoint"""
    prs = pptx.Presentation(file)
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def process_uploaded_file(file):
    """Traite un fichier uploadé selon son type"""
    file_ext = file.name.split('.')[-1].lower()
    
    if file_ext == 'pdf':
        return extract_text_from_pdf(file)
    elif file_ext in ['xlsx', 'xls']:
        return extract_text_from_excel(file)
    elif file_ext == 'docx':
        return extract_text_from_word(file)
    elif file_ext == 'pptx':
        return extract_text_from_ppt(file)
    elif file_ext == 'txt':
        return file.read().decode('utf-8')
    else:
        return f"Contenu du fichier {file.name} non extrait (format non supporté)"

# Fonctions pour les outils
def load_tools():
    """Charge les outils depuis le dossier tools/"""
    tools_dir = 'tools'
    os.makedirs(tools_dir, exist_ok=True)
    
    for tool_path in glob.glob(os.path.join(tools_dir, 'tool-*.py')):
        try:
            tool_name = os.path.splitext(os.path.basename(tool_path))[0].replace('tool-', '')
            spec = importlib.util.spec_from_file_location(tool_name, tool_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            st.session_state.available_tools[tool_name] = {
                'function': mod.function_call,
                'schema': getattr(mod, 'function_schema', {})
            }
        except Exception as e:
            st.error(f"Erreur de chargement de l'outil {tool_path}: {str(e)}")

def get_tools_schema():
    """Retourne le schéma des outils pour OpenAI"""
    return [
        {
            "name": name,
            "description": f"Exécute la fonction {name}",
            "parameters": info['schema']
        } for name, info in st.session_state.available_tools.items()
    ]

# Fonction principale de chat
def chat_with_llm(messages: List[Dict]) -> Dict:
    """Envoie les messages à l'API OpenAI"""
    try:
        tools = get_tools_schema()
        response = openai.ChatCompletion.create(
            engine=st.session_state.config['model'],
            messages=messages,
            tools=[{"type": "function", "function": t} for t in tools] if tools else None,
            tool_choice="auto" if tools else None,
        )
        
        return response.choices[0].message
    except Exception as e:
        st.error(f"Erreur OpenAI: {str(e)}")
        return None

# Interface utilisateur
def show_config_page():
    """Affiche la page de configuration"""
    st.title("🔧 Configuration de l'API")
    
    with st.form("api_config"):
        st.session_state.config['api_type'] = st.selectbox(
            "Type d'API",
            ["azure", "openai"],
            index=0 if st.session_state.config['api_type'] == "azure" else 1
        )
        
        st.session_state.config['api_base'] = st.text_input(
            "Endpoint API",
            value=st.session_state.config['api_base']
        )
        
        st.session_state.config['api_key'] = st.text_input(
            "Clé API",
            type="password",
            value=st.session_state.config['api_key']
        )
        
        st.session_state.config['api_version'] = st.text_input(
            "Version API",
            value=st.session_state.config['api_version']
        )
        
        st.session_state.config['model'] = st.text_input(
            "Modèle",
            value=st.session_state.config['model']
        )
        
        if st.form_submit_button("Sauvegarder la configuration"):
            save_config()
            init_openai()
            st.success("Configuration sauvegardée!")

def show_chat_page():
    """Affiche la page de chat principale"""
    st.title("💬 Chat Intelligent")
    
    # Sidebar pour les fichiers et outils
    with st.sidebar:
        st.header("📁 Fichiers")
        uploaded_files = st.file_uploader(
            "Ajouter des fichiers",
            type=['pdf', 'xlsx', 'xls', 'docx', 'pptx', 'txt'],
            accept_multiple_files=True
        )
        
        for file in uploaded_files:
            if file.name not in st.session_state.uploaded_files:
                content = process_uploaded_file(file)
                st.session_state.uploaded_files[file.name] = content
                st.success(f"Fichier {file.name} traité!")
        
        st.header("🛠 Outils")
        if st.button("Recharger les outils"):
            load_tools()
            st.success("Outils rechargés!")
        
        st.write("Outils disponibles:")
        for tool_name in st.session_state.available_tools:
            st.write(f"- {tool_name}")
    
    # Afficher l'historique
    for msg in st.session_state.conversation:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("timestamp"):
                st.caption(f"À {msg['timestamp']}")
    
    # Gestion des messages
    if prompt := st.chat_input("Votre message..."):
        now = datetime.now().strftime("%H:%M:%S")
        
        # Ajouter le message utilisateur
        user_msg = {"role": "user", "content": prompt, "timestamp": now}
        st.session_state.conversation.append(user_msg)
        
        with st.chat_message("user"):
            st.write(prompt)
            st.caption(f"À {now}")
        
        with st.spinner("Réflexion..."):
            start_time = time.time()
            
            # Préparer le contexte avec les fichiers uploadés
            context = []
            if st.session_state.uploaded_files:
                context.append({
                    "role": "system",
                    "content": "Fichiers joints:\n" + "\n\n".join(
                        f"=== {name} ===\n{content}" 
                        for name, content in st.session_state.uploaded_files.items()
                    )
                })
            
            # Ajouter l'historique de conversation
            messages = context + [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in st.session_state.conversation
                if msg["role"] in ["user", "assistant", "system"]
            ]
            
            # Premier appel au LLM
            response = chat_with_llm(messages)
            
            if response:
                # Gestion des outils
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # Exécuter les outils
                    tool_responses = []
                    for call in response.tool_calls:
                        tool_name = call.function.name
                        if tool_name in st.session_state.available_tools:
                            try:
                                args = json.loads(call.function.arguments)
                                result = st.session_state.available_tools[tool_name]['function'](**args)
                                tool_responses.append({
                                    "role": "tool",
                                    "content": str(result),
                                    "name": tool_name,
                                    "tool_call_id": call.id
                                })
                            except Exception as e:
                                tool_responses.append({
                                    "role": "tool",
                                    "content": f"Erreur: {str(e)}",
                                    "name": tool_name,
                                    "tool_call_id": call.id
                                })
                    
                    # Ajouter les réponses des outils
                    messages.append({
                        "role": response.role,
                        "content": response.content,
                        "tool_calls": response.tool_calls
                    })
                    messages.extend(tool_responses)
                    
                    # Deuxième appel avec les résultats des outils
                    final_response = chat_with_llm(messages)
                    
                    if final_response:
                        assistant_msg = {
                            "role": "assistant",
                            "content": final_response.content,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                    else:
                        assistant_msg = {
                            "role": "assistant",
                            "content": "Erreur lors de la réponse finale",
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                else:
                    # Réponse simple sans outils
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.content,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                
                # Ajouter à la conversation
                st.session_state.conversation.append(assistant_msg)
                
                # Afficher la réponse
                with st.chat_message("assistant"):
                    st.write(assistant_msg["content"])
                    st.caption(f"Réponse en {time.time()-start_time:.2f}s à {assistant_msg['timestamp']}")

# Page principale
def main():
    """Gestion des pages de l'application"""
    load_config()
    init_openai()
    load_tools()
    
    pages = {
        "Chat": show_chat_page,
        "Configuration": show_config_page
    }
    
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Aller à", list(pages.keys()))
    
    # Afficher la page sélectionnée
    pages[page]()

if __name__ == "__main__":
    main()
