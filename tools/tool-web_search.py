# web-search.py

import requests
from bs4 import BeautifulSoup
import urllib.parse

# Schema for tool specification
function_schema = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query to look up on Google"
        },
        "num_results": {
            "type": "number",
            "description": "Number of results to return (default: 5)",
            "default": 5
        }
    },
    "required": ["query"]
}

# Tool description
description = "Performs Google searches and returns organic results. Handles basic anti-bot protection."

# Main function
def function_call(query: str, num_results: int = 5) -> str:
    """
    Performs a Google search and returns formatted results.
    
    Args:
        query: Search term(s)
        num_results: Number of results to return (default 5)
    
    Returns:
        Formatted results with titles and URLs or error message
    """
    try:
        # Configuration
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # Prepare request
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}&hl=en"
        
        # Fetch results
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Extract organic results (div.g is Google's result container)
        for result in soup.select("div.g"):
            title = result.select_one("h3")
            link = result.select_one("a[href]")
            
            if title and link:
                raw_url = link['href']
                
                # Clean Google's tracking URL
                if raw_url.startswith("/url?q="):
                    clean_url = raw_url.split("/url?q=")[1].split("&")[0]
                else:
                    clean_url = raw_url
                
                results.append(f"• {title.text}\n  {clean_url}")
                
                if len(results) >= num_results:
                    break
        
        return "\n\n".join(results) if results else "No results found"
        
    except requests.exceptions.RequestException as e:
        return f"Request failed: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
