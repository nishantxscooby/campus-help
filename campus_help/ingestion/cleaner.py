"""Conservative normalization of extracted PDF text."""

import re


def clean_text(text: str) -> str:
    """Normalize PDF layout artifacts while preserving words, numbers, and punctuation."""
    text = text.replace("\u00ad", "")
    text = re.sub(r"-\s*\n\s*(?=\w)", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
