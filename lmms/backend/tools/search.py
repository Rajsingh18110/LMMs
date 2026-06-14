


def web_search(query: str, max_results: int = 5) -> str:
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSummary: {r.get('body', '')}\n"
                )
    except Exception as e:
        return f"Search failed: {str(e)}"

    if not results:
        return "No results found."

    return "\n---\n".join(results)
