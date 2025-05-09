# translation_service.py
import torch
import gc
import re
from config import LANGUAGES, MAX_LENGTH_DEFAULT, DEVICE
from model_utils import get_model_and_tokenizer

def get_dynamic_batch_size(num_texts, fast_mode=False):
    if DEVICE != "cuda":
        return min(8, num_texts) if num_texts > 0 else 1
    if num_texts == 0: return 1
    
    base_batch_size = 64 if fast_mode else 16
    return min(base_batch_size, num_texts)

def translate_batch(texts_to_translate, target_lang_full_name="Hindi", fast_mode=False):
    if not texts_to_translate:
        return []

    actual_texts_to_translate = [t for t in texts_to_translate if t and t.strip()]
    if not actual_texts_to_translate:
        return [""] * len(texts_to_translate)

    non_empty_indices = [i for i, t in enumerate(texts_to_translate) if t and t.strip()]

    tokenizer, model = get_model_and_tokenizer()

    batch_size = get_dynamic_batch_size(len(actual_texts_to_translate), fast_mode)
    translated_snippets = []

    if target_lang_full_name not in LANGUAGES:
        print(f"Warning: Target language '{target_lang_full_name}' not in config. Defaulting to Hindi.")
        target_lang_full_name = "Hindi"
    target_lang_code = LANGUAGES[target_lang_full_name]["code"]

    for i in range(0, len(actual_texts_to_translate), batch_size):
        batch = actual_texts_to_translate[i:i + batch_size]
        
        est_max_tokens_in_batch = 0
        if batch:
            est_max_tokens_in_batch = max(len(t.split()) for t in batch)
        
        current_max_length = min(max(MAX_LENGTH_DEFAULT, est_max_tokens_in_batch * 2 + 20), 1024)

        try:
            inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=current_max_length).to(DEVICE)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_lang_code),
                    max_length=current_max_length,
                    num_beams=3,
                    early_stopping=True,
                    use_cache=True
                )
            translated_batch_snippets = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
            translated_snippets.extend([re.sub(r'^\.+|\s*\.+$|^\s*…|…\s*$', '', t.strip()) for t in translated_batch_snippets])

            del inputs, outputs
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        except RuntimeError as e:
            print(f"RuntimeError during batch translation: {e}. Batch size: {len(batch)}. Attempting individual fallback.")
            if len(batch) > 1:
                individual_translations = []
                for item_in_batch in batch:
                    try:
                        individual_translations.extend(translate_batch([item_in_batch], target_lang_full_name, fast_mode=True))
                    except Exception as single_e:
                        print(f"Error translating single item '{item_in_batch[:50]}...': {single_e}. Using original.")
                        individual_translations.append(item_in_batch)
                translated_snippets.extend(individual_translations)
            else:
                print(f"Single item batch failed for '{batch[0][:50]}...'. Using original.")
                translated_snippets.extend(batch)
    
    final_translated_texts = [""] * len(texts_to_translate)
    for i, original_idx in enumerate(non_empty_indices):
        if i < len(translated_snippets):
            final_translated_texts[original_idx] = translated_snippets[i]
        
    return final_translated_texts 