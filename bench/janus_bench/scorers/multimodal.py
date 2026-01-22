"""Multimodal handling scoring for benchmark responses."""

from typing import Optional


def score_multimodal(
    response_text: Optional[str],
    has_image_input: bool,
    expected_keywords: Optional[list[str]] = None,
) -> float:
    """Score multimodal handling (image input processing).

    Args:
        response_text: The model's response text
        has_image_input: Whether the request included an image
        expected_keywords: Optional keywords expected in the response

    Returns:
        Score between 0.0 and 1.0
    """
    # If no image input, this isn't a multimodal task
    if not has_image_input:
        return 1.0  # N/A - give full score

    if response_text is None or response_text.strip() == "":
        return 0.0

    response_lower = response_text.lower()

    # Check for common image-related response patterns
    image_acknowledgment_terms = [
        "image",
        "picture",
        "photo",
        "see",
        "shows",
        "appears",
        "visible",
        "display",
        "color",
        "pixel",
    ]

    # Check if the model acknowledged the image
    acknowledged_image = any(term in response_lower for term in image_acknowledgment_terms)

    if not acknowledged_image:
        # Model didn't seem to process the image
        return 0.2

    # Check for expected keywords if provided
    if expected_keywords is not None and len(expected_keywords) > 0:
        matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        keyword_score = matches / len(expected_keywords)
        return 0.5 + 0.5 * keyword_score

    # Acknowledged image, no specific keywords to check
    return 0.8
