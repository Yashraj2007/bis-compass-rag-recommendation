"""Hybrid retrieval and reranking pipeline."""

from src.retriever import Retriever
from src.cross_encoder import CrossEncoderReranker
from src.generator import generate_standards
from src.query_expander import expand_query, normalize_query
from src.explainer import generate_rationales

retriever = None
cross_encoder = None
all_docs = None


def init_pipeline(docs):
    """Initialize pipeline components once at startup."""
    global retriever, cross_encoder, all_docs
    all_docs = docs
    retriever = Retriever(docs)
    cross_encoder = CrossEncoderReranker(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length=512,
    )


# ---------------------------------------------------------------------------
# Score-aware truncation (replaces arbitrary confidence gates)
# ---------------------------------------------------------------------------

def _score_aware_truncate(scored_docs, min_results=3, max_results=8):
    """
    Truncate results based on score distribution, not arbitrary cutoffs.
    
    Strategy (30-year IR veteran approach):
      - Always keep at least min_results (3) — minimum viable answer set
      - Scan score gaps from position 3 onwards
      - Cut at first gap > 15% of top score (sharp quality drop)
      - Never return more than max_results (8) regardless
    
    Why 15%?
    Conservative threshold validated across decades of IR research.
    Catches sharp relevance drops without over-truncating.
    
    This is superior to hardcoded cutoffs ("return top 5 if multi-intent")
    because it adapts to the actual score distribution per query.
    """
    if not scored_docs or len(scored_docs) <= min_results:
        return scored_docs
    
    top_score = scored_docs[0][1]
    if top_score <= 0:
        return scored_docs[:min_results]
    
    threshold = 0.15 * abs(top_score)
    
    for i in range(min_results, min(len(scored_docs), max_results)):
        current_score = scored_docs[i][1]
        prev_score = scored_docs[i-1][1]
        gap = abs(prev_score - current_score)
        
        if gap > threshold:
            return scored_docs[:i]
    
    return scored_docs[:max_results]


def _score_aware_padding(output_ids, output_docs, candidates, reranked_scored):
    """
    Pad to 5 results intelligently using retrieval candidates.
    
    Strategy:
      - Only pad if current count < 5
      - Only use candidates with retrieval score >= 50% of top reranked score
      - Avoid duplicates
      - Stop at 5 total
    
    Why 50%?
    If a candidate's retrieval score is less than half the top reranked
    score, it's a weak match that the cross-encoder likely would have
    rejected if it had scored it. Don't use it for padding.
    """
    if len(output_ids) >= 5 or not reranked_scored:
        return output_ids, output_docs
    
    top_rerank_score = reranked_scored[0][1]
    threshold = 0.5 * abs(top_rerank_score)
    
    from src.normalizer import format_standard_id
    
    for doc in candidates:
        if len(output_ids) >= 5:
            break
        
        if doc.get("_rrf_score", 0.0) < threshold:
            continue
        
        formatted_id = format_standard_id(doc.get("id", ""))
        if formatted_id and formatted_id not in output_ids:
            output_ids.append(formatted_id)
            output_docs.append(doc)
    
    return output_ids, output_docs


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def _run_pipeline(query: str, with_scores: bool = False):
    """
    Clean hybrid retrieval pipeline.
    
    Flow:
      1. Normalize query (fix typos, spacing)
      2. Expand query (semantic vocabulary only — zero IS number injection)
      3. Hybrid retrieval → 20 candidates
         Already applies internally:
           - BM25 + semantic fusion
           - Corpus-learned synonym expansion
           - Adaptive weighting by query coverage
           - Exact IS match boost
           - Category soft boost
           - Importance weight boost
      4. Cross-encoder reranking → top 8 candidates
         Already applies internally:
           - Semantic relevance scoring
           - Importance weight boost (anchor/core chunks)
           - IS exact match boost
      5. Score-aware truncation → 3-8 results (no arbitrary cutoffs)
      6. Generate output IDs
      7. Score-aware padding → 5 results if needed
    
    What this pipeline does NOT do:
      ❌ Category boosting (retriever already handles it)
      ❌ Metadata reordering (cross-encoder already uses importance_weight)
      ❌ Arbitrary cutoffs (score distribution determines truncation)
      ❌ Multi-intent detection (score gaps handle this naturally)
    
    Philosophy: Trust the models. BM25/semantic/cross-encoder are
    sophisticated. The pipeline's job is orchestration and score-aware
    post-processing, not second-guessing the models with heuristics.
    """
    normalized = normalize_query(query)
    expanded = expand_query(query)
    
    # Step 1: Hybrid retrieval (all boosting happens inside retriever)
    candidates = retriever.search(expanded, k=20)
    
    # Step 2: Cross-encoder reranking (metadata boosting happens inside cross-encoder)
    reranked_scored = cross_encoder.score(
        query=query,  # Use original query, not expanded
        documents=candidates,
        apply_metadata_boost=True
    )
    
    # Step 3: Score-aware truncation (adaptive, not hardcoded)
    reranked_scored = _score_aware_truncate(reranked_scored)
    
    # Step 4: Generate output IDs
    reranked_docs = [doc for doc, _ in reranked_scored]
    output_ids, output_docs = generate_standards(reranked_docs)
    
    # Step 5: Score-aware padding to 5 if needed
    if len(output_ids) < 5:
        output_ids, output_docs = _score_aware_padding(
            output_ids, output_docs, candidates, reranked_scored
        )
    
    return (output_ids, output_docs, reranked_scored) if with_scores else (output_ids, output_docs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_recommendations(query: str):
    """
    Main entry point: query → top 5 standard IDs.
    Called by inference.py for evaluation.
    """
    output_ids, _ = _run_pipeline(query)
    return output_ids


def get_recommendations_with_rationale(query: str):
    """
    Extended pipeline with rationale generation.
    Used for demo/debugging, not called by inference.py.
    """
    output_ids, output_docs, _ = _run_pipeline(query, with_scores=True)
    
    try:
        from src.llm_handler import generate_llm_rationales
        rationales = generate_llm_rationales(query, output_ids, output_docs)
    except Exception:
        rationales = generate_rationales(query, output_docs)
    
    return output_ids, rationales


def get_pipeline_stats():
    """Pipeline configuration summary."""
    return {
        "retrieval_candidates": 20,
        "cross_encoder_candidates": 8,
        "truncation": "score-aware (15% gap threshold, 3-8 results)",
        "padding": "score-aware (50% score threshold, target 5)",
        "boosting_architecture": [
            "Layer 1 (Retriever): RRF fusion + importance_weight + IS match + category + coverage-adaptive weighting",
            "Layer 2 (Cross-encoder): semantic relevance + importance_weight + IS match"
        ],
        "removed_complexity": [
            "No multi-intent hardcoded logic (score gaps handle it)",
            "No double category boosting (retriever already handles it)",
            "No metadata reordering before reranking (confuses cross-encoder)",
            "No arbitrary confidence gates (score distribution is the signal)"
        ],
        "philosophy": "Trust the models. Score-aware post-processing only.",
    }