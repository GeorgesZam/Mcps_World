import streamlit as st
import os
import importlib.util
import json
import inspect
import openai
from datetime import datetime
import pytz

# Configuration
TOOLS_DIR = "tools"
os.makedirs(TOOLS_DIR, exist_ok=True)

# Template pour nouveaux tools
TIME_TOOL_TEMPLATE = '''{
    "name": "get_current_time",
    "description": "Get the current time in a specific timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone like Europe/Paris, America/New_York etc.",
                "default": "local"
            },
            "format": {
                "type": "string",
                "description": "Time format string",
                "default": "%Y-%m-%d %H:%M:%S"
            }
        }
    },
    "function": "def get_current_time(timezone='local', format='%Y-%m-%d %H:%M:%S'):\n    if timezone == 'local':\n        current_time = datetime.now()\n    else:\n        tz = pytz.timezone(timezone)\n        current_time = datetime.now(tz)\n    return {\n        'time': current_time.strftime(format),\n        'timezone': timezone if timezone != 'local' else 'local time',\n        'timestamp': current_time.timestamp()\n    }"
}'''

# Charger un tool depuis un fichier
def load_tool(tool_path):
    with open(tool_path, 'r') as f:
        tool_data = json.load(f)
    
    # Créer un module dynamique
    module_name = os.path.splitext(os.path.basename(tool_path))[0]
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    tool_module = importlib.util.module_from_spec(spec)
    
    # Ajouter les imports nécessaires
    exec("from datetime import datetime\nimport pytz", tool_module.__dict__)
    
    # Exécuter la fonction dans le module
    exec(tool_data["function"], tool_module.__dict__)
    
    # Stocker le schéma
    tool_module.schema = {
        "name": tool_data["name"],
        "description": tool_data["description"],
        "parameters": tool_data["parameters"]
    }
    
    return tool_module

# Interface Streamlit
def main():
    st.title("🔧 Tools Manager with OpenAI Function Calling")
    
    # Configuration OpenAI
    with st.expander("⚙️ OpenAI Configuration"):
        api_key = st.text_input("API Key", type="password")
        endpoint = st.text_input("Endpoint URL", "https://your-resource.openai.azure.com/")
        api_version = st.text_input("API Version", "2023-07-01-preview")
        deployment = st.text_input("Deployment Name", "gpt-4")
        
        if api_key:
            openai.api_type = "azure"
            openai.api_key = api_key
            openai.api_base = endpoint
            openai.api_version = api_version
    
    # Liste des tools disponibles
    tools = [f for f in os.listdir(TOOLS_DIR) if f.endswith('.py')]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛠️ Available Tools")
        selected_tool = st.selectbox("Choose a tool", tools)
        
        if selected_tool:
            tool_path = os.path.join(TOOLS_DIR, selected_tool)
            tool_module = load_tool(tool_path)
            
            st.json(tool_module.schema, expanded=False)
            
            if "function" in tool_module.__dict__:
                st.code(inspect.getsource(tool_module.__dict__["get_current_time"] if "get_current_time" in tool_module.__dict__ else tool_module.__dict__[list(tool_module.__dict__.keys())[-1]]))
    
    with col2:
        st.subheader("🚀 Execute Tool")
        
        if selected_tool and api_key:
            try:
                tool_module = load_tool(os.path.join(TOOLS_DIR, selected_tool))
                
                # Créer l'interface dynamique basée sur le schéma
                params = tool_module.schema["parameters"]["properties"]
                kwargs = {}
                
                for param, props in params.items():
                    if props.get("type") == "string":
                        kwargs[param] = st.text_input(param, value=props.get("default", ""))
                    # Ajouter d'autres types au besoin...
                
                if st.button("Execute"):
                    func_name = [k for k in tool_module.__dict__.keys() if not k.startswith('_')][0]
                    result = tool_module.__dict__[func_name](**kwargs)
                    
                    st.subheader("Results")
                    st.json(result)
                    
                    # Appel via OpenAI function calling
                    messages = [
                        {"role": "user", "content": f"What's the current time in {kwargs.get('timezone', 'local')}?"}
                    ]
                    
                    response = openai.ChatCompletion.create(
                        engine=deployment,
                        messages=messages,
                        functions=[tool_module.schema],
                        function_call={"name": tool_module.schema["name"]}
                    )
                    
                    st.subheader("OpenAI Function Calling")
                    st.json(response.choices[0].message)
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Créer un nouveau tool
    with st.expander("🆕 Create New Tool"):
        new_tool_name = st.text_input("Tool Filename (must end with .py)")
        new_tool_code = st.text_area("Tool JSON Definition", value=TIME_TOOL_TEMPLATE, height=300)
        
        if st.button("Save Tool"):
            if new_tool_name and new_tool_name.endswith('.py'):
                try:
                    json.loads(new_tool_code)  # Validation JSON
                    
                    with open(os.path.join(TOOLS_DIR, new_tool_name), 'w') as f:
                        f.write(new_tool_code)
                    
                    st.success("Tool saved successfully!")
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
            else:
                st.error("Filename must end with .py")

if __name__ == "__main__":
    main()
