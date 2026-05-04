"""Chunk extraction and metadata enrichment."""

import fitz
import re
import json
from typing import List, Dict, Optional, Set

CATEGORY_KEYWORDS = {
    "cement": [
        "portland cement",
        "ordinary portland",
        "pozzolana cement",
        "slag cement",
        "rapid hardening",
        "white cement",
        "masonry cement",
        "supersulphated",
        "sulphate resisting",
        "high alumina",
        "aluminous",
        "hydrophobic cement",
        "low heat cement",
        "cement composition",
        "fineness",
        "soundness",
        "setting time",
        "compressive strength cement",
        "cement specification",
        "cement requirements",
        "cement chemical",
    ],
    "aggregate": [
        "coarse aggregate",
        "fine aggregate",
        "natural aggregate",
        "crushed stone",
        "gravel",
        "aggregate grading",
        "sand",
        "particle size distribution",
        "sieve analysis",
        "aggregate testing",
        "aggregate soundness",
        "aggregate crushing",
        "flakiness index",
    ],
    "concrete": [
        "reinforced concrete",
        "prestressed concrete",
        "plain concrete",
        "structural concrete",
        "mass concrete",
        "concrete specification",
        "concrete strength",
        "concrete workability",
    ],
    "pipe": [
        "concrete pipe",
        "precast pipe",
        "reinforced pipe",
        "pressure pipe",
        "water main",
        "sewer pipe",
        "culvert",
        "drainage pipe",
        "prestressed pipe",
        "asbestos cement pipe",
        "pipe specification",
        "pipe testing",
        "hydrostatic pressure",
    ],
    "block": [
        "concrete block",
        "masonry block",
        "hollow block",
        "solid block",
        "concrete masonry unit",
        "lightweight block",
        "aerated concrete",
        "autoclaved aerated",
        "load bearing block",
        "partition block",
        "block specification",
        "masonry unit",
    ],
    "sheet": [
        "corrugated sheet",
        "roofing sheet",
        "asbestos cement sheet",
        "cladding",
        "semi-corrugated",
        "roofing and cladding",
        "sheet specification",
        "roofing material",
    ],
    "brick": [
        "burnt clay brick",
        "common brick",
        "building brick",
        "fly ash brick",
        "lime brick",
        "brick specification",
        "brick testing",
        "brick strength",
    ],
    "mortar": [
        "masonry mortar",
        "sand for mortar",
        "lime mortar",
        "mortar specification",
        "mortar mix",
        "mortar strength",
    ],
}

TECHNICAL_TERMS = {
    "cement": [
        "composition",
        "fineness",
        "soundness",
        "setting time",
        "compressive strength",
        "tensile strength",
        "chemical requirements",
        "physical requirements",
        "specific gravity",
        "blaine",
        "autoclave",
        "le chatelier",
        "vicat",
        "gillmore",
        "consistency",
        "expansion",
    ],
    "aggregate": [
        "grading",
        "particle size",
        "sieve analysis",
        "moisture content",
        "water absorption",
        "specific gravity",
        "bulk density",
        "soundness",
        "abrasion",
        "crushing value",
        "impact value",
        "flakiness index",
        "elongation index",
        "deleterious materials",
    ],
    "concrete": [
        "workability",
        "slump",
        "compaction factor",
        "cube strength",
        "cylinder strength",
        "modulus of elasticity",
        "durability",
        "permeability",
        "water cement ratio",
    ],
    "pipe": [
        "internal diameter",
        "wall thickness",
        "hydrostatic pressure",
        "crushing strength",
        "absorption",
        "reinforcement",
        "joints",
        "impermeability",
        "three edge bearing",
    ],
    "block": [
        "compressive strength",
        "water absorption",
        "density",
        "dimensions",
        "drying shrinkage",
        "moisture movement",
        "load bearing capacity",
    ],
    "sheet": [
        "thickness",
        "width",
        "length",
        "corrugation",
        "pitch",
        "weathering",
        "transverse strength",
        "impact resistance",
    ],
}


def extract_clean_chunks(pdf_path: str, output_path: str):
    """
    Smart chunking pipeline with metadata enrichment.

    Pipeline:
      1. Extract raw standards from PDF
      2. For each standard:
         a. Create anchor chunk (BM25 bait summary)
         b. Create overlapping content chunks (300-token windows, 100-token overlap)
      3. Enrich all chunks with metadata:
         - category (detected from content)
         - keywords (technical terms extracted)
         - part_number (if applicable)
         - standard_year (if present)
         - is_summary_chunk (anchor flag)
      4. Save to JSON

    Args:
        pdf_path: Path to BIS standards PDF
        output_path: Output JSON file path
    """
    doc = fitz.open(pdf_path)

    raw_standards = _extract_raw_standards(doc)

    all_chunks = []

    for std in raw_standards:
        anchor = _create_anchor_chunk(std)
        all_chunks.append(anchor)

        content_chunks = _create_sliding_window_chunks(std)
        all_chunks.extend(content_chunks)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    anchor_count = sum(1 for c in all_chunks if c.get("is_summary_chunk"))
    print(f"✅ Extracted {len(raw_standards)} standards → {len(all_chunks)} chunks")
    print(
        f"   ({anchor_count} anchor chunks, {len(all_chunks) - anchor_count} content chunks)"
    )


