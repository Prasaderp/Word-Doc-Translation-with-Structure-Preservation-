import gradio as gr
import os
import docx_translator
import threading
import queue
import time
from dotenv import load_dotenv

load_dotenv()

def translate_document_interface(document_file, target_language, retain_terms):
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not document_file:
        yield "Please upload a document.", None
        return
    
    if not target_language:
        yield "Please select a target language.", None
        return

    if not openai_api_key:
        error_message = "Error: OPENAI_API_KEY not found in .env file."
        print(f"[ERROR] {error_message}")
        yield error_message, None
        return
            
    print(f"\n[INFO] Received new job: Translate {os.path.basename(document_file.name)} to {target_language}")
    
    try:
        start_time = time.time()
        input_path = document_file.name
        base_name = os.path.basename(input_path)
        name, ext = os.path.splitext(base_name)
        output_path = os.path.join(os.path.dirname(input_path), f"{name}_{target_language}{ext}")

        user_terms = []
        if retain_terms:
            parts = [p.strip() for p in retain_terms.replace("\r", "").replace("\t", " ").split("\n")]
            flat = []
            for p in parts:
                if "," in p:
                    flat.extend(s.strip() for s in p.split(","))
                else:
                    flat.append(p)
            user_terms = [t for t in (s.strip() for s in flat) if t]

        q = queue.Queue()
        def on_progress(pct):
            q.put(pct)

        worker_error = {"e": None}
        def runner():
            try:
                docx_translator.process_translation(input_path, output_path, target_language, openai_api_key, user_terms, on_progress)
            except Exception as e:
                worker_error["e"] = e
        worker = threading.Thread(target=runner)
        worker.start()

        last_pct = 0.0
        while worker.is_alive() or not q.empty():
            try:
                pct = q.get(timeout=0.2)
                last_pct = float(pct)
                elapsed = round(time.time() - start_time, 1)
                yield f"{last_pct:.0f}% | {elapsed}s", None
            except Exception:
                pass
        worker.join()

        if worker_error["e"] is not None:
            error_message = f"An unexpected error occurred: {str(worker_error['e'])}"
            print(f"[FATAL ERROR] {error_message}")
            yield error_message, None
            return

        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        status_message = f"Successfully translated to {target_language} in {processing_time} seconds."
        print(f"[SUCCESS] {status_message}")
        yield status_message, gr.File(value=output_path, visible=True)
        return

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(f"[FATAL ERROR] {error_message}")
        return error_message, None

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Document Translator
        Upload a .docx file, select the target language, and click translate.
        """
    )

    with gr.Row(variant="panel"):
        with gr.Column(scale=1):
            doc_input = gr.File(label="1. Upload Document", file_types=[".docx"])
            language_input = gr.Dropdown(["Hindi", "Tamil", "Telugu"], label="2. Select Target Language")
            retain_terms_input = gr.Textbox(
                label="3. Words to Keep (Optional)",
                placeholder="Terms to not translate, separated by commas or new lines.",
                lines=3
            )
            submit_button = gr.Button("Translate Document", variant="primary")

        with gr.Column(scale=1):
            status_output = gr.Textbox(label="Status", interactive=False, lines=4, placeholder="Translation progress will be shown here...")
            translated_output = gr.File(label="Download Translated File", interactive=False)

    submit_button.click(
        translate_document_interface,
        inputs=[doc_input, language_input, retain_terms_input],
        outputs=[status_output, translated_output]
    )

if __name__ == "__main__":
    print("[INFO] Loading API key from .env file...")
    print("[INFO] Starting Gradio application...")
    demo.launch(share=True, server_name="0.0.0.0")