# main.py
import os
import re
import time
import tempfile
import traceback

from docx import Document
from docx.shared import Inches

import config
from model_utils import check_memory_and_reset, get_model_and_tokenizer
from text_processing_utils import parse_user_entities, restore_entities
from docx_processing_utils import collect_texts_and_images, apply_formatting, split_text_by_proportions
from file_utils import convert_doc_to_docx
from translation_service import translate_batch

def process_document(input_path, output_path, entities_to_preserve_list, target_lang_full_name="Hindi"):
    get_model_and_tokenizer()
    
    doc = Document(input_path)

    with tempfile.TemporaryDirectory() as temp_img_dir_for_collection:
        collected_items, remaining_doc_images, _image_positions_map = \
            collect_texts_and_images(doc, temp_img_dir_for_collection, entities_to_preserve_list, input_path)

        if not collected_items:
            doc.save(output_path)
            print("No text content or images found/processed in the document.")
            return

        texts_to_translate_for_model_batch = []
        metadata_for_translation_assembly = []

        for item_idx, item_content in enumerate(collected_items):
            item_type, original_item_id_str, para_obj, original_text_group, \
            modified_text_group_for_model, placeholder_map_group, needs_trans_flag, \
            multi_word_segs_group, text_runs_list, fmt_info_list = item_content
            
            unique_group_id = f"group_{item_idx}_{original_item_id_str}"

            if item_type == "image" or item_type == "omath_object" or item_type == "drawing_element":
                metadata_for_translation_assembly.append(
                    (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                     placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                     False, 0, 1)
                )
                continue

            if needs_trans_flag:
                sentences_for_model = [s.strip() for s in re.split(r'(?<=[.!?])\s+', modified_text_group_for_model.strip()) if s.strip()]

                if not sentences_for_model:
                    if modified_text_group_for_model.strip():
                        sentences_for_model = [modified_text_group_for_model]
                    else:
                         metadata_for_translation_assembly.append(
                            (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                             placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                             False, 0, 1)
                        )
                         continue
                
                if sentences_for_model:
                    for sentence_idx, sentence_text in enumerate(sentences_for_model):
                        texts_to_translate_for_model_batch.append(sentence_text)
                        metadata_for_translation_assembly.append(
                            (item_type, unique_group_id, para_obj, original_text_group, sentence_text, 
                             placeholder_map_group, True, multi_word_segs_group, text_runs_list, fmt_info_list,
                             True, sentence_idx, len(sentences_for_model))
                        )
            else: 
                metadata_for_translation_assembly.append(
                    (item_type, unique_group_id, para_obj, original_text_group, modified_text_group_for_model,
                     placeholder_map_group, False, multi_word_segs_group, text_runs_list, fmt_info_list,
                     False, 0, 1)
                )
        
        translated_text_snippets_from_batch = []
        if texts_to_translate_for_model_batch :
            if check_memory_and_reset(len(texts_to_translate_for_model_batch)):
                print("GPU memory reset and model re-initialized.")
            
            fast_translation_mode = len(texts_to_translate_for_model_batch) <= 50
            
            translated_text_snippets_from_batch = translate_batch(
                texts_to_translate_for_model_batch, 
                target_lang_full_name, 
                fast_mode=fast_translation_mode
            )
        elif not any(m[6] for m in metadata_for_translation_assembly if len(m) > 10 and m[0] not in ["image", "omath_object", "drawing_element"]):
             print("No text segments were identified as needing translation.")

        translation_idx_batch = 0
        accumulated_translated_sentences_for_group = {}

        for meta_item_full_tuple in metadata_for_translation_assembly:
            item_type, unique_group_id, para_obj, original_text_group, \
            modified_text_segment_for_model, placeholder_map_group, \
            actual_needs_trans_flag, multi_word_segs_group, text_runs_list, \
            fmt_info_list, is_sentence_split_part, sentence_idx_in_group, total_sentences_in_group = meta_item_full_tuple

            if item_type == "image":
                if text_runs_list:
                    img_run = text_runs_list[0]
                    img_path_from_meta = modified_text_segment_for_model
                    img_run.clear()
                    try:
                        img_run.add_picture(img_path_from_meta, width=Inches(2.0))
                    except Exception as e:
                        print(f"Error adding picture {img_path_from_meta} to run: {e}")
                        img_run.text = f"[[Error adding image: {os.path.basename(img_path_from_meta)}]]"
                continue
            
            if item_type == "omath_object" or item_type == "drawing_element":
                pass 

            final_text_for_current_group_assembly = None
            
            full_placeholder_text_for_group_lookup = ""
            if is_sentence_split_part:
                original_item_idx_from_id = int(unique_group_id.split('_')[1])
                if original_item_idx_from_id < len(collected_items):
                    full_placeholder_text_for_group_lookup = collected_items[original_item_idx_from_id][4]
                else:
                    full_placeholder_text_for_group_lookup = modified_text_segment_for_model
            else:
                full_placeholder_text_for_group_lookup = modified_text_segment_for_model

            if not actual_needs_trans_flag:
                final_text_for_current_group_assembly = restore_entities(
                    modified_text_segment_for_model, 
                    placeholder_map_group,
                    original_text_group, 
                    target_lang_full_name, 
                    multi_word_segs_group
                )
            elif is_sentence_split_part:
                current_translated_sentence_part = ""
                if translation_idx_batch < len(translated_text_snippets_from_batch):
                    current_translated_sentence_part = translated_text_snippets_from_batch[translation_idx_batch]
                    translation_idx_batch += 1
                else:
                    current_translated_sentence_part = modified_text_segment_for_model

                if unique_group_id not in accumulated_translated_sentences_for_group:
                    accumulated_translated_sentences_for_group[unique_group_id] = [""] * total_sentences_in_group
                accumulated_translated_sentences_for_group[unique_group_id][sentence_idx_in_group] = current_translated_sentence_part

                if sentence_idx_in_group == total_sentences_in_group - 1:
                    if unique_group_id in accumulated_translated_sentences_for_group and \
                       all(isinstance(s, str) for s in accumulated_translated_sentences_for_group[unique_group_id]):
                        
                        full_translated_text_for_group_intermediate = " ".join(accumulated_translated_sentences_for_group[unique_group_id])
                        
                        final_text_for_current_group_assembly = restore_entities(
                            full_translated_text_for_group_intermediate,
                            placeholder_map_group,
                            original_text_group, 
                            target_lang_full_name,
                            multi_word_segs_group
                        )
                        del accumulated_translated_sentences_for_group[unique_group_id]
                    else:
                        final_text_for_current_group_assembly = restore_entities(
                            full_placeholder_text_for_group_lookup, 
                            placeholder_map_group, original_text_group, target_lang_full_name, multi_word_segs_group
                        )
                        if unique_group_id in accumulated_translated_sentences_for_group:
                             del accumulated_translated_sentences_for_group[unique_group_id]
            else:
                if translation_idx_batch < len(translated_text_snippets_from_batch):
                    translated_segment_from_model = translated_text_snippets_from_batch[translation_idx_batch]
                    final_text_for_current_group_assembly = restore_entities(
                        translated_segment_from_model,
                        placeholder_map_group,
                        original_text_group,
                        target_lang_full_name,
                        multi_word_segs_group
                    )
                    translation_idx_batch += 1
                else:
                    final_text_for_current_group_assembly = restore_entities(
                        modified_text_segment_for_model, 
                        placeholder_map_group, original_text_group, target_lang_full_name, multi_word_segs_group
                    )
            
            if final_text_for_current_group_assembly is not None and item_type not in ["image", "omath_object", "drawing_element"]:
                if text_runs_list:
                    parts_for_runs = split_text_by_proportions(
                        final_text_for_current_group_assembly, 
                        text_runs_list, 
                        original_text_group, 
                        placeholder_map_group
                    )
                    apply_formatting(text_runs_list, parts_for_runs, fmt_info_list)

        if remaining_doc_images:
            print(f"Appending {len(remaining_doc_images)} remaining (unlinked) images to the end of the document.")
            for img_path in remaining_doc_images:
                try:
                    new_para_for_img = doc.add_paragraph()
                    new_run_for_img = new_para_for_img.add_run()
                    new_run_for_img.add_picture(img_path, width=Inches(3.0))
                except Exception as e:
                    print(f"Error appending remaining image {img_path}: {e}")
    
    doc.save(output_path)

