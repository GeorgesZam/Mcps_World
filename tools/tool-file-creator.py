# Tool schema
function_schema = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Nom du fichier SANS extension",
            "examples": ["mon_programme"]
        },
        "content": {
            "type": "string", 
            "description": "Contenu brut du fichier",
            "examples": ["def hello():\n    print('Bonjour le monde')"]
        },
        "filetype": {
            "type": "string",
            "description": "Extension du fichier",
            "default": "py",
            "enum": ["py", "txt", "csv", "md", "json"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "Générateur de fichiers avec bouton de téléchargement natif Streamlit"

# Main function (à intégrer dans un script Streamlit)
def function_call(filename: str, content: str, filetype: str = "py"):
    """Crée un bouton de téléchargement Streamlit avec prévisualisation"""
    import streamlit as st

    # Interface utilisateur
    with st.expander("📁 Prévisualisation du fichier"):
        st.code(content, language=filetype)

    # Génération du bouton de téléchargement
    st.download_button(
        label="⬇️ Télécharger le fichier",
        data=content,
        file_name=f"{filename}.{filetype}",
        mime="application/json" if filetype == "json" else f"text/{filetype}",
        key=f"download_{filename}"
    )

    st.video("https://www.youtube.com/watch?v=v2eNUENWi2k")

    return f"Fichier {filename}.{filetype} prêt au téléchargement (Taille : {len(content)} octets)"
