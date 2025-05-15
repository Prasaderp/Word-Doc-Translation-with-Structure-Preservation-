import os
import re
import time
from docx import Document
from model_utils import check_memory_and_reset, get_model_and_tokenizer
from text_processing_utils import restore_entities
from docx_processing_utils import collect_texts_and_images, apply_formatting, split_text_by_proportions
from translation_service import translate_batch

def process_document(input_path, output_path, entities, target_lang="Hindi"):
    doc = Document(input_path)
    
    collected_items = collect_texts_and_images(doc, entities)
    
    if not collected_items:
        doc.save(output_path)
        return

    texts_to_translate_full = []
    metadata_for_translation = []
    for item_idx, item_content in enumerate(collected_items):
        item_type, original_item_id_str, para_obj, original_text_group, modified_text_group_for_model, \
        placeholder_map_group, needs_trans_flag, multi_word_segs_group, text_runs_list, fmt_info_list = item_content
        unique_group_id = f"group_{item_idx}_{original_item_id_str}"
        if item_type == "omath_object" or item_type == "preserved_drawing":
            metadata_for_translation.append(
                (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                 placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                 False, 0, 1)
            )
            continue
        if needs_trans_flag:
            sentences_for_model = [s for s in re.split(r'(?<=[.!?])\s+', modified_text_group_for_model.strip()) if s]
            if not sentences_for_model:
                if modified_text_group_for_model.strip():
                    sentences_for_model = [modified_text_group_for_model]
                else:
                    metadata_for_translation.append(
                        (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                         placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                         False, 0, 1)
                    )
                    continue
            if sentences_for_model:
                for sentence_idx, sentence_text in enumerate(sentences_for_model):
                    texts_to_translate_full.append(sentence_text)
                    metadata_for_translation.append(
                        (item_type, unique_group_id, para_obj, original_text_group, sentence_text,
                         placeholder_map_group, True, multi_word_segs_group, text_runs_list, fmt_info_list,
                         True, sentence_idx, len(sentences_for_model))
                    )
        else:
            metadata_for_translation.append(
                (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                 placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                 False, 0, 1)
            )

    translated_text_snippets = []
    if texts_to_translate_full :
        if check_memory_and_reset(len(texts_to_translate_full)):
            pass
        fast_translation_mode = len(texts_to_translate_full) <= 50 
        translated_text_snippets = translate_batch(texts_to_translate_full, target_lang, fast_mode=fast_translation_mode)
    elif not any(m[6] for m in metadata_for_translation if len(m) > 10 and m[0] not in ["omath_object", "preserved_drawing"]):
        pass

    translation_idx = 0
    accumulated_translated_sentences = {}
    for meta_item_full in metadata_for_translation:
        item_type, unique_group_id, para_obj, original_text_group, modified_text_segment, \
        placeholder_map_group, needs_trans_flag_from_meta, multi_word_segs_group, text_runs_list, fmt_info_list, \
        is_sentence_split, sentence_idx, total_sentences = meta_item_full
        if item_type == "omath_object" or item_type == "preserved_drawing":
            continue 
        final_text_for_group_assembly = None
        full_placeholder_text_for_group = ""
        if is_sentence_split:
            # Efficiently find the original full placeholder text
            # This assumes collected_items is accessible or its relevant part is passed/reconstructed
            # For simplicity, we search based on unique_group_id structure if item_idx is part of it
            original_item_idx_from_id = -1
            try:
                original_item_idx_from_id = int(unique_group_id.split('_')[1]) # group_ITEMIDX_...
            except (IndexError, ValueError):
                 pass # Could not parse item_idx

            if original_item_idx_from_id != -1 and original_item_idx_from_id < len(collected_items):
                 full_placeholder_text_for_group = collected_items[original_item_idx_from_id][4] # modified_text_group_for_model
            else: # Fallback or if ID structure changed
                full_placeholder_text_for_group = modified_text_segment # This is only the segment, not the whole group
                # This part might need adjustment if full_placeholder_text_for_group is critical and not found
        else:
            full_placeholder_text_for_group = modified_text_segment

        if not needs_trans_flag_from_meta:
            final_text_for_group_assembly = restore_entities(modified_text_segment, placeholder_map_group, original_text_group, target_lang, multi_word_segs_group)
        elif is_sentence_split:
            current_translated_sentence = ""
            if translation_idx < len(translated_text_snippets):
                current_translated_sentence = translated_text_snippets[translation_idx]
                translation_idx += 1
            else:
                current_translated_sentence = modified_text_segment
            if unique_group_id not in accumulated_translated_sentences:
                accumulated_translated_sentences[unique_group_id] = [""] * total_sentences
            accumulated_translated_sentences[unique_group_id][sentence_idx] = current_translated_sentence
            if sentence_idx == total_sentences - 1:
                if unique_group_id in accumulated_translated_sentences and \
                   all(isinstance(s, str) for s in accumulated_translated_sentences[unique_group_id]):
                    full_translated_text_intermediate = " ".join(accumulated_translated_sentences[unique_group_id])
                    final_text_for_group_assembly = restore_entities(full_translated_text_intermediate, placeholder_map_group, original_text_group, target_lang, multi_word_segs_group)
                    del accumulated_translated_sentences[unique_group_id]
                else:
                    final_text_for_group_assembly = restore_entities(full_placeholder_text_for_group, placeholder_map_group, original_text_group, target_lang, multi_word_segs_group)
                    if unique_group_id in accumulated_translated_sentences: del accumulated_translated_sentences[unique_group_id]
        else: 
            if translation_idx < len(translated_text_snippets):
                translated_segment = translated_text_snippets[translation_idx]
                final_text_for_group_assembly = restore_entities(translated_segment, placeholder_map_group, original_text_group, target_lang, multi_word_segs_group)
                translation_idx += 1
            else:
                final_text_for_group_assembly = restore_entities(modified_text_segment, placeholder_map_group, original_text_group, target_lang, multi_word_segs_group)
        
        if final_text_for_group_assembly is not None and item_type not in ["omath_object", "preserved_drawing"]:
            if text_runs_list: # Ensure text_runs_list is not empty
                parts = split_text_by_proportions(final_text_for_group_assembly, text_runs_list, original_text_group, placeholder_map_group)
                apply_formatting(text_runs_list, parts, fmt_info_list)
    
    doc.save(output_path)