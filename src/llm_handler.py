"""LLM-based rationale generation."""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BIS_RATIONALE_PROMPT = """You are a BIS (Bureau of Indian Standards) assistant.

Your task is to explain why the given BIS standards are relevant to the query.

IMPORTANT RULES:
- DO NOT generate new standards
- DO NOT modify the given standards
- ONLY explain the provided standards
- Use only the given context
- Keep explanation short (1 line per standard)
- No hallucination

INPUT:
Query: {query}

Standards:
{standards}

Context:
{context}

OUTPUT FORMAT:
[
  {{
    "standard": "IS XXXX: YYYY",
    "reason": "Short explanation"
  }}
]
"""


def _get_llm():
    """
    Lazy-load the LLM client. Returns None if API key is missing.
    This avoids import-time failures when the key isn't set.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set. LLM rationale generation disabled.")
        return None

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="meta-llama/llama-3-8b-instruct",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.2,
            max_tokens=1024,
            request_timeout=10,
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return None


def generate_llm_rationales(query, output_ids, output_docs):
    """
    Generate LLM-powered rationales for retrieved standards.

    Args:
        query: The original user query.
        output_ids: List of standard ID strings (e.g., ["IS 269 : 1989", ...]).
        output_docs: List of document dicts with 'text' field.

    Returns:
        List of dicts: [{"standard": "...", "reason": "..."}, ...]
        Falls back to template-based rationales if LLM fails.
    """
    llm = _get_llm()

    if llm is None:
        return _fallback_rationales(output_ids, output_docs)

    try:
        from langchain.prompts import PromptTemplate

        prompt = PromptTemplate(
            input_variables=["query", "standards", "context"],
            template=BIS_RATIONALE_PROMPT,
        )

        context_parts = []
        for doc in output_docs[:5]:
            doc_text = f"{doc['id']}: {doc.get('title', '')} — {doc['text'][:300]}"
            context_parts.append(doc_text)
        context = "\n\n".join(context_parts)

        standards_str = "\n".join([f"- {sid}" for sid in output_ids])

        formatted_prompt = prompt.format(
            query=query,
            standards=standards_str,
            context=context,
        )
        response = llm.invoke(formatted_prompt)

        rationales = _parse_llm_response(response.content, output_ids)
        return rationales

    except Exception as e:
        logger.error(f"LLM rationale generation failed: {e}")
        return _fallback_rationales(output_ids, output_docs)


def _parse_llm_response(response_text, output_ids):
    """
    Parse the LLM JSON response. If parsing fails, return raw text as rationale.
    Also validates that LLM didn't hallucinate new standards.
    """
    try:
        cleaned = response_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        rationales = json.loads(cleaned)

        from src.normalizer import normalize

        valid_norm_ids = {normalize(sid) for sid in output_ids}

        validated = []
        for r in rationales:
            std = r.get("standard", "")
            if normalize(std) in valid_norm_ids:
                validated.append(
                    {
                        "standard": std,
                        "reason": r.get("reason", "Relevant to your query."),
                    }
                )

        covered_norm = {normalize(v["standard"]) for v in validated}
        for sid in output_ids:
            if normalize(sid) not in covered_norm:
                validated.append(
                    {
                        "standard": sid,
                        "reason": "Relevant Indian Standard for your query.",
                    }
                )

        return validated

    except (json.JSONDecodeError, KeyError, IndexError):
        return [
            {
                "standard": sid,
                "reason": response_text[:200] if i == 0 else "See above explanation.",
            }
            for i, sid in enumerate(output_ids)
        ]


def _fallback_rationales(output_ids, output_docs):
    """
    Template-based fallback when LLM is unavailable.
    Uses document titles and text to generate simple rationales.
    """
    rationales = []
    for i, sid in enumerate(output_ids):
        if i < len(output_docs):
            doc = output_docs[i]
            title = doc.get("title", "")
            if title and len(title) > 5:
                reason = f"This standard covers {title}."
            else:
                reason = f"Relevant Indian Standard matching your query."
        else:
            reason = "Related BIS standard."

        rationales.append(
            {
                "standard": sid,
                "reason": reason,
            }
        )

    return rationales
