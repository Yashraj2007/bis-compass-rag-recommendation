"""Reranking layer — delegates to cross-encoder with metadata awareness."""

from typing import List, Tuple, Optional


def rerank(
    query: str,
    docs: List[dict],
    cross_encoder_reranker=None,
    query_category: Optional[str] = None,
) -> List[Tuple[dict, float]]:
    """
    Reranking entry point.
    
    Architecture (30-year IR veteran perspective):
      This is a thin delegation layer. The actual reranking logic lives in
      the CrossEncoderReranker class where it belongs.
      
      This function exists for:
        1. Backward compatibility with existing pipeline code
        2. Single import point (src.reranker.rerank)
        3. Graceful fallback if cross-encoder is unavailable
    
    Philosophy:
      Cross-encoder reranking IS the reranking. There is no separate
      "rule-based boosting" layer because:
      
        ❌ Hardcoded query→standard mappings = answer leakage
        ❌ Arbitrary boost multipliers = dataset overfitting
        ❌ Category penalties = fighting your semantic model
      
      The cross-encoder already applies:
        ✓ Semantic relevance scoring (its core job)
        ✓ importance_weight boost (anchor/core chunks)
        ✓ IS exact match boost (query mentions IS 8041 → doc IS 8041)
      
      That's all you need. Everything else is complexity without benefit.
    
    Args:
        query: Original user query (NOT expanded)
        docs: Candidate documents from retriever
        cross_encoder_reranker: CrossEncoderReranker instance
        query_category: Detected category (unused — kept for API compatibility)
    
    Returns:
        List of (document, score) tuples sorted by score descending
    """
    if not docs:
        return []
    
    if cross_encoder_reranker:
        # Primary path: delegate to cross-encoder (does all the work)
        return cross_encoder_reranker.score(
            query=query,
            documents=docs,
            apply_metadata_boost=True
        )
    
    # Fallback path: no cross-encoder available
    # (Should never happen in production, but handle gracefully)
    import re
    
    def _extract_is_numbers(text: str) -> set:
        pattern = re.compile(r'\bIS\s*(\d{1,5}(?:\s*\(Part\s*\d+\))?)', re.IGNORECASE)
        matches = pattern.findall(text)
        normalized = set()
        for m in matches:
            clean = re.sub(r'\s+', '', m).lower()
            normalized.add(clean)
            num_only = re.sub(r'[^\d]', '', m.split('(')[0])
            if num_only:
                normalized.add(num_only)
        return normalized
    
    def _extract_part_number(text: str) -> Optional[int]:
        match = re.search(r'part[\s\-]*(\d+)', text, re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    query_is = _extract_is_numbers(query)
    query_part = _extract_part_number(query)
    
    scored = []
    for doc in docs:
        score = 1.0
        
        # Importance weight from chunking
        score *= doc.get("importance_weight", 1.0)
        
        # IS exact match
        doc_is = _extract_is_numbers(doc.get("id", ""))
        if query_is and doc_is and (query_is & doc_is):
            score *= 1.3
        
        # Part exact match
        doc_part = _extract_part_number(doc.get("id", ""))
        if query_part is not None and doc_part is not None:
            score *= 1.2 if doc_part == query_part else 0.8
        
        scored.append((doc, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def get_reranker_stats():
    """Return reranking architecture summary."""
    return {
        "primary_ranker": "CrossEncoderReranker (ms-marco-MiniLM-L-6-v2)",
        "signals_applied": [
            "Semantic relevance (cross-encoder core)",
            "importance_weight (1.0-1.2x from chunking)",
            "IS exact match (1.3x when query mentions specific IS number)",
            "Part exact match (1.2x match, 0.8x mismatch)"
        ],
        "removed_complexity": [
            "No ANCHORS dictionary (600+ lines of hardcoded mappings)",
            "No arbitrary boost multipliers (2.5, 2.0, 0.8, etc.)",
            "No category penalties (cross-encoder handles semantic fit)",
            "No domain hints integration (kept optional in expander, not used here)",
            "No year bonuses (arbitrary)",
            "No noise penalties (arbitrary)"
        ],
        "lines_of_code": "~80 (was ~400)",
        "philosophy": "Cross-encoder does the work. Minimal metadata post-processing for signals it can't see.",
    }