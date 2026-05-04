"""Metadata enrichment and validation pipeline."""

import json
import re
from collections import Counter, defaultdict
from typing import List, Dict, Set, Optional, Tuple

TECHNICAL_PROPERTIES = {
    # Physical properties
    "physical": [
        "compressive strength",
        "tensile strength",
        "flexural strength",
        "modulus of elasticity",
        "density",
        "bulk density",
        "specific gravity",
        "fineness",
        "surface area",
        "blaine fineness",
        "particle size",
        "water absorption",
        "moisture content",
        "permeability",
        "dimensional stability",
        "shrinkage",
        "expansion",
        "soundness",
        "setting time",
        "initial setting",
        "final setting",
        "consistency",
        "workability",
        "slump",
        "flow",
        "compaction factor",
    ],
    # Chemical properties
    "chemical": [
        "chemical composition",
        "loss on ignition",
        "insoluble residue",
        "magnesia content",
        "sulphuric anhydride",
        "chloride content",
        "alkali content",
        "lime saturation factor",
        "alumina modulus",
        "silica modulus",
        "iron modulus",
        "free lime",
        "tricalcium aluminate",
        "tricalcium silicate",
        "dicalcium silicate",
        "ph value",
    ],
    # Test methods
    "testing": [
        "test method",
        "sampling procedure",
        "specimen preparation",
        "sieve analysis",
        "grading",
        "gradation",
        "particle size distribution",
        "crushing value",
        "impact value",
        "abrasion value",
        "soundness test",
        "autoclave expansion",
        "le chatelier test",
        "vicat apparatus",
        "gillmore needle",
        "compressive testing",
        "tensile testing",
        "hydrostatic pressure test",
        "impermeability test",
    ],
    # Manufacturing
    "manufacturing": [
        "manufacture",
        "production",
        "processing",
        "composition",
        "raw materials",
        "clinker",
        "gypsum",
        "grinding",
        "blending",
        "calcination",
        "hydration",
        "curing",
        "autoclaving",
        "steam curing",
        "air curing",
        "maturity",
        "age",
    ],
    # Quality requirements
    "quality": [
        "specification",
        "requirements",
        "tolerance",
        "acceptance criteria",
        "conformity",
        "compliance",
        "quality control",
        "quality assurance",
        "inspection",
        "certification",
        "marking",
        "packaging",
        "storage",
    ],
}


APPLICATION_DOMAINS = {
    "structural_concrete": [
        "structural concrete",
        "reinforced concrete",
        "load bearing",
        "beam",
        "column",
        "slab",
        "foundation",
        "footing",
        "retaining wall",
    ],
    "mass_concrete": [
        "mass concrete",
        "dam",
        "large volume",
        "low heat",
        "thermal cracking",
    ],
    "marine_coastal": [
        "marine",
        "coastal",
        "aggressive water",
        "seawater",
        "tidal",
        "offshore",
        "sulphate attack",
        "chloride environment",
    ],
    "road_pavement": ["road", "pavement", "highway", "runway", "rigid pavement"],
    "building_construction": [
        "building",
        "residential",
        "commercial",
        "housing",
        "superstructure",
        "wall",
        "partition",
        "flooring",
        "roofing",
        "cladding",
    ],
    "precast_products": [
        "precast",
        "prefabricated",
        "factory made",
        "modular",
        "ready-made",
    ],
    "masonry_work": [
        "masonry",
        "brickwork",
        "blockwork",
        "stone masonry",
        "mortar",
        "jointing",
        "plastering",
        "rendering",
    ],
    "water_infrastructure": [
        "water supply",
        "water main",
        "pipeline",
        "drainage",
        "sewerage",
        "sewer",
        "culvert",
        "irrigation",
        "water tank",
        "reservoir",
    ],
    "architectural_decorative": [
        "architectural",
        "decorative",
        "aesthetic",
        "finish",
        "facade",
        "white cement",
        "colored",
        "textured",
    ],
    "special_applications": [
        "refractory",
        "high temperature",
        "furnace",
        "kiln",
        "chemical resistant",
        "acid resistant",
        "abrasion resistant",
        "waterproofing",
        "insulation",
    ],
}


