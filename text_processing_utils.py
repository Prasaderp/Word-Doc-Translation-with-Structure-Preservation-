# text_processing_utils.py
import re
from config import MATH_LIKE_CHARS, COMMON_VAR_INTRO_WORDS
# translate_batch is imported locally in restore_entities to avoid circular dependency at module load time

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except ImportError:
    print("spaCy library or the en_core_web_sm model is not installed. Proper noun preservation will be disabled.")
    nlp = None
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'. Proper noun preservation will be disabled.")
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
        # print("No entities provided by user input.") # Less verbose for library function
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

    if unique_entities:
        print(f"User-defined entities to preserve: {', '.join(unique_entities)}")
    # else: # Avoid printing if no valid entities, can be confusing if called internally
        # print("No valid user-defined entities provided or parsed.")

    if invalid_entities:
        for entity, reason in invalid_entities:
            print(f"Invalid user-defined entity '{entity}': {reason}")

    return unique_entities

def extract_proper_nouns(text, user_entities):
    if not nlp:
        return [], []
    doc = nlp(text)
    proper_nouns = []
    multi_word_segments = [] # For storing (text, start_char, end_char) of multi-word proper nouns
    user_entity_set = set(e.lower() for e in user_entities)

    for ent in doc.ents:
        if ent.label_ in ("PERSON", "GPE", "ORG", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE", "NORP"):
            if any(char.isalpha() for char in ent.text):
                words = ent.text.split()
                is_user_entity_substring = False
                for user_ent_lower in user_entity_set:
                    if user_ent_lower in ent.text.lower():
                        is_user_entity_substring = True
                        break

                if not is_user_entity_substring:
                    if len(words) == 1 and words[0].isalpha() and len(words[0]) > 1:
                        proper_nouns.append(ent.text)
                    elif len(words) > 1:
                        all_words_alpha_or_mixed = True
                        for word in words:
                            if not (word.isalpha() or (any(c.isalpha() for c in word) and any(c.isnumeric() for c in word))):
                                all_words_alpha_or_mixed = False
                                break
                        if all_words_alpha_or_mixed:
                            multi_word_segments.append((ent.text, ent.start_char, ent.end_char))
                            proper_nouns.append(ent.text) # Also add multi-word to proper_nouns list for unified handling
                            
    # Remove duplicates while preserving order (based on first appearance, then sort by length)
    seen = set()
    unique_proper_nouns = []
    for pn in proper_nouns:
        if pn.lower() not in seen:
            seen.add(pn.lower())
            unique_proper_nouns.append(pn)
            
    return sorted(unique_proper_nouns, key=len, reverse=True), multi_word_segments

def generate_placeholder(index, is_multi_word=False, is_other=False, is_variable=False):
    if is_variable:
        return f"__VAR_{index:06d}__"
    if is_other:
        return f"__OTHER_{index:06d}__"
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
            is_already_placeholder = match.startswith("__") and match.endswith("__") and \
                                     any(pt in match for pt in ["_ENTITY_", "_MULTI_ENTITY_", "_VAR_", "_OTHER_"])

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
        (re.compile(r'\|'), "separators"),
        (re.compile(r'[–—-]'), "dashes"),
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
    combined_entities = sorted(list(set(combined_entities)), key=len, reverse=True)

    for ent in combined_entities:
        if not ent.strip(): continue
        is_substring = False
        for larger_ent in final_entities_to_preserve:
            if (" " + ent.lower() + " ") in (" " + larger_ent.lower() + " "):
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
            is_inside = current_segment.startswith("__") and current_segment.endswith("__")

            new_modified_text += modified_text[last_pos:start]
            if not is_inside:
                index += 1
                original_text_matched = match.group(0)
                placeholder = generate_placeholder(index, is_multi_word)
                placeholder_map[placeholder] = original_text_matched
                new_modified_text += placeholder
            else:
                new_modified_text += modified_text[start:end]
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

        if not is_protected and re.fullmatch(r'[a-zA-Z]\d+[a-zA-Z]*', word):
            index += 1
            placeholder = generate_placeholder(index, is_variable=True)
            placeholder_map[placeholder] = word
            result.append(placeholder)
            is_protected = True

        if not is_protected and re.fullmatch(r'\d+[a-zA-Z]+\d*', word):
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
                   re.fullmatch(r'[a-zA-Z]\d+[a-zA-Z]*', prev_word_stripped) or \
                   re.fullmatch(r'\d+[a-zA-Z]+\d*', prev_word_stripped) :
                    is_math_context = True

            if not is_math_context and next_word_stripped:
                if next_word_stripped.isnumeric() or \
                   next_word_stripped in MATH_LIKE_CHARS or \
                   (next_word_stripped.startswith("__VAR_") and next_word_stripped.endswith("__")) or \
                   re.fullmatch(r'[a-zA-Z]\d+[a-zA-Z]*', next_word_stripped) or \
                   re.fullmatch(r'\d+[a-zA-Z]+\d*', next_word_stripped) :
                    is_math_context = True

            if (not prev_word_stripped and next_word_stripped and \
                (next_word_stripped in MATH_LIKE_CHARS or next_word_stripped.isnumeric() or \
                 re.fullmatch(r'[a-zA-Z]\d+[a-zA-Z]*', next_word_stripped) or re.fullmatch(r'\d+[a-zA-Z]+\d*', next_word_stripped))) or \
               (not next_word_stripped and prev_word_stripped and \
                (prev_word_stripped in MATH_LIKE_CHARS or prev_word_stripped.isnumeric() or \
                 re.fullmatch(r'[a-zA-Z]\d+[a-zA-Z]*', prev_word_stripped) or re.fullmatch(r'\d+[a-zA-Z]+\d*', prev_word_stripped))):
                is_math_context = True

            if word in ['a', 'i', 'o', 's', 't', 'd'] :
                is_strongly_math_context = False
                if prev_word_stripped and next_word_stripped:
                    if (prev_word_stripped in MATH_LIKE_CHARS or prev_word_stripped.isnumeric() or (prev_word_stripped.startswith("__VAR_") and prev_word_stripped.endswith("__"))) and \
                       (next_word_stripped in MATH_LIKE_CHARS or next_word_stripped.isnumeric() or (next_word_stripped.startswith("__VAR_") and next_word_stripped.endswith("__"))):
                        is_strongly_math_context = True
                elif prev_word_stripped and (prev_word_stripped in MATH_LIKE_CHARS or prev_word_stripped.isnumeric() or (prev_word_stripped.startswith("__VAR_") and prev_word_stripped.endswith("__"))):
                    is_strongly_math_context = True
                elif next_word_stripped and (next_word_stripped in MATH_LIKE_CHARS or next_word_stripped.isnumeric() or (next_word_stripped.startswith("__VAR_") and next_word_stripped.endswith("__"))):
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
    cleaned = re.sub(r'__\w*?_\d{6}__', '', modified_text) # Match any placeholder type
    return bool(re.search(r'[a-zA-Z]', cleaned))

def fix_broken_placeholders(text):
    text = re.sub(r'__\s*EN\s*TITY_(\d{6})__', r'__ENTITY_\1__', text)
    text = re.sub(r'__\s*MULTI_ENTITY_(\d{6})__', r'__MULTI_ENTITY_\1__', text)
    text = re.sub(r'__\s*OTHER_(\d{6})__', r'__OTHER_\1__', text)
    text = re.sub(r'__\s*VAR_(\d{6})__', r'__VAR_\1__', text)
    text = re.sub(r'__(EN|MULTI_EN|O|VA)\n*(TITY|THER|R)_(\d{6})__', r'__\1\2_\3__', text)
    
    text = re.sub(r'(?<!_)ENTITY_(\d{6})__', r'__ENTITY_\1__', text)
    text = re.sub(r'__ENTITY_(\d{6})(?!_)', r'__ENTITY_\1__', text)

    text = re.sub(r'(?<!_)MULTI_ENTITY_(\d{6})__', r'__MULTI_ENTITY_\1__', text)
    text = re.sub(r'__MULTI_ENTITY_(\d{6})(?!_)', r'__MULTI_ENTITY_\1__', text)

    text = re.sub(r'(?<!_)VAR_(\d{6})__', r'__VAR_\1__', text)
    text = re.sub(r'__VAR_(\d{6})(?!_)', r'__VAR_\1__', text)

    text = re.sub(r'(?<!_)OTHER_(\d{6})__', r'__OTHER_\1__', text)
    text = re.sub(r'__OTHER_(\d{6})(?!_)', r'__OTHER_\1__', text)

    text = re.sub(r'(?<!_)_(ENTITY|MULTI_ENTITY|VAR|OTHER)_(\d{6})__', r'__\1_\2__', text)
    text = re.sub(r'__(ENTITY|MULTI_ENTITY|VAR|OTHER)_(\d{6})_(?!_)', r'__\1_\2__', text)
    
    text = re.sub(r'__\s*(ENTITY|MULTI_ENTITY|VAR|OTHER)\s*_\s*(\d{6})\s*__', r'__\1_\2__', text)
    return text

def restore_entities(translated_text, placeholder_map, original_text_segment_group, target_lang_full_name, multi_word_segments_spacy):
    from translation_service import translate_batch # Local import to break potential circular dependency
    text_after_fixing = fix_broken_placeholders(translated_text)

    restored_text_stage1 = text_after_fixing
    sorted_placeholders_keys = sorted(placeholder_map.keys(), key=lambda k: (len(k), k), reverse=True)

    for placeholder_key in sorted_placeholders_keys:
        original_value = placeholder_map[placeholder_key]
        restored_text_stage1 = re.sub(r'\b' + re.escape(placeholder_key) + r'\b', original_value, restored_text_stage1)

    restored_text_stage2 = restored_text_stage1 
    typo_pattern = re.compile(
        r'__\w*EN[ITTY]+(?:_TYPO)?_\d{6}__|'              # ENTITY typos
        r'\s*__\w*MULTI_?ENTITY(?:_TYPO)?_\d{6}__\s*|' # MULTI_ENTITY typos
        r'\s*__\w*VA[AR]+(?:_TYPO)?_\d{6}__\s*|'       # VAR typos
        r'\s*__\w*OT[HER]+(?:_TYPO)?_\d{6}__\s*'        # OTHER typos
    , re.VERBOSE)
    
    new_text_parts = []
    last_end = 0
    for match_obj in typo_pattern.finditer(restored_text_stage2):
        match_text = match_obj.group(0)
        start, end = match_obj.span()
        new_text_parts.append(restored_text_stage2[last_end:start])

        corrected_match_val = None
        num_part = re.search(r'\d{6}', match_text)
        if num_part:
            num_str = num_part.group(0)
            original_placeholder_if_corrected = None
            # Check for entity types
            if "EN" in match_text.upper() or "ITY" in match_text.upper():
                if f"__ENTITY_{num_str}__" in placeholder_map:
                    original_placeholder_if_corrected = f"__ENTITY_{num_str}__"
                elif f"__MULTI_ENTITY_{num_str}__" in placeholder_map:
                    original_placeholder_if_corrected = f"__MULTI_ENTITY_{num_str}__"
            # Check for variable types
            elif "VA" in match_text.upper() or "AR" in match_text.upper():
                if f"__VAR_{num_str}__" in placeholder_map:
                    original_placeholder_if_corrected = f"__VAR_{num_str}__"
            # Check for other types
            elif "OT" in match_text.upper() or "HER" in match_text.upper():
                if f"__OTHER_{num_str}__" in placeholder_map:
                    original_placeholder_if_corrected = f"__OTHER_{num_str}__"
            
            if original_placeholder_if_corrected and original_placeholder_if_corrected in placeholder_map:
                corrected_match_val = placeholder_map[original_placeholder_if_corrected]
        
        if corrected_match_val is not None:
            leading_space = " " if match_text.startswith(" ") and not corrected_match_val.startswith(" ") else ""
            trailing_space = " " if match_text.endswith(" ") and not corrected_match_val.endswith(" ") else ""
            new_text_parts.append(leading_space + corrected_match_val + trailing_space)
        else:
            new_text_parts.append(match_text) 
        last_end = end
    new_text_parts.append(restored_text_stage2[last_end:])
    restored_text_stage3 = "".join(new_text_parts)

    unresolved_patterns = [
        re.compile(r'__([A-Z_]+?)_\d{6}__'),
        re.compile(r'_(ENTITY|MULTI_ENTITY|VAR|OTHER)_\d{6}__'),
        re.compile(r'__(ENTITY|MULTI_ENTITY|VAR|OTHER)_\d{6}_(?!_)'),
        re.compile(r'\b(ENTITY|MULTI_ENTITY|VAR|OTHER)_\d{6}\b')
    ]

    is_still_corrupted = False
    for pattern in unresolved_patterns:
        if pattern.search(restored_text_stage3):
            is_still_corrupted = True
            break
    
    if is_still_corrupted:
        if original_text_segment_group:
            fallback_translation = translate_batch([original_text_segment_group], target_lang_full_name, fast_mode=True)
            if fallback_translation and fallback_translation[0].strip():
                return fallback_translation[0].strip()
            else: 
                return original_text_segment_group 
        else:
            return restored_text_stage3.strip()
            
    return restored_text_stage3.strip() 