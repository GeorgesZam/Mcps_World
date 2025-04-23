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
description = "Affiche et télécharge un knowledge graph dans Streamlit via NetworkX avec layout physique"

# Main function (à intégrer dans un script Streamlit)
def function_call(filename: str, content: str, filetype: str = "ttl"):
    """Parse le knowledge graph, l'affiche sous forme de graphe interactif avec NetworkX (force-directed) et propose son téléchargement"""
    import streamlit as st
    from rdflib import Graph
    import networkx as nx
    import matplotlib.pyplot as plt

    st.title("Knowledge Graph Viewer")
    st.write("## Prévisualisation brute")
    # Affichage brut
    if filetype == "jsonld":
        st.json(content)
    else:
        st.code(content, language="ttl" if filetype in ["ttl","rdf"] else filetype)

    st.write("---")
    st.write("## Visualisation du graphe (NetworkX avec layout physique)")

    # Parse et création du graphe RDF
    rdf_graph = Graph()
    try:
        rdf_graph.parse(data=content, format=filetype)
    except Exception as e:
        st.error(f"Erreur de parsing du knowledge graph: {e}")
        return

    # Construction du graphe NetworkX dirigé
    nx_graph = nx.DiGraph()
    for subj, pred, obj in rdf_graph:
        nx_graph.add_edge(str(subj), str(obj), label=str(pred))

    # Calcul du layout physique (force-directed)
    pos = nx.spring_layout(nx_graph, k=None, iterations=50)

    # Dessin du graphe
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw_networkx_nodes(nx_graph, pos, ax=ax, node_size=500)
    nx.draw_networkx_edges(nx_graph, pos, ax=ax, arrowstyle='->')
    nx.draw_networkx_labels(nx_graph, pos, ax=ax, font_size=8)
    edge_labels = nx.get_edge_attributes(nx_graph, 'label')
    nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels=edge_labels, font_size=6)
    plt.axis('off')
    st.pyplot(fig)

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
