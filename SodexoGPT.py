import streamlit as st
import os
import json
import importlib.util
import openai
import glob
from datetime import datetime
from typing import Dict, List, Any

# Configuration
TOOLS_DIR = "tools"
os.makedirs(TOOLS_DIR, exist_ok=True)

# Template pour le tool temporel
TIME_TOOL = {
    "name": "get_current_time",
    "description": "Get the current time in specified timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone ID (e.g. Europe/Paris)",
                "default": "local"
            },
            "format": {
                "type": "string",
                "description": "Python strftime format",
                "default": "%Y-%m-%d %H:%M:%S"
            }
        }
    },
    "code": (
        "def get_current_time(timezone='local', format='%Y-%m-%d %H:%M:%S'):\n"
        "    from datetime import datetime\n"
        "    import pytz\n"
        "    if timezone == 'local':\n"
        "        return datetime.now().strftime(format)\n"
        "    tz = pytz.timezone(timezone)\n"
        "    return datetime.now(tz).strftime(format)"
    )
}

# Gestion des outils
class ToolManager:
    @staticmethod
    def list_tools() -> List[str]:
        return [f for f in os.listdir(TOOLS_DIR) if f.endswith('.json')]
    
    @staticmethod
    def load_tool(tool_name: str) -> Dict[str, Any]:
        with open(os.path.join(TOOLS_DIR, tool_name), 'r') as f:
            return json.load(f)
    
    @staticmethod
    def save_tool(tool_data: Dict[str, Any]):
        filename = f"{tool_data['name']}.json"
        with open(os.path.join(TOOLS_DIR, filename), 'w') as f:
            json.dump(tool_data, f, indent=2)
    
    @staticmethod
    def execute_tool(tool_data: Dict[str, Any], **kwargs) -> Any:
        spec = importlib.util.spec_from_loader(tool_data['name'], loader=None)
        module = importlib.util.module_from_spec(spec)
        exec("from datetime import datetime\nimport pytz", module.__dict__)
        exec(tool_data['code'], module.__dict__)
        func_name = tool_data['name']
        return module.__dict__[func_name](**kwargs)

def main():
    st.set_page_config(page_title="Azure AI Tools", layout="wide")
    st.title("🤖 Azure OpenAI Chat with Tools")

    # Initialisation session
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    
    # Configuration Azure
    with st.sidebar:
        st.header("Azure Configuration")
        api_type = st.text_input("API Type", "azure", disabled=True)
        api_key = st.text_input("API Key", type="password")
        api_base = st.text_input("Endpoint", "https://your-resource.openai.azure.com/")
        api_version = st.text_input("API Version", "2023-03-15-preview")
        deployment_name = st.text_input("Deployment", "gpt-4o-mini")
        
        # Gestion des outils
        st.header("🛠️ Tools Manager")
        selected_tool = st.selectbox("Select tool", ToolManager.list_tools())
        
        if selected_tool:
            tool_data = ToolManager.load_tool(selected_tool)
            st.json(tool_data, expanded=False)
            
            # Test du tool
            st.subheader("Test Tool")
            params = {}
            for param, props in tool_data['parameters']['properties'].items():
                params[param] = st.text_input(param, props.get('default', ''))
            
            if st.button("Execute"):
                try:
                    result = ToolManager.execute_tool(tool_data, **params)
                    st.success(f"Result: {result}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Création d'un nouveau tool
        st.header("🆕 Create Tool")
        new_tool = st.text_area("Tool JSON", json.dumps(TIME_TOOL, indent=2))
        
        if st.button("Save New Tool"):
            try:
                tool_data = json.loads(new_tool)
                ToolManager.save_tool(tool_data)
                st.success("Tool saved!")
            except json.JSONDecodeError:
                st.error("Invalid JSON format")

    # Interface principale
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("💬 Conversation")
        
        # Affichage conversation
        for msg in st.session_state.conversation:
            role = "assistant" if msg["role"] != "user" else "user"
            with st.chat_message(role):
                st.markdown(msg["content"])
        
        # Saisie utilisateur
        if prompt := st.chat_input("Type your message..."):
            st.session_state.conversation.append({"role": "user", "content": prompt})
            
            # Appel API
            if api_key:
                try:
                    # Configuration OpenAI
                    openai.api_type = api_type
                    openai.api_base = api_base
                    openai.api_version = api_version
                    openai.api_key = api_key

                    # Appel Azure OpenAI
                    response = openai.ChatCompletion.create(
                        engine=deployment_name,
                        messages=st.session_state.conversation,
                        max_tokens=300
                    )
                    
                    # Traitement réponse
                    if response.choices:
                        assistant_message = response.choices[0].message
                        st.session_state.conversation.append({
                            "role": "assistant",
                            "content": assistant_message.content
                        })
                except Exception as e:
                    st.error(f"API Error: {str(e)}")
    
    with col2:
        st.header("🧰 Available Tools")
        for tool_file in ToolManager.list_tools():
            with st.expander(tool_file.replace('.json', '')):
                tool_data = ToolManager.load_tool(tool_file)
                st.json(tool_data, expanded=False)

if __name__ == "__main__":
    main()
