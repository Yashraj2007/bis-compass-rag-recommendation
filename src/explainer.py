"""Template-based rationale generation."""

import re


def _extract_scope(text):
    """Extract the scope/purpose statement from the chunk text."""
    scope_match = re.search(
        r"(?:1\.\s*)?Scope\s*[—\-:]+\s*(.+?)(?:\.|2\.\s|Note\s)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if scope_match:
        scope = scope_match.group(1).strip()
        scope = re.sub(r"\s+", " ", scope)
        return scope[:200]
    return ""


def _find_matched_terms(query, text):
    """Find significant terms that appear in both query and document."""
    stopwords = {
        "the",
        "is",
        "a",
        "an",
        "for",
        "of",
        "and",
        "in",
        "to",
        "with",
        "which",
        "that",
        "are",
        "be",
        "by",
        "on",
        "or",
        "as",
        "we",
        "our",
        "i",
        "need",
        "want",
        "looking",
        "what",
        "standard",
        "bis",
        "indian",
        "specification",
        "requirements",
        "comply",
        "regulations",
        "covers",
        "applicable",
        "official",
        "company",
        "manufacturing",
        "intended",
        "used",
        "use",
        "shall",
        "may",
        "not",
        "more",
        "less",
        "than",
    }

    query_words = set(query.lower().split()) - stopwords
    text_lower = text.lower()

    matched = []
    for word in query_words:
        if len(word) > 3 and word in text_lower:
            matched.append(word)

    return matched[:5]


def generate_rationales(query, ranked_docs, scores=None):
    """
    Generate rationale for each recommended standard.

    Args:
        query: The original query string.
        ranked_docs: List of document dicts in ranked order.
        scores: Optional list of confidence scores (0-1).

    Returns:
        List of rationale dicts with id, rationale, confidence.
    """
    rationales = []

    for i, doc in enumerate(ranked_docs):
        std_id = doc["id"]
        title = doc.get("title", "")
        text = doc.get("text", "")

        scope = _extract_scope(text)

        matched = _find_matched_terms(query, text)
        matched_str = ", ".join(matched) if matched else "related specifications"

        if scope:
            rationale = f"{std_id} covers {scope}."
        elif title and len(title) > 5:
            rationale = f"{std_id} pertains to {title}."
        else:
            rationale = f"{std_id} is a relevant Indian Standard."

        rationale += f" Matches your query on: {matched_str}."

        if scores and i < len(scores):
            confidence = round(min(max(float(scores[i]), 0), 1), 3)
        else:
            confidence = round(max(0.95 - (i * 0.1), 0.3), 3)

        rationales.append(
            {
                "id": std_id,
                "rationale": rationale,
                "confidence": confidence,
                "rank": i + 1,
            }
        )

    return rationales
