"""Standard ID deduplication and output formatting."""

import re
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
from src.normalizer import format_standard_id

_VALID_OUTPUT = re.compile(
    r"^IS\s+\d+(?:\s+\(Part\s+\d+\))?\s*:\s*\d{4}$", re.IGNORECASE
)


def extract_base_key(formatted_id: str) -> str:
    """
    Extract base key for deduplication grouping.

    Key format: "<IS_number>_part<N>" or just "<IS_number>"

    Examples:
        "IS 2185 (Part 1): 1979" → "2185_part1"
        "IS 2185 (Part 2): 1983" → "2185_part2"  (different from Part 1!)
        "IS 269: 1989"           → "269"

    This ensures Part 1 and Part 2 are treated as SEPARATE standards.
    """
    num_match = re.search(r"IS\s+(\d+)", formatted_id, re.IGNORECASE)
    if not num_match:
        return formatted_id.lower()

    base = num_match.group(1)

    part_match = re.search(r"\(Part\s+(\d+)\)", formatted_id, re.IGNORECASE)
    if part_match:
        base += f"_part{part_match.group(1)}"

    return base


def extract_year_from_id(formatted_id: str) -> Optional[int]:
    """
    Extract year from formatted standard ID.

    Examples:
        "IS 269: 1989" → 1989
        "IS 2185 (Part 1): 1979" → 1979
        "IS 383" → None
    """
    match = re.search(r":\s*(\d{4})\s*$", formatted_id)
    if match:
        return int(match.group(1))
    return None


def pick_best_year_version(candidates: List[Dict]) -> Dict:
    """
    From multiple versions of same standard with different years,
    pick the best one.

    Selection priority:
    1. Matches chunk metadata year (most reliable source)
    2. Most recent year (likely current version)
    3. First in ranking order (preserves reranker preference)

    Args:
        candidates: List of candidate dicts with keys:
                   {doc, formatted_id, year, metadata_year, rank_position}

    Returns:
        Dict: Best candidate
    """
    if len(candidates) == 1:
        return candidates[0]

    for candidate in candidates:
        id_year = candidate.get("year")
        meta_year = candidate.get("metadata_year")

        if id_year and meta_year and id_year == meta_year:
            return candidate

    candidates_with_year = [c for c in candidates if c.get("year")]
    if candidates_with_year:
        return max(candidates_with_year, key=lambda c: c["year"])

    return min(candidates, key=lambda c: c.get("rank_position", 9999))


def generate_standards(
    docs: List[Dict], max_results: int = 5
) -> Tuple[List[str], List[Dict]]:
    """
    Deduplicate reranked documents and generate exactly max_results standard IDs.

    Smart deduplication:
    - Groups by base standard key (IS number + Part if exists)
    - For duplicate years, picks best match (metadata year > recent > first)
    - Part 1 and Part 2 treated as DIFFERENT standards
    - Always outputs EXACTLY max_results (pads if needed)

    Output format validation:
    - Enforces canonical format: "IS 2185 (Part 1): 1979"
    - Rejects IDs without valid year
    - Matches evaluation dataset format exactly

    Args:
        docs: List of document dicts (from reranker, in ranked order)
        max_results: Number of standards to return (default 5)

    Returns:
        Tuple[List[str], List[Dict]]:
            - List of standard IDs (formatted, deduplicated)
            - List of corresponding document dicts (for rationale generation)

    Guarantees:
        - Output length == max_results (exact, not "up to")
        - All IDs match _VALID_OUTPUT pattern
        - Ranking order preserved (best first)
        - No duplicates (same base standard + part + year)
    """

    if not docs:
        return [], []

    candidates_by_key = defaultdict(list)

    for rank_pos, doc in enumerate(docs):
        raw_id = doc.get("id", "")
        formatted_id = format_standard_id(raw_id)

        if not _VALID_OUTPUT.match(formatted_id):
            continue

        base_key = extract_base_key(formatted_id)

        id_year = extract_year_from_id(formatted_id)
        metadata_year = doc.get("standard_year")

        candidate = {
            "doc": doc,
            "formatted_id": formatted_id,
            "year": id_year,
            "metadata_year": metadata_year,
            "rank_position": rank_pos,
        }

        candidates_by_key[base_key].append(candidate)

    deduplicated = []

    for base_key, candidates in candidates_by_key.items():
        best = pick_best_year_version(candidates)
        deduplicated.append(best)

    deduplicated.sort(key=lambda c: c["rank_position"])

    output_ids = []
    output_docs = []
    seen_ids = set()

    for candidate in deduplicated:
        if len(output_ids) >= max_results:
            break

        formatted_id = candidate["formatted_id"]

        if formatted_id in seen_ids:
            continue

        output_ids.append(formatted_id)
        output_docs.append(candidate["doc"])
        seen_ids.add(formatted_id)

    if len(output_ids) < max_results:
        for rank_pos, doc in enumerate(docs):
            if len(output_ids) >= max_results:
                break

            formatted_id = format_standard_id(doc.get("id", ""))

            if _VALID_OUTPUT.match(formatted_id) and formatted_id not in seen_ids:
                output_ids.append(formatted_id)
                output_docs.append(doc)
                seen_ids.add(formatted_id)

    if len(output_ids) < max_results:
        import sys

        print(
            f"⚠️  Warning: Only {len(output_ids)} valid standards found "
            f"(requested {max_results}). Input had {len(docs)} docs.",
            file=sys.stderr,
        )

    return output_ids[:max_results], output_docs[:max_results]


