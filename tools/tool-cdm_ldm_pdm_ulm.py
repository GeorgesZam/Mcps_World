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
            "description": "Raw PlantUML content for the MCD or other UML diagram",
            "examples": [
                "@startuml\nentity Customer {\n  *id : Integer\n  name : String\n}\nentity Order {\n  *id : Integer\n  date : Date\n}\nCustomer ||--o{ Order : places\n@enduml"
            ]
        },
        "filetype": {
            "type": "string",
            "description": "File extension for source (puml) or output format (png)",
            "default": "puml",
            "enum": ["puml", "png"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "PlantUML (MCD & other UML) generator with native Streamlit preview, rendering, and download buttons"

# Main function (to integrate into your Streamlit app)
def function_call(filename: str, content: str, filetype: str = "puml"):
    """Creates a Streamlit interface to preview PlantUML code, render the diagram, and provide download buttons."""
    import streamlit as st
    from io import BytesIO
    try:
        from plantuml import PlantUML
    except ImportError:
        st.warning("plantuml package not found. Install via `pip install plantuml` to enable diagram rendering.")
        PlantUML = None

    # Preview PlantUML source
    with st.expander("📁 PlantUML Source Preview"):
        st.code(content, language="puml")

    # Render and display diagram if possible
    if PlantUML:
        try:
            server = PlantUML(url="http://www.plantuml.com/plantuml/img/")
            png_data = server.processes(content)
            if png_data:
                st.image(png_data, caption="Rendered Diagram")
                # Download rendered PNG
                st.download_button(
                    label="⬇️ Download Diagram (PNG)",
                    data=png_data,
                    file_name=f"{filename}.png",
                    mime="image/png",
                    key=f"download_{filename}_png"
                )
        except Exception as e:
            st.error(f"Diagram rendering failed: {e}")

    # Download PlantUML source
    st.download_button(
        label="⬇️ Download PlantUML File",
        data=content,
        file_name=f"{filename}.puml",
        mime="text/plain",
        key=f"download_{filename}_puml"
    )

    return (
        "Your PlantUML diagram is ready! You can view or download the source and the rendered image above. "
        "Click the respective buttons to get your files."  
    )
