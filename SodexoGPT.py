import streamlit as st
import requests
import base64
import io
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

# Store de conversation
if 'history' not in st.session_state:
    st.session_state['history'] = []

# Upload de fichier
uploaded_file = st.file_uploader("Uploader un fichier pour l'envoyer au serveur", type=None)
if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    b64_content = base64.b64encode(file_bytes).decode()
    st.session_state['uploaded_file'] = {
        "filename": uploaded_file.name,
        "data": b64_content
    }
    st.success(f"Fichier '{uploaded_file.name}' prêt à être envoyé.")

# Input utilisateur
user_input = st.text_input("Posez votre question à ChatGPT :", "")

if st.button("Envoyer"):
    data = {"question": user_input}

    # Ajout d'outils / fichiers si fournis
    if 'uploaded_file' in st.session_state:
        data["file"] = st.session_state['uploaded_file']
    if 'uploaded_audio' in st.session_state:
        data["audio"] = base64.b64encode(st.session_state['uploaded_audio']).decode()

    # Envoie la question (et les outils si présents) à ton backend local
    response = requests.post("http://localhost:8000/ask", json=data)
    if response.ok:
        answer = response.json().get("answer", "")
        st.session_state['history'].append(("Vous", user_input))
        st.session_state['history'].append(("Assistant", answer))
    else:
        msg = response.text
        st.error(f"Erreur serveur: {msg}")

# Affichage historique
st.subheader("Historique de la conversation :")
for role, msg in st.session_state['history']:
    st.markdown(f"**{role}**: {msg}")

# Gestion de la fermeture propre du serveur quand l'application Streamlit se termine
def cleanup():
    if server_process:
        server_process.terminate()
        server_process.wait()
        print("Serveur arrêté")

# Enregistre la fonction cleanup pour qu'elle soit appelée à la fermeture
import atexit
atexit.register(cleanup)
