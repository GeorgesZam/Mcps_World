# Tool schema
tool_schema = {
    "type": "object",
    "properties": {
        "tool_name": {
            "type": "string",
            "description": "Name of the new Streamlit tool module (without extension)",
            "examples": ["diagram_tool"]
        },
        "description": {
            "type": "string",
            "description": "Brief description of what the new tool does",
            "examples": ["Generates PlantUML-based MCD diagrams with preview and download"]
        },
        "properties": {
            "type": "array",
            "description": "List of input properties for the new tool schema",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Property name"},
                    "type": {"type": "string", "description": "JSON schema type (e.g., string, array)"},
                    "description": {"type": "string", "description": "Description of the property"},
                    "examples": {"type": "array", "items": {"type": "string"}, "description": "Example values for this property"}
                },
                "required": ["name", "type", "description"]
            }
        }
    },
    "required": ["tool_name", "description", "properties"]
}

# Tool description
description = (
    "Generates boilerplate Streamlit tool code based on the tutorial: "
    "defines schema, description, function and integrates download buttons without links"
)

# Main function (to integrate in your Streamlit app)
def function_call(tool_name: str, description: str, properties: list):
    """Creates a Python module generating a new Streamlit tool template."""
    import streamlit as st
    import json

    # Build schema dict string
    schema_props = []
    for prop in properties:
        examples = prop.get("examples", [])
        ex_str = f"[" + ", ".join(f'\"{e}\"' for e in examples) + "]" if examples else "[]"
        schema_props.append(
            f"        \"{prop['name']}\": {{\"type\": \"{prop['type']}\", \"description\": \"{prop['description']}\", \"examples\": {ex_str}}}"
        )
    schema_content = (
        "function_schema = {\n"
        "    \"type\": \"object\",\n"
        "    \"properties\": {\n"
        + ",\n".join(schema_props)
        + "\n    },\n"
        "    \"required\": [" + ", ".join(f'\"{p['name']}\"' for p in properties) + "]\n}"
    )

    # Template for code file
    code = f"""
# Auto-generated Streamlit tool: {tool_name}.py
{schema_content}

description = "{description}"

def function_call({', '.join(p['name'] for p in properties)}):
    """{description}"""
    import streamlit as st

    # Preview inputs
    with st.expander("📁 Input Preview"):
"""
    for p in properties:
        code += f"        st.write(\"{p['name']}:\", {p['name']})\n"
    code += """

    # (Add processing logic here following the tutorial steps)
    # Download button placeholder
    tool_data = json.dumps({{{', '.join(f'\"{p['name']}\": {p['name']}' for p in properties)}}}, indent=2)
    st.download_button(
        label="⬇️ Download Generated Tool Code",
        data=tool_data,
        file_name=f"{tool_name}.py",
        mime="text/plain",
        key="download_template"
    )

    return "Your Streamlit tool template is ready! Expand the code above, customize, and use the download button."
"""

    # Display generated code
    st.code(code, language="python")
    return "Use the button below to download your new tool module."