def _extract_raw_standards(doc) -> List[Dict]:
    """
    Extract raw standards from PDF.

    Returns:
        List[Dict]: Each dict contains {id, title, text}
    """
    id_pattern = re.compile(
        r"(IS\s+\d{1,5}(?:\s*\(Part\s+\d+\))?(?:\s*\(Sec\s+\d+\))?\s*[:\-]?\s*\d{4}|IS\s+\d{1,5})",
        re.IGNORECASE,
    )

    standards = []
    current_std = None

    for page in doc:
        text = page.get_text("text")
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for line in lines:
            match = id_pattern.search(line)
            if match:
                if current_std and len(current_std.get("text", "").strip()) > 20:
                    standards.append(current_std)

                full_id = match.group(1).strip()
                full_id = re.sub(r"[:\-]+$", "", full_id).strip()

                current_std = {
                    "id": full_id,
                    "title": line.replace(full_id, "").strip(": -"),
                    "text": line,
                }
            elif current_std:
                current_std["text"] += " " + line

    if current_std and len(current_std.get("text", "").strip()) > 20:
        standards.append(current_std)

    return standards


def _create_anchor_chunk(std: Dict) -> Dict:
    """
    Create special anchor/summary chunk for a standard.

    This is the BM25 bait — packs all key information into one chunk:
    - Standard ID + Title
    - Category
    - Top keywords
    - Part number (if applicable)

    Marked with is_summary_chunk=True for special handling in retriever.

    Args:
        std: Raw standard dict {id, title, text}

    Returns:
        Dict: Anchor chunk with full metadata
    """
    std_id = std["id"]
    title = std.get("title", "")
    full_text = std.get("text", "")

    category = _detect_category(full_text)
    keywords = _extract_keywords(full_text, category)
    part_num = _extract_part_number(std_id)
    year = _extract_year(std_id)

    anchor_parts = [
        std_id,
        title,
        category if category != "general" else "",
        " ".join(keywords[:15]),
    ]
    anchor_text = " ".join(filter(None, anchor_parts))

    return {
        "id": std_id,
        "title": title,
        "text": anchor_text,
        "category": category,
        "keywords": keywords[:20],
        "part_number": part_num,
        "standard_year": year,
        "is_summary_chunk": True,
    }


def _create_sliding_window_chunks(std: Dict) -> List[Dict]:
    """
    Create overlapping sliding window chunks for a standard.

    Strategy:
    - Core chunk (first 600 chars): never split, contains essential description
    - Remaining text: 300-token windows with 100-token overlap
    - Each chunk prefixed with standard ID + title for context preservation

    Window sizing:
    - 300 tokens ≈ 1200 chars (conservative estimate: 4 chars/token)
    - 100 token overlap ≈ 400 chars
    - Stride = 1200 - 400 = 800 chars

    Args:
        std: Raw standard dict {id, title, text}

    Returns:
        List[Dict]: Overlapping content chunks with metadata
    """
    std_id = std["id"]
    title = std.get("title", "")
    full_text = std.get("text", "")

    category = _detect_category(full_text)
    keywords = _extract_keywords(full_text, category)
    part_num = _extract_part_number(std_id)
    year = _extract_year(std_id)

    chunks = []

    core_length = 600

    if len(full_text) <= core_length:
        chunk = _build_chunk(
            std_id, title, full_text, category, keywords, part_num, year, chunk_index=0
        )
        chunks.append(chunk)
    else:
        core_text = full_text[:core_length]
        core_chunk = _build_chunk(
            std_id, title, core_text, category, keywords, part_num, year, chunk_index=0
        )
        chunks.append(core_chunk)

        remaining = full_text[core_length:]

        window_size = 1200
        overlap = 400
        stride = window_size - overlap

        start = 0
        chunk_idx = 1

        while start < len(remaining):
            end = start + window_size
            chunk_text = remaining[start:end]

            enriched_text = f"{std_id} {title} {chunk_text}"

            chunk = _build_chunk(
                std_id,
                title,
                enriched_text,
                category,
                keywords,
                part_num,
                year,
                chunk_index=chunk_idx,
            )
            chunks.append(chunk)

            start += stride
            chunk_idx += 1

    return chunks


