# Tool schema (identique à la version 1)
function_schema = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Nom du fichier SANS extension",
            "examples": ["mon_script"]
        },
        "content": {
            "type": "string",
            "description": "Contenu du fichier",
            "examples": ["print('Hello World')"]
        },
        "filetype": {
            "type": "string",
            "description": "Extension du fichier",
            "default": "py",
            "enum": ["py", "txt", "json", "csv"]
        }
    },
    "required": ["filename", "content"]
}

# Main function modifiée pour Flask
def function_call(filename: str, content: str, filetype: str = "py"):
    """Génère un fichier téléchargeable via HTTP"""
    from flask import make_response
    import io
    
    # Crée un fichier en mémoire
    buffer = io.BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}.{filetype}'
    response.mimetype = f"text/{filetype}" if filetype != 'json' else 'application/json'
    
    return response
