# translation_handler.py

import threading
from openai import OpenAI
import utils

thread_local = threading.local()

def get_openai_client(api_key):
    if not hasattr(thread_local, "client"):
        thread_local.client = OpenAI(api_key=api_key)
    return thread_local.client

def translate_text(text, target_lang, api_key, user_terms):
    client = get_openai_client(api_key)
    try:
        protected_terms = utils.get_protected_terms(text, user_terms or [])

        prompt = f"You are a professional document translator. Translate the following text to natural, fluent {target_lang}."

        instructions = [
            "Preserve all placeholders like `__MATH_OBJ_n__`, `__RUN_SEG_n__`, `__TAB__`, etc., exactly as they appear in the source text.",
            "Translate only the natural language surrounding these placeholders and any protected terms.",
            "Output only the final, translated text with all placeholders and protected terms perfectly intact."
        ]
        
        if protected_terms:
            terms_list_str = ", ".join(f'"{term}"' for term in protected_terms)
            protection_instruction = f"CRITICAL: Do not translate the following proper nouns, brand names, or specific terms. Keep them in their original form: {terms_list_str}."
            instructions.insert(0, protection_instruction)

        prompt += "\n\n**TRANSLATION RULES:**\n" + "\n".join(f"{i+1}. {inst}" for i, inst in enumerate(instructions))
        
        message = [{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=message,
            temperature=0.1,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        
        if not content or not content.strip():
            print("\n[WARNING] Model returned an empty response; reverting to source for this segment.")
            return text
        
        return content.strip()
        
    except Exception as e:
        print(f"\n[WARNING] API call failed for text segment: '{text[:30]}...'. Error: {e}. Using original text.")
        return text

def translate_segment(text, language, cache, api_key, user_terms, counter, lock, total, progress_callback=None):
    translated_text = translate_text(text, language, api_key, user_terms)
    cache[text] = translated_text
    
    with lock:
        counter[0] += 1
        progress = (counter[0] / total) * 100
        print(f"\rTranslation progress: {counter[0]}/{total} ({progress:.1f}%)", end="", flush=True)
        if progress_callback is not None:
            try:
                progress_callback(progress)
            except Exception:
                pass