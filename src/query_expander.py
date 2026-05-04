"""Domain-aware query preprocessing and expansion — zero answer leakage."""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Typo correction
# ---------------------------------------------------------------------------

_TYPO_FIXES: dict[str, str] = {
    "asbestous": "asbestos",
    "asbestus": "asbestos",
    "portand": "portland",
    "portlnd": "portland",
    "cememnt": "cement",
    "cment": "cement",
    "aggreagte": "aggregate",
    "aggregaet": "aggregate",
    "reinfored": "reinforced",
    "reinforcment": "reinforcement",
    "sulphte": "sulphate",
    "sulpahte": "sulphate",
    "pozzalana": "pozzolana",
    "pozzlana": "pozzolana",
}

# ---------------------------------------------------------------------------
# Abbreviation expansion — semantic only, zero IS numbers
# ---------------------------------------------------------------------------

_ABBREVIATIONS: dict[str, str] = {
    "opc":  "ordinary portland cement",
    "ppc":  "portland pozzolana cement",
    "psc":  "portland slag cement",
    "hac":  "high alumina cement aluminous",
    "ssc":  "supersulphated cement marine",
    "rpc":  "rapid hardening portland cement",
    "rhpc": "rapid hardening portland cement",
    "srpc": "sulphate resisting portland cement",
    "lhpc": "low heat portland cement",
    "wpc":  "white portland cement",
    "rhc":  "rapid hardening cement",
    "esc":  "early strength cement",
    "fsc":  "fast setting cement",
    "rcc":  "reinforced cement concrete",
    "pcc":  "plain cement concrete",
    "ac":   "asbestos cement",
    "tmt":  "thermo mechanically treated bars steel",
    "fa":   "fine aggregate sand",
    "ca":   "coarse aggregate gravel crushed stone",
    "aac":  "autoclaved aerated concrete lightweight",
}

# ---------------------------------------------------------------------------
# Pre-compiled regex
# ---------------------------------------------------------------------------

