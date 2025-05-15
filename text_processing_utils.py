import re
import spacy
from config import MATH_LIKE_CHARS, COMMON_VAR_INTRO_WORDS

nlp = None
try:
    nlp = spacy.load("en_core_web_sm")
except ImportError:
    nlp = None
except OSError:
    try:
        spacy.cli.download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = None

def is_math_variable(token, previous_token_str, next_token_str):
    if not (len(token) == 1 and token.isalpha() and token.isupper()):
        return False
    if token == "A":
        if next_token_str and next_token_str.isalpha():
            is_next_var_like = (len(next_token_str) == 1 and next_token_str.isupper()) or \
                               re.fullmatch(r'[a-zA-Z]\d+', next_token_str) or \
                               next_token_str in MATH_LIKE_CHARS
            if not is_next_var_like:
                if len(next_token_str) > 1 :
                    return False
    if previous_token_str:
        if previous_token_str.endswith('.'):
            pass
        elif previous_token_str.isalpha():
            if previous_token_str.lower() not in COMMON_VAR_INTRO_WORDS:
                return False
    if next_token_str:
        if next_token_str.isalpha():
            if not (next_token_str[0].isupper() or next_token_str[0].isdigit()):
                if token != "I":
                    if not (next_token_str in MATH_LIKE_CHARS or \
                            (len(next_token_str) <=2 and next_token_str.isalnum() and not next_token_str.isdigit())):
                        return False
    if previous_token_str and previous_token_str in ["The", "A", "An"]:
        return True
    return True

def parse_user_entities(user_input):
    if not user_input or user_input.isspace():
        return []
    entities = []
    invalid_entities = []
    for e in user_input.split(','):
        e = e.strip()
        if not e:
            continue
        words = e.split()
        if not words:
            invalid_entities.append((e, "Entity cannot be empty"))
        elif not all(word.isalpha() and len(word) >= 3 for word in words):
            invalid_entities.append((e, "Each word must contain only alphabetic characters and have at least 3 letters"))
        else:
            entities.append(e)
    unique_entities = []
    seen_lowercase = set()
    for e in entities:
        e_lower = e.lower()
        if e_lower not in seen_lowercase:
            seen_lowercase.add(e_lower)
            unique_entities.append(e)
    unique_entities = sorted(unique_entities, key=len, reverse=True)
    return unique_entities

def extract_proper_nouns(text, user_entities):
    if not nlp:
        return [], []
    doc = nlp(text)
    proper_nouns = []
    multi_word_segments = []
    user_entity_set = set(e.lower() for e in user_entities)
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "GPE", "ORG"):
            if any(char.isalpha() for char in ent.text):
                words = ent.text.split()
                is_user_entity = False
                for user_ent in user_entity_set:
                    if user_ent in ent.text.lower():
                        is_user_entity = True
                        break
                if not is_user_entity:
                    if len(words) == 1 and words[0].isalpha() and len(words[0]) > 1 :
                        proper_nouns.append(ent.text)
                    elif len(words) > 1:
                        all_words_alpha_or_mixed = True
                        for word in words:
                            if not (word.isalpha() or (any(c.isalpha() for c in word) and any(c.isnumeric() for c in word))):
                                all_words_alpha_or_mixed = False
                                break
                        if all_words_alpha_or_mixed:
                            multi_word_segments.append((ent.text, ent.start_char, ent.end_char))
    final_proper_nouns = sorted(list(set(proper_nouns)), key=len, reverse=True)
    return final_proper_nouns, multi_word_segments

def generate_placeholder(index, is_multi_word=False, is_other=False, is_variable=False):
    if is_variable:
        return f"__VAR_{index:06d}__"
    if is_other:
        return f"__OTHx_{index:06d}__"
    return f"__{'MULTI_ENTITY' if is_multi_word else 'ENTITY'}_{index:06d}__"

