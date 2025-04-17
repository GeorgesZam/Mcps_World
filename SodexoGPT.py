import streamlit as st
import requests
import base64
import subprocess
import time
import os

# Lancement du serveur en arrière-plan
server_process = None
try:
    server_process = subprocess.Popen(['python', 'Server.py'], 
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
    # Attendre un peu que le serveur démarre
    time.sleep(2)
    st.sidebar.success("Serveur local démarré en arrière-plan")
except Exception as e:
    st.sidebar.error(f"Erreur lors du démarrage du serveur: {e}")

# Configuration de la page
st.set_page_config(page_title="SodexoGPT", layout="wide")

# Initialisation de l'historique
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("SodexoGPT - Chat")

# Sidebar pour l'upload de fichier
with st.sidebar:
    st.header("Options")
    uploaded_file = st.file_uploader("Joindre un fichier", type=None)
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        b64_content = base64.b64encode(file_bytes).decode()
        st.session_state['uploaded_file'] = {
            "filename": uploaded_file.name,
            "data": b64_content
        }
        st.success(f"Fichier '{uploaded_file.name}' prêt à être envoyé.")

# Section principale - Affichage de l'historique du chat
st.container(height=500)
for role, msg in st.session_state['history']:
    if role == "Vous":
        st.markdown(f"<div style='background-color:#e6f7ff; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role}:</b> {msg}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background-color:#f0f0f0; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role}:</b> {msg}</div>", unsafe_allow_html=True)

# Zone de saisie utilisateur
user_input = st.text_input("Message:", "")

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("Envoyer", use_container_width=True):
        if user_input:
            # Afficher le message utilisateur immédiatement
            st.session_state['history'].append(("Vous", user_input))
            
            # Préparation des données à envoyer
            data = {"question": user_input}
            
            # Ajout du fichier si fourni
            if 'uploaded_file' in st.session_state:
                data["file"] = st.session_state['uploaded_file']
            
            # Envoie la question au backend
            try:
                response = requests.post("http://localhost:8000/ask", json=data)
                if response.ok:
                    answer = response.json().get("answer", "")
                    st.session_state['history'].append(("Assistant", answer))
                else:
                    msg = response.text
                    st.error(f"Erreur serveur: {msg}")
            except requests.exceptions.ConnectionError:
                st.error("Impossible de se connecter au serveur. Vérifiez que le serveur est bien démarré.")
            
            # Rechargement de la page pour afficher les nouveaux messages
            st.experimental_rerun()

# Gestion de la fermeture propre du serveur
def cleanup():
    if server_process:
        server_process.terminate()
        server_process.wait()
        print("Serveur arrêté")

# Enregistre la fonction cleanup pour qu'elle soit appelée à la fermeture
import atexit
atexit.register(cleanup)
