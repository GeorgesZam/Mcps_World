import streamlit as st
from datetime import datetime
import time
import os
import json
import openai
from typing import Dict, List, Any, Union
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
import textwrap
import inspect

# -- Authentication setup --
# Définir les identifiants valides (en production, utiliser st.secrets pour plus de sécurité)
VALID_USERS = {
    "admin": "admin123",
    # Ajouter d'autres utilisateurs ici
}

def login():
    """Afficher le formulaire de connexion et valider les informations"""
    st.title("🔒 Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe invalide")

def logout():
    """Déconnecter l'utilisateur"""
    st.session_state.logged_in = False
    if "username" in st.session_state:
        del st.session_state["username"]
    st.experimental_rerun()

# Initialisation de l'état de session pour l'authentification
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Si non authentifié, afficher la page de connexion et stopper l'exécution
if not st.session_state.logged_in:
    login()
    st.stop()

# Une fois connecté, afficher un bouton de déconnexion
st.sidebar.button("Déconnexion", on_click=logout)

# Configuration par défaut
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key-here",
    "api_version": "2023-03-15-preview",
    "model": "gpt-4o-mini"
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

# Utils

def ensure_string_content(content: Any) -> str:
    """Assure que le contenu est une chaîne valide"""
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

# Fonctions de traitement de fichiers

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_excel(file):
    df = pd.read_excel(file)
    return df.to_markdown()

def extract_text_from_word(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_ppt(file):
    prs = pptx.Presentation(file)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
    return "\n".join(texts)

def process_uploaded_file(file):
    ext = file.name.split('.')[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(file)
    if ext in ['xlsx', 'xls']:
        return extract_text_from_excel(file)
    if ext == 'docx':
        return extract_text_from_word(file)
    if ext == 'pptx':
        return extract_text_from_ppt(file)
    if ext == 'txt':
        return file.read().decode('utf-8')
    return f"Format non supporté: {file.name}"

# Gestion des outils

def load_tools():
    tools_dir = 'tools'
    os.makedirs(tools_dir, exist_ok=True)
    st.session_state.available_tools = {}
    for path in glob.glob(os.path.join(tools_dir, 'tool-*.py')):
        try:
            name = os.path.splitext(os.path.basename(path))[0].replace('tool-', '')
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            st.session_state.available_tools[name] = {
                'function': mod.function_call,
                'schema': getattr(mod, 'function_schema', {}),
                'description': getattr(mod, 'description', ""),
                'code': inspect.getsource(mod)
            }
        except Exception as e:
            st.error(f"Erreur chargement outil {path}: {e}")

def get_tools_schema():
    return [
        {"name": n, "description": i['description'], "parameters": i['schema']}
        for n, i in st.session_state.available_tools.items()
    ]

def execute_tool(name: str, args: Dict) -> Dict:
    if name not in st.session_state.available_tools:
        return {"success": False, "content": "Outil non trouvé"}
    try:
        res = st.session_state.available_tools[name]['function'](**args)
        return {"success": True, "content": ensure_string_content(res), "raw": res}
    except Exception as e:
        return {"success": False, "content": f"Erreur exécution {name}: {e}"}

# Intégration OpenAI

def save_config():
    with open('config.json', 'w') as f:
        json.dump(st.session_state.config, f)

def load_config():
    try:
        with open('config.json') as f:
            st.session_state.config.update(json.load(f))
    except FileNotFoundError:
        pass

def init_openai():
    o = st.session_state.config
    openai.api_type = o['api_type']
    openai.api_base = o['api_base']
    openai.api_key = o['api_key']
    openai.api_version = o['api_version']

def chat_with_llm(messages: List[Dict]) -> Any:
    msgs = [{"role": m['role'], "content": ensure_string_content(m.get('content',''))} for m in messages]
    tools = get_tools_schema()
    try:
        resp = openai.ChatCompletion.create(
            engine=st.session_state.config['model'],
            messages=msgs,
            tools=[{"type":"function","function":t} for t in tools] if tools else None,
            tool_choice="auto" if tools else None
        )
        return resp.choices[0].message
    except Exception as e:
        st.error(f"Erreur OpenAI: {e}")
        return None

# Pages UI

def show_config_page():
    st.title("🔧 Configuration API")
    with st.form("config"): 
        c = st.session_state.config
        c['api_type'] = st.selectbox("Type API", ["azure","openai"], index=0 if c['api_type']=='azure' else 1)
        c['api_base'] = st.text_input("Endpoint", value=c['api_base'])
        c['api_key'] = st.text_input("Clé API", type="password", value=c['api_key'])
        c['api_version'] = st.text_input("Version API", value=c['api_version'])
        c['model'] = st.text_input("Modèle", value=c['model'])
        if st.form_submit_button("Enregistrer"):
            save_config(); init_openai(); st.success("Config sauvegardée !")

def show_chat_page():
    st.title("💬 Smart Chat")
    with st.sidebar:
        st.header("📁 File")
        files = st.file_uploader("Upload", type=['pdf','xlsx','xls','docx','pptx','txt'], accept_multiple_files=True)
        for f in files:
            if f.name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files[f.name] = process_uploaded_file(f)
                st.success(f"{f.name} traité !")
        st.header("🛠 Outils")
        if st.button("Recharger outils"): load_tools(); st.success("Outils rechargés !")
        if st.button("Gérer outils"): st.session_state.current_page="Tool Management"; st.rerun()

    for msg in st.session_state.conversation:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    if prompt := st.chat_input("Votre message..."):
        t0=time.time()
        st.session_state.conversation.append({"role":"user","content":prompt})
        msgs = []
        if st.session_state.uploaded_files:
            msgs.append({"role":"system","content":"Fichiers joints:\n" + "\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.uploaded_files.items())})
        msgs += [{"role":m['role'],"content":m['content']} for m in st.session_state.conversation]
        resp = chat_with_llm(msgs)
        if resp:
            # gérer tool_calls si présent
            if hasattr(resp,'tool_calls') and resp.tool_calls:
                tool_msgs = []
                for call in resp.tool_calls:
                    name = call.function.name; args=json.loads(call.function.arguments)
                    out = execute_tool(name,args)
                    tool_msgs.append({"role":"tool","content":out['content']})
                msgs.append({"role":resp.role,"content":resp.content})
                msgs.extend(tool_msgs)
                final = chat_with_llm(msgs)
                content = final.content if final else "Erreur"
            else:
                content = resp.content
        else:
            content = "Erreur réponse"
        dur=time.time()-t0
        st.session_state.conversation.append({"role":"assistant","content":content})
        with st.chat_message("assistant"): st.write(content); st.caption(f"Réponse en {dur:.2f}s")

# Main

def main():
    load_config(); init_openai(); load_tools()
    if 'current_page' not in st.session_state: st.session_state.current_page="Chat"
    st.sidebar.title("Navigation")
    st.session_state.current_page = st.sidebar.radio("Aller à", ["Chat","API Configuration","Tool Management"], index=["Chat","API Configuration","Tool Management"].index(st.session_state.current_page))
    if st.session_state.current_page=="Chat": show_chat_page()
    elif st.session_state.current_page=="API Configuration": show_config_page()
    else: 
        # Importer interface de gestion des outils
        from streamlit import _main as sm;
        st.experimental_rerun()

if __name__ == "__main__":
    main()
