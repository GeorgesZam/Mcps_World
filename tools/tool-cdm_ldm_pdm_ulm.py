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
            "description": "Raw Mermaid content for the MCD or other UML diagram",
            "examples": [
                "```mermaid\nerDiagram\n    CUSTOMER {\n      integer id\n      string name\n    }\n    ORDER {\n      integer id\n      date date\n    }\n    CUSTOMER ||--o{ ORDER : places\n```"
            ]
        },
        "filetype": {
            "type": "string",
            "description": "File extension for source (mmd) or output format (png)",
            "default": "mmd",
            "enum": ["mmd", "png"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "Mermaid (MCD & other UML) generator with native Streamlit preview, rendering, and download buttons"

# Main function (to integrate into your Streamlit app)
def function_call(filename: str, content: str, filetype: str = "mmd"):
    """Creates a Streamlit interface to preview Mermaid code, render the diagram, and provide download buttons."""
    import streamlit as st

    # Preview Mermaid source
    with st.expander("📁 Mermaid Source Preview"):
        st.code(content, language="mermaid")

    # Render and display diagram using Mermaid.js
    # (requires internet or local Mermaid.js bundle)
    mermaid_html = f"""
    <div class="mermaid">
    {content}
    </div>
    <script>
      if (window.mermaid) {{
        mermaid.initialize({{ startOnLoad: true }});
      }} else {{
        const script = document.createElement('script');
        script.src = "https://unpkg.com/mermaid@10/dist/mermaid.min.js";
        script.onload = () => mermaid.initialize({{ startOnLoad: true }});
        document.head.appendChild(script);
      }}
    </script>
    """
    st.components.v1.html(mermaid_html, height=400)

    # Download rendered PNG placeholder (actual server-side rendering would require additional tooling)
    # Here we only offer direct download of Mermaid source
    st.download_button(
        label="⬇️ Download Mermaid File",
        data=content,
        file_name=f"{filename}.mmd",
        mime="text/plain",
        key=f"download_{filename}_mmd"
    )

    return (
        "Your Mermaid diagram is ready! You can view the source in the expander above, "
        "see the rendered diagram, and download the .mmd file. Click the respective buttons to get your files."
    )