def replace_with_placeholders(text, entities=[]):
    placeholder_map = {}
    modified_text = text
    index = 0
    proper_nouns, multi_word_segments_spacy = extract_proper_nouns(text, entities)
    fraction_pattern = re.compile(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+/[₀₁₂₃₄₅₆₇₈₉]+')
    matches = fraction_pattern.findall(modified_text)
    for match in matches:
        index += 1
        placeholder = generate_placeholder(index, is_other=True)
        placeholder_map[placeholder] = match
        modified_text = modified_text.replace(match, placeholder, 1)
    unicode_super_sub_chars = "⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉"
    math_pattern = re.compile(r'\b\S*[' + unicode_super_sub_chars + r']\S*\b|\b['+ unicode_super_sub_chars + r']+\b')
    if any(c in unicode_super_sub_chars for c in modified_text):
        new_modified_text_after_math = ""
        last_pos_math = 0
        for match_obj in math_pattern.finditer(modified_text):
            match = match_obj.group(0)
            start, end = match_obj.span()
            new_modified_text_after_math += modified_text[last_pos_math:start]
            is_already_placeholder = match.startswith("__") and match.endswith("__") and ("_ENTITY_" in match or "_MULTI_ENTITY_" in match or "_VAR_" in match or "_OTHER_" in match or "_OTHx_" in match)
            if not is_already_placeholder:
                index += 1
                placeholder = generate_placeholder(index, is_other=True)
                placeholder_map[placeholder] = match
                new_modified_text_after_math += placeholder
            else:
                new_modified_text_after_math += match
            last_pos_math = end
        new_modified_text_after_math += modified_text[last_pos_math:]
        modified_text = new_modified_text_after_math
    patterns = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "emails"),
        (re.compile(r'https?://\S+|www\.\S+|github\.com/\S+|linkedin\.com/\S+'), "URLs"),
        (re.compile(r'\+?\d{2,4}[-\s]?\d{6,}'), "phone_numbers"),
        (re.compile(r'CGPA:\s*\d+\.\d+'), "CGPA"),
        (re.compile(r'\b\d{4}\s*–\s*\d{2,4}\b|\b\d{4}-\d{2,4}\b'), "year_ranges"),
        (re.compile(r'\b[A-Z]\.(?!\.)(?=\s|\w|$)'), "uppercase_letter_marker"),
        (re.compile(r'(?<![-–])[-–](?![-–])'), "isolated_dashes"),
    ]
    for pattern, category in patterns:
        new_modified_text_loop = ""
        last_match_end = 0
        for match_obj in pattern.finditer(modified_text):
            match_start, match_end = match_obj.span()
            match = match_obj.group(0)
            new_modified_text_loop += modified_text[last_match_end:match_start]
            index += 1
            placeholder = generate_placeholder(index, is_other=True)
            placeholder_map[placeholder] = match
            new_modified_text_loop += placeholder
            last_match_end = match_end
        new_modified_text_loop += modified_text[last_match_end:]
        modified_text = new_modified_text_loop
    combined_entities = entities + proper_nouns
    final_entities_to_preserve = []
    combined_entities = sorted(list(set(e for e in combined_entities if e and e.strip())), key=len, reverse=True)

    for ent in combined_entities:
        if not ent.strip(): continue
        is_substring = False
        for larger_ent in final_entities_to_preserve:
            if (" " + ent.lower() + " ") in (" " + larger_ent.lower() + " ") or ent.lower() == larger_ent.lower():
                if ent.lower() != larger_ent.lower():
                    is_substring = True
                    break
        if not is_substring:
            final_entities_to_preserve.append(ent)
    for entity in final_entities_to_preserve:
        if not entity.strip(): continue
        is_multi_word = len(entity.split()) > 1
        try:
            pattern = re.compile(r'\b' + re.escape(entity) + r'\b', re.IGNORECASE)
        except re.error:
            continue
        new_modified_text = ""
        last_pos = 0
        for match in pattern.finditer(modified_text):
            start, end = match.span()
            current_segment = modified_text[start:end]
            is_inside_existing_placeholder = bool(re.search(r'__(ENTITY|MULTI_ENTITY|VAR|OTHx)_\d{6}__', modified_text[max(0, start-2):min(len(modified_text), end+2)])) and \
                                         current_segment not in placeholder_map.values()
            new_modified_text += modified_text[last_pos:start]
            if not is_inside_existing_placeholder and not (current_segment.startswith("__") and current_segment.endswith("__")):
                index += 1
                original_text_matched = match.group(0)
                placeholder = generate_placeholder(index, is_multi_word)
                placeholder_map[placeholder] = original_text_matched
                new_modified_text += placeholder
            else:
                new_modified_text += current_segment
            last_pos = end
        new_modified_text += modified_text[last_pos:]
        modified_text = new_modified_text
    words = re.findall(r'\S+|\s+', modified_text)
    result = []
    i = 0
    common_lowercase_vars = {'x', 'y', 'z', 'a', 'b', 'c', 'n', 'm', 'k', 't', 'p', 'v', 'f', 's', 'g', 'h', 'e', 'i', 'j', 'l', 'o', 'q', 'r', 'u', 'w', 'd'}
    while i < len(words):
        word = words[i]
        if (word.startswith("__") and word.endswith("__")) or word.isspace():
            result.append(word)
            i += 1
            continue
        prev_word_stripped = words[i-1].strip() if i > 0 and words[i-1].strip() else ""
        next_word_stripped = words[i+1].strip() if i+1 < len(words) and words[i+1].strip() else ""
        is_protected = False
        if len(word) == 1 and word.isalpha() and word.isupper():
            if is_math_variable(word, prev_word_stripped, next_word_stripped):
                index += 1
                placeholder = generate_placeholder(index, is_variable=True)
                placeholder_map[placeholder] = word
                result.append(placeholder)
                is_protected = True
        if not is_protected and re.fullmatch(r'[a-zA-Z]\d+', word):
            index += 1
            placeholder = generate_placeholder(index, is_variable=True)
            placeholder_map[placeholder] = word
            result.append(placeholder)
            is_protected = True
        if not is_protected and re.fullmatch(r'\d+[a-zA-Z]\d*', word):
            index += 1
            placeholder = generate_placeholder(index, is_variable=True)
            placeholder_map[placeholder] = word
            result.append(placeholder)
            is_protected = True
        if not is_protected and word in common_lowercase_vars:
            is_math_context = False
            if prev_word_stripped:
                if prev_word_stripped.isnumeric() or \
                   prev_word_stripped in MATH_LIKE_CHARS or \
                   (prev_word_stripped.startswith("__VAR_") and prev_word_stripped.endswith("__")) or \
                   re.fullmatch(r'[a-zA-Z]\d+', prev_word_stripped) or \
                   re.fullmatch(r'\d+[a-zA-Z]\d*', prev_word_stripped) :
                    is_math_context = True
            if not is_math_context and next_word_stripped:
                if next_word_stripped.isnumeric() or \
                   next_word_stripped in MATH_LIKE_CHARS or \
                   (next_word_stripped.startswith("__VAR_") and next_word_stripped.endswith("__")) or \
                   re.fullmatch(r'[a-zA-Z]\d+', next_word_stripped) or \
                   re.fullmatch(r'\d+[a-zA-Z]\d*', next_word_stripped) :
                    is_math_context = True
            if (not prev_word_stripped and next_word_stripped and \
                (next_word_stripped in MATH_LIKE_CHARS or next_word_stripped.isnumeric() or \
                 re.fullmatch(r'[a-zA-Z]\d*', next_word_stripped) or re.fullmatch(r'\d+[a-zA-Z]\d*', next_word_stripped))) or \
               (not next_word_stripped and prev_word_stripped and \
                (prev_word_stripped in MATH_LIKE_CHARS or prev_word_stripped.isnumeric() or \
                 re.fullmatch(r'[a-zA-Z]\d*', prev_word_stripped) or re.fullmatch(r'\d+[a-zA-Z]\d*', prev_word_stripped))):
                is_math_context = True
            if word in ['a', 'i', 'o', 's', 't', 'd'] :
                is_strongly_math_context = False
                if prev_word_stripped and next_word_stripped:
                    if (prev_word_stripped in MATH_LIKE_CHARS or prev_word_stripped.isnumeric() or (prev_word_stripped.startswith("__VAR_") and prev_word_stripped.endswith("__"))) and \
                       (next_word_stripped in MATH_LIKE_CHARS or next_word_stripped.isnumeric() or (next_word_stripped.startswith("__VAR_") and next_word_stripped.endswith("__"))):
                        is_strongly_math_context = True
                if not is_strongly_math_context:
                    is_math_context = False
            if is_math_context:
                index += 1
                placeholder = generate_placeholder(index, is_variable=True)
                placeholder_map[placeholder] = word
                result.append(placeholder)
                is_protected = True
        if not is_protected:
            result.append(word)
        i += 1
    modified_text = ''.join(result)
    return modified_text, placeholder_map, multi_word_segments_spacy

