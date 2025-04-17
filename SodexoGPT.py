import streamlit as st
import importlib.util
import os
import glob
import sys
from datetime import datetime
from typing import Any, Dict, List
import openai

# --- CONFIG SECTION ---
st.set_page_config(page_title="🧑‍💻 All-in-one LLM Plugin Platform", page_icon="💡")

# ---- 1. CONFIGURATION INIT (API KEY & MODEL CHOICE) ----
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.history = []
    st.session_state.tools = {}
    st.session_state.cfg = {}
    st.session_state.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

st.title("🛠️ Plateforme LLM+Tools (All-In-One, 100% Streamlit)")

if not st.session_state.initialized:
    st.subheader("Configuration API LLM")
    provider = st.selectbox("Fournisseur LLM", ["Ollama", "OpenAI", "Azure OpenAI"], index=2)
    if provider == "Ollama":
        url = st.text_input("URL Ollama", "http://localhost:11434")
        st.session_state.cfg = {"provider": "ollama", "url": url}
    elif provider == "OpenAI":
        key = st.text_input("OpenAI API Key", type="password")
        st.session_state.cfg = {"provider": "openai", "key": key}
    else:
        ep = st.text_input("Azure Endpoint", value="https://...")
        azkey = st.text_input("Azure API Key", type="password")
        model = st.text_input("Nom du modèle Azure", value="gpt-4o-mini")
        apiver = st.text_input("API Version", value="2023-03-15-preview")
        st.session_state.cfg = {
            "provider": "azure",
            "endpoint": ep, "key": azkey, "model": model, "apiver": apiver
        }
if st.button("Valider et démarrer"):
    st.session_state.initialized = True
    st.experimental_rerun()
else:
    st.stop()
config = st.session_state.cfg

# ---- 2. LOADING TOOLS FROM tools/ ----
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
            tool_modules[tool_name] = {
                "function_call": mod.function_call,
                "schema": getattr(mod, "function_schema", {
                    "type": "object", "properties": {}, "required": []
                }),
                "source": file,
            }
        except Exception as e:
            st.warning(f"Echec import {file} : {e}")
    return tool_modules

if st.button("🔁 Recharger Tools"):
    st.session_state.tools = load_tools()
else:
    if not st.session_state.tools:
        st.session_state.tools = load_tools()

tools = st.session_state.tools

# --- 3. Tools management UI
st.sidebar.header("🧩 Gestion des Tools")
st.sidebar.markdown("Placez vos scripts Python dans `tools/tool-*.py`. Le nom du module sera utilisé comme nom d’outil.")

with st.sidebar.expander("➕ Ajouter nouveau tool"):
    uploaded = st.file_uploader("Charger un script tool-xxx.py", type="py")
    if uploaded:
        bytes_content = uploaded.read()
        path = os.path.join(TOOLS_FOLDER, uploaded.name)
        with open(path, "wb") as f:
            f.write(bytes_content)
        st.success(f"Ajouté : {uploaded.name}")
        st.session_state.tools = load_tools()

with st.sidebar.expander("🗑️ Supprimer/un tool"):
    choix = st.selectbox("Sélection pour suppression", options=list(tools.keys()))
    if st.button(f"Supprimer {choix}"):
        t = tools[choix]
        os.remove(t["source"])
        del st.session_state.tools[choix]
        st.success(f"{choix} supprimé.")
        st.experimental_rerun()

with st.sidebar.expander("📋 Liste & Test outil"):
    for tname, tinfo in tools.items():
        st.write(f"**{tname}** - {os.path.basename(tinfo['source'])}")
        with st.form(f"test_{tname}"):
            params = {}
            for pname, pinf in tinfo["schema"].get("properties", {}).items():
                val = st.text_input(f"{tname} – {pname}: {pinf.get('description','')}")
                params[pname] = val
            if st.form_submit_button("Tester"):
                try:
                    result = tinfo["function_call"](**{k: float(v) if v.replace('.','',1).isdigit() else v for k,v in params.items()})
                    st.success(f"Résultat: {result}")
                except Exception as ex:
                    st.error(str(ex))

# --- 4. Chat + LLM Section

# Préparer le LLM API client selon le provider choisi
def call_llm(messages: List[Dict], tools: Dict[str,Any]=None) -> Dict:
    # Pour démo : le LLM propose "appelle tool-X si question correspond"
    # Ici, on le simule avec quelques if, mais tu peux brancher OpenAI/others plus tard
    last = messages[-1]["content"].lower()
    # Simulation : si question contient "additionne", "somme", "heure", etc.
    if "heure" in last and "time" in tools:
        rep = tools["time"]["function_call"]()
        return {"role":"assistant","content":f"[TOOL time] {rep}","tools_used":["time"]}
    if ("additionne" in last or "somme" in last or "add" in last) and "add" in tools:
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", last)
        n1, n2 = map(float, nums[:2]) if len(nums)>=2 else (0,0)
        rep = tools["add"]["function_call"](n1, n2)
        return {"role":"assistant","content":f"[TOOL add] {n1} + {n2} = {rep}","tools_used":["add"]}
    # Sinon réponse LLM API vraie si OpenAI/Azure sélectionné
    if config["provider"]=="openai":
        openai.api_key = config["key"]
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        return {"role":"assistant","content": resp["choices"][0]["message"]["content"],"tools_used":[]}
    elif config["provider"]=="azure":
        openai.api_type = "azure"
        openai.api_version = config["apiver"]
        openai.api_key = config["key"]
        openai.api_base = config["endpoint"]
        resp = openai.ChatCompletion.create(
            engine=config["model"],
            messages=messages
        )
        return {"role":"assistant","content": resp["choices"][0]["message"]["content"],"tools_used":[]}
    return {"role":"assistant", "content":"(Réponse LLM simulée - demo locale)", "tools_used":[]}

st.subheader("💬 Conversation")
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.write(m["content"])

if prompt := st.chat_input("Votre message..."):
    hmsg = {"role":"user", "content":prompt}
    st.session_state.history.append(hmsg)
    with st.spinner("En réflexion..."):
        reponse = call_llm(st.session_state.history, tools)
        st.session_state.history.append(reponse)
        with st.chat_message("assistant"):
            st.write(reponse["content"])
            if reponse.get("tools_used"):
                st.info(f"Tools appelés: {', '.join(reponse['tools_used'])}")

# END
