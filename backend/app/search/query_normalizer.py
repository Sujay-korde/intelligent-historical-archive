import re
import unicodedata

LIGATURE_MAP = {
    "æ": "ae",
    "Æ": "AE",
    "œ": "oe",
    "Œ": "OE",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ſ": "s",
}


def normalize_search_query(query: str) -> str:
    """
    Normalizes historical and modern search query strings for optimal vector and keyword matching:
    1. Strips extraneous whitespace and control characters.
    2. Decomposes/replaces historical typographic ligatures (æ, œ, ﬁ, etc.).
    3. Normalizes smart quotes, apostrophes, and dashes to standard ASCII equivalents.
    4. Condenses internal whitespace.
    """
    if not query:
        return ""

    text = query.strip()

    # Replace ligatures
    for lig, rep in LIGATURE_MAP.items():
        text = text.replace(lig, rep)

    # Normalize typographic quotes and apostrophes
    text = re.sub(r"[\u2018\u2019\u201A\u201B`]", "'", text)
    text = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', text)

    # Normalize typographic dashes/hyphens
    text = re.sub(r"[\u2013\u2014\u2015]", "-", text)

    # Unicode normalization (NFKC)
    text = unicodedata.normalize("NFKC", text)

    # Condense multiple whitespace chars
    text = re.sub(r"\s+", " ", text)

    return text.strip()
