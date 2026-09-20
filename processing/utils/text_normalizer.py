import re
import unicodedata

LIGATURE_MAP = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "ft",
    "ﬆ": "st",
    "œ": "oe",
    "Œ": "OE",
    "æ": "ae",
    "Æ": "AE",
    "\u00ad": "",  # Soft hyphen
}


def normalize_archival_text(text: str) -> str:
    """
    Normalizes extracted text from historical archival documents.
    
    Performs:
    1. Unicode NFKC normalization
    2. Historical ligature and special character unfolding
    3. Soft hyphen and hyphenated line break resolution (dehyphenation)
    4. Control character removal (preserving tabs and newlines)
    5. Line-ending regularization and excessive whitespace collapse
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Historical ligature replacement
    for lig, replacement in LIGATURE_MAP.items():
        text = text.replace(lig, replacement)

    # 3. Regularize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 4. Remove unprintable control characters (keep \t, \n)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # 5. Resolve line-break hyphenation (e.g., 'revo-\nlution' -> 'revolution')
    # Match lowercase word character followed by hyphen, newline, and lowercase word character
    text = re.sub(r"([a-zA-Z]{2,})-\n([a-zA-Z]{2,})", r"\1\2", text)

    # 6. Normalize multiple horizontal whitespace characters (spaces/tabs) on each line
    lines = []
    for line in text.split("\n"):
        normalized_line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(normalized_line)

    text = "\n".join(lines)

    # 7. Collapse more than 2 consecutive newlines into 2 (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