COMPOSITION_TERMS = [
    # Cement types and components
    "portland cement",
    "clinker",
    "gypsum",
    "pozzolana",
    "fly ash",
    "ground granulated blast furnace slag",
    "ggbs",
    "slag",
    "calcined clay",
    "silica fume",
    "metakaolin",
    # Aggregates
    "fine aggregate",
    "sand",
    "coarse aggregate",
    "gravel",
    "crushed stone",
    "lightweight aggregate",
    "expanded clay",
    "pumice",
    "vermiculite",
    # Admixtures
    "admixture",
    "plasticizer",
    "superplasticizer",
    "retarder",
    "accelerator",
    "air entraining agent",
    "waterproofing compound",
    # Reinforcement
    "steel reinforcement",
    "rebar",
    "wire",
    "mesh",
    "fiber",
    "prestressing steel",
    "high tensile wire",
    # Special materials
    "asbestos fiber",
    "cellulose fiber",
    "polypropylene fiber",
    "calcium aluminate",
    "alumina cement",
    "lime",
    "hydrated lime",
    "calcium hydroxide",
    "calcium carbonate",
    "dolomite",
]


TEST_METHOD_INDICATORS = [
    "test method",
    "method of test",
    "determination of",
    "testing of",
    "sampling of",
    "procedure for",
    "measurement of",
    "analysis of",
    "specification for tests",
    "methods of sampling",
]

TEST_METHOD_STANDARDS = {
    "4031",
    "4032",
    "1727",
    "3812",
    "3535",
    "8142",
    "8143",
    "2386",
    "1199",
    "1124",
    "5512",
    "5514",
    "6441",
}


def extract_standard_number(std_id: str) -> str:
    """Extract base standard number from ID (e.g., 'IS 2185 (Part 1): 1979' → '2185')"""
    match = re.search(r"IS\s*(\d+)", std_id, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_related_standards(text: str, own_id: str) -> List[str]:
    """
    Extract references to other IS standards mentioned in text.
    Returns list of standard IDs (without duplicating the document's own ID).
    """
    pattern = re.compile(
        r"IS\s+(\d{1,5}(?:\s*\(Part\s+\d+\))?(?:\s*:\s*\d{4})?)", re.IGNORECASE
    )

    matches = pattern.findall(text)

    own_base = extract_standard_number(own_id)

    related = set()
    for match in matches:
        normalized = "IS " + re.sub(r"\s+", " ", match).strip()

        ref_base = extract_standard_number(normalized)
        if ref_base != own_base:
            related.add(normalized)

    return sorted(list(related))[:15]


def extract_technical_properties(text: str) -> Dict[str, List[str]]:
    """
    Extract technical property terms from text, grouped by category.
    Returns dict: {category: [terms found]}
    """
    text_lower = text.lower()

    found_properties = {}
    for category, terms in TECHNICAL_PROPERTIES.items():
        found = [term for term in terms if term in text_lower]
        if found:
            found_properties[category] = list(set(found))[:10]

    return found_properties


def detect_application_domains(text: str) -> List[str]:
    """
    Detect applicable domain(s) for the standard.
    Returns list of domain names, sorted by relevance (match count).
    """
    text_lower = text.lower()

    domain_scores = {}
    for domain, keywords in APPLICATION_DOMAINS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            domain_scores[domain] = score

    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)

    return [domain for domain, _ in sorted_domains][:3]


def extract_composition_terms(text: str) -> List[str]:
    """Extract material composition terms from text."""
    text_lower = text.lower()

    found = [term for term in COMPOSITION_TERMS if term in text_lower]
    return list(set(found))[:12]


def is_test_method_standard(text: str, std_id: str) -> bool:
    """
    Determine if this is a test method/sampling standard.
    Returns True if likely a test method standard.
    """
    text_lower = text.lower()

    base_num = extract_standard_number(std_id)
    if base_num in TEST_METHOD_STANDARDS:
        return True

    indicator_count = sum(
        1 for indicator in TEST_METHOD_INDICATORS if indicator in text_lower
    )

    return indicator_count >= 2


def extract_superseding_info(text: str) -> Optional[str]:
    """
    Extract information about superseding standards if mentioned.
    Returns standard ID string or None.
    """
    pattern = re.compile(
        r"(?:superseded|replaced|revised)\s+by\s+IS\s+(\d+(?:\s*:\s*\d{4})?)",
        re.IGNORECASE,
    )

    match = pattern.search(text)
    if match:
        return "IS " + match.group(1)
    return None


