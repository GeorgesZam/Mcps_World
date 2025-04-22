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
/* Chat container styling */
.chat-container {
  max-height: 70vh;
  overflow-y: auto;
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 8px;
  border: 1px solid #ddd;
}
/* Chat bubbles */
.streamlit-expanderContent p {
  margin: 0.5rem 0;
}
.chat-user {
  background-color: #dcf8c6;
  padding: 0.75rem;
  border-radius: 12px;
  margin-bottom: 0.5rem;
  width: fit-content;
}
.chat-assistant {
  background-color: #fff;
  padding: 0.75rem;
  border-radius: 12px;
  margin-bottom: 0.5rem;
  width: fit-content;
}
</style>
""", unsafe_allow_html=True)

# ---------- STATE ----------
DEFAULT_ENV = {
    "Development": {
        "api_type": "azure",
        "api_base": "https://your-endpoint.openai.azure.com/",
        "api_key": "your-api-key-here",
        "api_version": "2023-03-15-preview",
        "model": "gpt-4o-mini"
    }
}
if 'envs' not in st.session_state:
    st.session_state.envs = DEFAULT_ENV.copy()
if 'current_env' not in st.session_state:
    st.session_state.current_env = list(st.session_state.envs.keys())[0]
if 'conv' not in st.session_state:
    st.session_state.conv: List[Dict[str, Any]] = []
if 'files' not in st.session_state:
    st.session_state.files: Dict[str, str] = {}
if 'tools' not in st.session_state:
    st.session_state.tools: Dict[str, Any] = {}

# ---------- UTILITIES ----------
def ensure_str(x: Any) -> str:
    if x is None: return "[No content]"
    if isinstance(x, (dict, list)): return json.dumps(x, ensure_ascii=False)
    return str(x)

# ---------- CONFIGURATION HANDLING ----------
def load_env(name: str):
    cfg = st.session_state.envs[name]
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

# ---------- FILE PROCESSING ----------
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

# ---------- LLM & TOOL EXECUTION ----------
def get_tools_schema():
    return [{"name":n,"description":t['desc'],"parameters":t['schema']} for n,t in st.session_state.tools.items()]

def call_llm(messages: List[Dict]) -> Any:
    tools = get_tools_schema()
    resp = openai.ChatCompletion.create(
        engine=st.session_state.model,
        messages=messages,
        tools=[{"type":"function","function":t} for t in tools] if tools else None,
        tool_choice="auto" if tools else None
    )
    return resp.choices[0].message

# ---------- SIDEBAR ----------
def sidebar():
    st.sidebar.title("mcpGPT")
    # Environments
    st.sidebar.subheader("🌐 Environment")
    env = st.sidebar.selectbox("Select Env", list(st.session_state.envs.keys()), index=list(st.session_state.envs).index(st.session_state.current_env))
    if env != st.session_state.current_env:
        st.session_state.current_env = env
        load_env(env)
    # Tools
    st.sidebar.subheader("🛠️ Tools")
    for name in st.session_state.tools:
        st.sidebar.checkbox(name, key=f"tool_{name}", value=True)
    if st.sidebar.button("Reload Tools"):
        load_tools(); st.sidebar.success("Reloaded!")
    # File context
    st.sidebar.subheader("📁 Files")
    files = st.sidebar.file_uploader("Upload", type=['pdf','xlsx','xls','docx','pptx','txt','csv'], accept_multiple_files=True)
    for f in files:
        if f.name not in st.session_state.files:
            st.session_state.files[f.name] = extract_text(f)
            st.sidebar.success(f"Processed {f.name}")
    # History collapse
    with st.sidebar.expander("💬 History", expanded=False):
        for m in st.session_state.conv:
            st.write(f"[{m['role']}] {m['content']}")

# ---------- PAGES ----------
def page_chat():
    st.title("💬 Chat")
    # Chat container
    container = st.container()
    container.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.conv:
        cls = 'chat-user' if msg['role']=='user' else 'chat-assistant'
        container.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)
    container.markdown('</div>', unsafe_allow_html=True)

    # Input
    user_input = st.text_input("Your message…", key="inp")
    if user_input:
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.conv.append({"role":"user","content":user_input,"ts":ts})
        messages = [{"role":"system","content":"Files:\n"+"\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.files.items())}] + [
            {"role":m['role'],"content":m['content']} for m in st.session_state.conv
        ]
        with st.spinner("Thinking…"):
            resp = call_llm(messages)
        text = ensure_str(resp.content)
        st.session_state.conv.append({"role":"assistant","content":text,"ts":datetime.now().strftime("%H:%M:%S")})
        st.experimental_rerun()

# ---------- MAIN ----------
def main():
    load_env(st.session_state.current_env)
    load_tools()
    sidebar()
    st.markdown("---")
    page_chat()

if __name__ == '__main__':
    main()
