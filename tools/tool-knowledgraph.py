# Tool schema
function_schema = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Nom du fichier SANS extension",
            "examples": ["mon_knowledge_graph"]
        },
        "content": {
            "type": "string", 
            "description": "Contenu brut du knowledge graph",
            "examples": [
                "@prefix ex: <http://example.com/> .\nex:Alice ex:knows ex:Bob ."
            ]
        },
        "filetype": {
            "type": "string",
            "description": "Extension du fichier de knowledge graph",
            "default": "ttl",
            "enum": ["ttl", "rdf", "jsonld", "graphml", "csv"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "Générateur de fichiers de knowledge graph avec bouton de téléchargement natif Streamlit"

# Main function (à intégrer dans un script Streamlit)
def function_call(filename: str, content: str, filetype: str = "ttl"):
    """Crée un bouton de téléchargement Streamlit pour un knowledge graph avec prévisualisation"""
    import streamlit as st

    # Prévisualisation du contenu selon le format
    with st.expander("📁 Prévisualisation du knowledge graph"):
        if filetype in ["ttl", "rdf"]:
            st.code(content, language="ttl")
        elif filetype == "jsonld":
            try:
                import json
                parsed = json.loads(content)
                st.json(parsed)
            except Exception:
                st.code(content, language="json")
        elif filetype == "graphml":
            st.code(content, language="xml")
        else:
            st.code(content, language=filetype)

    # Génération du bouton de téléchargement avec MIME approprié
    mime = {
        "ttl": "text/turtle",
        "rdf": "application/rdf+xml",
        "jsonld": "application/ld+json",
        "graphml": "application/xml",
        "csv": "text/csv"
    }.get(filetype, f"text/{filetype}")

    st.download_button(
        label="⬇️ Télécharger le knowledge graph",
        data=content,
        file_name=f"{filename}.{filetype}",
        mime=mime,
        key=f"download_{filename}"
    )

    return f"Knowledge graph {filename}.{filetype} prêt au téléchargement (Taille : {len(content)} octets)"
