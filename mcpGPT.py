import streamlit as st
from datetime import datetime
import time
import os
import json
import openai
from typing import Dict, List, Any
import base64
from io import StringIO
import importlib.util
import glob
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
    st.session_state.pop("username", None)
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
st.session_state.setdefault('config', DEFAULT_CONFIG.copy())
st.session_state.setdefault('conversation', [])
st.session_state.setdefault('uploaded_files', {})
st.session_state.setdefault('available_tools', {})

# Utilitaires

def ensure_string_content(content: Any) -> str:
    if content is None:
        return "[No content]"
    if isinstance(content, (str, int, float)):
        return str(content)
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content)

# Extraction de texte

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    return "".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_excel(file):
    df = pd.read_excel(file)
    return df.to_markdown()

def extract_text_from_word(file):
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_ppt(file):
    prs = pptx.Presentation(file)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
    return "\n".join(texts)

def process_uploaded_file(file):
    ext = file.name.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(file)
    if ext in ('xlsx', 'xls'):
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
    os.makedirs('tools', exist_ok=True)
    st.session_state.available_tools.clear()
    for path in glob.glob('tools/tool-*.py'):
        try:
            name = os.path.basename(path)[5:-3]
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            st.session_state.available_tools[name] = {
                'function': mod.function_call,
                'schema': getattr(mod, 'function_schema', {}),
                'description': getattr(mod, 'description', ''),
                'code': inspect.getsource(mod)
            }
        except Exception as e:
            st.error(f"Erreur chargé outil {path}: {e}")

def get_tools_schema():
    return [
        {"name": n, "description": i['description'], "parameters": i['schema']}
        for n, i in st.session_state.available_tools.items()
    ]

def execute_tool(name: str, args: Dict) -> Dict:
    if name not in st.session_state.available_tools:
        return {"success": False, "content": "Outil non trouvé"}
    try:
        result = st.session_state.available_tools[name]['function'](**args)
        return {"success": True, "content": ensure_string_content(result), "raw": result}
    except Exception as e:
        return {"success": False, "content": f"Erreur exécution {name}: {e}"}

# Configuration OpenAI

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
    cfg = st.session_state.config
    openai.api_type = cfg['api_type']
    openai.api_base = cfg['api_base']
    openai.api_key = cfg['api_key']
    openai.api_version = cfg['api_version']

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
    with st.form("config_form"):
        c = st.session_state.config
        c['api_type'] = st.selectbox("Type API", ["azure","openai"], index=0 if c['api_type']=='azure' else 1)
        c['api_base'] = st.text_input("Endpoint", value=c['api_base'])
        c['api_key'] = st.text_input("Clé API", type="password", value=c['api_key'])
        c['api_version'] = st.text_input("Version API", value=c['api_version'])
        c['model'] = st.text_input("Modèle", value=c['model'])
        if st.form_submit_button("Enregistrer"):
            save_config()
            init_openai()
            st.success("Configuration sauvegardée !")

def show_chat_page():
    st.title("💬 Smart Chat")
    with st.sidebar:
        st.header("📁 Fichiers")
        uploads = st.file_uploader("Uploader fichiers", type=['pdf','xlsx','xls','docx','pptx','txt'], accept_multiple_files=True)
        for f in uploads:
            if f.name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files[f.name] = process_uploaded_file(f)
                st.success(f"{f.name} traité !")
        st.header("🛠 Outils")
        if st.button("Recharger outils"):
            load_tools()
            st.success("Outils rechargés !")
        if st.button("Gérer outils"):
            st.session_state.current_page = "Tool Management"
            st.experimental_rerun()

    for msg in st.session_state.conversation:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Votre message..."):
        start = time.time()
        st.session_state.conversation.append({"role":"user","content":prompt})
        context = []
        if st.session_state.uploaded_files:
            files_txt = "\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.uploaded_files.items())
            context.append({"role":"system","content":f"Fichiers joints:\n{files_txt}"})
        messages = context + st.session_state.conversation
        resp = chat_with_llm(messages)
        if resp:
            if hasattr(resp, 'tool_calls') and resp.tool_calls:
                tool_res = []
                for call in resp.tool_calls:
                    name, args = call.function.name, json.loads(call.function.arguments)
                    out = execute_tool(name, args)
                    tool_res.append({"role":"tool","content":out['content']})
                messages.append({"role":resp.role,"content":resp.content})
                messages.extend(tool_res)
                final = chat_with_llm(messages)
                content = final.content if final else "Erreur"  
            else:
                content = resp.content
        else:
            content = "Erreur réponse"
        timer = time.time() - start
        st.session_state.conversation.append({"role":"assistant","content":content})
        with st.chat_message("assistant"):
            st.write(content)
            st.caption(f"Réponse en {timer:.2f}s")

# Main

def main():
    load_config()
    init_openai()
    load_tools()
    st.sidebar.title("Navigation")
    pages = ["Chat","API Configuration","Tool Management"]
    st.session_state.current_page = st.sidebar.radio("Aller à", pages, index=pages.index(st.session_state.get('current_page','Chat')))
    if st.session_state.current_page == "Chat":
        show_chat_page()
    elif st.session_state.current_page == "API Configuration":
        show_config_page()
    else:
        # Afficher la gestion des outils
        import streamlit as _st; _st.experimental_rerun()

if __name__ == "__main__":
    main()
