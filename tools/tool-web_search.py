# tool/web-search.py

import requests
from bs4 import BeautifulSoup

# Schéma pour spécifier la structure attendue des appels
function_schema = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "La requête de recherche Google"
        }
    },
    "required": ["query"]
}

def function_call(query: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        }
        response = requests.get(f"https://www.google.com/search?q={query}", headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for g in soup.select("div.g"):
            title = g.select_one("h3")
            link = g.select_one("a")
            if title and link:
                results.append(f"{title.text} ({link['href']})")
            if len(results) >= 5:
                break

        if not results:
            return "Aucun résultat trouvé."

        return "\n".join(results)

    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"
