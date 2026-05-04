"""Cross-encoder reranker."""

from typing import List, Tuple, Dict, Any, Optional
import re
import numpy as np
from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """
    SPEED-OPTIMIZED cross-encoder for BIS standard retrieval.

    Design goals:
    - Keep reranking model-driven
    - Use only light metadata signals
    - Stay fast enough for hackathon/demo use
    - Match the pipeline signature cleanly
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length: int = 512,
        max_chars: int = 250,
        max_candidates: int = 8,
    ):
        self.model = CrossEncoder(model_name, max_length=max_length)
        self.max_length = max_length
        self.max_chars = max_chars
        self.max_candidates = max_candidates

    def _build_document_text(self, doc: Dict[str, Any]) -> str:
        """
        Build a compact but informative document string for the cross-encoder.
        Includes only high-signal metadata to avoid bloating input length.
        """
        doc_id = str(doc.get("id", "")).strip()
        title = str(doc.get("title", "")).strip()
        text = str(doc.get("text", "")).strip()
        category = str(doc.get("category", "")).strip()

        keywords = doc.get("keywords", [])
        if isinstance(keywords, list):
            keywords = " ".join(str(x).strip() for x in keywords[:5] if x)
        else:
            keywords = str(keywords).strip()

        related = doc.get("related_standards", [])
        if isinstance(related, list):
            related = " ".join(str(x).strip() for x in related[:3] if x)
        else:
            related = str(related).strip()

        # Compact but useful ordering: identity -> title -> category -> keywords -> related -> snippet
        parts = [
            doc_id,
            title,
            category,
            keywords,
            related,
            text[:120],
        ]
        return " ".join(p for p in parts if p).strip()

    def _fast_truncate(self, text: str) -> str:
        """Truncate text to model-friendly length."""
        return text[: self.max_chars]

    def _extract_is_numbers(self, text: str) -> set[str]:
        """
        Extract IS number variants from a string.
        Supports forms like:
          IS 8041
          IS8041
          IS 8041 (Part 2)
        """
        if not text:
            return set()

        pattern = re.compile(
            r"\bIS\s*(\d{1,5}(?:\s*\(Part\s*\d+\))?(?:\s*\(Sec\s*\d+\))?)\b",
            re.IGNORECASE,
        )
        matches = pattern.findall(text)
        normalized = set()

        for m in matches:
            clean = re.sub(r"\s+", "", m).lower()
            normalized.add(clean)
            num_only = re.sub(r"[^\d]", "", m.split("(")[0])
            if num_only:
                normalized.add(num_only)

        return normalized

    def _extract_part_number(self, text: str) -> Optional[int]:
        """Extract part number from text if present."""
        if not text:
            return None
        match = re.search(r"part[\s\-]*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _apply_metadata_boost(
        self, query: str, doc: Dict[str, Any], base_score: float
    ) -> float:
        """
        Apply only light, defensible metadata boosts:
        - importance_weight from chunking
        - exact IS number match
        - exact part match
        """
        score = float(base_score)

        # Chunk importance
        importance = float(doc.get("importance_weight", 1.0))
        score *= importance

        query_is = self._extract_is_numbers(query)
        query_part = self._extract_part_number(query)

        doc_text_for_id = f"{doc.get('id', '')} {doc.get('title', '')}"
        doc_is = self._extract_is_numbers(doc_text_for_id)

        # Exact IS match
        if query_is and doc_is and (query_is & doc_is):
            score *= 1.2

        # Exact part match
        if query_part is not None:
            doc_part = self._extract_part_number(doc_text_for_id)
            if doc_part is not None:
                if doc_part == query_part:
                    score *= 1.1
                else:
                    score *= 0.95

        return score

    def score(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        apply_metadata_boost: bool = True,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Score documents against a query."""
        if not documents:
            return []

        if not query or not query.strip():
            return [(doc, 0.0) for doc in documents]

        candidate_docs = documents[: self.max_candidates]

        pairs = []
        valid_docs = []

        for doc in candidate_docs:
            try:
                doc_text = self._build_document_text(doc)
                if not doc_text.strip():
                    continue

                doc_text = self._fast_truncate(doc_text)
                pairs.append((query.strip(), doc_text))
                valid_docs.append(doc)
            except Exception:
                continue

        if not pairs:
            return []

        try:
            batch_size = min(4, len(pairs))
            scores = self.model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            scores = np.atleast_1d(scores).astype(float)
        except Exception:
            return [(doc, 0.0) for doc in valid_docs]

        final_scores = []
        for doc, score in zip(valid_docs, scores):
            s = float(score)
            if apply_metadata_boost:
                s = self._apply_metadata_boost(query, doc, s)
            final_scores.append(s)

        scored = list(zip(valid_docs, final_scores))
        scored.sort(key=lambda x: float(x[1]), reverse=True)
        return scored

    def score_single(self, query: str, document: Dict[str, Any]) -> float:
        """Score a single document."""
        results = self.score(query, [document], apply_metadata_boost=True)
        return results[0][1] if results else 0.0

    def get_model_info(self) -> Dict[str, Any]:
        """Return model configuration."""
        return {
            "model_name": getattr(self.model, "model_name", "ms-marco-MiniLM-L-6-v2"),
            "max_length": self.max_length,
            "max_chars": self.max_chars,
            "speed_mode": "ULTRA_FAST",
            "candidates_processed": self.max_candidates,
            "batch_size": 4,
            "device": getattr(self.model, "device", "cpu"),
            "metadata_boost": True,
        }

    def get_performance_stats(self) -> Dict[str, str]:
        """Return configured performance metadata."""
        return {
            "candidates": f"{self.max_candidates} (fast rerank)",
            "text_length": f"{self.max_chars} chars",
            "batch_size": "up to 4",
            "doc_building": "Compact + metadata-aware",
            "expected_speedup": "~fast enough for interactive demo",
            "target_latency": "<2 seconds",
        }