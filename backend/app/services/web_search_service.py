from ddgs import DDGS


def search_web(
    question: str,
    max_results: int = 5
) -> list[dict]:
    """
    Search the web for a question.

    Returns a list of search results containing:
    - title
    - url
    - snippet
    """

    results = []

    with DDGS() as ddgs:
        search_results = ddgs.text(
            question,
            max_results=max_results
        )

        for result in search_results:
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                }
            )

    return results

def build_web_answer(
    question: str,
    max_results: int = 5
) -> dict:
    """
    Search the web and return structured search results.
    """

    results = search_web(
        question=question,
        max_results=max_results
    )

    if not results:
        return {
            "source": "web",
            "answer": None,
            "results": []
        }

    answer_parts = [
        f"Web search results for: {question}",
        ""
    ]

    for index, result in enumerate(results, start=1):
        answer_parts.append(
            f"{index}. {result['title']}"
        )
        answer_parts.append(
            f"   {result['snippet']}"
        )
        answer_parts.append(
            f"   Source: {result['url']}"
        )
        answer_parts.append("")

    return {
        "source": "web",
        "answer": "\n".join(answer_parts),
        "results": results
    }
