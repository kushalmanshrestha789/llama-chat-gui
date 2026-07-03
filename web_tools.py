"""Web search and fetch utilities for Llama-cpp Chat GUI Pro."""


def search_web(query, max_results=5):
    """Search DuckDuckGo. Returns (success, formatted_string)."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return False, "Web search requires: pip install ddgs"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return True, "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   {r['body']}")
            lines.append(f"   URL: {r['href']}")
        return True, "\n".join(lines)
    except Exception as e:
        return False, f"Search error: {e}"


def fetch_url(url):
    """Fetch and extract text from a URL. Returns (success, formatted_string)."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return False, (
            "URL fetching requires: pip install requests beautifulsoup4"
        )

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type:
            text = resp.text[:8000]
            return True, text
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return True, "\n".join(lines[:200])
    except Exception as e:
        return False, f"Fetch error: {e}"
