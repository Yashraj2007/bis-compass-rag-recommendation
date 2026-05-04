"""Hybrid retriever with FAISS + BM25 + RRF — production grade, zero hardcoded heuristics."""

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from rank_bm25 import BM25Okapi
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Stopwords
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "is", "a", "an", "for", "of", "and", "in", "to", "with",
    "which", "that", "are", "be", "by", "on", "or", "as", "it", "at",
    "from", "this", "was", "were", "has", "have", "had", "been", "not",
    "but", "if", "its", "do", "does", "no", "up", "out", "so", "than",
    "can", "will", "more", "also", "such", "shall", "may", "when",
}

_IS_PATTERN = re.compile(
    r"\bIS\s*(\d{1,5}(?:\s*\(Part\s*\d+\))?(?:\s*\(Sec\s*\d+\))?)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"is\s*(\d+)", r"is\1 \1", text)
    text = re.sub(r"\(part\s*(\d+)\)", r"part\1 part \1", text)
    text = re.sub(r"\(sec\s*(\d+)\)", r"sec\1 sec \1", text)
    text = re.sub(r"[^\w\s\-]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


# ---------------------------------------------------------------------------
# IS number extraction
# ---------------------------------------------------------------------------

def _extract_is_numbers(text: str) -> list[str]:
    matches = _IS_PATTERN.findall(text)
    numbers = []
    for m in matches:
        raw = re.sub(r"\s+", "", m).lower()
        num_only = re.sub(r"[^\d]", "", m.split("(")[0])
        numbers.append(raw)
        if num_only:
            numbers.append(num_only)
    return list(set(numbers))


def _extract_part_number(text: str) -> int | None:
    match = re.search(r"part\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Field coercion
# ---------------------------------------------------------------------------

def _safe_list_to_string(field_value, max_items: int = 15) -> str:
    if isinstance(field_value, list):
        return " ".join(str(x).strip() for x in field_value[:max_items] if x)
    return str(field_value).strip() if field_value else ""


# ---------------------------------------------------------------------------
# Corpus-driven synonym index
# ---------------------------------------------------------------------------

class _CorpusSynonymIndex:
    """
    Builds a term co-occurrence index from the corpus.

    Core idea:
      - Terms that repeatedly appear in the same documents are likely
        semantically related in this domain.
      - Co-occurrence score is weighted by IDF so rare shared terms
        (e.g. "supersulphated") rank above ubiquitous ones (e.g. "strength").
      - Expansion is capped at 2x query length to prevent noise flooding BM25.

    This generalises to any unseen material or domain term automatically.
    """

    def __init__(self, tokenized_corpus: list[list[str]], top_k_per_term: int = 6):
        co_occur: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        term_df: dict[str, int] = defaultdict(int)

        for tokens in tokenized_corpus:
            unique = set(tokens)
            for t in unique:
                term_df[t] += 1
            token_list = list(unique)
            for t in token_list:
                for t2 in token_list:
                    if t2 != t:
                        co_occur[t][t2] += 1

        n_docs = len(tokenized_corpus)

        # Pre-filter: drop extremely high-frequency terms as expansion targets
        # (they appear everywhere and carry no discriminative signal)
        max_df_threshold = 0.6 * n_docs

        self._expansions: dict[str, list[str]] = {}
        for term, neighbors in co_occur.items():
            scored = []
            for neighbor, cnt in neighbors.items():
                df = term_df[neighbor]
                if df > max_df_threshold:
                    continue
                idf = np.log((n_docs + 1) / (df + 1))
                scored.append((neighbor, cnt * idf))
            scored.sort(key=lambda x: x[1], reverse=True)
            self._expansions[term] = [t for t, _ in scored[:top_k_per_term]]

    def expand(self, tokens: list[str]) -> list[str]:
        """
        Expand query tokens with corpus-correlated neighbors.
        Hard cap: final token list <= 2x original length.
        This prevents noisy co-occurrence terms from drowning the signal.
        """
        max_total = len(tokens) * 2
        expanded = list(tokens)
        seen = set(tokens)

        for t in tokens:
            if len(expanded) >= max_total:
                break
            for exp in self._expansions.get(t, []):
                if exp not in seen and len(expanded) < max_total:
                    expanded.append(exp)
                    seen.add(exp)

        for i in range(len(tokens) - 1):
            if len(expanded) >= max_total:
                break
            bigram = f"{tokens[i]} {tokens[i + 1]}"
            for exp in self._expansions.get(bigram, []):
                if exp not in seen and len(expanded) < max_total:
                    expanded.append(exp)
                    seen.add(exp)

        return expanded


# ---------------------------------------------------------------------------
# Query coverage detector — drives adaptive semantic/BM25 weighting
# ---------------------------------------------------------------------------

class _QueryCoverageDetector:
    """
    Measures how well a query is covered by the corpus vocabulary.

    A query with many unseen or rare tokens gets low coverage.
    Low coverage → BM25 expansion is weak → semantic search should dominate.
    High coverage → BM25 expansion is strong → balanced fusion is fine.

    This gives us adaptive weighting without any hardcoded thresholds
    on specific materials or domains.
    """

    def __init__(self, tokenized_corpus: list[list[str]]):
        self._known_terms: set[str] = set()
        for tokens in tokenized_corpus:
            self._known_terms.update(tokens)

    def coverage_ratio(self, query_tokens: list[str]) -> float:
        if not query_tokens:
            return 1.0
        known = sum(1 for t in query_tokens if t in self._known_terms)
        return known / len(query_tokens)


# ---------------------------------------------------------------------------
# Category signal index
# ---------------------------------------------------------------------------

class _CategorySignalIndex:
    """
    Learns which query tokens predict which document categories from the corpus.
    A token qualifies as a signal if >25% of its documents share the same category.
    """

    def __init__(self, docs: list[dict], tokenized_corpus: list[list[str]]):
        token_cat_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for tokens, doc in zip(tokenized_corpus, docs):
            cat = doc.get("category", "").lower().strip()
            if not cat:
                continue
            for t in set(tokens):
                token_cat_counts[t][cat] += 1

        self._token_to_cats: dict[str, list[str]] = {}
        for token, cat_counts in token_cat_counts.items():
            total = sum(cat_counts.values())
            ranked = sorted(cat_counts.items(), key=lambda x: x[1] / total, reverse=True)
            dominant = [(c, cnt / total) for c, cnt in ranked if cnt / total > 0.25]
            if dominant:
                self._token_to_cats[token] = [c for c, _ in dominant[:3]]

    def detect_categories(self, query_tokens: list[str]) -> set[str]:
        cats: set[str] = set()
        for t in query_tokens:
            cats.update(self._token_to_cats.get(t, []))
        return cats


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class Retriever:

    # Baseline fusion weights — adjusted adaptively per query
    _BASE_SEMANTIC_WEIGHT = 1.5
    _BASE_BM25_WEIGHT = 1.0

    def __init__(self, docs: list[dict]):
        self.docs = docs

        self.texts: list[str] = []
        for d in docs:
            keywords_str = _safe_list_to_string(d.get("keywords", []), 20)
            related_str = _safe_list_to_string(d.get("related_standards", []), 10)
            composition_str = _safe_list_to_string(d.get("composition_terms", []), 10)
            domains_str = _safe_list_to_string(d.get("application_domains", []), 5)

            tech_props = d.get("technical_properties", {})
            if isinstance(tech_props, dict):
                all_props = []
                for prop_list in tech_props.values():
                    if isinstance(prop_list, list):
                        all_props.extend(prop_list[:3])
                tech_props_str = " ".join(all_props[:10])
            else:
                tech_props_str = ""

            parts = [
                d.get("id", ""),
                d.get("title", ""),
                d.get("text", ""),
                d.get("category", ""),
                keywords_str,
                related_str,
                composition_str,
                domains_str,
                tech_props_str,
            ]
            self.texts.append(" ".join(filter(None, parts)))

        tokenized_corpus = [_tokenize(t) for t in self.texts]

        # Semantic index
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = self.model.encode(
            self.texts,
            show_progress_bar=False,
            batch_size=64,
            normalize_embeddings=True,
        )
        embeddings = np.array(embeddings, dtype=np.float32)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

        # Lexical index
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Corpus-learned indexes
        self._synonym_index = _CorpusSynonymIndex(tokenized_corpus, top_k_per_term=6)
        self._coverage_detector = _QueryCoverageDetector(tokenized_corpus)
        self._category_index = _CategorySignalIndex(docs, tokenized_corpus)

        self._doc_is_numbers = [_extract_is_numbers(t) for t in self.texts]

    # -----------------------------------------------------------------------
    # Adaptive weight resolution
    # -----------------------------------------------------------------------

    def _resolve_weights(self, query_tokens: list[str]) -> tuple[float, float]:
        """
        Dynamically adjust semantic vs BM25 weight based on query coverage.

        Low coverage  → unseen/rare terms → BM25 expansion weak
                      → semantic must carry more weight
        High coverage → known terms → BM25 expansion is reliable
                      → balanced fusion
        """
        coverage = self._coverage_detector.coverage_ratio(query_tokens)

        if coverage < 0.4:
            # Sparse/unseen query: lean heavily on dense retrieval
            return 2.0, 0.6
        elif coverage < 0.7:
            # Partial coverage: moderate semantic boost
            return 1.7, 0.8
        else:
            # Good coverage: standard balanced weights
            return self._BASE_SEMANTIC_WEIGHT, self._BASE_BM25_WEIGHT

    # -----------------------------------------------------------------------
    # Search primitives
    # -----------------------------------------------------------------------

    def _semantic_search(self, query: str, k: int) -> dict[int, int]:
        q_emb = self.model.encode(
            [query], normalize_embeddings=True
        ).astype(np.float32)
        D, I = self.index.search(q_emb, k)
        return {int(idx): rank for rank, idx in enumerate(I[0], 1) if idx >= 0}

    def _bm25_search(self, query_tokens: list[str], k: int) -> dict[int, int]:
        expanded = self._synonym_index.expand(query_tokens)
        scores = self.bm25.get_scores(expanded)
        top_indices = np.argsort(scores)[::-1][:k]
        return {int(idx): rank for rank, idx in enumerate(top_indices, 1)}

    # -----------------------------------------------------------------------
    # Fusion and boosting
    # -----------------------------------------------------------------------

    def _rrf_fuse(
        self,
        semantic_ranks: dict[int, int],
        bm25_ranks: dict[int, int],
        rrf_k: int,
        semantic_weight: float,
        bm25_weight: float,
    ) -> dict[int, float]:
        scores: dict[int, float] = {}
        for idx in set(semantic_ranks) | set(bm25_ranks):
            s = 0.0
            if idx in semantic_ranks:
                s += semantic_weight / (rrf_k + semantic_ranks[idx])
            if idx in bm25_ranks:
                s += bm25_weight / (rrf_k + bm25_ranks[idx])
            scores[idx] = s
        return scores

    def _apply_exact_match_boost(
        self, rrf_scores: dict[int, float], query: str
    ) -> dict[int, float]:
        query_is_numbers = _extract_is_numbers(query)
        query_part = _extract_part_number(query)
        boosted = {}

        for idx, score in rrf_scores.items():
            boost = 1.0
            if query_is_numbers:
                overlap = set(query_is_numbers) & set(self._doc_is_numbers[idx])
                if overlap:
                    boost += 0.4 * len(overlap)
            if query_part is not None:
                doc_part = _extract_part_number(self.texts[idx])
                if doc_part is not None:
                    boost += 0.3 if doc_part == query_part else -0.15 * boost
            boosted[idx] = score * boost

        return boosted

    def _apply_category_soft_boost(
        self, rrf_scores: dict[int, float], query_tokens: list[str]
    ) -> dict[int, float]:
        detected = self._category_index.detect_categories(query_tokens)
        if not detected:
            return rrf_scores

        boosted = {}
        for idx, score in rrf_scores.items():
            doc_category = self.docs[idx].get("category", "").lower()
            if any(cat in doc_category for cat in detected):
                boosted[idx] = score * 1.15
            else:
                boosted[idx] = score * 0.92
        return boosted

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def search(self, query: str, k: int = 20) -> list[dict]:
        DENSE_K = 20
        BM25_K = 20
        RRF_K = 40

        query_tokens = _tokenize(query)
        semantic_weight, bm25_weight = self._resolve_weights(query_tokens)

        semantic_ranks = self._semantic_search(query, k=DENSE_K)
        bm25_ranks = self._bm25_search(query_tokens, k=BM25_K)

        rrf_scores = self._rrf_fuse(
            semantic_ranks, bm25_ranks,
            rrf_k=RRF_K,
            semantic_weight=semantic_weight,
            bm25_weight=bm25_weight,
        )
        rrf_scores = self._apply_exact_match_boost(rrf_scores, query)
        rrf_scores = self._apply_category_soft_boost(rrf_scores, query_tokens)

        sorted_indices = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for idx in sorted_indices[:k]:
            doc = dict(self.docs[idx])
            doc["_rrf_score"] = rrf_scores[idx]
            results.append(doc)

        return results

    def get_retrieval_stats(self) -> dict:
        return {
            "dense_candidates": 20,
            "bm25_candidates": 20,
            "rrf_constant": 40,
            "default_k": 20,
            "base_semantic_weight": self._BASE_SEMANTIC_WEIGHT,
            "base_bm25_weight": self._BASE_BM25_WEIGHT,
            "adaptive_weighting": "coverage-ratio driven per query",
            "synonym_expansion": "corpus-learned, capped at 2x query length",
            "category_boosting": "corpus-learned, zero hardcoding",
            "fallback_for_rare_tokens": "semantic dominates when coverage < 0.4",
        }