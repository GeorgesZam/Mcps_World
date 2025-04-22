import streamlit as st
from datetime import datetime
import time
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

# ---------- CSS STYLES ----------
st.markdown("""
<style>
.chat-container { max-height: 70vh; overflow-y: auto; padding: 1rem; background: #f5f5f5; border-radius: 8px; }
.chat-user { background: #dcf8c6; padding: .75rem; border-radius: 12px; margin-bottom: .5rem; width: fit-content; }
.chat-assistant { background: #fff; padding: .75rem; border-radius: 12px; margin-bottom: .5rem; width: fit-content; }
</style>
""", unsafe_allow_html=True)

# ---------- STATE ----------
# Single API configuration
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key",
    "api_version": "2023-03-15-preview",
    "model": "gpt-4o-mini"
}
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

# ---------- UTILS ----------
def ensure_str(x: Any) -> str:
    if x is None: return "[No content]"
    if isinstance(x, (dict, list)): return json.dumps(x, ensure_ascii=False)
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
        return "\n".join(shp.text for prs in pptx.Presentation(file).slides for shp in prs.shapes if hasattr(shp, 'text'))
    if ext in ('txt', 'csv'):
        return file.read().decode('utf-8')
    return f"Unsupported: {file.name}"

# ---------- LLM & TOOL EXECUTION ----------
def get_tools_schema():
    return [{"name":n, "description":t['desc'], "parameters":t['schema']} for n, t in st.session_state.tools.items()]

def call_llm(messages: List[Dict[str, Any]]):
    tools = get_tools_schema()
    response = openai.ChatCompletion.create(
        engine=st.session_state.model,
        messages=messages,
        tools=[{"type": "function", "function": t} for t in tools] if tools else None,
        tool_choice="auto" if tools else None,
    )
    return response.choices[0].message

# ---------- SIDEBAR ----------
def sidebar():
    st.sidebar.title("mcpGPT")
    # Navigation
    st.sidebar.radio("Navigation", ["chat", "api", "tools"], index=["chat","api","tools"].index(st.session_state.page), key='page')
    st.sidebar.markdown('---')
    # Tools
    st.sidebar.subheader("🛠 Tools")
    if st.sidebar.button("Reload Tools"):
        load_tools()
        st.sidebar.success("Tools reloaded!")
    for name in st.session_state.tools:
        st.sidebar.checkbox(name, key=f"tool_{name}", value=True)
    # Files
    st.sidebar.subheader("📁 Files")
    files = st.sidebar.file_uploader("Upload files", type=['pdf','xlsx','xls','docx','pptx','txt','csv'], accept_multiple_files=True)
    for f in files:
        if f.name not in st.session_state.files:
            st.session_state.files[f.name] = extract_text(f)
            st.sidebar.success(f"Processed {f.name}")

# ---------- PAGES ----------
def page_chat():
    st.header("💬 Chat")
    # Display conversation
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.conversation:
        cls = 'chat-user' if msg['role']=='user' else 'chat-assistant'
        st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    # Input
    user_input = st.text_input("Your message…", key='inp')
    if user_input:
        st.session_state.conversation.append({"role":"user", "content": user_input})
        messages = [{"role": "system", "content": "Files:\n" + "\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.files.items())}]
        messages += [{"role": m['role'], "content": m['content']} for m in st.session_state.conversation]
        with st.spinner("Thinking…"):
            resp = call_llm(messages)
        text = ensure_str(resp.content)
        st.session_state.conversation.append({"role":"assistant", "content": text})
        st.experimental_rerun()


def page_api():
    st.header("🔧 API Configuration")
    cfg = st.session_state.config
    with st.form("cfg"):
        cfg['api_type'] = st.selectbox("API Type", ["azure","openai"], index=["azure","openai"].index(cfg['api_type']))
        cfg['api_base'] = st.text_input("Endpoint", cfg['api_base'])
        cfg['api_key'] = st.text_input("Key", cfg['api_key'], type="password")
        cfg['api_version'] = st.text_input("Version", cfg['api_version'])
        cfg['model'] = st.text_input("Model", cfg['model'])
        if st.form_submit_button("Save"):
            init_openai()
            st.success("Configuration saved!")


def page_tools():
    st.header("🔧 Tool Management")
    tabs = st.tabs(["Upload","Existing"])
    with tabs[0]:
        f = st.file_uploader("Upload .py tool", type='py')
        if f:
            path = os.path.join('tools', f.name)
            with open(path,'wb') as wf: wf.write(f.getbuffer())
            load_tools()
            st.success("Tool uploaded.")
    with tabs[1]:
        for name, info in st.session_state.tools.items():
            with st.expander(name):
                st.write(info['desc'])
                st.code(info['code'], language='python')
                if st.button(f"Delete {name}"):
                    os.remove(os.path.join('tools', f'tool-{name}.py'))
                    load_tools()
                    st.experimental_rerun()

# ---------- MAIN ----------
def main():
    init_openai()
    load_tools()
    sidebar()
    st.markdown('---')
    if st.session_state.page == 'chat':
        page_chat()
    elif st.session_state.page == 'api':
        page_api()
    else:
        page_tools()

if __name__ == '__main__':
    main()
