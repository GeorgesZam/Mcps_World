import streamlit as st
import os
import json
import importlib.util
import shutil
from pathlib import Path
import openai
import base64

# Configuration de l'application
st.set_page_config(page_title="Local Tools Manager for Azure OpenAI", layout="wide")

# Variables globales
TOOLS_DIR = "tools"
ARCHIVE_DIR = "tools_archive"
TOOL_TEMPLATE = """# Tool Template
def run(model, openai, **kwargs):
    \"\"\"
    Exemple de fonction principale du tool
    
    Args:
        model (str): Nom du modèle Azure OpenAI
        openai: Module OpenAI configuré
        **kwargs: Arguments supplémentaires spécifiques au tool
        
    Returns:
        Résultat de l'exécution du tool
    \"\"\"
    try:
        # Exemple d'appel à l'API OpenAI
        response = openai.ChatCompletion.create(
            engine=model,
            messages=[{"role": "user", "content": "Bonjour, qui es-tu?"}]
        )
        return response.choices[0].message['content']
    except Exception as e:
        return {"error": str(e)}
"""

# Créer les répertoires s'ils n'existent pas
Path(TOOLS_DIR).mkdir(exist_ok=True)
Path(ARCHIVE_DIR).mkdir(exist_ok=True)

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
            # Lire les métadonnées si elles existent
            meta_path = os.path.join(tool_dir, "meta.json")
            metadata = {"name": item, "description": "Aucune description disponible"}
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    metadata.update(json.load(f))
            tools.append(metadata)
    return sorted(tools, key=lambda x: x["name"])

# Fonction pour sauvegarder un tool
def save_tool(tool_name, tool_code, description="", author=""):
    tool_dir = os.path.join(TOOLS_DIR, tool_name)
    os.makedirs(tool_dir, exist_ok=True)
    
    # Sauvegarder le code
    with open(os.path.join(tool_dir, "tool.py"), "w") as f:
        f.write(tool_code)
    
    # Sauvegarder les métadonnées
    metadata = {
        "name": tool_name,
        "description": description,
        "author": author,
        "version": "1.0.0"
    }
    with open(os.path.join(tool_dir, "meta.json"), "w") as f:
        json.dump(metadata, f)
    
    return True

# Fonction pour exporter un tool
def export_tool(tool_name):
    tool_dir = os.path.join(TOOLS_DIR, tool_name)
    if not os.path.exists(tool_dir):
        return None
    
    # Créer un zip du tool
    archive_path = os.path.join(ARCHIVE_DIR, f"{tool_name}.zip")
    shutil.make_archive(os.path.join(ARCHIVE_DIR, tool_name), 'zip', tool_dir)
    
    # Lire le fichier zip
    with open(archive_path, "rb") as f:
        zip_data = f.read()
    
    return zip_data

# Fonction pour importer un tool
def import_tool(uploaded_file):
    try:
        # Extraire le nom du fichier sans extension
        tool_name = os.path.splitext(uploaded_file.name)[0]
        tool_dir = os.path.join(TOOLS_DIR, tool_name)
        
        # Créer un répertoire temporaire
        with tempfile.TemporaryDirectory() as temp_dir:
            # Sauvegarder le fichier uploadé
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Extraire le zip
            shutil.unpack_archive(temp_path, tool_dir)
        
        return True, tool_name
    except Exception as e:
        return False, str(e)

# Initialisation de la session
if 'openai_config' not in st.session_state:
    st.session_state.openai_config = {
        'api_key': '',
        'api_base': '',
        'api_version': '2023-05-15',
        'model': 'gpt-35-turbo'
    }

# Interface principale
st.title("Local Tools Manager for Azure OpenAI")

# Configuration OpenAI
with st.sidebar:
    st.header("Configuration OpenAI Azure")
    st.session_state.openai_config['api_key'] = st.text_input("Clé API", st.session_state.openai_config['api_key'], type="password")
    st.session_state.openai_config['api_base'] = st.text_input("Endpoint", st.session_state.openai_config['api_base'])
    st.session_state.openai_config['api_version'] = st.text_input("Version API", st.session_state.openai_config['api_version'])
    st.session_state.openai_config['model'] = st.text_input("Modèle", st.session_state.openai_config['model'])

