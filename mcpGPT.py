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

# ---------- CONFIGURATION & STATE ----------
DEFAULT_ENVIRONMENTS = {
    "Development": {
        "api_type": "azure",
        "api_base": "https://your-endpoint.openai.azure.com/",
        "api_key": "your-api-key-here",
        "api_version": "2023-03-15-preview",
        "model": "gpt-4o-mini"
    }
}

st.set_page_config(page_title="mcpGPT", layout="wide")
if 'environments' not in st.session_state:
    st.session_state.environments = DEFAULT_ENVIRONMENTS.copy()
if 'current_env' not in st.session_state:
    st.session_state.current_env = list(st.session_state.environments.keys())[0]
if 'conversation' not in st.session_state:
    st.session_state.conversation: List[Dict[str, Any]] = []
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files: Dict[str, str] = {}
if 'tools' not in st.session_state:
    st.session_state.tools: Dict[str, Any] = {}

# ---------- UTILITY FUNCTIONS ----------
def ensure_str(x: Any) -> str:
    if x is None: return "[No content]"
    if isinstance(x, (dict, list)): return json.dumps(x, ensure_ascii=False)
    return str(x)

# ---------- CONFIG HANDLING ----------
def load_env(name: str):
    cfg = st.session_state.environments[name]
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
            'desc': getattr(mod, 'description', ""),
            'code': inspect.getsource(mod)
        }

# ---------- FILE UPLOAD PROCESSING ----------

def extract_text(file) -> str:
    ext = file.name.split('.')[-1].lower()
    if ext == 'pdf':
        reader = PdfReader(file)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext in ('xlsx', 'xls'):
        df = pd.read_excel(file)
        return df.to_markdown()
    if ext == 'docx':
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == 'pptx':
        prs = pptx.Presentation(file)
        texts = []
        for s in prs.slides:
            for shp in s.shapes:
                if hasattr(shp, 'text'): texts.append(shp.text)
        return "\n".join(texts)
    if ext in ('txt', 'csv'):
        return file.read().decode('utf-8')
    return f"Unsupported format: {file.name}"

# ---------- CHAT & TOOL EXECUTION ----------
def get_tools_schema() -> List[Dict]:
    return [
        {"name": n, "description": t['desc'], "parameters": t['schema']}
        for n, t in st.session_state.tools.items()
    ]

def call_llm(messages: List[Dict]) -> Any:
    tools = get_tools_schema()
    resp = openai.ChatCompletion.create(
        engine=st.session_state.model,
        messages=messages,
        tools=[{"type":"function","function":t} for t in tools] if tools else None,
        tool_choice="auto" if tools else None
    )
    return resp.choices[0].message

# ---------- UI COMPONENTS ----------
def sidebar_environments():
    st.sidebar.subheader("🌐 Environments")
    env = st.sidebar.selectbox("Select", list(st.session_state.environments.keys()), index=list(st.session_state.environments).index(st.session_state.current_env))
    st.session_state.current_env = env
    load_env(env)
    if st.sidebar.button("New Environment"):
        st.sidebar.text_input("Name", key='new_env_name')
        # TODO: implement creation

def sidebar_tools():
    st.sidebar.subheader("🛠️ Active Tools")
    for name in st.session_state.tools:
        st.sidebar.checkbox(name, key=f"tool_{name}", value=True)
    if st.sidebar.button("Reload Tools"):
        load_tools()
        st.sidebar.success("Tools reloaded!")
    if st.sidebar.button("Manage Tools"):
        st.session_state.page = 'tools'

def sidebar_history():
    with st.sidebar.expander("💬 Chat History", expanded=True):
        for msg in st.session_state.conversation:
            st.write(f"[{msg['role']}] {msg['content']}")

# ---------- PAGE VIEWS ----------
def page_chat():
    st.header("💬 Chat")
    # File uploader
    files = st.file_uploader("Upload files to context", type=['pdf','xlsx','xls','docx','pptx','txt','csv'], accept_multiple_files=True)
    for f in files:
        if f.name not in st.session_state.uploaded_files:
            st.session_state.uploaded_files[f.name] = extract_text(f)
            st.success(f"Processed {f.name}")

    # Display conversation
    for msg in st.session_state.conversation:
        with st.chat_message(msg['role']):
            st.write(msg['content'])

    # User input
    user_input = st.chat_input("Type your message...")
    if user_input:
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.conversation.append({"role":"user","content":user_input,"ts":timestamp})
        messages = [{"role":"system","content":"Attached files:\n" + "\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.uploaded_files.items())}] + [
            {"role":m['role'],"content":m['content']} for m in st.session_state.conversation
        ]
        with st.spinner():
            resp = call_llm(messages)
        content = ensure_str(resp.content)
        st.session_state.conversation.append({"role":"assistant","content":content,"ts":datetime.now().strftime("%H:%M:%S")})
        st.chat_message("assistant").write(content)


def page_api():
    st.header("🔧 API Configuration")
    cfg = st.session_state.environments[st.session_state.current_env]
    with st.form("cfg"):
        cfg['api_type'] = st.selectbox("API Type", ["azure","openai"], index=["azure","openai"].index(cfg['api_type']))
        cfg['api_base'] = st.text_input("Endpoint", cfg['api_base'])
        cfg['api_key'] = st.text_input("Key", cfg['api_key'], type="password")
        cfg['api_version'] = st.text_input("Version", cfg['api_version'])
        cfg['model'] = st.text_input("Model", cfg['model'])
        if st.form_submit_button("Save"):
            st.success("Saved.")


def page_tools():
    st.header("🔧 Tool Management")
    tabs = st.tabs(["Upload","Existing"])
    with tabs[0]:
        st.file_uploader("Upload .py tool", type='py', key='upl')
        if st.session_state.get('upl'):
            f = st.session_state['upl']
            path = os.path.join('tools', f.name)
            with open(path,'wb') as w: w.write(f.getbuffer())
            load_tools(); st.success("Uploaded.")
    with tabs[1]:
        for name,info in st.session_state.tools.items():
            exp = st.expander(name)
            exp.write(info['desc'])
            exp.code(info['code'], language='python')
            if exp.button(f"Delete {name}"):
                os.remove(os.path.join('tools',f'tool-{name}.py'))
                load_tools(); st.experimental_rerun()

# ---------- LAYOUT & NAVIGATION ----------
if __name__ == '__main__':
    sidebar_environments()
    sidebar_tools()
    sidebar_history()
    st.markdown("---")
    st.session_state.page = st.session_state.get('page','chat')
    if st.session_state.page == 'chat':
        page_chat()
    elif st.session_state.page == 'api':
        page_api()
    else:
        page_tools()
