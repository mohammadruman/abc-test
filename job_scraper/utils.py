import re

def sanitize_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())

def text_contains_any(text, skills):
    text = text.lower()
    for s in skills:
        if s.lower() in text:
            return True
    return False
