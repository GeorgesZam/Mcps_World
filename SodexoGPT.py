import streamlit as st
import importlib.util
import os
import glob
import sys
import openai
import json
from datetime import datetime
from typing import Any, Dict, List

st.set_page_config(page_title="🧠 Chat LLM + Outils Hybride", page_icon="🤖")

# -------- 1. Init session --------
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.history = []
    st.session_state.tools = {}
    st.session_state.cfg = {}
    st.session_state.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

st.title("🧠 LLM + OUTILS (robuste, non-natif)")

# -------- 2. Choix LLM --------
if not st.session_state.initialized:
    st.subheader("Choix fournisseur LLM")
    provider = st.selectbox("Fournisseur LLM", ["Démo locale", "OpenAI", "Azure OpenAI"], index=0)
    if provider == "Démo locale":
        st.session_state.cfg = {"provider": "demo"}
    elif provider == "OpenAI":
        key = st.text_input("OpenAI API Key", type="password")
        st.session_state.cfg = {"provider": "openai", "key": key}
    else:  # Azure
        ep = st.text_input("Azure Endpoint", value="https://")
        azkey = st.text_input("Azure API Key", type="password")
        model = st.text_input("Modèle Azure (deployment)", value="gpt-4")
        apiver = st.text_input("API Version", value="2024-03-15-preview")
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
            matcher = getattr(mod, "matcher", None)
            tool_modules[tool_name] = {
                "function_call": mod.function_call,
                "matcher": matcher,
                "source": file,
                "doc": mod.__doc__ or ""
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
    uploaded = st.file_uploader("tool-xxx.py", type="py")
    if uploaded:
        bytes_content = uploaded.read()
        path = os.path.join(TOOLS_FOLDER, uploaded.name)
        with open(path, "wb") as f:
            f.write(bytes_content)
        st.session_state.tools = load_tools()
        st.success(f"Ajouté : {uploaded.name}")
        st.experimental_rerun()

with st.sidebar.expander("🗑️ Supprimer"):
    liste = list(tools.keys())
    if liste:
        choix = st.selectbox("Suppression", options=liste)
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
        st.write(f"**{tname}** - {os.path.basename(tinfo['source'])} - {tinfo.get('doc','')}")
        with st.form(f"test_{tname}"):
            params = {}
            import inspect
            sig = inspect.signature(tinfo["function_call"])
            for pname, p in sig.parameters.items():
                val = st.text_input(f"{tname}:{pname}")
                params[pname] = val
            if st.form_submit_button("Tester"):
                try:
                    typed_params = {}
                    for k,v in params.items():
                        if v.isdigit():
                            typed_params[k] = int(v)
                        else:
                            try:
                                typed_params[k] = float(v)
                            except Exception:
                                typed_params[k] = v
                    result = tinfo["function_call"](**typed_params)
                    st.success(f"Résultat: {result}")
                except Exception as ex:
                    st.error(str(ex))

# -------- 5. Appel LLM + Tool (par matcher ou clé) --------
import re

def extract_tool_usages(prompt: str, tools: Dict[str,Any]):
    found = []
    for name, tinfo in tools.items():
        matcher = tinfo.get("matcher", None)
        if matcher:
            if callable(matcher) and matcher(prompt):
                found.append(name)
            elif isinstance(matcher, str) and matcher in prompt:
                found.append(name)
        elif name in prompt:
            found.append(name)
    return found

def call_llm(messages: List[Dict], tools: Dict[str, Any]=None) -> Dict:
    # Chercher une commande outil (simple)
    last_user = messages[-1]["content"]
    used_tools = extract_tool_usages(last_user, tools)
    steps = []
    tool_results = {}

    for name in used_tools:
        tinfo = tools[name]
        import inspect
        sig = inspect.signature(tinfo["function_call"])
        args = {}
        for pname in sig.parameters:
            match = re.search(rf"{pname}\s*=\s*([-\w.]+)", last_user)
            if match:
                val = match.group(1)
                # essai autotypage basique
                try:
                    val = float(val) if '.' in val else int(val)
                except:
                    pass
                args[pname] = val
            else:
                args[pname] = 0  # default, modifiez ou raffinez selon vos tools
        try:
            out = tinfo["function_call"](**args)
        except Exception as ex:
            out = f"Erreur lors de l'appel du tool: {ex}"
        steps.append({"tool": name, "args": args, "output": out})
        tool_results[name] = out

    # Génère la réponse
    if config["provider"] == "openai":
        openai.api_key = config["key"]
        base_prompt = f"L'utilisateur a demandé à utiliser les outils suivants: {steps}. Fournis une réponse cohérente et claire en t'appuyant sur leur résultat."
        msgs = [{"role": "system", "content": base_prompt}] + messages
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=msgs
            )
            content = resp["choices"][0]["message"]["content"]
        except Exception as ex:
            content = f"(Erreur OpenAI: {ex}) - Résultats outils: {tool_results}"
    elif config["provider"] == "azure":
        openai.api_type = "azure"
        openai.api_version = config["apiver"]
        openai.api_key = config["key"]
        openai.api_base = config["endpoint"]
        base_prompt = f"L'utilisateur a demandé à utiliser les outils suivants: {steps}. Fournis une réponse cohérente et claire en t'appuyant sur leur résultat."
        msgs = [{"role": "system", "content": base_prompt}] + messages
        try:
            resp = openai.ChatCompletion.create(
                engine=config["model"],
                messages=msgs
            )
            content = resp["choices"][0]["message"]["content"]
        except Exception as ex:
            content = f"(Erreur Azure: {ex}) - Résultats outils: {tool_results}"
    else:
        content = f"(Réponse LLM factice/demo) – Résultats outils : {tool_results}"

    return {"role": "assistant", "content": content, "tools_steps": steps}

# -------- 6. Affichage chat --------
st.subheader("💬 Conversation")
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("tools_steps"):
            st.write("**Détail outils utilisés:**")
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
