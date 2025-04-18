# web-search.py

import requests
from bs4 import BeautifulSoup
import urllib.parse

# ----- CONFIGURATION -----
function_schema = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string", 
            "description": "Search term to look up on Google",
            "examples": ["Python documentation"]
        },
        "max_results": {
            "type": "number",
            "description": "Maximum number of results to return",
            "default": 3,
            "minimum": 1,
            "maximum": 10
        }
    },
    "required": ["query"]
}

description = """Performs Google web searches and returns structured results. 
Features:
- Bypasses basic bot protection with realistic headers
- Cleans tracking parameters from URLs
- Handles errors gracefully"""

# ----- MAIN FUNCTION -----
def function_call(query: str, max_results: int = 3) -> str:
    """
    Executes a Google search and returns formatted results
    
    Args:
        query (str): Search query (e.g., "weather in Paris")
        max_results (int): Number of results to return (1-10)
    
    Returns:
        str: Formatted results (title + URL) or error message
    
    Examples:
        >>> function_call("Python 3.12 release notes")
        "• Python 3.12 Release Notes - https://docs.python.org/..."
    """
    try:
        # --- Prepare request ---
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/"
        }
        
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded_query}&num={max_results}"

        # --- Execute search ---
        response = requests.get(search_url, headers=headers, timeout=8)
        response.raise_for_status()

        # --- Parse results ---
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Detection pattern for organic results
        for result in soup.select('div[class*="tF2Cxc"]'):
            title = result.select_one('h3')
            link = result.select_one('a[href]')
            
            if not (title and link):
                continue
                
            # URL cleaning
            raw_url = link['href']
            if '/url?q=' in raw_url:
                clean_url = raw_url.split('/url?q=')[1].split('&')[0]
                clean_url = urllib.parse.unquote(clean_url)
            else:
                clean_url = raw_url

            results.append(f"• {title.text.strip()}\n  {clean_url}")
            
            if len(results) >= max_results:
                break

        # --- Return handling ---
        if not results:
            return "🔍 No results found - Try different keywords or check your connection"
            
        return "\n\n".join(results)
        
    except requests.exceptions.RequestException as e:
        return f"⚠️ Search failed: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"
