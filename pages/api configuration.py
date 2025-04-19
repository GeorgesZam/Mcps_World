import streamlit as st
from main import save_config, init_openai

st.title("🔧 API Configuration")

with st.form("api_config"):
    st.session_state.config['api_type'] = st.selectbox(
        "API Type",
        ["azure", "openai"],
        index=0 if st.session_state.config['api_type'] == "azure" else 1
    )
    
    st.session_state.config['api_base'] = st.text_input(
        "API Endpoint",
        value=st.session_state.config['api_base']
    )
    
    st.session_state.config['api_key'] = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.config['api_key']
    )
    
    st.session_state.config['api_version'] = st.text_input(
        "API Version",
        value=st.session_state.config['api_version']
    )
    
    st.session_state.config['model'] = st.text_input(
        "Model",
        value=st.session_state.config['model']
    )
    
    if st.form_submit_button("Save Configuration"):
        save_config()
        init_openai()
        st.success("Configuration saved!")