def validate_chunk_quality(chunk: Dict) -> Tuple[bool, List[str]]:
    """
    Validate chunk metadata quality.
    Returns (is_valid, list_of_issues)
    """
    issues = []

    if not chunk.get("id"):
        issues.append("Missing ID")

    if not chunk.get("text") or len(chunk["text"].strip()) < 20:
        issues.append("Text too short or missing")

    if not chunk.get("category"):
        issues.append("Missing category")

    if not chunk.get("keywords") or len(chunk.get("keywords", [])) == 0:
        issues.append("No keywords extracted")

    text = chunk.get("text", "")
    if text.count("*") > 50 or text.count("†") > 20:
        issues.append("Possible text corruption (excessive symbols)")

    is_valid = len(issues) == 0
    return is_valid, issues


def enrich_chunk(chunk: Dict) -> Dict:
    """
    Enrich a single chunk with additional metadata.

    Adds:
    - related_standards: cross-referenced IS standards
    - technical_properties: property terms grouped by category
    - application_domains: where this standard is used
    - composition_terms: material ingredients
    - is_test_method: flag for test/sampling standards
    - superseded_by: if this standard is superseded

    Returns enriched chunk dict.
    """
    std_id = chunk.get("id", "")
    text = chunk.get("text", "")

    related = extract_related_standards(text, std_id)
    properties = extract_technical_properties(text)
    domains = detect_application_domains(text)
    composition = extract_composition_terms(text)
    is_test = is_test_method_standard(text, std_id)
    superseded = extract_superseding_info(text)

    enriched = dict(chunk)

    enriched["related_standards"] = related
    enriched["technical_properties"] = properties
    enriched["application_domains"] = domains
    enriched["composition_terms"] = composition
    enriched["is_test_method"] = is_test

    if superseded:
        enriched["superseded_by"] = superseded

    return enriched


def build_enriched_chunks(input_path: str, output_path: str):
    """
    Main enrichment pipeline.

    Input: chunks.json from chunking.py (with basic metadata)
    Output: chunks_enriched.json (with full metadata)

    Process:
    1. Load chunks from chunking.py
    2. Enrich each chunk with additional metadata
    3. Validate chunk quality
    4. Generate statistics
    5. Save enriched chunks
    """
    print("\n" + "=" * 70)
    print("🔧 METADATA ENRICHMENT PIPELINE")
    print("=" * 70)

    print(f"\n📥 Loading chunks from: {input_path}")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {input_path}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in input file: {e}")
        return

    print(f"   Loaded {len(chunks)} chunks")

    print(f"\n⚙️  Enriching chunks with additional metadata...")

    enriched_chunks = []
    validation_issues = []

    for i, chunk in enumerate(chunks):
        try:
            enriched = enrich_chunk(chunk)

            is_valid, issues = validate_chunk_quality(enriched)
            if not is_valid:
                validation_issues.append(
                    {
                        "chunk_index": i,
                        "id": enriched.get("id", "unknown"),
                        "issues": issues,
                    }
                )

            enriched_chunks.append(enriched)

        except Exception as e:
            print(
                f"   ⚠️  Warning: Failed to enrich chunk {i} ({chunk.get('id', 'unknown')}): {e}"
            )
            enriched_chunks.append(chunk)

    print(f"   ✓ Enriched {len(enriched_chunks)} chunks")

    if validation_issues:
        print(f"   ⚠️  Found {len(validation_issues)} chunks with quality issues")

    print(f"\n📊 Generating statistics...")

    categories = Counter(c.get("category", "unknown") for c in enriched_chunks)

    all_domains = []
    for c in enriched_chunks:
        all_domains.extend(c.get("application_domains", []))
    domains = Counter(all_domains)

    test_method_count = sum(1 for c in enriched_chunks if c.get("is_test_method"))

    anchor_count = sum(1 for c in enriched_chunks if c.get("is_summary_chunk"))
    content_count = len(enriched_chunks) - anchor_count

    part_chunks = sum(1 for c in enriched_chunks if c.get("part_number") is not None)

    chunks_with_refs = sum(1 for c in enriched_chunks if c.get("related_standards"))

    print("\n" + "=" * 70)
    print("📈 ENRICHMENT STATISTICS")
    print("=" * 70)

    print(f"\n📦 Chunk Breakdown:")
    print(f"   Total chunks:           {len(enriched_chunks)}")
    print(f"   ⚓ Anchor chunks:        {anchor_count}")
    print(f"   📄 Content chunks:       {content_count}")
    print(f"   🔢 Multi-part chunks:    {part_chunks}")
    print(f"   🧪 Test method stds:     {test_method_count}")
    print(f"   🔗 With cross-refs:      {chunks_with_refs}")

    print(f"\n📂 Top 10 Categories:")
    for cat, count in categories.most_common(10):
        pct = (count / len(enriched_chunks)) * 100
        print(f"   {cat:25} {count:4} ({pct:5.1f}%)")

    print(f"\n🌍 Top 10 Application Domains:")
    for domain, count in domains.most_common(10):
        print(f"   {domain:30} {count:4}")

    if validation_issues:
        print(f"\n⚠️  Quality Issues ({len(validation_issues)} chunks):")
        for issue in validation_issues[:5]:
            print(
                f"   Chunk {issue['chunk_index']} ({issue['id']}): {', '.join(issue['issues'])}"
            )
        if len(validation_issues) > 5:
            print(f"   ... and {len(validation_issues) - 5} more")

    print(f"\n💾 Saving enriched chunks to: {output_path}")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enriched_chunks, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Successfully saved {len(enriched_chunks)} enriched chunks")
    except Exception as e:
        print(f"   ❌ Error saving output: {e}")
        return

    print("\n" + "=" * 70)
    print("✨ ENRICHMENT COMPLETE")
    print("=" * 70 + "\n")


