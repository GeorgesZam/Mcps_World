import streamlit as st
from datetime import datetime
import os
import json
import openai
from typing import Dict, List, Any
import glob
import importlib.util
import inspect
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import pptx

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="mcpGPT", layout="wide")

# ---------- STATE ----------
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key",
    "api_version": "2023-03-15-preview",
    "model": "gpt-4o-mini"
}
CREDENTIALS = {"normal": "normal_pass", "admin": "admin_pass", "root": "root_pass"}

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG.copy()
if 'conversation' not in st.session_state:
    st.session_state.conversation: List[Dict[str, Any]] = []
if 'files' not in st.session_state:
    st.session_state.files: Dict[str, str] = {}
if 'tools' not in st.session_state:
    st.session_state.tools: Dict[str, Any] = {}
if 'page' not in st.session_state:
    st.session_state.page = 'chat'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None

# ---------- UTILS ----------
def ensure_str(x: Any) -> str:
    if x is None:
        return "[No content]"
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False)
    return str(x)

# ---------- CONFIG HANDLING ----------
def init_openai():
    cfg = st.session_state.config
    openai.api_type = cfg['api_type']
    openai.api_base = cfg['api_base']
    openai.api_key = cfg['api_key']
    openai.api_version = cfg['api_version']
    st.session_state.model = cfg['model']

# ---------- TOOL MANAGEMENT ----------
def load_tools():
    st.session_state.tools.clear()
    os.makedirs('tools', exist_ok=True)
    for path in glob.glob('tools/tool-*.py'):
        name = os.path.splitext(os.path.basename(path))[0].replace('tool-', '')
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        st.session_state.tools[name] = {
            'func': mod.function_call,
            'schema': getattr(mod, 'function_schema', {}),
            'desc': getattr(mod, 'description', ''),
            'code': inspect.getsource(mod)
        }

# ---------- FILE PROCESSING ----------
def extract_text(file) -> str:
    ext = file.name.split('.')[-1].lower()
    if ext == 'pdf':
        reader = PdfReader(file)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext in ('xlsx', 'xls'):
        return pd.read_excel(file).to_markdown()
    if ext == 'docx':
        return "\n".join(p.text for p in Document(file).paragraphs)
    if ext == 'pptx':
        return "\n".join(
            shp.text for prs in pptx.Presentation(file).slides
            for shp in prs.shapes if hasattr(shp, 'text')
        )
    if ext in ('txt', 'csv'):
        return file.read().decode('utf-8')
    return f"Unsupported format: {file.name}"

# ---------- LLM & TOOL EXECUTION ----------
def get_tools_schema() -> List[Dict[str, Any]]:
    return [
        {"name": n, "description": t['desc'], "parameters": t['schema']}
        for n, t in st.session_state.tools.items()
    ]

def call_llm(messages: List[Dict[str, Any]]):
    tools = get_tools_schema()
    return openai.ChatCompletion.create(
        engine=st.session_state.model,
        messages=messages,
        tools=[{"type":"function","function":t} for t in tools] if tools else None,
        tool_choice="auto" if tools else None
    ).choices[0]

# ---------- AUTH ----------
def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in CREDENTIALS and CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            init_openai()
            load_tools()
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

# ---------- SIDE BAR ----------
def sidebar():
    st.sidebar.title(f"mcpGPT ({st.session_state.user})")
    # Navigation buttons
    if st.sidebar.button("💬 Chat"): st.session_state.page = 'chat'
    if st.sidebar.button("🔧 API"): st.session_state.page = 'api'
    if st.sidebar.button("🛠 Tools"): st.session_state.page = 'tools'
    st.sidebar.markdown('---')
    # Tools section
    st.sidebar.subheader("🛠 Available Tools")
    if st.sidebar.button("Reload Tools"): load_tools(); st.sidebar.success("Tools reloaded")
    if st.session_state.user in ['admin', 'root']:
        for name in st.session_state.tools:
            st.sidebar.checkbox(name, key=f"tool_{name}", value=True)
    else:
        st.sidebar.info("No tools available for your role.")
    # Files section back in sidebar
    st.sidebar.subheader("📁 Files")
    uploaded = st.sidebar.file_uploader(
        "Upload files to context", type=['pdf','xlsx','xls','docx','pptx','txt','csv'],
        accept_multiple_files=True
    )
    for f in uploaded:
        if f and f.name not in st.session_state.files:
            st.session_state.files[f.name] = extract_text(f)
            st.sidebar.success(f"Processed {f.name}")

# ---------- PAGES ----------
def page_chat():
    st.header(f"💬 Chat - {st.session_state.user}")
    # Display conversation
    for msg in st.session_state.conversation:
        with st.chat_message(msg['role']): st.write(msg['content'])
    # User input
    user_input = st.chat_input("Your message…")
    if user_input:
        st.session_state.conversation.append({"role":"user","content":user_input})
        # Build context including files
        context = "Files:\n" + "\n\n".join(f"=== {n} ===\n{c}" for n, c in st.session_state.files.items())
        messages = [{"role":"system","content":context}]
        messages += [{"role":m['role'],"content":m['content']} for m in st.session_state.conversation]
        with st.spinner("Processing…"):
            choice = call_llm(messages)
        # Tool handling
        if hasattr(choice, 'function_call') and choice.function_call:
            fn = choice.function_call
            name, args = fn.name, json.loads(fn.arguments)
            res = st.session_state.tools[name]['func'](**args)
            tool_content = ensure_str(res)
            messages.append({"role":"assistant","content":"","function_call":fn})
            messages.append({"role":"tool","name":name,"content":tool_content})
            with st.spinner("Finalizing…"):
                final = openai.ChatCompletion.create(engine=st.session_state.model,messages=messages).choices[0].message
            text = ensure_str(final.content)
        else:
            text = ensure_str(choice.content)
        st.session_state.conversation.append({"role":"assistant","content":text})
        st.experimental_rerun()

def page_api():
    st.header("🔧 API Configuration")
    cfg = st.session_state.config
    with st.form("api_cfg"):
        cfg['api_type'] = st.selectbox("API Type", ["azure","openai"], index=["azure","openai"].index(cfg['api_type']))
        cfg['api_base'] = st.text_input("Endpoint", cfg['api_base'])
        cfg['api_key'] = st.text_input("Key", cfg['api_key'], type="password")
        cfg['api_version'] = st.text_input("Version", cfg['api_version'])
        cfg['model'] = st.text_input("Model", cfg['model'])
        if st.form_submit_button("Save Config"):
            init_openai(); st.success("Configuration saved")

def page_tools():
    st.header("🔧 Tool Management")
    up, ex = st.tabs(["Upload","Existing"])
    with up:
        f = st.file_uploader("Upload .py tool", type='py')
        if f:
            path = os.path.join('tools',f.name)
            open(path,'wb').write(f.getbuffer())
            load_tools(); st.success("Tool uploaded")
    with ex:
        if st.session_state.user in ['admin','root']:
            for n, info in st.session_state.tools.items():
                with st.expander(n):
                    st.write(info['desc']); st.code(info['code'],language='python')
                    if st.button(f"Delete {n}"): os.remove(os.path.join('tools',f'tool-{n}.py')); load_tools(); st.experimental_rerun()
        else:
            st.info("Admin privileges required.")

# ---------- MAIN ----------
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        sidebar(); st.markdown('---')
        if st.session_state.page=='chat': page_chat()
        elif st.session_state.page=='api': page_api()
        else: page_tools()

if __name__=='__main__': main()
