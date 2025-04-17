import streamlit as st
import requests
import base64
import io

# Store de conversation
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("ChatGPT-like App avec Upload & Whisper")

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

# Whisper - Reconnaissance vocale via audio upload
st.subheader("Reconnaissance vocale (Whisper)")
audio_file = st.file_uploader("Uploader un fichier audio (mp3, wav)", type=['mp3', 'wav'])
if audio_file is not None:
    audio_bytes = audio_file.read()
    st.session_state['uploaded_audio'] = audio_bytes
    st.success(f"Audio '{audio_file.name}' prêt pour Whisper.")

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
