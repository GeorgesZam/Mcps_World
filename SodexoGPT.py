import streamlit as st
import importlib.util
import os
import glob
import sys
import openai
import json
from datetime import datetime
from typing import Any, Dict, List

st.set_page_config(page_title="🧑‍💻 All-in-one LLM Plugin Platform", page_icon="💡")

# -------- 1. Initialisation de l'état de session --------
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.history = []
    st.session_state.tools = {}
    st.session_state.cfg = {}
    st.session_state.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

st.title("🛠️ Plateforme LLM+Tools (OpenAI/Azure tool-calling natif)")

# -------- 2. Configuration API LLM --------
if not st.session_state.initialized:
    st.subheader("Configuration API LLM")
    provider = st.selectbox("Fournisseur LLM", ["Ollama", "OpenAI", "Azure OpenAI"], index=2)
    if provider == "Ollama":
        url = st.text_input("URL Ollama", "http://localhost:11434")
        st.session_state.cfg = {"provider": "ollama", "url": url}
    elif provider == "OpenAI":
        key = st.text_input("OpenAI API Key", type="password")
        st.session_state.cfg = {"provider": "openai", "key": key}
    else:  # Azure
        ep = st.text_input("Azure Endpoint", value="https://...")
        azkey = st.text_input("Azure API Key", type="password")
        model = st.text_input("Nom du modèle Azure (deployment)", value="gpt-4o")
        apiver = st.text_input("API Version", value="2024-02-15-preview")
        st.session_state.cfg = {
            "provider": "azure",
            "endpoint": ep, "key": azkey, "model": model, "apiver": apiver
        }
    if st.button("Valider et démarrer"):
        st.session_state.initialized = True
        st.rerun()
    st.stop()

config = st.session_state.cfg

# -------- 3. Gestion Tools dynamiques --------
TOOLS_FOLDER = "tools"
os.makedirs(TOOLS_FOLDER, exist_ok=True)

def load_tools() -> Dict[str,Any]:
    tool_modules = {}
    for file in glob.glob(os.path.join(TOOLS_FOLDER, "tool-*.py")):
        tool_name = os.path.splitext(os.path.basename(file))[0][5:]
        try:
            spec = importlib.util.spec_from_file_location(f"tools.{tool_name}", file)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"tools.{tool_name}"] = mod
            spec.loader.exec_module(mod)
            schema = getattr(mod, "function_schema", {
                "type": "object", "properties": {}, "required": [],
                "name": tool_name, "description": tool_name
            })
            tool_modules[tool_name] = {
                "function_call": mod.function_call,
                "schema": schema,
                "source": file,
            }
        except Exception as e:
            st.warning(f"Echec import {file} : {e}")
    return tool_modules

if st.button("🔁 Recharger Tools"):
    st.session_state.tools = load_tools()
elif not st.session_state.tools:
    st.session_state.tools = load_tools()
tools = st.session_state.tools

# -------- 4. Sidebar tools: upload/suppr/test --------
st.sidebar.header("🧩 Gestion des Tools")
with st.sidebar.expander("➕ Ajouter nouveau tool"):
    uploaded = st.file_uploader("Charger un script tool-xxx.py", type="py")
    if uploaded:
        bytes_content = uploaded.read()
        path = os.path.join(TOOLS_FOLDER, uploaded.name)
        with open(path, "wb") as f:
            f.write(bytes_content)
        st.success(f"Ajouté : {uploaded.name}")
        st.session_state.tools = load_tools()
        st.experimental_rerun()

with st.sidebar.expander("🗑️ Supprimer/un tool"):
    liste = list(tools.keys())
    if liste:
        choix = st.selectbox("Sélection pour suppression", options=liste)
        if st.button(f"Supprimer {choix}"):
            t = tools[choix]
            os.remove(t["source"])
            del st.session_state.tools[choix]
            st.success(f"{choix} supprimé.")
            st.experimental_rerun()
    else:
        st.info("Aucun tool chargé.")

