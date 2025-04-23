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
            "description": "Contenu brut du knowledge graph (TTL, RDF/XML, JSON-LD)",
            "examples": [
                "@prefix ex: <http://example.com/> .\nex:Alice ex:knows ex:Bob ."
            ]
        },
        "filetype": {
            "type": "string",
            "description": "Format du knowledge graph",
            "default": "ttl",
            "enum": ["ttl", "rdf", "jsonld"]
        }
    },
    "required": ["filename", "content"]
}

# Tool description
description = "Affiche et télécharge un knowledge graph dans Streamlit avec rendu Graphviz"

# Main function (à intégrer dans un script Streamlit)
def function_call(filename: str, content: str, filetype: str = "ttl"):
    """Parse le knowledge graph, l'affiche sous forme de graphe interactif et propose son téléchargement"""
    import streamlit as st
    from rdflib import Graph

    st.title("Knowledge Graph Viewer")
    st.write("## Prévisualisation brute")
    # Affichage brut
    if filetype == "jsonld":
        st.json(content)
    else:
        st.code(content, language="ttl" if filetype in ["ttl","rdf"] else filetype)

    st.write("---")
    st.write("## Visualisation du graphe")
    # Parse et création du graphe RDF
    graph = Graph()
    try:
        graph.parse(data=content, format=filetype)
    except Exception as e:
        st.error(f"Erreur de parsing du knowledge graph: {e}")
        return

    # Génération du DOT pour Graphviz
    dot_lines = ["digraph G {", "  rankdir=LR;", "  node [shape=ellipse];"]
    for subj, pred, obj in graph:
        dot_lines.append(f'  "{subj}" -> "{obj}" [label="{pred}"];')
    dot_lines.append("}")
    dot_graph = "\n".join(dot_lines)

    # Affichage via Graphviz
    st.graphviz_chart(dot_graph)

    st.write("---")
    # Bouton de téléchargement
    mime = {
        "ttl": "text/turtle",
        "rdf": "application/rdf+xml",
        "jsonld": "application/ld+json"
    }.get(filetype, f"text/{filetype}")

    with st.expander("⬇️ Télécharger le knowledge graph"):
        st.download_button(
            label="Télécharger",
            data=content,
            file_name=f"{filename}.{filetype}",
            mime=mime,
            key=f"download_{filename}"
        )

    return f"Knowledge graph {filename}.{filetype} prêt (taille: {len(content)} octets)"
