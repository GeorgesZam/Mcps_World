import streamlit as st
import os
import json
import importlib.util
import openai
import glob
from datetime import datetime
from typing import Dict, List, Any
import pytz
import requests

# Configuration
TOOLS_DIR = "tools"
os.makedirs(TOOLS_DIR, exist_ok=True)

# Initialisation de la configuration Azure
def init_azure_config():
    """Charge la config depuis les secrets ou variables d'environnement"""
    return {
        "api_type": "azure",
        "api_key": st.secrets.get("AZURE_OPENAI_KEY", os.getenv("AZURE_OPENAI_KEY")),
        "api_base": st.secrets.get("AZURE_OPENAI_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT")),
        "api_version": "2023-03-15-preview",
        "engine": "gpt-4"
    }

# Modèle de template pour les nouveaux outils
TOOL_TEMPLATE = '''# Schema definition
function_schema = {{
    "type": "object",
    "properties": {{
        "param1": {{
            "type": "number",
            "description": "Description du paramètre 1"
        }},
        "param2": {{
            "type": "string", 
            "description": "Description du paramètre 2"
        }}
    }},
    "required": ["param1", "param2"]
}}

def function_call(param1: float, param2: str) -> Any:
    """Description de votre outil
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Résultat renvoyé
    """
    # Implémentation ici
    return {{"result": param2 * int(param1)}}
'''

# Gestion des outils
class ToolManager:
    @staticmethod
    def list_tools() -> List[str]:
        """Liste tous les outils disponibles"""
        return sorted([f.split('.')[0] for f in os.listdir(TOOLS_DIR) 
                      if f.endswith('.py') and not f.startswith('_')])

    @staticmethod
    def load_tool(tool_name: str) -> Dict[str, Any]:
        """Charge un outil spécifique"""
        try:
            spec = importlib.util.spec_from_file_location(
                tool_name,
                os.path.join(TOOLS_DIR, f"{tool_name}.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return {
                "function": module.function_call,
                "schema": module.function_schema,
                "doc": module.function_call.__doc__
            }
        except Exception as e:
            st.error(f"Erreur de chargement de l'outil {tool_name}: {str(e)}")
            return None

    @staticmethod
    def create_new_tool(tool_name: str, description: str):
        """Crée un nouveau fichier d'outil"""
        try:
            filename = os.path.join(TOOLS_DIR, f"{tool_name}.py")
            with open(filename, 'w') as f:
                f.write(TOOL_TEMPLATE.format(
                    tool_name=tool_name,
                    description=description
                ))
            return True
        except Exception as e:
            st.error(f"Erreur création outil: {str(e)}")
            return False

# Initialisation de l'application
def init_app_state():
    """Initialise l'état de la session"""
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "azure_config" not in st.session_state:
        st.session_state.azure_config = init_azure_config()
    if "selected_tool" not in st.session_state:
        st.session_state.selected_tool = None

# Fonction principale
def main():
    st.set_page_config(
        page_title="MCP Azure Chat",
        page_icon="🤖",
        layout="wide"
    )
    init_app_state()

    # Configure OpenAI
    openai.api_type = st.session_state.azure_config["api_type"]
    openai.api_base = st.session_state.azure_config["api_base"]
    openai.api_version = st.session_state.azure_config["api_version"]
    openai.api_key = st.session_state.azure_config["api_key"]

    # Interface
    st.title("💬 MCP Azure Chat with Tools")
    st.caption(f"Endpoint: {st.session_state.azure_config['api_base']}")

    # Layout
    col1, col2 = st.columns([3, 1])

    with col1:
        # Configuration Azure
        with st.expander("🔧 Configuration Azure", expanded=True):
            new_api_key = st.text_input(
                "Clé API Azure OpenAI",
                value="••••••••••••" if st.session_state.azure_config.get("api_key") else "",
                type="password"
            )
            
            new_api_base = st.text_input(
                "Endpoint Azure OpenAI",
                value=st.session_state.azure_config.get("api_base", "")
            )

            if st.button("Mettre à jour la configuration"):
                if new_api_key and new_api_base:
                    st.session_state.azure_config.update({
                        "api_key": new_api_key,
                        "api_base": new_api_base
                    })
                    st.success("Configuration mise à jour !")
                else:
                    st.error("Veuillez remplir tous les champs")

        # Conversation chat
        for msg in st.session_state.conversation:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "timestamp" in msg:
                    st.caption(f"Envoyé à {msg['timestamp']}")

        # Input utilisateur
        if prompt := st.chat_input("Écrivez votre message..."):
            user_msg = {
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.conversation.append(user_msg)

            with st.chat_message("user"):
                st.write(prompt)
                st.caption(f"À {user_msg['timestamp']}")

            # Appel à Azure OpenAI
            with st.spinner("Attendez la réponse..."):
                try:
                    response = openai.ChatCompletion.create(
                        engine=st.session_state.azure_config["engine"],
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500
                    )

                    assistant_msg = {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                    st.session_state.conversation.append(assistant_msg)

                    with st.chat_message("assistant"):
                        st.write(assistant_msg["content"])
                        st.caption(f"Réponse à {assistant_msg['timestamp']}")

                except openai.error.AuthenticationError:
                    st.error("Erreur d'authentification : vérifiez votre clé API et endpoint")
                except Exception as e:
                    st.error(f"Erreur API OpenAI: {str(e)}")

    with col2:
        # Gestion des outils
        st.header("🛠️ Outils disponibles")
        
        selected_tool = st.selectbox(
            "Choisir un outil",
            [""] + ToolManager.list_tools(),
            index=0
        )

        if selected_tool:
            st.session_state.selected_tool = selected_tool
            tool_data = ToolManager.load_tool(selected_tool)
            
            if tool_data:
                st.subheader(f"Outil: {selected_tool}")
                st.markdown(f"**Description:**\n{tool_data['doc']}")
                st.json(tool_data["schema"])

                # Interface pour exécuter l'outil
                st.subheader("Exécuter l'outil")
                args = {}
                for param, props in tool_data["schema"]["properties"].items():
                    if props["type"] == "number":
                        args[param] = st.number_input(param)
                    else:
                        args[param] = st.text_input(param)

                if st.button("Exécuter"):
                    try:
                        result = tool_data["function"](**args)
                        st.success(f"Résultat: {result}")
                    except Exception as e:
                        st.error(f"Erreur d'exécution: {str(e)}")

        # Création de nouvel outil
        with st.expander("➕ Créer un nouveau outil"):
            new_tool_name = st.text_input("Nom du nouvel outil (sans espaces)")
            new_tool_desc = st.text_area("Description")

            if st.button("Créer l'outil"):
                if new_tool_name and new_tool_desc:
                    if ToolManager.create_new_tool(new_tool_name, new_tool_desc):
                        st.success(f"Outil '{new_tool_name}' créé avec succès!")
                    else:
                        st.error("Erreur lors de la création")
                else:
                    st.warning("Veuillez remplir tous les champs")

if __name__ == "__main__":
    main()
