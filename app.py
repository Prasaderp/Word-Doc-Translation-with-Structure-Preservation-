# app.py
import gradio as gr
import os
import traceback
import tempfile
import shutil
import atexit

from main import process_document
from config import LANGUAGES
from text_processing_utils import parse_user_entities
from file_utils import convert_doc_to_docx
from model_utils import get_model_and_tokenizer

temp_items_to_clean = []

def cleanup_temp_items():
    print(f"Cleaning up {len(temp_items_to_clean)} temporary items...")
    for item_path in temp_items_to_clean:
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Error cleaning up temp item {item_path}: {e}")
    temp_items_to_clean.clear()

atexit.register(cleanup_temp_items)

def translation_pipeline_gradio(uploaded_file_obj, target_lang, entities_str):
    if uploaded_file_obj is None:
        return None, "Error: Please upload a document first."

    gradio_temp_input_path = uploaded_file_obj.name
    original_input_filename = os.path.basename(
        uploaded_file_obj.orig_name if hasattr(uploaded_file_obj, 'orig_name') and uploaded_file_obj.orig_name 
        else gradio_temp_input_path
    )

    status_log = [f"Received: {original_input_filename}"]
    
    path_to_process_doc = gradio_temp_input_path
    conversion_work_dir = None 

    if gradio_temp_input_path.lower().endswith('.doc'):
        status_log.append("Input is a .doc file, attempting conversion to .docx...")
        conversion_work_dir = tempfile.mkdtemp()
        temp_items_to_clean.append(conversion_work_dir)

        copied_doc_for_conversion = os.path.join(conversion_work_dir, os.path.basename(gradio_temp_input_path))
        shutil.copyfile(gradio_temp_input_path, copied_doc_for_conversion)

        try:
            converted_docx_path = convert_doc_to_docx(copied_doc_for_conversion)
            if not converted_docx_path.lower().endswith('.docx') or not os.path.exists(converted_docx_path):
                raise FileNotFoundError("Conversion did not produce a valid .docx file or the file was not found.")
            status_log.append(f"Successfully converted .doc to .docx: {os.path.basename(converted_docx_path)}")
            path_to_process_doc = converted_docx_path
        except Exception as e:
            detailed_error = traceback.format_exc()
            status_log.append(f"Error during .doc conversion: {str(e)}\nDetails: {detailed_error}")
            return None, "\n".join(status_log)
    
    final_translated_output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_output_gen:
            final_translated_output_path = tmp_output_gen.name
        temp_items_to_clean.append(final_translated_output_path) 

        status_log.append(f"Processing document: {os.path.basename(path_to_process_doc)}")
        status_log.append(f"Target language: {target_lang}")
        
        entities_list = parse_user_entities(entities_str)
        if entities_list:
            status_log.append(f"User-defined entities to preserve: {', '.join(entities_list)}")
        else:
            status_log.append("No custom entities specified for preservation.")
        
        get_model_and_tokenizer() 
        
        process_document(path_to_process_doc, final_translated_output_path, entities_list, target_lang)
        
        if not os.path.exists(final_translated_output_path) or os.path.getsize(final_translated_output_path) == 0:
            raise FileNotFoundError("Translated document was not created or is empty.")

        output_base_name, _ = os.path.splitext(original_input_filename)
        download_filename_suggestion = f"{output_base_name}_translated_{target_lang.lower()}.docx"

        status_log.append(f"Processing complete. Translated document '{download_filename_suggestion}' is ready for download.")
        
        return final_translated_output_path, "\n".join(status_log)

    except Exception as e:
        detailed_error = traceback.format_exc()
        status_log.append(f"An error occurred during the translation process: {str(e)}\nDetails: {detailed_error}")
        return None, "\n".join(status_log)


app_title = "Document Translator with Structure Preservation"
app_description = ("""
Upload a .docx or .doc file, select the target language, and optionally list comma-separated entities to preserve. 
All processing happens on the server. The translated .docx file will be provided for download.
Note: 
- .doc file conversion requires LibreOffice to be installed and accessible in the system's PATH.
- Model initialization (first time) or GPU memory resets can cause a delay on the first translation after app start.
- Processing times vary based on document size and system (GPU recommended).
""")
article_info = "<p style='text-align: center;'>Powered by NLLB, spaCy, python-docx, and Gradio. <br> Ensure LibreOffice is installed for .doc support.</p>"

print("Initializing translation model for Gradio application...")
get_model_and_tokenizer()
print("Translation model ready.")

iface = gr.Interface(
    fn=translation_pipeline_gradio,
    inputs=[
        gr.File(label="Upload Document (.docx or .doc)", file_types=['.docx', '.doc']),
        gr.Dropdown(label="Select Target Language", choices=list(LANGUAGES.keys()), value=list(LANGUAGES.keys())[0]),
        gr.Textbox(label="Entities to Preserve (comma-separated, optional)", placeholder="e.g., ProjectName, ModelX, Terminology")
    ],
    outputs=[
        gr.File(label="Download Translated Document"),
        gr.Textbox(label="Status / Log", lines=15, interactive=False, show_label=True)
    ],
    title=app_title,
    description=app_description,
    article=article_info,
    allow_flagging='never',
    examples=[
        [None, "Hindi", "NLLB, Python"], 
    ]
)

if __name__ == '__main__':
    print("Launching Gradio interface...")
    iface.launch(share=True, debug=True) 