def needs_translation(modified_text):
    cleaned = re.sub(r'__(?:ENTITY|MULTI_ENTITY|VAR|OTHx)_\d{6}__', '', modified_text)
    return bool(re.search(r'[a-zA-Z]', cleaned))

def fix_broken_placeholders(text):
    original_text = text
    placeholder_types = {
        "ENTITY": "ENTITY",
        "MULTI_ENTITY": "MULTI_ENTITY",
        "VAR": "VAR",
        "OTHx": "OTHx"
    }
    for _ in range(2):
        for key_prefix, actual_prefix in placeholder_types.items():
            text = re.sub(rf'(_\s*_)\s*({actual_prefix})\s*(_)\s*(\d{{6}})\s*(_\s*_)', rf'__\2_\4__', text)
            text = re.sub(rf'__\s*({actual_prefix})\s*_\s*(\d{{6}})\s*__', rf'__\1_\2__', text)
            text = re.sub(rf'__\s*({actual_prefix})\s+(\d{{6}})\s*__', rf'__\1_\2__', text)
            text = re.sub(rf'__\s*({actual_prefix}_\d{{6}})\s*__', rf'__\1__', text)
            text = re.sub(rf'(?<!_)_\s*({actual_prefix}_\d{{6}})\s*__', rf'__\1__', text)
            text = re.sub(rf'__\s*({actual_prefix}_\d{{6}})\s*_(?!_)', rf'__\1__', text)
            text = re.sub(rf'\b({actual_prefix}_\d{{6}})\s*__', rf'__\1__', text)
            text = re.sub(rf'__\s*({actual_prefix}_\d{{6}})\b', rf'__\1__', text)
            if actual_prefix == "ENTITY":
                text = re.sub(r'__\s*EN\s*TITY\s*_\s*(\d{6})\s*__', r'__ENTITY_\1__', text)
            elif actual_prefix == "MULTI_ENTITY":
                text = re.sub(r'__\s*MULTI\s*[_ ]?\s*ENTITY\s*_\s*(\d{6})\s*__', r'__MULTI_ENTITY_\1__', text)
        text = re.sub(r'__\s*(EN)\s*\n?\s*(TITY)\s*_\s*(\d{6})\s*__', r'__ENTITY_\3__', text)
        text = re.sub(r'__\s*(MULTI)\s*[_ ]?\s*(EN)\s*\n?\s*(TITY)\s*_\s*(\d{6})\s*__', r'__MULTI_ENTITY_\4__', text)
        text = re.sub(r'__\s*(O)\s*\n?\s*(THx)\s*_\s*(\d{6})\s*__', r'__OTHx_\3__', text)
        text = re.sub(r'__\s*(VA)\s*\n?\s*(R)\s*_\s*(\d{6})\s*__', r'__VAR_\3__', text)
    for _, actual_prefix in placeholder_types.items():
        text = re.sub(rf'__\s+({actual_prefix}_\d{{6}})\s+__', rf'__\1__', text)
        text = re.sub(rf'__\s+({actual_prefix}_\d{{6}})\s*__', rf'__\1__', text)
        text = re.sub(rf'__\s*({actual_prefix}_\d{{6}})\s+__', rf'__\1__', text)
        text = re.sub(rf'__\s*({actual_prefix})\s*_\s*(\d{{6}})\s*__', rf'__\1_\2__', text)
    return text

