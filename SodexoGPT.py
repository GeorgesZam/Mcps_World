import streamlit as st
import os
import json
import importlib.util
import zipfile
import tempfile
from pathlib import Path
import openai
import requests

# Configuration de l'application
st.set_page_config(page_title="Tools Runner for Azure OpenAI", layout="wide")

# Variables globales
TOOLS_DIR = "tools"
TOOLS_STORE_URL = "https://example.com/tools_store"  # Remplacez par votre URL de store

# Créer le répertoire tools s'il n'existe pas
Path(TOOLS_DIR).mkdir(exist_ok=True)

# Fonction utilitaire pour charger un tool
def load_tool(tool_name):
    tool_path = os.path.join(TOOLS_DIR, tool_name, "tool.py")
    if not os.path.exists(tool_path):
        return None
    
    spec = importlib.util.spec_from_file_location(f"{tool_name}.tool", tool_path)
    tool_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool_module)
    return tool_module

# Fonction pour lister les tools disponibles
def list_tools():
    tools = []
    for item in os.listdir(TOOLS_DIR):
        tool_dir = os.path.join(TOOLS_DIR, item)
        if os.path.isdir(tool_dir) and os.path.exists(os.path.join(tool_dir, "tool.py")):
            tools.append(item)
    return tools

# Fonction pour télécharger un tool depuis le store
def download_tool(tool_name):
    try:
        response = requests.get(f"{TOOLS_STORE_URL}/{tool_name}.zip")
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(TOOLS_DIR, tool_name))
            
            os.unlink(tmp_path)
            return True
        return False
    except Exception as e:
        st.error(f"Erreur lors du téléchargement: {str(e)}")
        return False

# Fonction pour créer un nouveau tool
def create_tool(tool_name, tool_code):
    tool_dir = os.path.join(TOOLS_DIR, tool_name)
    os.makedirs(tool_dir, exist_ok=True)
    
    with open(os.path.join(tool_dir, "tool.py"), "w") as f:
        f.write(tool_code)
    
    return True

# Initialisation de la session
if 'openai_config' not in st.session_state:
    st.session_state.openai_config = {
        'api_key': '',
        'api_base': '',
        'api_version': '2023-05-15',
        'model': 'gpt-35-turbo'
    }

# Interface principale
st.title("Tools Runner for Azure OpenAI")

# Configuration OpenAI
with st.expander("Configuration OpenAI Azure"):
    st.session_state.openai_config['api_key'] = st.text_input("Clé API", st.session_state.openai_config['api_key'], type="password")
    st.session_state.openai_config['api_base'] = st.text_input("Endpoint", st.session_state.openai_config['api_base'])
    st.session_state.openai_config['api_version'] = st.text_input("Version API", st.session_state.openai_config['api_version'])
    st.session_state.openai_config['model'] = st.text_input("Modèle", st.session_state.openai_config['model'])

# Gestion des tools
tab1, tab2, tab3 = st.tabs(["Utiliser des Tools", "Télécharger des Tools", "Créer un Tool"])

with tab1:
    st.header("Utiliser des Tools")
    available_tools = list_tools()
    
    if not available_tools:
        st.warning("Aucun tool disponible. Veuillez en télécharger ou en créer.")
    else:
        selected_tool = st.selectbox("Choisir un tool", available_tools)
        tool_module = load_tool(selected_tool)
        
        if tool_module:
            # Configurer OpenAI avec les paramètres de l'utilisateur
            openai.api_type = "azure"
            openai.api_key = st.session_state.openai_config['api_key']
            openai.api_base = st.session_state.openai_config['api_base']
            openai.api_version = st.session_state.openai_config['api_version']
            
            # Appel du tool
            try:
                result = tool_module.run(
                    model=st.session_state.openai_config['model'],
                    openai=openai  # Passer le module openai configuré
                )
                st.success("Tool exécuté avec succès!")
                st.json(result)
            except Exception as e:
                st.error(f"Erreur lors de l'exécution du tool: {str(e)}")

with tab2:
    st.header("Télécharger des Tools")
    st.write("Rechercher et télécharger des tools depuis le store")
    
    # Dans une application réelle, vous devriez récupérer la liste des tools disponibles
    available_in_store = ["text_analyzer", "image_generator", "data_extractor"]  # Exemple
    
    tool_to_download = st.selectbox("Choisir un tool à télécharger", available_in_store)
    
    if st.button("Télécharger"):
        if download_tool(tool_to_download):
            st.success(f"Tool {tool_to_download} téléchargé avec succès!")
        else:
            st.error("Échec du téléchargement")

with tab3:
    st.header("Créer un nouveau Tool")
    
    new_tool_name = st.text_input("Nom du nouveau tool")
    new_tool_code = st.text_area("Code du tool", height=400, value="""# Exemple de structure de tool
def run(model, openai, **kwargs):
    \"\"\"
    Fonction principale du tool
    \"\"\"
    try:
        # Exemple: appel à l'API OpenAI
        response = openai.ChatCompletion.create(
            engine=model,
            messages=[{"role": "user", "content": "Bonjour, qui es-tu?"}]
        )
        return response.choices[0].message['content']
    except Exception as e:
        return {"error": str(e)}
""")
    
    if st.button("Créer le Tool"):
        if new_tool_name and new_tool_code:
            if create_tool(new_tool_name, new_tool_code):
                st.success(f"Tool {new_tool_name} créé avec succès!")
            else:
                st.error("Erreur lors de la création du tool")
        else:
            st.warning("Veuillez fournir un nom et un code pour le tool")