def analyze_enriched_chunks(enriched_path: str):
    """
    Detailed analysis of enriched chunks.
    Useful for debugging and quality checking.
    """
    with open(enriched_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print("\n" + "=" * 70)
    print("🔍 DETAILED ENRICHED CHUNKS ANALYSIS")
    print("=" * 70)

    print("\n📝 Sample Enriched Chunks:\n")

    for i, chunk in enumerate(chunks[:3], 1):
        print(f"{'─'*70}")
        print(f"SAMPLE {i}")
        print(f"{'─'*70}")
        print(f"ID:               {chunk.get('id', 'N/A')}")
        print(f"Title:            {chunk.get('title', 'N/A')[:60]}...")
        print(f"Category:         {chunk.get('category', 'N/A')}")
        print(f"Part Number:      {chunk.get('part_number', 'N/A')}")
        print(f"Year:             {chunk.get('standard_year', 'N/A')}")
        print(f"Is Summary:       {chunk.get('is_summary_chunk', False)}")
        print(f"Is Test Method:   {chunk.get('is_test_method', False)}")
        print(f"\nKeywords ({len(chunk.get('keywords', []))}):")
        print(f"  {', '.join(chunk.get('keywords', [])[:8])}")
        print(f"\nApplication Domains ({len(chunk.get('application_domains', []))}):")
        print(f"  {', '.join(chunk.get('application_domains', []))}")
        print(f"\nComposition Terms ({len(chunk.get('composition_terms', []))}):")
        print(f"  {', '.join(chunk.get('composition_terms', [])[:6])}")
        print(f"\nRelated Standards ({len(chunk.get('related_standards', []))}):")
        print(f"  {', '.join(chunk.get('related_standards', [])[:5])}")

        tech_props = chunk.get("technical_properties", {})
        if tech_props:
            print(f"\nTechnical Properties:")
            for prop_type, props in list(tech_props.items())[:2]:
                print(f"  {prop_type}: {', '.join(props[:3])}")

        print(f"\nText preview: {chunk.get('text', '')[:150]}...")
        print()

    print("=" * 70 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python metadata_builder.py <input_chunks.json> <output_enriched.json>"
        )
        print("\nExample:")
        print("  python metadata_builder.py data/chunks.json data/chunks_enriched.json")
        print("\nFor analysis:")
        print("  python metadata_builder.py --analyze data/chunks_enriched.json")
        sys.exit(1)

    if sys.argv[1] == "--analyze":
        analyze_enriched_chunks(sys.argv[2])
    else:
        input_path = sys.argv[1]
        output_path = sys.argv[2]

        build_enriched_chunks(input_path, output_path)

        print("\n" + "=" * 70)
        print("Running automatic analysis on enriched output...")
        print("=" * 70)
        analyze_enriched_chunks(output_path)