with st.sidebar.expander("📋 Liste & Test outil"):
    for tname, tinfo in tools.items():
        st.write(f"**{tname}** - {os.path.basename(tinfo['source'])}")
        with st.form(f"test_{tname}"):
            params = {}
            schema = tinfo["schema"]
            for pname, pinf in schema.get("properties", {}).items():
                val = st.text_input(f"{tname} – {pname}: {pinf.get('description','')}")
                params[pname] = val
            if st.form_submit_button("Tester"):
                try:
                    typed_params = {}
                    for k, v in params.items():
                        # auto convert number if possible
                        try:
                            if schema["properties"][k]["type"] == "number":
                                typed_params[k] = float(v)
                            elif schema["properties"][k]["type"] == "integer":
                                typed_params[k] = int(v)
                            else:
                                typed_params[k] = v
                        except Exception:
                            typed_params[k] = v
                    result = tinfo["function_call"](**typed_params)
                    st.success(f"Résultat: {result}")
                except Exception as ex:
                    st.error(str(ex))

# -------- 5. Appel LLM natif tool-calling OpenAI/Azure --------
def call_llm(messages: List[Dict], tools: Dict[str, Any]=None) -> Dict:
    tool_defs = []
    tool_calls = {}
    for tname, tinfo in (tools or {}).items():
        schema = tinfo.get("schema", {})
        tool_defs.append({
            "type": "function",  # ← INDISPENSABLE !
            "name": schema.get("name", tname),
            "description": schema.get("description", tname),
            "parameters": {
                k: v for k, v in schema.items() if k in ("type", "properties", "required")
            }
        })
        tool_calls[schema.get("name",tname)] = tinfo["function_call"]

    config = st.session_state.cfg
    chat = messages.copy()
    all_steps = []

    if config["provider"] in ("openai", "azure"):
        if config["provider"] == "openai":
            openai.api_key = config["key"]
            params = {
                "model": "gpt-4o",
                "messages": chat,
                "tools": tool_defs,
                "tool_choice": "auto"
            }
        else:  # Azure
            openai.api_type = "azure"
            openai.api_version = config["apiver"]
            openai.api_key = config["key"]
            openai.api_base = config["endpoint"]
            params = {
                "engine": config["model"],
                "messages": chat,
                "tools": tool_defs,
                "tool_choice": "auto"
            }
        need_tool = True
        content = ""
        while need_tool:
            resp = openai.ChatCompletion.create(**params)
            m = resp["choices"][0]["message"]
            if m.get("tool_calls"):
                for call in m["tool_calls"]:
                    toolname = call["function"]["name"]
                    args = json.loads(call["function"]["arguments"])
                    tool_res = tool_calls[toolname](**args)
                    all_steps.append({"tool": toolname, "args": args, "output": tool_res})
                    chat.append({
                        "tool_call_id": call["id"],
                        "role": "tool",
                        "name": toolname,
                        "content": str(tool_res)
                    })
                params["messages"] = chat
            else:
                need_tool = False
                content = m["content"]
        return {"role": "assistant", "content": content, "tools_steps": all_steps}
    else:
        # Ollama/demo fallback
        return {"role": "assistant", "content": "(Réponse LLM simulée/demo locale)", "tools_steps": []}

# -------- 6. Affichage chat --------
st.subheader("💬 Conversation")
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("tools_steps"):
            st.write("**Détail outils utilisés :**")
            for stp in m["tools_steps"]:
                st.info(f"> **{stp['tool']}** — Args: `{stp['args']}` — Résultat: `{stp['output']}`")

if prompt := st.chat_input("Votre message..."):
    hmsg = {"role": "user", "content": prompt}
    st.session_state.history.append(hmsg)
    with st.spinner("En réflexion..."):
        reponse = call_llm(st.session_state.history, tools)
        st.session_state.history.append(reponse)
        with st.chat_message("assistant"):
            st.write(reponse["content"])
            if reponse.get("tools_steps"):
                st.write("**Détail outils utilisés :**")
                for stp in reponse["tools_steps"]:
                    st.info(f"> **{stp['tool']}** — Args: `{stp['args']}` — Résultat: `{stp['output']}`")