def restore_entities(translated_text, placeholder_map, original_text_segment_group, target_lang, multi_word_segments_spacy):
    from translation_service import translate_batch
    text_after_fixing = fix_broken_placeholders(translated_text)
    restored_text_stage2 = text_after_fixing
    sorted_placeholders_keys = sorted(placeholder_map.keys(), key=len, reverse=True)
    for placeholder_key in sorted_placeholders_keys:
        original_value = placeholder_map[placeholder_key]
        restored_text_stage2 = re.sub(r'\b' + re.escape(placeholder_key) + r'\b', original_value, restored_text_stage2)
    restored_text_stage3 = restored_text_stage2
    typo_pattern = re.compile(r"__\s*[^_]*?\s*_\s*(\d{6})\s*__")
    new_text_parts = []
    last_end = 0
    for match_obj in typo_pattern.finditer(restored_text_stage3):
        match_text = match_obj.group(0)
        start, end = match_obj.span()
        new_text_parts.append(restored_text_stage3[last_end:start])
        num_str = match_obj.group(1)
        corrected_match_val = None
        if num_str:
            possible_original_placeholders = [
                f"__ENTITY_{num_str}__", f"__MULTI_ENTITY_{num_str}__",
                f"__VAR_{num_str}__", f"__OTHx_{num_str}__"
            ]
            found_original_key = None
            for p_key in possible_original_placeholders:
                if p_key in placeholder_map:
                    found_original_key = p_key
                    break
            if found_original_key:
                corrected_match_val = placeholder_map[found_original_key]
        if corrected_match_val is not None:
            leading_space = " " if match_text.startswith(" ") and not corrected_match_val.startswith(" ") else ""
            trailing_space = " " if match_text.endswith(" ") and not corrected_match_val.endswith(" ") else ""
            new_text_parts.append(leading_space + corrected_match_val + trailing_space)
        else:
            new_text_parts.append(match_text)
        last_end = end
    new_text_parts.append(restored_text_stage3[last_end:])
    restored_text_stage3 = "".join(new_text_parts)
    unresolved_patterns = [
        re.compile(r'__([A-Z_]+?)_\d{6}__'),
        re.compile(r'_(ENTITY|MULTI_ENTITY|VAR|OTHx)_\d{6}__'),
        re.compile(r'__(ENTITY|MULTI_ENTITY|VAR|OTHx)_\d{6}_(?!_)'),
        re.compile(r'\b(ENTITY|MULTI_ENTITY|VAR|OTHx)_\d{6}\b')
    ]
    is_still_corrupted = False
    for pattern in unresolved_patterns:
        if pattern.search(restored_text_stage3):
            is_still_corrupted = True
            break
    if is_still_corrupted:
        if original_text_segment_group:
            fallback_translation = translate_batch([original_text_segment_group], target_lang, fast_mode=True)
            if fallback_translation:
                return fallback_translation[0].strip()
            else:
                return original_text_segment_group
        else:
            return restored_text_stage3.strip()
    return restored_text_stage3.strip()