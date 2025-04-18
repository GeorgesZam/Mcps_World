import requests
from bs4 import BeautifulSoup
import urllib.parse

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
    """
    Scraping Google Search avec timeout, encodage, détection de blocage, et CSS selectors à jour.
    """
    try:
        # Encodage de la requête
        params = {
            "q": query,
            "hl": "fr",         # langue
            "gl": "fr",         # pays
            "num": 5            # nombre de résultats
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8"
        }
        resp = requests.get(
            "https://www.google.com/search",
            params=params,
            headers=headers,
            timeout=5
        )
        resp.raise_for_status()
        html = resp.text

        # Détection d’un éventuel blocage / captcha
        if "Our systems have detected unusual traffic" in html or "désolé" in html.lower():
            return "Erreur : Google a bloqué la requête (Captcha ou filtrage)."

        soup = BeautifulSoup(html, "html.parser")
        results = []
        # Google change souvent sa structure : on cible le container principal
        for g in soup.select("div#search .g"):
            title_tag = g.find("h3")
            link_tag  = g.find("a", href=True)
            if title_tag and link_tag:
                title = title_tag.get_text().strip()
                href  = link_tag["href"]
                # Nettoyage si Google renvoie un lien de tracking
                if href.startswith("/url?"):
                    href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("q", [href])[0]
                results.append(f"{title} — {href}")
            if len(results) >= 5:
                break

        return "\n".join(results) if results else "Aucun résultat trouvé."
    except requests.Timeout:
        return "Erreur : délai de connexion dépassé."
    except Exception as e:
        return f"Erreur inattendue : {e}"
