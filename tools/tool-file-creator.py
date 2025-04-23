# tool-<ton_tool>.py

function_schema = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Nom du fichier SANS extension"
        },
        "content": {
            "type": "string",
            "description": "Contenu brut du fichier"
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

description = "Générateur de fichiers (métadonnées uniquement)"

def function_call(filename: str, content: str, filetype: str = "py"):
    """
    Ne fait plus d'affichage Streamlit,
    mais renvoie un dict avec le nom, le contenu et le type.
    """
    return {
        "filename": filename,
        "content": content,
        "filetype": filetype
    }
