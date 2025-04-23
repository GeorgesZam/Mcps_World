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

# ---------- INITIAL CONFIG ----------
DEFAULT_CONFIG = {
    "api_type": "azure",
    "api_base": "https://your-endpoint.openai.azure.com/",
    "api_key": "your-api-key-here",
    "api_version": "2023-05-15",
    "model": "gpt-4"
}
CREDENTIALS = {"normal": "normal_pass", "admin": "admin_pass", "root": "root_pass"}

# ---------- SESSION STATE ----------
if 'config' not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG.copy()
if 'conversation' not in st.session_state:
    st.session_state.conversation: List[Dict[str, Any]] = []
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files: Dict[str, str] = {}
if 'available_tools' not in st.session_state:
    st.session_state.available_tools: Dict[str, Any] = {}
if 'page' not in st.session_state:
    st.session_state.page = 'Chat'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None

# ---------- UTILITIES ----------
def ensure_str(x: Any) -> str:
    if x is None:
        return "[No content]"
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False)
    return str(x)

def save_config():
    with open('config.json', 'w') as f:
        json.dump(st.session_state.config, f)

def load_config():
    try:
        with open('config.json', 'r') as f:
            st.session_state.config.update(json.load(f))
    except FileNotFoundError:
        pass

# ---------- OPENAI SETUP ----------
def init_openai():
    cfg = st.session_state.config
    openai.api_type = cfg['api_type']
    openai.api_base = cfg['api_base']
    openai.api_key = cfg['api_key']
    openai.api_version = cfg['api_version']
    st.session_state.model = cfg['model']

# ---------- FILE PROCESSING ----------
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_excel(file):
    df = pd.read_excel(file)
    return df.to_markdown()

def extract_text_from_word(file):
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_ppt(file):
    prs = pptx.Presentation(file)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, 'text'):
                texts.append(shape.text)
    return "\n".join(texts)

def process_uploaded_file(file):
    ext = file.name.split('.')[-1].lower()
    if ext == 'pdf': return extract_text_from_pdf(file)
    if ext in ('xlsx','xls'): return extract_text_from_excel(file)
    if ext == 'docx': return extract_text_from_word(file)
    if ext == 'pptx': return extract_text_from_ppt(file)
    if ext in ('txt','csv'): return file.read().decode('utf-8')
    return f"File {file.name} not extracted (unsupported format)"

# ---------- TOOL MANAGEMENT ----------
def load_tools():
    st.session_state.available_tools.clear()
    os.makedirs('tools', exist_ok=True)
    for path in glob.glob('tools/tool-*.py'):
        name = os.path.splitext(os.path.basename(path))[0].replace('tool-', '')
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        st.session_state.available_tools[name] = {
            'function': mod.function_call,
            'schema': getattr(mod, 'function_schema', {}),
            'description': getattr(mod, 'description', '')
        }

def get_tools_schema():
    return [
        {"name": name, "description": info['description'], "parameters": info['schema']}
        for name, info in st.session_state.available_tools.items()
    ]

# ---------- CHAT WITH LLM ----------
def chat_with_llm(messages: List[Dict]) -> Any:
    try:
        tools = get_tools_schema()
        kwargs = { 'model': st.session_state.model, 'messages': messages }
        if tools:
            kwargs['functions'] = tools
            kwargs['function_call'] = 'auto'
        resp = openai.ChatCompletion.create(**kwargs)
        return resp.choices[0].message
    except Exception as e:
        st.error(f"OpenAI error: {e}")
        return None

# ---------- PAGES ----------
def show_login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if CREDENTIALS.get(username) == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            init_openai()
            load_tools()
        else:
            st.error("Invalid credentials")


def show_config_page():
    st.title("🔧 API Configuration")
    load_config()
    init_openai()
    with st.form("api_config"):
        st.selectbox("API Type", ["azure","openai"], key='config.api_type')
        st.text_input("API Base", key='config.api_base')
        st.text_input("API Key", type="password", key='config.api_key')
        st.text_input("API Version", key='config.api_version')
        st.text_input("Model", key='config.model')
        if st.form_submit_button("Save"):
            save_config()
            init_openai()
            st.success("Configuration saved!")


def show_chat_page():
    st.title("💬 Chat Intelligent")
    # Files & tools in sidebar
    with st.sidebar:
        st.header("📁 Files")
        files = st.file_uploader("Upload files", type=['pdf','xlsx','xls','docx','pptx','txt','csv'], accept_multiple_files=True)
        for f in files:
            if f.name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files[f.name] = process_uploaded_file(f)
                st.success(f"{f.name} processed!")
        st.header("🛠 Tools")
        if st.button("Reload Tools"):
            load_tools()
            st.success("Tools reloaded!")
        for name in st.session_state.available_tools:
            st.write(f"- {name}")
    # Conversation
    for msg in st.session_state.conversation:
        with st.chat_message(msg['role']):
            st.write(msg['content'])
            if msg.get('timestamp'):
                st.caption(msg['timestamp'])
    if prompt := st.chat_input("Your message..."):
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.conversation.append({"role":"user","content":prompt,"timestamp":ts})
        system_ctx = []
        if st.session_state.uploaded_files:
            contents = "\n\n".join(f"=== {n} ===\n{c}" for n,c in st.session_state.uploaded_files.items())
            system_ctx.append({"role":"system","content":"Attached files:\n"+contents})
        messages = system_ctx + [ {"role":m['role'],"content":m['content']} for m in st.session_state.conversation ]
        res = chat_with_llm(messages)
        if res:
            if hasattr(res, 'function_call') and res.function_call:
                name = res.function_call.name
                args = json.loads(res.function_call.arguments)
                result = st.session_state.available_tools[name]['function'](**args)
                st.session_state.conversation.append({"role":"tool","content":str(result)})
                messages.append({"role":"tool","content":str(result)})
                res = chat_with_llm(messages)
            content = res.content
            ts = datetime.now().strftime("%H:%M:%S")
            st.session_state.conversation.append({"role":"assistant","content":content,"timestamp":ts})
            with st.chat_message("assistant"):
                st.write(content)
                st.caption(f"At {ts}")


def show_tool_page():
    st.title("🔧 Tool Management")
    tabs = st.tabs(["Upload","Manage"])
    with tabs[0]:
        tool_file = st.file_uploader("Upload tool .py", type='py')
        if tool_file:
            path = os.path.join('tools', tool_file.name)
            with open(path,'wb') as f: f.write(tool_file.getbuffer())
            load_tools(); st.success("Tool uploaded")
    with tabs[1]:
        for name, info in st.session_state.available_tools.items():
            with st.expander(name):
                st.write(info['description'])
                st.code(info['schema'])
                st.code(info['function'].__doc__ or "No code docstring")
                if st.button(f"Delete {name}"):
                    os.remove(os.path.join('tools',f'tool-{name}.py'))
                    load_tools(); st.success(f"Deleted {name}")

# ---------- MAIN ----------
def main():
    init_openai()
    load_tools()
    pages = {"Chat": show_chat_page, "Configuration": show_config_page, "Tools": show_tool_page}
    if not st.session_state.logged_in:
        show_login_page()
    else:
        choice = st.sidebar.radio("Navigation", list(pages.keys()), index=list(pages.keys()).index(st.session_state.page))
        st.session_state.page = choice
        pages[choice]()

if __name__ == "__main__":
    main()