def validate_output_format(standard_ids: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all output IDs match canonical format.

    Returns:
        Tuple[bool, List[str]]: (all_valid, list_of_invalid_ids)
    """
    invalid = []

    for std_id in standard_ids:
        if not _VALID_OUTPUT.match(std_id):
            invalid.append(std_id)

    all_valid = len(invalid) == 0
    return all_valid, invalid


def analyze_deduplication(docs: List[Dict], output_ids: List[str]):
    """
    Print deduplication analysis for debugging.
    Shows what was merged and why.
    """
    print("\n" + "=" * 70)
    print("📊 DEDUPLICATION ANALYSIS")
    print("=" * 70)

    print(f"\nInput:  {len(docs)} documents")
    print(f"Output: {len(output_ids)} unique standards")
    print(f"Merged: {len(docs) - len(output_ids)} duplicates")

    groups = defaultdict(list)
    for doc in docs:
        formatted = format_standard_id(doc.get("id", ""))
        if _VALID_OUTPUT.match(formatted):
            key = extract_base_key(formatted)
            groups[key].append(formatted)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if duplicates:
        print(f"\n🔀 Found {len(duplicates)} standards with multiple versions:")
        for base_key, versions in list(duplicates.items())[:5]:
            print(f"\n  {base_key}:")
            for v in versions:
                selected = "✓ SELECTED" if v in output_ids else "  (skipped)"
                print(f"    {v} {selected}")

        if len(duplicates) > 5:
            print(f"\n  ... and {len(duplicates) - 5} more")
    else:
        print("\n✓ No duplicate versions found")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    test_docs = [
        {
            "id": "IS 269: 1989",
            "standard_year": 1989,
            "text": "Ordinary Portland Cement 33 grade...",
        },
        {
            "id": "IS269:1989",
            "standard_year": 1989,
            "text": "Ordinary Portland Cement...",
        },
        {
            "id": "IS 269: 2013",
            "standard_year": 2013,
            "text": "Ordinary Portland Cement 33 grade (revised)...",
        },
        {
            "id": "IS 2185 (Part 1): 1979",
            "standard_year": 1979,
            "text": "Concrete masonry units Part 1...",
        },
        {
            "id": "IS 2185 (Part 2): 1983",
            "standard_year": 1983,
            "text": "Concrete masonry units Part 2 lightweight...",
        },
        {
            "id": "IS 383: 1970",
            "standard_year": 1970,
            "text": "Coarse and fine aggregates...",
        },
    ]

    print("Testing generate_standards()...\n")

    output_ids, output_docs = generate_standards(test_docs, max_results=5)

    print(f"Output IDs ({len(output_ids)}):")
    for i, std_id in enumerate(output_ids, 1):
        print(f"  {i}. {std_id}")

    all_valid, invalid = validate_output_format(output_ids)

    if all_valid:
        print("\n✅ All output IDs have valid format")
    else:
        print(f"\n❌ Invalid IDs found: {invalid}")

    analyze_deduplication(test_docs, output_ids)
