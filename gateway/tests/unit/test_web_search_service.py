"""Unit tests for gateway web search helpers."""

from janus_gateway.services.web_search import normalize_serper_results


def test_normalize_serper_results() -> None:
    payload = {
        "organic": [
            {
                "title": "Python 3.12 release notes",
                "link": "https://www.python.org/downloads/release/python-3120/",
                "snippet": "Python 3.12.0 is the newest major release of the Python programming language.",
            }
        ]
    }
    results = normalize_serper_results(payload)
    assert results == [
        {
            "title": "Python 3.12 release notes",
            "url": "https://www.python.org/downloads/release/python-3120/",
            "snippet": "Python 3.12.0 is the newest major release of the Python programming language.",
        }
    ]