if __name__ == "__main__":
    print("Document Translation Script")
    print("-" * 30)

    doc_path_input = input("Enter the full path to the DOCX or DOC file: ").strip()
    
    if not os.path.exists(doc_path_input):
        print(f"Error: Document not found at '{doc_path_input}'")
        exit(1)

    original_doc_path_for_processing = doc_path_input
    if doc_path_input.lower().endswith('.doc'):
        print("Input is a .doc file. Attempting conversion to .docx (requires LibreOffice)...")
        try:
            original_doc_path_for_processing = convert_doc_to_docx(doc_path_input)
            if original_doc_path_for_processing.lower().endswith('.docx') and original_doc_path_for_processing != doc_path_input:
                 print(f"Successfully converted to .docx: {original_doc_path_for_processing}")
            elif original_doc_path_for_processing == doc_path_input:
                 print("File was already .docx or conversion failed to produce a new path name.")
            
        except Exception as e:
            print(f"Error during .doc to .docx conversion: {e}")
            print("Please convert the .doc file to .docx manually and try again.")
            exit(1)
    elif not doc_path_input.lower().endswith('.docx'):
        print("Error: Input file must be a .docx or .doc file.")
        exit(1)

    print("\n" + "=" * 40)
    print(f"Supported languages: {', '.join(config.LANGUAGES.keys())}")
    default_lang = list(config.LANGUAGES.keys())[0]
    target_lang_input_str = input(f"Select target language (e.g., Hindi, default is {default_lang}): ").strip().capitalize()

    selected_target_lang = ""
    if not target_lang_input_str:
        selected_target_lang = default_lang
        print(f"No language selected, defaulting to {selected_target_lang}.")
    elif target_lang_input_str in config.LANGUAGES:
        selected_target_lang = target_lang_input_str
    else:
        selected_target_lang = default_lang
        print(f"Invalid language '{target_lang_input_str}'. Defaulting to {selected_target_lang}.")
    print(f"Target language set to: {selected_target_lang}")

    print("\nEnter entities to preserve (comma-separated, optional, e.g., ProjectName, ModelX, Another Term):")
    user_entities_str = input().strip()
    entities_list_to_preserve = parse_user_entities(user_entities_str)

    start_time_processing_total = time.time()

    file_basename, file_ext = os.path.splitext(os.path.basename(original_doc_path_for_processing))
    output_directory = os.path.dirname(original_doc_path_for_processing) 
    if not output_directory:
        output_directory = "."
    
    output_filename_default = f"{file_basename}_translated_{selected_target_lang.lower()}{file_ext}"
    output_file_path = os.path.join(output_directory, output_filename_default)

    if os.path.abspath(original_doc_path_for_processing) == os.path.abspath(output_file_path):
        output_filename_modified = f"{file_basename}_translated_{selected_target_lang.lower()}_v2{file_ext}"
        output_file_path = os.path.join(output_directory, output_filename_modified)
        print(f"Output path would overwrite input; changing output to: {output_file_path}")

    try:
        print(f"\nProcessing document '{original_doc_path_for_processing}'.")
        print(f"Output will be saved to: {output_file_path}")
        process_document(original_doc_path_for_processing, output_file_path, entities_list_to_preserve, selected_target_lang)
        
        total_processing_time = time.time() - start_time_processing_total
        print(f"\n--- Translation to {selected_target_lang} completed ---")
        print(f"Output saved to: {output_file_path}")
        print(f"Total processing time: {total_processing_time:.2f} seconds")

    except Exception as e:
        print(f"\n--- An error occurred during document processing ---")
        print(f"Error: {e}")
        print("-" * 20 + " Traceback " + "-" * 20)
        traceback.print_exc()
        print("-" * 50)
        print("Processing aborted due to the error.") 