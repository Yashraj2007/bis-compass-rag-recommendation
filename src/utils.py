def expand_query(query):
    q = query.lower()
    synonyms = {
        "opc": "ordinary portland cement",
        "ppc": "portland pozzolana cement",
        "psc": "portland slag cement",
        "tmt": "thermo mechanically treated bars",
        "ac": "asbestos cement",
        "hac": "high alumina cement",
        "ssc": "supersulphated cement",
        "33 grade": "is 269 ordinary portland cement 33 grade",
        "43 grade": "is 8112 ordinary portland cement 43 grade",
        "53 grade": "is 12269 ordinary portland cement 53 grade",
    }

    expanded = q
    for abbrev, full in synonyms.items():
        if abbrev in q:
            expanded += f" {full}"
    return expanded
