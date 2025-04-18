import streamlit as st
import importlib.util
import os
import glob
import sys
import openai
from datetime import datetime
from typing import Any, Dict, List

st.set_page_config(page_title="🧠 Chat LLM + Hybrid Tools", page_icon="🤖")

# -------- 1. Init session --------
def init_session():
    """Initializes session state variables if not yet set."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
        st.session_state.history = []
        st.session_state.tools = {}
        st.session_state.cfg = {}
        st.session_state.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

init_session()
st.title("🧠 LLM + TOOLS (robust, non-native)")

# -------- 2. LLM Provider Selection --------
if not st.session_state.initialized:
    st.subheader("Choose LLM Provider")
    provider = st.selectbox("LLM Provider", ["Local Demo", "OpenAI", "Azure OpenAI"], index=0)
    if provider == "Local Demo":
        st.session_state.cfg = {"provider": "demo"}
    elif provider == "OpenAI":
        key = st.text_input("OpenAI API Key", type="password")
        st.session_state.cfg = {"provider": "openai", "key": key}
    else:  # Azure
        endpoint = st.text_input("Azure Endpoint", value="https://")
        az_key = st.text_input("Azure API Key", type="password")
        model = st.text_input("Azure Model Deployment", value="")
        api_version = st.text_input("API Version", value="")
        st.session_state.cfg = {
            "provider": "azure",
            "endpoint": endpoint,
            "key": az_key,
            "model": model,
            "apiver": api_version
        }
    if st.button("Confirm and Start"):
        st.session_state.initialized = True
        st.rerun()
    st.stop()

config = st.session_state.cfg

# -------- 3. Dynamic Tools Management --------
TOOLS_FOLDER = "tools"
os.makedirs(TOOLS_FOLDER, exist_ok=True)

def load_tools() -> Dict[str, Any]:
    """Dynamically import Python modules as tools from the tools folder."""
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
            st.warning(f"Failed to import {file}: {e}")
    return tool_modules

if st.button("🔁 Reload Tools"):
    st.session_state.tools = load_tools()
elif not st.session_state.tools:
    st.session_state.tools = load_tools()
tools = st.session_state.tools

# -------- 4. Sidebar: Upload/Delete/Test Tools --------
st.sidebar.header("🧩 Tools Management")
with st.sidebar.expander("➕ Upload new tool"):
    uploaded = st.file_uploader("tool-xxx.py", type="py")
    if uploaded:
        file_path = os.path.join(TOOLS_FOLDER, uploaded.name)
        with open(file_path, "wb") as f:
            f.write(uploaded.read())
        st.session_state.tools = load_tools()
        st.success(f"Uploaded: {uploaded.name}")
        st.experimental_rerun()

with st.sidebar.expander("🗑️ Delete Tool"):
    available_tools = list(tools.keys())
    if available_tools:
        selected = st.selectbox("Select to Delete", options=available_tools)
        if st.button(f"Delete {selected}"):
            tool_info = tools[selected]
            os.remove(tool_info["source"])
            del st.session_state.tools[selected]
            st.success(f"{selected} deleted.")
            st.experimental_rerun()
    else:
        st.info("No tools loaded.")

with st.sidebar.expander("📋 List & Test Tool"):
    import inspect
    for tname, tinfo in tools.items():
        st.write(f"**{tname}** - {os.path.basename(tinfo['source'])} - {tinfo.get('doc','')}")
        with st.form(f"test_{tname}"):
            params = {}
            sig = inspect.signature(tinfo["function_call"])
            for pname, param in sig.parameters.items():
                default = "" if param.default == inspect.Parameter.empty else param.default
                val = st.text_input(f"{tname}:{pname}", value=str(default))
                params[pname] = val
            if st.form_submit_button("Test"):
                try:
                    typed_params = {}
                    for k, v in params.items():
                        annotation = sig.parameters[k].annotation
                        if annotation is int:
                            typed_params[k] = int(v)
                        elif annotation is float:
                            typed_params[k] = float(v)
                        else:
                            typed_params[k] = v
                    result = tinfo["function_call"](**typed_params)
                    st.success(f"Result: {result}")
                except Exception as ex:
                    st.error(str(ex))

# -------- 5. LLM + Tool Call (by matcher or key) --------
import re

def extract_tool_usages(prompt: str, tools: Dict[str, Any]) -> List[str]:
    """Returns a list of tool names referenced in the prompt."""
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

def call_llm(messages: List[Dict[str, Any]], tools: Dict[str, Any] = None) -> Dict[str, Any]:
    """Calls the LLM and optionally tool(s), returning AI response including tool step info."""
    last_user_input = messages[-1]["content"]
    used_tools = extract_tool_usages(last_user_input, tools)
    steps = []
    tool_results = {}

    for name in used_tools:
        tinfo = tools[name]
        import inspect
        sig = inspect.signature(tinfo["function_call"])
        args = {}
        for pname, param in sig.parameters.items():
            match = re.search(rf"{pname}\s*=\s*([-\w.]+)", last_user_input)
            if match:
                val = match.group(1)
                try:
                    # Type autocast according to annotation if available
                    annotation = param.annotation
                    if annotation is int:
                        val = int(val)
                    elif annotation is float:
                        val = float(val)
                except Exception:
                    pass
                args[pname] = val
            else:
                # Default from signature, still try to cast if annotated
                if param.default != inspect.Parameter.empty:
                    args[pname] = param.default
                elif param.annotation is int:
                    args[pname] = 0
                elif param.annotation is float:
                    args[pname] = 0.0
                else:
                    args[pname] = ""
        try:
            output = tinfo["function_call"](**args)
        except Exception as ex:
            output = f"Error calling tool: {ex}"
        steps.append({"tool": name, "args": args, "output": output})
        tool_results[name] = output

    # Generate LLM response using tool outputs
    base_prompt = (
        f"The user requested to use the following tools: {steps}. "
        "Provide a coherent, clear answer using the results."
    )
    response_content = ""
    if config["provider"] == "openai":
        openai.api_key = config["key"]
        msgs = [{"role": "system", "content": base_prompt}] + messages
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=msgs
            )
            response_content = response["choices"][0]["message"]["content"]
        except Exception as e:
            response_content = f"(OpenAI Error: {e}) - Tool results: {tool_results}"
    elif config["provider"] == "azure":
        openai.api_type = "azure"
        openai.api_version = config["apiver"]
        openai.api_key = config["key"]
        openai.api_base = config["endpoint"]
        msgs = [{"role": "system", "content": base_prompt}] + messages
        try:
            response = openai.ChatCompletion.create(
                engine=config["model"],
                messages=msgs
            )
            response_content = response["choices"][0]["message"]["content"]
        except Exception as e:
            response_content = f"(Azure Error: {e}) - Tool results: {tool_results}"
    else:
        response_content = f"(Demo/Mock LLM Response) – Tool results: {tool_results}"

    return {"role": "assistant", "content": response_content, "tools_steps": steps}

# -------- 6. Chat Display --------
st.subheader("💬 Conversation")
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("tools_steps"):
            st.write("**Tool details:**")
            for step in m["tools_steps"]:
                st.info(f"> **{step['tool']}** — Args: `{step['args']}` — Result: `{step['output']}`")

if prompt := st.chat_input("Your message..."):
    user_msg = {"role": "user", "content": prompt}
    st.session_state.history.append(user_msg)
    with st.spinner("Thinking..."):
        reply = call_llm(st.session_state.history, tools)
        st.session_state.history.append(reply)
        with st.chat_message("assistant"):
            st.write(reply["content"])
            if reply.get("tools_steps"):
                st.write("**Tool details:**")
                for step in reply["tools_steps"]:
                    st.info(f"> **{step['tool']}** — Args: `{step['args']}` — Result: `{step['output']}`")