# Gestion des tools
tab1, tab2, tab3 = st.tabs(["Utiliser des Tools", "Gérer les Tools", "Créer un Tool"])

with tab1:
    st.header("Utiliser des Tools")
    available_tools = list_tools()
    
    if not available_tools:
        st.warning("Aucun tool disponible. Veuillez en créer ou en importer.")
    else:
        selected_tool = st.selectbox(
            "Choisir un tool", 
            available_tools,
            format_func=lambda x: f"{x['name']} - {x['description']}"
        )
        
        tool_module = load_tool(selected_tool["name"])
        
        if tool_module:
            # Afficher la description détaillée
            st.markdown(f"**Description:** {selected_tool.get('description', 'Aucune description disponible')}")
            if selected_tool.get('author'):
                st.markdown(f"**Auteur:** {selected_tool['author']}")
            if selected_tool.get('version'):
                st.markdown(f"**Version:** {selected_tool['version']}")
            
            # Configurer OpenAI avec les paramètres de l'utilisateur
            openai.api_type = "azure"
            openai.api_key = st.session_state.openai_config['api_key']
            openai.api_base = st.session_state.openai_config['api_base']
            openai.api_version = st.session_state.openai_config['api_version']
            
            # Section pour les paramètres spécifiques au tool
            st.subheader("Paramètres d'exécution")
            user_input = st.text_area("Entrée utilisateur", "Bonjour, qui es-tu?")
            
            # Appel du tool
            if st.button("Exécuter le Tool"):
                try:
                    result = tool_module.run(
                        model=st.session_state.openai_config['model'],
                        openai=openai,
                        user_input=user_input
                    )
                    st.success("Tool exécuté avec succès!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Erreur lors de l'exécution du tool: {str(e)}")

with tab2:
    st.header("Gérer les Tools")
    
    # Sous-onglets pour la gestion
    subtab1, subtab2 = st.tabs(["Exporter un Tool", "Importer un Tool"])
    
    with subtab1:
        st.subheader("Exporter un Tool")
        available_tools = list_tools()
        
        if not available_tools:
            st.warning("Aucun tool disponible pour l'export.")
        else:
            tool_to_export = st.selectbox(
                "Choisir un tool à exporter", 
                available_tools,
                format_func=lambda x: x['name']
            )
            
            if st.button("Exporter le Tool"):
                zip_data = export_tool(tool_to_export["name"])
                if zip_data:
                    # Créer un bouton de téléchargement
                    b64 = base64.b64encode(zip_data).decode()
                    href = f'<a href="data:application/zip;base64,{b64}" download="{tool_to_export["name"]}.zip">Télécharger {tool_to_export["name"]}.zip</a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("Erreur lors de l'export du tool")
    
    with subtab2:
        st.subheader("Importer un Tool")
        uploaded_file = st.file_uploader(
            "Choisir un fichier ZIP de tool", 
            type="zip",
            accept_multiple_files=False
        )
        
        if uploaded_file and st.button("Importer le Tool"):
            success, result = import_tool(uploaded_file)
            if success:
                st.success(f"Tool {result} importé avec succès!")
                st.experimental_rerun()  # Rafraîchir la liste des tools
            else:
                st.error(f"Erreur lors de l'import: {result}")

with tab3:
    st.header("Créer un nouveau Tool")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_tool_name = st.text_input("Nom du tool*")
        new_tool_author = st.text_input("Auteur")
        new_tool_description = st.text_area("Description")
    
    with col2:
        new_tool_code = st.text_area(
            "Code Python*", 
            height=400, 
            value=TOOL_TEMPLATE,
            help="Doit contenir une fonction 'run(model, openai, **kwargs)'"
        )
    
    if st.button("Enregistrer le Tool"):
        if new_tool_name and new_tool_code:
            if save_tool(
                new_tool_name,
                new_tool_code,
                new_tool_description,
                new_tool_author
            ):
                st.success(f"Tool {new_tool_name} créé avec succès!")
                st.experimental_rerun()  # Rafraîchir la liste des tools
            else:
                st.error("Erreur lors de la création du tool")
        else:
            st.warning("Veuillez remplir au moins le nom et le code du tool (champs marqués d'un *)")
