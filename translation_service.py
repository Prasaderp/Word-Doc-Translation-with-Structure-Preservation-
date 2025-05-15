import torch
import gc
import re
from config import LANGUAGES, MAX_LENGTH_DEFAULT, DEVICE
from model_utils import get_model_and_tokenizer, initialize_model
import time

def get_dynamic_batch_size(num_texts, fast_mode=False):
    if DEVICE != "cuda":
        bs = min(8, num_texts) if num_texts > 0 else 1
        return bs
    if num_texts == 0: return 1
    base_batch_size = 64 if fast_mode else 16
    bs = min(base_batch_size, num_texts)
    return bs

def translate_batch(texts_to_translate, target_lang="Hindi", fast_mode=False):
    if not texts_to_translate:
        return []
    actual_texts_to_translate = [t for t in texts_to_translate if t and t.strip()]
    if not actual_texts_to_translate:
        return [""] * len(texts_to_translate)
    
    tokenizer, model = get_model_and_tokenizer()
    if tokenizer is None or model is None: # Should not happen if get_model_and_tokenizer works
        tokenizer, model = initialize_model()


    non_empty_indices = [i for i, t in enumerate(texts_to_translate) if t and t.strip()]
    batch_size = get_dynamic_batch_size(len(actual_texts_to_translate), fast_mode)
    translated_snippets = []
    target_lang_code = LANGUAGES[target_lang]["code"]
    
    num_batches = (len(actual_texts_to_translate) + batch_size - 1) // batch_size
    total_translation_time_model = 0

    for i in range(0, len(actual_texts_to_translate), batch_size):
        batch_start_time = time.time()
        batch = actual_texts_to_translate[i:i + batch_size]
        est_max_tokens_in_batch = 0
        if batch:
            est_max_tokens_in_batch = max(len(t.split()) for t in batch)
        current_max_length = min(max(MAX_LENGTH_DEFAULT, int(est_max_tokens_in_batch * 2.5) + 20), 1024)
        try:
            inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=current_max_length).to(DEVICE)
            gen_start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_lang_code),
                    max_length=current_max_length,
                    num_beams=3 if not fast_mode else 1,
                    early_stopping=True,
                    use_cache=True
                )
            gen_time = time.time() - gen_start_time
            total_translation_time_model += gen_time
            translated_batch_snippets = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
            translated_snippets.extend([re.sub(r'^\.+|\s*\.+$|^\s*…|…\s*$', '', t.strip()) for t in translated_batch_snippets])
            del inputs, outputs
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
        except RuntimeError as e:
            if DEVICE == "cuda": torch.cuda.empty_cache()
            gc.collect()
            if batch_size > 1 and len(batch) > 1 : # ensure len(batch) for single item retry logic
                individual_translations = []
                for item_in_batch in batch:
                    try:
                        individual_translations.extend(translate_batch([item_in_batch], target_lang, fast_mode=True))
                    except Exception as single_e:
                        individual_translations.append(item_in_batch)
                translated_snippets.extend(individual_translations)
            elif batch: # if batch_size was 1 or became 1
                translated_snippets.extend(batch)
            else: # Should not happen if actual_texts_to_translate is not empty
                pass

    final_translated_texts = [""] * len(texts_to_translate)
    for i, original_idx in enumerate(non_empty_indices):
        if i < len(translated_snippets):
            final_translated_texts[original_idx] = translated_snippets[i]
    return final_translated_texts