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
DEFAULT_MODEL = "gpt-4"

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
        # Création d'un module dynamique
        spec = importlib.util.spec_from_loader(tool_data['name'], loader=None)
        module = importlib.util.module_from_spec(spec)
        
        # Injecte les dépendances requises
        exec("from datetime import datetime\nimport pytz", module.__dict__)
        
        # Exécute le code
        exec(tool_data['code'], module.__dict__)
        
        # Appel la fonction
        func_name = tool_data['name']
        return module.__dict__[func_name](**kwargs)

# Interface utilisateur
def main():
    st.set_page_config(page_title="Azure Tools Chat", layout="wide")
    st.title("🚀 Azure OpenAI with Tools Integration")
    
    # Initialisation session
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    
    # Configuration Azure OpenAI
    with st.sidebar:
        st.header("⚙️ Configuration")
        openai.api_type = "azure"
        openai.api_key = st.text_input("Azure OpenAI Key", type="password")
        openai.api_base = st.text_input("Endpoint", "https://your-resource.openai.azure.com/")
        openai.api_version = st.text_input("API Version", "2023-07-01-preview")
        model_name = st.text_input("Model", DEFAULT_MODEL)
        
        st.divider()
        
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
        st.divider()
        st.header("🆕 Create Tool")
        new_tool = st.text_area("Tool JSON Definition", json.dumps(TIME_TOOL, indent=2), height=300)
        
        if st.button("Save Tool"):
            try:
                tool_data = json.loads(new_tool)
                ToolManager.save_tool(tool_data)
                st.success("Tool saved!")
            except json.JSONDecodeError:
                st.error("Invalid JSON format")
    
    # Interface de chat principale
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("💬 Chat")
        
        # Affichage de la conversation
        for msg in st.session_state.conversation:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("tool"):
                    st.caption(f"Tool used: {msg['tool']}")
        
        # Saisie utilisateur
        if prompt := st.chat_input("Type your message..."):
            st.session_state.conversation.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Si configuré, appel API
            if openai.api_key:
                try:
                    # Préparation des messages
                    messages = [{"role": m["role"], "content": m["content"]} 
                              for m in st.session_state.conversation]
                    
                    # Chargement des tools disponibles
                    tools = []
                    for tool_file in ToolManager.list_tools():
                        tool_data = ToolManager.load_tool(tool_file)
                        tools.append({
                            "type": "function",
                            "function": {
                                "name": tool_data["name"],
                                "description": tool_data["description"],
                                "parameters": tool_data["parameters"]
                            }
                        })
                    
                    # Appel Azure OpenAI
                    response = openai.ChatCompletion.create(
                        engine=model_name,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto"
                    )
                    
                    # Traitement de la réponse
                    assistant_message = response.choices[0].message
                    st.session_state.conversation.append({
                        "role": "assistant",
                        "content": assistant_message.content or ""
                    })
                    
                    # Si tool appelé
                    if tool_calls := assistant_message.tool_calls:
                        for tool_call in tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                tool_data = next(
                                    ToolManager.load_tool(f"{t}.json") 
                                    for t in ToolManager.list_tools() 
                                    if t.startswith(tool_name)
                                )
                                
                                args = json.loads(tool_call.function.arguments)
                                result = ToolManager.execute_tool(tool_data, **args)
                                
                                st.session_state.conversation.append({
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": f"Result: {result}",
                                    "tool": tool_name
                                })
                                
                            except Exception as e:
                                st.error(f"Tool error: {str(e)}")
                
                except openai.error.AuthenticationError:
                    st.error("Invalid Azure OpenAI credentials")
                except Exception as e:
                    st.error(f"API error: {str(e)}")
    
    with col2:
        st.header("🧰 Available Tools")
        for tool_file in ToolManager.list_tools():
            with st.expander(f"🔧 {tool_file.replace('.json', '')}"):
                tool_data = ToolManager.load_tool(tool_file)
                st.caption(tool_data['description'])
                st.json(tool_data['parameters'], expanded=False)

if __name__ == "__main__":
    main()
