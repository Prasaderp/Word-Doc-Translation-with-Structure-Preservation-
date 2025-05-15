import os
import time
import tempfile
import gradio as gr
import traceback

from main import process_document
from config import LANGUAGES
from text_processing_utils import parse_user_entities
from file_utils import convert_doc_to_docx
from model_utils import get_model_and_tokenizer, initialize_model

get_model_and_tokenizer()


def translation_interface_fn(input_docx_file, target_language, entities_to_preserve_str):
    if input_docx_file is None:
        return None, "Error: No DOCX/DOC file provided."
    
    doc_path = input_docx_file.name
    original_file_name = os.path.basename(input_docx_file.name if hasattr(input_docx_file, 'name') else str(input_docx_file))


    if not doc_path.lower().endswith(('.docx', '.doc')):
        return None, "Error: Input file must be a .doc or .docx file."
    
    status_messages = [f"Received file: {original_file_name}"]
    processed_doc_path = doc_path
    output_temp_dir_obj = tempfile.TemporaryDirectory()
    output_temp_dir = output_temp_dir_obj.name

    
    try:
        if doc_path.lower().endswith('.doc'):
            status_messages.append("Input is a .doc file. Attempting conversion to .docx...")
            conversion_start_time = time.time()
            # Copy the uploaded .doc file to a path with the correct extension for LibreOffice
            temp_doc_for_conversion_name = os.path.join(output_temp_dir, original_file_name)
            with open(doc_path, 'rb') as f_src, open(temp_doc_for_conversion_name, 'wb') as f_dst:
                f_dst.write(f_src.read())

            try:
                processed_doc_path = convert_doc_to_docx(temp_doc_for_conversion_name)
                status_messages.append(f".doc successfully converted to: {os.path.basename(processed_doc_path)}")
            except Exception as e:
                error_msg = f"Error during .doc to .docx conversion: {e}. Please convert the .doc file to .docx manually and try again."
                status_messages.append(error_msg)
                return None, "\n".join(status_messages)
        
        entities_to_preserve = parse_user_entities(entities_to_preserve_str)
        status_messages.append(f"Target language: {target_language}")
        if entities_to_preserve:
            status_messages.append(f"User-defined entities to preserve: {', '.join(entities_to_preserve)}")
        else:
            status_messages.append("No additional user-defined entities to preserve.")
        
        status_messages.append(f"Starting translation process for {os.path.basename(processed_doc_path)}...")
        start_time_processing = time.time()
        
        # Ensure output_path for process_document is within the temp directory
        base, ext = os.path.splitext(os.path.basename(original_file_name)) # Use original_file_name for consistent output naming
        output_filename = f"{base}_translated_{target_language.lower()}{'.docx'}" # Ensure .docx extension
        output_path = os.path.join(output_temp_dir, output_filename)
        
        process_document(processed_doc_path, output_path, entities_to_preserve, target_language)
        
        total_time = time.time() - start_time_processing
        status_messages.append(f"Translation to {target_language} completed.")
        status_messages.append(f"Output file '{output_filename}' is ready for download.")
        status_messages.append(f"Total processing time: {total_time:.1f}s")
        
        return output_path, "\n".join(status_messages)

    except Exception as e:
        error_full_trace = traceback.format_exc()
        status_messages.append(f"An critical error occurred: {e}")
        status_messages.append(f"Details: {error_full_trace}")
        return None, "\n".join(status_messages)
    # TemporaryDirectory will be cleaned up automatically when output_temp_dir_obj goes out of scope
    # or by Gradio's own temp file handling if output_path is correctly handled as a temp file by gr.File output.


iface = gr.Interface(
    fn=translation_interface_fn,
    inputs=[
        gr.File(label="Upload DOCX or DOC File", file_types=[".docx", ".doc"]),
        gr.Dropdown(label="Select Target Language", choices=list(LANGUAGES.keys()), value="Hindi"),
        gr.Textbox(label="Entities to Preserve (comma-separated, optional)", placeholder="e.g., Aigenthix, Model_X1")
    ],
    outputs=[
        gr.File(label="Download Translated Document"),
        gr.Textbox(label="Processing Status & Logs", lines=15, interactive=False)
    ],
    title="Word Document Translator (Indic Languages)",
    description="Translate .docx or .doc files to Hindi, Tamil, or Telugu. \n" \
                "The system preserves formatting, structure (including images and tables by not modifying them) and tries to keep specified entities untranslated. \n" \
                "Processing can take some time depending on document size and complexity. \n" \
                "Note: .doc to .docx conversion requires LibreOffice installed on the system where this Tool is run.",
    allow_flagging="never",
    examples=[
        [None, "Hindi", "Planck Institute, Albert Einstein"],
        [None, "Tamil", "University of Cambridge, Project Kavach"],
        [None, "Telugu", "IIT, RDBMS"],
    ]
)

if __name__ == "__main__":
    iface.launch(share=True, debug=True)