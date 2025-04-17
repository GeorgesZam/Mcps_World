import streamlit as st
import importlib.util
import os
import glob
import sys
from datetime import datetime
from typing import Any, Dict, List
import openai
import re

st.set_page_config(page_title="🧑‍💻 All-in-one LLM Plugin Platform", page_icon="💡")

# ---- 1. Initialisation session state ----
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.history = []
    st.session_state.tools = {}
    st.session_state.cfg = {}
    st.session_state.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

st.title("🛠️ Plateforme LLM+Tools (All-In-One, 100% Streamlit)")

# ---- 2. Config API LLM ----
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
        model = st.text_input("Nom du modèle Azure", value="gpt-4o-mini")
        apiver = st.text_input("API Version", value="2023-03-15-preview")
        st.session_state.cfg = {
            "provider": "azure",
            "endpoint": ep, "key": azkey, "model": model, "apiver": apiver
        }
    if st.button("Valider et démarrer"):
        st.session_state.initialized = True
        st.rerun()
    st.stop()

config = st.session_state.cfg

# ---- 3. Gestion tools/ dynamiques ----
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
            # Fallback triggers: nom du tool seul si rien de défini
            schema = getattr(mod, "function_schema", {
                "type": "object", "properties": {}, "required": []
            })
            if not schema.get("triggers"):
                schema["triggers"] = [tool_name]
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

# ---- 4. Sidebar tools: load/upload/suppr/test/debug triggers ----
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
        st.write(f"⚡ **Triggers**: {', '.join(map(str, tinfo['schema'].get('triggers',[])))}")
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

# ---- 5. Appel LLM + outils + triggers dynamiques ----
def call_llm(messages: List[Dict], tools: Dict[str,Any]=None) -> Dict:
    last = messages[-1]["content"].lower()
    steps = []
    tool_results = {}
    if tools:
        for tname, tinfo in tools.items():
            schema = tinfo.get('schema', {})
            triggers = schema.get("triggers", [tname])

            # Matching par simple inclusion
            trig_found = any(trig.lower() in last for trig in triggers)

            # Option: trigger par regex aussi
            triggers_regex = schema.get("triggers_regex", [])
            regex_found = any(re.search(rgx, last) for rgx in triggers_regex)

            if trig_found or regex_found:
                # Addition spéciale
                if tname == "add":
                    nums = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", last)
                    if len(nums)>=2:
                        n1, n2 = map(float, nums[:2])
                        out = tinfo["function_call"](n1, n2)
                        steps.append({"tool":tname,"args":{"number1":n1,"number2":n2},"output": out})
                        tool_results[tname] = out
                else:
                    out = tinfo["function_call"]()
                    steps.append({"tool":tname,"args":{},"output":out})
                    tool_results[tname] = out

    # --- Génération explicative multi-tool ---
    if steps:
        system_instructions = (
            "Voici les résultats de fonctions/outils spécialisés appelés pour cette question. "
            "Utilise-les pour composer ta réponse de façon claire, concise et polie.\n"
        )
        for stp in steps:
            system_instructions += f"[TOOL {stp['tool']}] Résultat: {stp['output']} (args={stp['args']})\n"

        new_messages = [{"role": "system", "content": system_instructions}] + messages

        content = ""
        if config["provider"]=="openai":
            openai.api_key = config["key"]
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=new_messages
            )
            content += resp["choices"][0]["message"]["content"]
        elif config["provider"]=="azure":
            openai.api_type = "azure"
            openai.api_version = config["apiver"]
            openai.api_key = config["key"]
            openai.api_base = config["endpoint"]
            resp = openai.ChatCompletion.create(
                engine=config["model"], messages=new_messages
            )
            content += resp["choices"][0]["message"]["content"]
        else:
            content += "Demo : Voici les résultats des outils :" + str(tool_results)
        content += "\n\n(Détail des étapes outils ci-dessous)"
        return {"role":"assistant", "content":content, "tools_steps":steps}

    # --- Si aucun outil, LLM seul ---
    content = ""
    if config["provider"]=="openai":
        openai.api_key = config["key"]
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        content += resp["choices"][0]["message"]["content"]
    elif config["provider"]=="azure":
        openai.api_type = "azure"
        openai.api_version = config["apiver"]
        openai.api_key = config["key"]
        openai.api_base = config["endpoint"]
        resp = openai.ChatCompletion.create(
            engine=config["model"], messages=messages
        )
        content += resp["choices"][0]["message"]["content"]
    else:
        content = "(Réponse LLM simulée - demo locale)"
    return {"role":"assistant", "content":content, "tools_steps":[]}

# ---- 6. Affichage chat ----
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
            if reponse.get("tools_steps"):
                st.write("**Détail outils utilisés :**")
                for stp in reponse["tools_steps"]:
                    st.info(f"> **{stp['tool']}** — Args: `{stp['args']}` — Résultat: `{stp['output']}`")
