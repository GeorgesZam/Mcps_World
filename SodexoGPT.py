import streamlit as st
import os
import importlib.util
import openai
from datetime import datetime
import json
from typing import Dict, List, Any

# Configuration
TOOLS_DIR = "tools"
os.makedirs(TOOLS_DIR, exist_ok=True)

# --- Gestion sécurisée des credentials ---
def get_azure_config():
    """Récupère la config Azure depuis les secrets ou variables d'environnement"""
    return {
        "api_key": st.secrets.get("AZURE_OPENAI_KEY", os.getenv("AZURE_OPENAI_KEY")),
        "api_base": st.secrets.get("AZURE_OPENAI_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT")),
        "api_version": "2023-03-15-preview",
        "engine": "gpt-4"
    }

# --- Gestion des outils ---
class ToolManager:
    @staticmethod
    def list_available_tools() -> List[str]:
        """Liste les noms des outils disponibles"""
        return [f[:-3] for f in os.listdir(TOOLS_DIR) if f.endswith('.py')]

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
                "schema": module.function_schema
            }
        except Exception as e:
            st.error(f"Erreur de chargement de l'outil {tool_name}: {str(e)}")
            raise

# --- Interface Streamlit ---
def main():
    st.title("🚀 MCP Client - Azure OpenAI")
    
    # Initialisation de la session
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
        st.session_state.tools_loaded = False

    # Sidebar pour la configuration
    with st.sidebar:
        st.subheader("Configuration Azure")
        config = get_azure_config()
        
        api_key = st.text_input("Clé API", type="password", value=config["api_key"])
        api_base = st.text_input("Endpoint", value=config["api_base"])
        engine = st.selectbox("Modèle", ["gpt-4", "gpt-35-turbo"])

        if st.button("Connecter"):
            openai.api_type = "azure"
            openai.api_version = config["api_version"]
            openai.api_key = api_key
            openai.api_base = api_base
            
            st.session_state.tools_loaded = True
            st.success("Connecté à Azure OpenAI!")

    # Onglets principaux
    tab_chat, tab_tools = st.tabs(["💬 Chat", "🛠️ Outils"])

    with tab_chat:
        # Afficher l'historique de conversation
        for msg in st.session_state.conversation:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "timestamp" in msg:
                    st.caption(msg["timestamp"])

        # Nouveau message utilisateur
        if prompt := st.chat_input("Tapez votre message..."):
            user_msg = {"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%H:%M:%S")}
            st.session_state.conversation.append(user_msg)
            
            with st.chat_message("user"):
                st.write(prompt)
                st.caption(user_msg["timestamp"])

            # Appel à Azure OpenAI
            with st.spinner("Génération en cours..."):
                try:
                    response = openai.ChatCompletion.create(
                        engine=engine,
                        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.conversation],
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
                        st.caption(assistant_msg["timestamp"])
                
                except Exception as e:
                    st.error(f"Erreur de l'API: {str(e)}")

    with tab_tools:
        if st.session_state.get("tools_loaded", False):
            st.write("### Outils disponibles")
            
            selected_tool = st.selectbox(
                "Sélectionnez un outil",
                ToolManager.list_available_tools()
            )
            
            if selected_tool:
                tool_data = ToolManager.load_tool(selected_tool)
                
                st.write(f"**Description:** {tool_data.get('schema', {}).get('description', 'Non spécifiée')}")
                
                # Génération dynamique du formulaire basé sur le schema
                tool_args = {}
                for param, props in tool_data["schema"]["properties"].items():
                    if props["type"] == "number":
                        tool_args[param] = st.number_input(param)
                    else:
                        tool_args[param] = st.text_input(param)
                
                if st.button("Exécuter"):
                    try:
                        result = tool_data["function"](**tool_args)
                        st.json(result)
                    except Exception as e:
                        st.error(f"Erreur d'exécution: {str(e)}")
        else:
            st.warning("Configurez Azure OpenAI dans la sidebar d'abord")

if __name__ == "__main__":
    main()
