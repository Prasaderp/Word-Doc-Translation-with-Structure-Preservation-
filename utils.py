# utils.py

import re
from typing import List

def is_translatable(text):
    if text is None or not text.strip():
        return False
    
    has_alpha = any(char.isalpha() for char in text)
    if not has_alpha:
        return False
        
    return True

try:
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    spacy = None
    _SPACY_AVAILABLE = False

_spacy_nlp = None

def _get_spacy_nlp():
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp
    if not _SPACY_AVAILABLE:
        return None
    try:
        _spacy_nlp = spacy.load("en_core_web_sm")
    except Exception:
        try:
            _spacy_nlp = spacy.load("xx_ent_wiki_sm")
        except Exception:
            _spacy_nlp = None
    return _spacy_nlp

def _get_spacy_entities(text: str) -> List[str]:
    nlp = _get_spacy_nlp()
    if nlp is None:
        return []

    structural_pattern = re.compile(r"(__MATH_OBJ_\d+__|__TAB__|__BR__|__CR__|__RUN_SEG_\d+__)")
    cleaned = structural_pattern.sub(" ", text)

    doc = nlp(cleaned)
    allowed = {"PERSON", "ORG", "GPE", "LOC"}
    entities: List[str] = []
    for ent in doc.ents:
        if ent.label_ in allowed:
            ent_text = ent.text.strip()
            if ent_text and len(ent_text) > 1:
                entities.append(ent_text)
    return entities

def get_protected_terms(text: str, user_terms: List[str] | None = None) -> List[str]:
    spacy_entities = _get_spacy_entities(text)
    
    filtered_user_terms = [term for term in (user_terms or []) if len(term) > 3]

    all_terms = spacy_entities + filtered_user_terms
    
    if not all_terms:
        return []

    unique_terms = sorted(list(set(t.strip() for t in all_terms if t.strip())), key=len, reverse=True)
    return unique_terms