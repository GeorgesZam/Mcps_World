import openai
import importlib.util, sys, glob, os
import streamlit as st

# ---- Chargement dynamique des tools ----
def load_tools():
    tool_defs = []
    tool_calls = {}
    for file in glob.glob("tools/tool-*.py"):
        tool_name = os.path.splitext(os.path.basename(file))[0][5:]
        spec = importlib.util.spec_from_file_location(f"tools.{tool_name}", file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"tools.{tool_name}"] = mod
        spec.loader.exec_module(mod)
        fn_schema = getattr(mod, "function_schema", None)
        if fn_schema:
            tool_defs.append({
                "name": tool_name,
                "description": fn_schema.get("description", tool_name),
                "parameters": {
                    k:v for k,v in fn_schema.items() if k in ("type","properties","required")
                }
            })
            tool_calls[tool_name] = mod.function_call
    return tool_defs, tool_calls

openai.api_key = st.text_input("OpenAI Key", type="password", key="oaikey")
if not openai.api_key: st.stop()
tool_defs, tool_calls = load_tools()

# ---- Chat + Tool Calling natif ----
if "history" not in st.session_state: 
    st.session_state.history = []

userq = st.chat_input("Votre question...")
if userq:
    st.session_state.history.append({"role":"user","content":userq})

msgs = st.session_state.history.copy()
need_tool = True
tools_steps = []
while need_tool:
    result = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=msgs,
        tools=tool_defs,
        tool_choice="auto"
    )
    m = result["choices"][0]["message"]
    if m.get("tool_calls"):
        for call in m["tool_calls"]:
            toolname = call["function"]["name"]
            args = eval(call["function"]["arguments"])
            toolres = tool_calls[toolname](**args)
            tools_steps.append({"tool":toolname,"args":args,"output":toolres})
            msgs.append({
                "tool_call_id": call["id"],
                "role":"tool",
                "name":toolname,
                "content":str(toolres),
            })
    else:
        need_tool = False
        st.session_state.history.append({"role":"assistant","content":m["content"]})
        st.write("🤖", m["content"])
        if tools_steps:
            st.write("🛠️ **Détail des appels tools :**")
            for step in tools_steps:
                st.info(f"*{step['tool']}* Args: `{step['args']}` -> Résultat: `{step['output']}`")