def _build_chunk(
    std_id: str,
    title: str,
    text: str,
    category: str,
    keywords: List[str],
    part_num: Optional[int],
    year: Optional[int],
    chunk_index: int = 0,
) -> Dict:
    """
    Build standardized chunk dictionary with full metadata.

    All chunks share same structure for consistent downstream processing.
    """
    return {
        "id": std_id,
        "title": title,
        "text": text,
        "category": category,
        "keywords": keywords[:10],
        "part_number": part_num,
        "standard_year": year,
        "is_summary_chunk": False,
        "chunk_index": chunk_index,
    }


def _detect_category(text: str) -> str:
    """
    Detect category using weighted keyword matching.

    Scoring:
    - Count keyword matches per category
    - Category with most matches wins
    - Require minimum 2 matches to avoid false positives

    Returns:
        str: Category name or "general" if no confident match
    """
    text_lower = text.lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return "general"

    best_category = max(scores, key=scores.get)

    if scores[best_category] < 2:
        return "general"

    return best_category


def _extract_keywords(text: str, category: str) -> List[str]:
    """
    Extract technical keywords from text.

    Strategy:
    1. Match category-specific technical terms
    2. Match general technical terms from other categories
    3. Add common domain nouns
    4. Deduplicate while preserving order

    Returns:
        List[str]: Ordered list of unique keywords
    """
    text_lower = text.lower()
    keywords = []

    if category in TECHNICAL_TERMS:
        for term in TECHNICAL_TERMS[category]:
            if term in text_lower:
                keywords.append(term)

    for cat, terms in TECHNICAL_TERMS.items():
        if cat != category:
            for term in terms:
                if term in text_lower and term not in keywords:
                    keywords.append(term)

    if category != "general" and category not in keywords:
        keywords.insert(0, category)

    domain_nouns = [
        "specification",
        "requirements",
        "testing",
        "test method",
        "chemical",
        "physical",
        "mechanical",
        "properties",
        "composition",
        "standard",
        "grade",
        "type",
        "class",
        "manufacture",
        "quality",
        "sampling",
        "procedure",
    ]
    for noun in domain_nouns:
        if noun in text_lower and noun not in keywords:
            keywords.append(noun)

    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique


def _extract_part_number(std_id: str) -> Optional[int]:
    """
    Extract part number from standard ID.

    Examples:
        "IS 2185 (Part 1): 1979" → 1
        "IS 1489 (Part 2): 1991" → 2
        "IS 269: 1989" → None
    """
    match = re.search(r"\(Part\s+(\d+)\)", std_id, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_year(std_id: str) -> Optional[int]:
    """
    Extract year from standard ID.

    Examples:
        "IS 269: 1989" → 1989
        "IS 2185 (Part 1): 1979" → 1979
        "IS 383" → None
    """
    match = re.search(r"\b(19\d{2}|20\d{2})\b", std_id)
    if match:
        return int(match.group(1))
    return None


def analyze_chunks(output_path: str):
    """
    Analyze generated chunks and print statistics.
    Useful for debugging and validation.
    """
    with open(output_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print("\n" + "=" * 60)
    print("📊 CHUNKING ANALYSIS")
    print("=" * 60)

    print(f"\n📦 Total chunks: {len(chunks)}")

    anchor_count = sum(1 for c in chunks if c.get("is_summary_chunk"))
    print(f"   ⚓ Anchor chunks: {anchor_count}")
    print(f"   📄 Content chunks: {len(chunks) - anchor_count}")

    categories = {}
    for c in chunks:
        cat = c.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n📂 Category Distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = (count / len(chunks)) * 100
        print(f"   {cat:12} {count:4} ({pct:5.1f}%)")

    parts = {}
    for c in chunks:
        pn = c.get("part_number")
        if pn is not None:
            parts[pn] = parts.get(pn, 0) + 1

    if parts:
        print("\n🔢 Part Number Distribution:")
        for pn, count in sorted(parts.items()):
            print(f"   Part {pn}: {count} chunks")

    print("\n📝 Sample Chunks:\n")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"--- Sample {i} ---")
        print(f"ID: {chunk['id']}")
        print(f"Category: {chunk.get('category', 'N/A')}")
        print(f"Keywords: {', '.join(chunk.get('keywords', [])[:5])}")
        print(f"Is Summary: {chunk.get('is_summary_chunk', False)}")
        print(f"Text (first 150 chars): {chunk['text'][:150]}...")
        print()

    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python chunking.py <pdf_path> <output_json>")
        print("Example: python chunking.py data/standards.pdf data/chunks.json")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Processing: {pdf_path}")
    extract_clean_chunks(pdf_path, output_path)

    analyze_chunks(output_path)
