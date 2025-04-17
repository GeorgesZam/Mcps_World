import streamlit as st
import importlib.util, glob, os, sys
import openai
import json

# ---- CONFIG ----
st.set_page_config(page_title="🧑‍💻 Tool-calling Azure/OpenAI, ready!", page_icon="🪄")
st.title("🛠️ Plateforme LLM+Tools, Tool-calling Natif (Azure & OpenAI)")

def load_tools():
    tool_defs = []
    tool_calls = {}
    for file in glob.glob("tools/tool-*.py"):
        tool_name = os.path.splitext(os.path.basename(file))[0][5:]
        spec = importlib.util.spec_from_file_location(f"tools.{tool_name}", file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"tools.{tool_name}"] = mod
        spec.loader.exec_module(mod)
        schema = getattr(mod, "function_schema", None)
        if schema:
            tool_defs.append({
                "name": schema["name"],
                "description": schema.get("description", tool_name),
                "parameters": {
                    k: v for k, v in schema.items() if k in ("type", "properties", "required")
                }
            })
            tool_calls[schema["name"]] = mod.function_call
    return tool_defs, tool_calls

st.sidebar.header("Connexion API")
api_type = st.sidebar.selectbox("Provider",["Azure","OpenAI"],index=0)
if api_type=="Azure":
    openai.api_type = "azure"
    openai.api_base = st.sidebar.text_input("Azure Endpoint",value="https://...")
    openai.api_version = st.sidebar.text_input("Api Version",value="2023-12-01-preview")
    openai.api_key = st.sidebar.text_input("Azure Key",type="password")
    engine = st.sidebar.text_input("Deployment Name", value="gpt-4o")  # Change selon ton déploiement
else:
    openai.api_type = "open_ai"
    openai.api_key = st.sidebar.text_input("OpenAI Key",type="password")
    openai.api_base = None
    openai.api_version = None
    engine = st.sidebar.selectbox("Model",["gpt-4o","gpt-4-1106-preview","gpt-3.5-turbo-1106"],index=0)

if not openai.api_key:
    st.info("Connecte-toi à Azure/OpenAI à gauche !")
    st.stop()

tools, tool_calls = load_tools()

if "history" not in st.session_state: st.session_state.history = []
msg = st.chat_input("Votre demande...")
if msg:
    st.session_state.history.append({"role":"user","content":msg})

msgs = st.session_state.history.copy()
need_tool = True
all_steps = []

while need_tool:
    # ---- Appel complet API Azure/OpenAI ----
    params = {
        "messages": msgs,
        "tools": tools,
        "tool_choice": "auto",
    }
    if api_type=="Azure":
        params["engine"] = engine
    else:
        params["model"] = engine
    resp = openai.ChatCompletion.create(**params)
    m = resp["choices"][0]["message"]
    if m.get("tool_calls"):
        # Appel outil natif
        for call in m["tool_calls"]:
            toolname = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            toolres = tool_calls[toolname](**args)
            all_steps.append({"tool":toolname,"args":args,"output":toolres})
            msgs.append(dict(
                tool_call_id=call["id"],
                role="tool",
                name=toolname,
                content=str(toolres)
            ))
    else:
        need_tool = False
        st.session_state.history.append({"role":"assistant","content":m["content"]})
        st.write("🤖",m["content"])
        if all_steps:
            st.write("🛠️ Détail des outils utilisés :")
            for s in all_steps:
                st.info(f"*{s['tool']}* ({s['args']}) ➔ {s['output']}")
