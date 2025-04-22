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
/* Sidebar styling */
.sidebar-title { font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem; }
/* Chat container */
.chat-container { max-height: 60vh; overflow-y: auto; padding: 1rem; background: #f5f5f5; border-radius: 8px; }
.chat-user { background: #dcf8c6; padding: .75rem; border-radius: 12px; margin-bottom: .5rem; width: fit-content; }
.chat-assistant { background: #fff; padding: .75rem; border-radius: 12px; margin-bottom: .5rem; width: fit-content; }
</style>
""", unsafe_allow_html=True)

# ---------- STATE ----------
DEFAULT_ENV = {
    "Development": {"api_type":"azure","api_base":"https://your-endpoint.openai.azure.com/","api_key":"your-api-key","api_version":"2023-03-15-preview","model":"gpt-4o-mini"}
}
if 'envs' not in st.session_state: st.session_state.envs = DEFAULT_ENV.copy()
if 'current_env' not in st.session_state: st.session_state.current_env = list(st.session_state.envs.keys())[0]
if 'conv' not in st.session_state: st.session_state.conv: List[Dict[str,Any]] = []
if 'files' not in st.session_state: st.session_state.files: Dict[str,str] = {}
if 'tools' not in st.session_state: st.session_state.tools: Dict[str,Any] = {}
if 'page' not in st.session_state: st.session_state.page = 'chat'

# ---------- UTILS ----------
def ensure_str(x: Any) -> str:
    if x is None: return "[No content]"
    if isinstance(x, (dict, list)): return json.dumps(x, ensure_ascii=False)
    return str(x)

# ---------- CONFIG ----------
def load_env(name: str):
    cfg = st.session_state.envs[name]
    openai.api_type = cfg['api_type']; openai.api_base = cfg['api_base']; openai.api_key = cfg['api_key']; openai.api_version = cfg['api_version']
    st.session_state.model = cfg['model']

# ---------- TOOL MANAGEMENT ----------
def load_tools():
    st.session_state.tools.clear()
    os.makedirs('tools', exist_ok=True)
    for path in glob.glob('tools/tool-*.py'):
        name = os.path.splitext(os.path.basename(path))[0].replace('tool-', '')
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        st.session_state.tools[name] = {'func':mod.function_call,'schema':getattr(mod,'function_schema',{}),'desc':getattr(mod,'description',''),'code':inspect.getsource(mod)}

# ---------- FILE PROCESSING ----------
def extract_text(file) -> str:
    ext = file.name.split('.')[-1].lower()
    if ext=='pdf': reader=PdfReader(file); return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext in ('xlsx','xls'): return pd.read_excel(file).to_markdown()
    if ext=='docx': return "\n".join(p.text for p in Document(file).paragraphs)
    if ext=='pptx': return "\n".join([shp.text for prs in pptx.Presentation(file).slides for shp in prs.shapes if hasattr(shp,'text')])
    if ext in ('txt','csv'): return file.read().decode('utf-8')
    return f"Unsupported: {file.name}"

# ---------- LLM ----------
def get_tools_schema(): return [{"name":n,"description":t['desc'],"parameters":t['schema']} for n,t in st.session_state.tools.items()]
def call_llm(msgs: List[Dict]) -> Any:
    tools=get_tools_schema(); resp=openai.ChatCompletion.create(engine=st.session_state.model,messages=msgs,tools=[{"type":"function","function":t} for t in tools] if tools else None,tool_choice="auto" if tools else None)
    return resp.choices[0].message

# ---------- SIDEBAR ----------
def sidebar():
    st.sidebar.markdown("<div class='sidebar-title'>mcpGPT</div>", unsafe_allow_html=True)
    # Navigation
    st.sidebar.radio("_", options=["chat","api","tools"], format_func=lambda x: x.capitalize(), key='page')
    st.sidebar.markdown("---")
    # Environment
    st.sidebar.subheader("Environment")
    env=st.sidebar.selectbox("Select Env", list(st.session_state.envs.keys()), index=list(st.session_state.envs).index(st.session_state.current_env))
    if env!=st.session_state.current_env: st.session_state.current_env=env; load_env(env)
    # Tools
    st.sidebar.subheader("Tools")
    if st.sidebar.button("Reload Tools"): load_tools(); st.sidebar.success("Reloaded")
    # Files
    st.sidebar.subheader("Files")
    up=st.sidebar.file_uploader("Upload", type=['pdf','xlsx','xls','docx','pptx','txt','csv'], accept_multiple_files=True)
    for f in up:
        if f.name not in st.session_state.files: st.session_state.files[f.name]=extract_text(f); st.sidebar.success(f"Processed {f.name}")
    # History
    with st.sidebar.expander("History", expanded=False):
        for m in st.session_state.conv: st.write(f"[{m['role']}] {m['content']}")

# ---------- PAGES ----------
def page_chat():
    st.title("Chat")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.conv:
        cls='chat-user' if msg['role']=='user' else 'chat-assistant'
        st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    inp=st.text_input("Your message…", key='inp')
    if inp:
        st.session_state.conv.append({"role":"user","content":inp});
        msgs=[{"role":"system","content":"Files:\n"+"\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.files.items())}]+[{"role":m['role'],"content":m['content']} for m in st.session_state.conv]
        with st.spinner(): r=call_llm(msgs)
        txt=ensure_str(r.content); st.session_state.conv.append({"role":"assistant","content":txt}); st.experimental_rerun()

def page_api():
    st.title("API Configuration")
    cfg=st.session_state.envs[st.session_state.current_env]
    with st.form('form_api'):
        cfg['api_type']=st.selectbox("API Type", ['azure','openai'], index=['azure','openai'].index(cfg['api_type']))
        cfg['api_base']=st.text_input("Endpoint", cfg['api_base'])
        cfg['api_key']=st.text_input("Key", cfg['api_key'], type='password')
        cfg['api_version']=st.text_input("Version", cfg['api_version'])
        cfg['model']=st.text_input("Model", cfg['model'])
        if st.form_submit_button("Save"): load_env(st.session_state.current_env); st.success("Saved")

def page_tools():
    st.title("Tool Management")
    tabs=st.tabs(["Upload","Existing"])
    with tabs[0]:
        f=st.file_uploader(".py Tool", type='py')
        if f: open(os.path.join('tools',f.name),'wb').write(f.getbuffer()); load_tools(); st.success('Uploaded')
    with tabs[1]:
        for name,info in st.session_state.tools.items():
            with st.expander(name): st.write(info['desc']); st.code(info['code'],language='python');
            if st.button(f"Delete {name}"): os.remove(os.path.join('tools',f'tool-{name}.py')); load_tools(); st.experimental_rerun()

# ---------- MAIN ----------
def main():
    load_env(st.session_state.current_env); load_tools(); sidebar(); st.markdown('---')
    if st.session_state.page=='chat': page_chat()
    elif st.session_state.page=='api': page_api()
    else: page_tools()

if __name__=='__main__': main()