_IS_NUMBER_RE  = re.compile(r"\bis[\-\s]*(\d)", re.IGNORECASE)
_PART_RE       = re.compile(r"part[\-\s]*(\d)", re.IGNORECASE)
_SEC_RE        = re.compile(r"sec[\-\s]*(\d)",  re.IGNORECASE)
_PART_PAREN_RE = re.compile(r"\(part\s*(\d+)\)", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize_query(query: str) -> str:
    """
    Lowercase, fix typos, normalise IS/part/sec spacing.
    Pure cleaning — no semantic injection.
    """
    q = query.strip().lower()

    for typo, fix in _TYPO_FIXES.items():
        if typo in q:
            q = q.replace(typo, fix)

    q = _IS_NUMBER_RE.sub(r"is \1", q)
    q = _PART_PAREN_RE.sub(r"part \1", q)
    q = _PART_RE.sub(r"part \1", q)
    q = _SEC_RE.sub(r"sec \1", q)
    q = _WHITESPACE_RE.sub(" ", q).strip()

    return q


# ---------------------------------------------------------------------------
# Semantic expansion map — ZERO IS numbers, ZERO answer leakage
#
# Philosophy (30-year veteran IR perspective):
#   • Query expansion adds SYNONYMS and RELATED CONCEPTS, not document IDs
#   • The retriever learns query→document mappings from corpus statistics
#   • If you inject "IS 8041" when the user says "rapid hardening", you are
#     hardcoding the answer instead of letting BM25/semantic search discover it
#   • This map should work even if you swap the corpus to BSI, ASTM, DIN, etc.
#
# Every entry here is a vocabulary bridge:
#   - "early strength" → "rapid hardening fast setting" (synonym)
#   - "sand" → "fine aggregate" (technical synonym)
#   - "marine" → "aggressive water supersulphated" (domain co-concepts)
#
# NOT allowed:
#   - "rapid hardening" → "IS 8041" ❌
#   - "sand" → "IS 2116" ❌
# ---------------------------------------------------------------------------

_EXPANSION_MAP: dict[str, str] = {
    # OPC grades — cement type vocabulary only
    "33 grade":              "ordinary portland cement low strength general purpose",
    "43 grade":              "ordinary portland cement moderate strength general construction",
    "53 grade":              "ordinary portland cement high strength structural",
    "grade 33":              "ordinary portland cement low strength",
    "grade 43":              "ordinary portland cement moderate strength",
    "grade 53":              "ordinary portland cement high strength",

    # Rapid hardening — synonym web only
    "rapid hardening":       "early strength fast setting quick hardening accelerated strength gain",
    "early strength":        "rapid hardening fast setting quick hardening accelerated",
    "early setting":         "rapid hardening fast setting early strength accelerated",
    "fast hardening":        "rapid hardening early strength fast setting accelerated",
    "fast setting":          "rapid hardening early strength quick setting accelerated",
    "quick hardening":       "rapid hardening early strength fast setting",
    "quick setting":         "rapid hardening fast setting early strength",

    # PPC — material synonyms only
    "fly ash cement":        "portland pozzolana cement pulverised fuel ash",
    "calcined clay cement":  "portland pozzolana cement thermally activated clay",
    "fly ash":               "pulverised fuel ash pozzolanic material",
    "calcined clay":         "thermally activated clay pozzolanic material",
    "pozzolana":             "pozzolanic material supplementary cementitious",

    # PSC — material synonyms only
    "slag cement":           "portland slag cement ground granulated blast furnace slag",
    "blast furnace slag":    "granulated slag ground blast furnace slag",
    "slag":                  "ground granulated blast furnace slag",

    # White cement — functional synonyms
    "white cement":          "white portland cement decorative architectural finishing",
    "decorative cement":     "white portland cement architectural finishing aesthetic",

    # Supersulphated — environmental/application synonyms
    "supersulphated":        "marine construction aggressive water sulphate attack resistance",
    "marine":                "aggressive water seawater sulphate attack corrosive environment",
    "aggressive water":      "marine environment sulphate attack corrosive water",

    # Sulphate resisting — chemical resistance synonyms
    "sulphate resisting":    "sulphate attack resistance chemical resistance aggressive soil",
    "sulphate resistant":    "sulphate resisting chemical resistance",
    "sulphate":              "sulphate attack chemical resistance aggressive environment",

    # High alumina — material/application synonyms
    "high alumina":          "aluminous cement refractory high temperature calcium aluminate",
    "aluminous":             "high alumina refractory calcium aluminate",
    "refractory cement":     "high alumina high temperature resistant",

    # Masonry cement
    "masonry cement":        "mortar general purpose non-structural masonry work",
    "masonry mortar":        "masonry cement mortar mix non-structural",

    # Hydrophobic
    "hydrophobic":           "water repellent prolonged storage moisture resistance",
    "prolonged storage":     "long term storage moisture resistance",

    # Low heat
    "low heat":              "low heat of hydration mass concrete dam construction thermal cracking",
    "mass concrete":         "large volume concrete low heat dam construction",

    # Sand / fine aggregate
    "sand":                  "fine aggregate masonry mortar",
    "sand for mortar":       "fine aggregate masonry mortar",
    "fine aggregate":        "sand natural aggregate",
    "coarse aggregate":      "crushed stone gravel natural aggregate",
    "aggregate":             "coarse fine natural aggregate crushed stone gravel",
    "crushed stone":         "coarse aggregate crushed rock angular aggregate",
    "gravel":                "coarse aggregate rounded aggregate natural stone",

    # Pipes — functional/application synonyms
    "precast pipe":          "precast concrete pipe drainage water supply",
    "water mains":           "water supply pipe distribution pipe potable water",
    "sewer pipe":            "drainage pipe wastewater sewerage",
    "culvert":               "drainage pipe storm water highway drainage",
    "drainage pipe":         "sewer pipe wastewater storm water",
    "prestressed pipe":      "prestressed concrete pipe pressure pipe",

    # Roofing / asbestos sheets
    "roofing":               "roofing sheet corrugated cladding covering",
    "roofing sheet":         "corrugated sheet roofing cladding covering",
    "cladding":              "roofing sheet corrugated covering facade",
    "corrugated sheet":      "corrugated roofing cladding profiled sheet",
    "asbestos sheet":        "asbestos cement sheet corrugated fibre cement",

    # Concrete blocks — functional/material synonyms
    "hollow block":          "hollow concrete block masonry unit cavity block",
    "solid block":           "solid concrete block masonry unit dense block",
    "concrete block":        "concrete masonry unit hollow solid block",
    "masonry block":         "concrete masonry unit building block",
    "lightweight block":     "lightweight concrete aerated block low density",
    "aerated concrete":      "autoclaved aerated concrete cellular concrete lightweight",
    "autoclaved aerated":    "aerated concrete cellular concrete lightweight",
    "precast hollow block":  "precast concrete hollow block masonry unit",
    "load bearing block":    "structural block load bearing masonry",
    "partition wall":        "non-load bearing block partition masonry",

    # Prestressed concrete
    "prestressed concrete":  "prestressing tendons post-tensioned pre-tensioned code of practice",
    "prestressed":           "prestressing post-tensioning pre-tensioning tendons",

    # Bricks
    "brick":                 "burnt clay brick masonry unit",
    "burnt clay brick":      "fired clay brick building brick masonry",
    "fly ash brick":         "fly ash lime brick non-fired brick",

    # Asbestos pressure pipe
    "asbestos cement pipe":  "asbestos cement pressure pipe fibre cement pipe",
}


def expand_query(query: str) -> str:
    """
    Normalise then inject relevant vocabulary.

    Zero IS numbers injected. Zero answer leakage.
    Expansion = semantic vocabulary bridging only.

    Cap: 5x original token count to prevent dilution.
    """
    q = normalize_query(query)
    parts = [q]

    # Abbreviation expansion
    for abbrev, full in _ABBREVIATIONS.items():
        if re.search(rf"\b{re.escape(abbrev)}\b", q):
            parts.append(full)

    # Phrase expansion — longest first, max 3 to stay focused
    matched = sorted(
        ((phrase, ctx) for phrase, ctx in _EXPANSION_MAP.items() if phrase in q),
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for phrase, ctx in matched[:3]:
        parts.append(ctx)

    combined = " ".join(parts)

    # Deduplicate
    seen: set[str] = set()
    deduped: list[str] = []
    for token in combined.split():
        tl = token.lower()
        if tl not in seen:
            seen.add(tl)
            deduped.append(token)

    # Cap at 5x original length
    original_len = len(q.split())
    return " ".join(deduped[: original_len * 5])


# ---------------------------------------------------------------------------
# Category detection — unchanged, zero IS numbers here either
# ---------------------------------------------------------------------------

_CATEGORY_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "cement_opc":              [("ordinary portland cement", 3), ("33 grade", 3), ("43 grade", 3), ("53 grade", 3), ("opc", 2), ("portland cement", 1)],
    "cement_rapid":            [("rapid hardening portland cement", 3), ("rapid hardening cement", 3), ("rapid hardening", 3), ("early strength cement", 3), ("early setting cement", 3), ("fast setting cement", 3), ("quick setting cement", 3), ("rhpc", 3), ("early strength", 2), ("fast setting", 2), ("rapid", 1)],
    "cement_ppc":              [("portland pozzolana cement", 3), ("fly ash based pozzolana", 3), ("calcined clay based pozzolana", 3), ("fly ash cement", 2), ("calcined clay", 2), ("ppc", 2), ("pozzolana", 1), ("fly ash", 1)],
    "cement_psc":              [("portland slag cement", 3), ("blast furnace slag cement", 3), ("slag cement", 2), ("blast furnace", 2), ("psc", 2), ("slag", 1)],
    "cement_white":            [("white portland cement", 3), ("white cement", 3), ("decorative cement", 2), ("wpc", 2), ("decorative", 1), ("architectural", 1)],
    "cement_supersulphated":   [("supersulphated cement", 3), ("marine works cement", 3), ("aggressive water cement", 3), ("supersulphated", 3), ("ssc", 2), ("marine works", 2), ("aggressive water", 2), ("marine", 1)],
    "cement_sulphate":         [("sulphate resisting portland cement", 3), ("sulphate resisting cement", 3), ("srpc", 3), ("sulphate resistant", 2), ("sulphate resisting", 2), ("sulphate", 1)],
    "cement_high_alumina":     [("high alumina cement", 3), ("aluminous cement", 3), ("refractory cement", 2), ("hac", 2), ("high alumina", 2), ("aluminous", 1)],
    "cement_masonry":          [("masonry cement", 3), ("mortar for masonry", 3), ("not structural concrete", 2), ("masonry mortar", 2), ("masonry", 1)],
    "cement_hydrophobic":      [("hydrophobic portland cement", 3), ("hydrophobic cement", 3), ("prolonged storage cement", 2), ("hydrophobic", 2)],
    "cement_low_heat":         [("low heat portland cement", 3), ("low heat cement", 3), ("mass concrete cement", 2), ("low heat", 2)],
    "aggregate":               [("coarse and fine aggregate", 3), ("aggregate for concrete", 2), ("coarse aggregate", 2), ("fine aggregate", 2), ("natural aggregate", 2), ("crushed stone", 1), ("gravel", 1), ("aggregate", 1)],
    "sand_mortar":             [("sand for masonry mortar", 3), ("fine aggregate mortar", 2), ("sand for mortar", 2), ("masonry sand", 2), ("sand", 1)],
    "pipe_concrete":           [("precast concrete pipe", 3), ("reinforced concrete pipe", 3), ("water main pipe", 3), ("sewer pipe", 2), ("culvert pipe", 2), ("water mains", 2), ("precast pipe", 2), ("concrete pipe", 1)],
    "sheet_asbestos":          [("corrugated asbestos cement sheet", 3), ("asbestos cement sheet", 3), ("roofing and cladding", 2), ("corrugated sheet", 2), ("roofing sheet", 2), ("asbestos sheet", 2), ("roofing", 1), ("cladding", 1)],
    "masonry_block":           [("hollow lightweight concrete block", 3), ("aerated concrete block", 3), ("autoclaved aerated block", 3), ("precast hollow block", 3), ("hollow concrete block", 2), ("concrete masonry unit", 2), ("concrete block", 2), ("hollow block", 2), ("lightweight block", 2), ("masonry block", 1)],
    "prestressed_pipe":        [("prestressed concrete pipe", 3), ("prestressed pipe", 3)],
    "prestressed_general":     [("prestressed concrete", 3), ("code of practice prestressed", 3), ("prestressed", 2), ("prestressing", 1)],
}


def detect_category(query: str) -> Optional[str]:
    """
    Return dominant category for soft boosting, or None if ambiguous.
    Minimum weighted score of 2 required.
    """
    q = normalize_query(query)
    scores: dict[str, int] = {}

    for category, signals in _CATEGORY_SIGNALS.items():
        total = sum(w for phrase, w in signals if phrase in q)
        if total > 0:
            scores[category] = total

    if not scores:
        return None

    best = max(scores, key=scores.__getitem__)
    return best if scores[best] >= 2 else None


# ---------------------------------------------------------------------------
# Domain hints — ISOLATED, OPTIONAL, RERANKER-ONLY
#
# ⚠️ WARNING: This is a hardcoded query→document mapping.
# It should ONLY be used for final reranking, NOT query expansion.
# The pipeline should have a flag to disable this entirely.
#
# Philosophy:
#   • The retriever finds candidates using BM25 + semantic search
#   • Domain hints apply a small final boost to specific standards
#     when we have HIGH CONFIDENCE the query implies them
#   • Boost magnitude should be small (1.05–1.15x, not 2x)
#   • This is the ONLY place IS numbers appear in the entire expander
# ---------------------------------------------------------------------------

_DOMAIN_HINTS: dict[str, list[str]] = {
    "33 grade":                    ["IS 269"],
    "grade 33":                    ["IS 269"],
    "43 grade":                    ["IS 8112"],
    "grade 43":                    ["IS 8112"],
    "53 grade":                    ["IS 12269"],
    "grade 53":                    ["IS 12269"],
    "rapid hardening":             ["IS 8041"],
    "early strength":              ["IS 8041"],
    "fly ash":                     ["IS 1489"],
    "calcined clay":               ["IS 1489"],
    "slag":                        ["IS 455"],
    "white cement":                ["IS 8042"],
    "supersulphated":              ["IS 6909"],
    "marine":                      ["IS 6909"],
    "sulphate resisting":          ["IS 12330"],
    "high alumina":                ["IS 6452"],
    "masonry cement":              ["IS 3466"],
    "hydrophobic":                 ["IS 8043"],
    "low heat":                    ["IS 12600"],
    "sand":                        ["IS 2116"],
    "coarse aggregate":            ["IS 383"],
    "fine aggregate":              ["IS 383"],
    "precast pipe":                ["IS 458"],
    "prestressed pipe":            ["IS 784"],
    "roofing":                     ["IS 459"],
    "asbestos":                    ["IS 459", "IS 1592"],
    "hollow block":                ["IS 2185", "IS 9142"],
    "aerated":                     ["IS 2185"],
    "prestressed concrete":        ["IS 1343"],
    "brick":                       ["IS 1077"],
}


def get_domain_hints(query: str, enabled: bool = False) -> list[str]:
    """
    Return IS standard identifiers for final reranking boost.

    Args:
        query: Normalized user query
        enabled: Master switch — set False to disable all hint logic

    Returns:
        List of IS standard numbers (e.g. ["IS 8041", "IS 1343"])
        Empty list if disabled or no confident match
    """
    if not enabled:
        return []

    q = normalize_query(query)
    hints: list[str] = []
    seen: set[str] = set()

    # Longest phrase first so specific wins over general
    candidates = sorted(
        ((phrase, stds) for phrase, stds in _DOMAIN_HINTS.items() if phrase in q),
        key=lambda x: len(x[0]),
        reverse=True,
    )

    for phrase, stds in candidates:
        for std in stds:
            if std not in seen:
                hints.append(std)
                seen.add(std)

    return hints


def get_expander_stats() -> dict:
    return {
        "abbreviations":       len(_ABBREVIATIONS),
        "expansion_map":       len(_EXPANSION_MAP),
        "category_signals":    len(_CATEGORY_SIGNALS),
        "domain_hints":        len(_DOMAIN_HINTS),
        "expansion_cap":       "5x original token count",
        "phrase_match":        "longest-first, max 3 expansions",
        "is_numbers_in_expansion": 0,  # ← ZERO
        "philosophy":          "semantic vocabulary only, zero answer leakage",
    }