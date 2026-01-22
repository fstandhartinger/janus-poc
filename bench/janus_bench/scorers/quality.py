"""Quality scoring for benchmark responses."""

from typing import Optional


def score_quality(
    response_text: Optional[str],
    expected_answer: Optional[str] = None,
    expected_keywords: Optional[list[str]] = None,
) -> float:
    """Score response quality based on expected answer or keywords.

    Args:
        response_text: The model's response text
        expected_answer: Optional exact expected answer
        expected_keywords: Optional list of keywords that should appear

    Returns:
        Score between 0.0 and 1.0
    """
    if response_text is None or response_text.strip() == "":
        return 0.0

    response_lower = response_text.lower()

    # If exact answer expected, check for it
    if expected_answer is not None:
        if expected_answer.lower() in response_lower:
            return 1.0
        else:
            return 0.0

    # If keywords expected, check how many are present
    if expected_keywords is not None and len(expected_keywords) > 0:
        matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return matches / len(expected_keywords)

    # No expected answer or keywords - just verify non-empty response
    # Give partial credit for having some content
    if len(response_text.strip()) > 10:
        return 0.7  # Reasonable response length
    else:
        return 0.3  # Very short response
