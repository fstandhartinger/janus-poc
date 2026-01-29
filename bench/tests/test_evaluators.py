"""Tests for public dataset evaluators."""

from janus_bench.evaluators.citation_evaluator import evaluate_citations
from janus_bench.evaluators.code_evaluator import evaluate_code
from janus_bench.evaluators.multimodal_evaluator import evaluate_multimodal
from janus_bench.evaluators.text_evaluator import evaluate_text


def test_text_evaluator_contains():
    expected = {"contains": ["Paris"]}
    result = evaluate_text("Paris is the capital of France.", expected)
    assert result.score == 1.0


def test_citation_evaluator_requires_sources():
    expected = {"contains": ["1991"], "requires_citations": True, "min_sources": 1}
    response = "Python was released in 1991. Source: https://example.com"
    result = evaluate_citations(response, expected)
    assert result.score >= 0.9
    assert result.details["citation_count"] >= 1


def test_code_evaluator_executes():
    expected = {
        "language": "python",
        "function_name": "is_even",
        "test_cases": [
            {"input": [2], "output": True},
            {"input": [3], "output": False},
        ],
    }
    response = """
    def is_even(n):
        return n % 2 == 0
    """
    result = evaluate_code(response, expected)
    assert result.score == 1.0


def test_multimodal_evaluator_adds_image_flag():
    expected = {"contains": ["red"]}
    result = evaluate_multimodal("The image is red.", expected, has_image_input=True)
    assert result.score == 1.0
    assert result.details["has_image_input"] is True
