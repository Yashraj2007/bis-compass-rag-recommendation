"""Standard ID normalization and canonical formatting."""

import re


def normalize(std_string):
    if not std_string:
        return ""
    return str(std_string).replace(" ", "").lower()


_KNOWN_YEARS = {
    "269": "1989",
    "260": "1978",
    "280": "1978",
    "383": "1970",
    "432": "1982",
    "455": "1989",
    "458": "2003",
    "459": "1992",
    "784": "2001",
    "1077": "1992",
    "1127": "1970",
    "1195": "2002",
    "1237": "1980",
    "1489": "1991",
    "1542": "1992",
    "1592": "2003",
    "1626": "1994",
    "1755": "1983",
    "1786": "1985",
    "1834": "1984",
    "2062": "1999",
    "2090": "1983",
    "2096": "1991",
    "2098": "1997",
    "2116": "1980",
    "2185": "1979",
    "2386": "1963",
    "2686": "1977",
    "2849": "1983",
    "3182": "1986",
    "3466": "1988",
    "3812": "1981",
    "3954": "1991",
    "4031": "1988",
    "4032": "1985",
    "4350": "1967",
    "4351": "2003",
    "4996": "1984",
    "5455": "1969",
    "5751": "1984",
    "5758": "1984",
    "5820": "1969",
    "5913": "2003",
    "6073": "1971",
    "6441": "1985",
    "6452": "1989",
    "6523": "1983",
    "6579": "1981",
    "6598": "1972",
    "6908": "1991",
    "6909": "1990",
    "7322": "1985",
    "7509": "1993",
    "8041": "1990",
    "8042": "1989",
    "8043": "1991",
    "8112": "1989",
    "9142": "1979",
    "9523": "1980",
    "9627": "1980",
    "9743": "1990",
    "9893": "1981",
    "10388": "1982",
    "10772": "1983",
    "12269": "1987",
    "12330": "1988",
    "12423": "1988",
    "12440": "1988",
    "12592": "2002",
    "13000": "1990",
    "13008": "1990",
    "13356": "1992",
    "13990": "1994",
    "14215": "1994",
    "14241": "1995",
    "14242": "1995",
    "14856": "2000",
    "14862": "2000",
    "14871": "2000",
    "15380": "2003",
    "15476": "2004",
    "1784": "2001",
}

_KNOWN_PART_YEARS = {
    "1489-1": "1991",
    "1489-2": "1991",
    "1626-2": "1994",
    "2185-1": "1979",
    "2185-2": "1983",
    "2185-3": "1984",
    "2386-2": "1963",
    "4031-1": "1996",
    "4031-2": "1999",
}


def format_standard_id(raw_id):
    """
    Convert any raw standard ID string into canonical format: "IS XXXX: YYYY"
    or "IS XXXX (Part N): YYYY" for multi-part standards.

    Handles all known edge cases:
      "IS 269 : 1989"       → "IS 269: 1989"
      "IS 8112:1989"        → "IS 8112: 1989"
      "IS 459"              → "IS 459: 1992"
      "IS 1489(Part 2):1991"→ "IS 1489 (Part 2): 1991"
      "IS 2185 (Part 2) 1983"→"IS 2185 (Part 2): 1983"
    """
    if not raw_id:
        return raw_id

    text = str(raw_id).strip()

    pattern = re.compile(
        r"IS\s*(\d+)" r"(?:\s*\(?\s*Part\s*(\d+)\s*\)?)?" r"(?:\s*[:\-]?\s*(\d{4}))?",
        re.IGNORECASE,
    )

    match = pattern.search(text)
    if not match:
        return text

    main_num = match.group(1)
    part_num = match.group(2)
    year = match.group(3)

    if not year:
        if part_num:
            key = f"{main_num}-{part_num}"
            year = _KNOWN_PART_YEARS.get(key, _KNOWN_YEARS.get(main_num, ""))
        else:
            year = _KNOWN_YEARS.get(main_num, "")

    if part_num and year:
        return f"IS {main_num} (Part {part_num}): {year}"
    elif part_num:
        return f"IS {main_num} (Part {part_num})"
    elif year:
        return f"IS {main_num}: {year}"
    else:
        return f"IS {main_num}"
