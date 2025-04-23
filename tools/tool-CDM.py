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
            "description": "Raw content of the MCD file",
            "examples": [
                "Entity Customer {\n    id: Integer\n    name: String\n}\n\nEntity Order {\n    id: Integer\n    date: Date\n}\n\nRelationship places {\n    Customer 1—* Order\n}"
            ]
        },
        "filetype": {
            "type": "string",
            "description": "File extension",
            "default": "mcd",
            "enum": ["mcd", "txt", "json", "md"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "MCD (Conceptual Data Model) file generator with native Streamlit download button"

# Main function (to integrate into your Streamlit app)
def function_call(filename: str, content: str, filetype: str = "mcd"):
    """Creates a Streamlit download button with file preview."""
    import streamlit as st

    # User interface: preview the file content
    with st.expander("📁 File Preview"):
        st.code(content, language=filetype)

    # Generate the download button
    st.download_button(
        label="⬇️ Download File",
        data=content,
        file_name=f"{filename}.{filetype}",
        mime="application/json" if filetype == "json" else f"text/{filetype}",
        key=f"download_{filename}"
    )

    return (
        "The user now has access to a download button for their MCD file. "
        "You can tell them: “You can click the Download File button above to get your file.” "
        "Do not provide an external link."
    )
