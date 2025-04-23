# Tool schema
function_schema = {
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Name of the file WITHOUT extension",
            "examples": ["my_conceptual_model"]
        },
        "content": {
            "type": "string",
            "description": "Raw PlantUML content for the MCD diagram",
            "examples": [
                "@startuml\nentity Customer {\n  *id : Integer\n  name : String\n}\nentity Order {\n  *id : Integer\n  date : Date\n}\nCustomer ||--o{ Order : places\n@enduml"
            ]
        },
        "filetype": {
            "type": "string",
            "description": "File extension",
            "default": "puml",
            "enum": ["puml", "txt", "md"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "PlantUML (MCD) file generator with native Streamlit download button"

# Main function (to integrate into your Streamlit app)
def function_call(filename: str, content: str, filetype: str = "puml"):
    """Creates a Streamlit download button with file preview for PlantUML diagrams."""
    import streamlit as st

    # User interface: preview the PlantUML code
    with st.expander("📁 PlantUML Preview"):
        st.code(content, language="puml")

    # Generate the download button
    st.download_button(
        label="⬇️ Download PlantUML File",
        data=content,
        file_name=f"{filename}.{filetype}",
        mime="text/plain",
        key=f"download_{filename}"
    )

    return (
        "The user now has access to a download button for their PlantUML file. "
        "You can tell them: 'You can click the Download PlantUML File button above to download your diagram file.' "
        "Do not provide an external link."
    )
