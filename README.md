# Word Document Translation with Structure Preservation

This project translates Microsoft Word documents (`.docx` and `.doc`) into Hindi, Tamil, or Telugu, focusing on preserving the original structure, formatting, and user-specified terms. It uses the NLLB model for translation and provides a Gradio web interface for ease of use.

## Key Features

* **Preserves Structure & Formatting**: Aims to maintain paragraphs, tables, headers, footers, and text styles (bold, italic, fonts, colors).
* **Entity & Variable Protection**: Allows users to specify terms to keep untranslated and automatically attempts to preserve proper nouns and mathematical variables.
* **Image & Equation Handling**: Images are retained, and OMML equation objects are preserved (not translated).
* **.doc Support**: Converts older `.doc` files to `.docx` using LibreOffice.
* **Target Languages**: Translates from English to Hindi, Tamil, and Telugu.
* **User Interface**: Simple Gradio web UI for file upload, language selection, and entity input.
* **Performance**: Supports CUDA for GPU acceleration.

## Getting Started

### Prerequisites

* **Python**: 3.8+
* **LibreOffice**: Required for `.doc` conversion. Ensure it's installed and accessible from the command line.
* **CUDA Toolkit** (Optional): For GPU acceleration.

### Installation

1.  **Clone the repository (if applicable) or place project files in a directory.**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Linux/macOS: source venv/bin/activate
    # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download spaCy language model (for proper noun detection):**
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Usage

The primary way to use this tool is through the Gradio Web Interface.

1.  **Run the application:**
    ```bash
    python app.py
    ```
2.  **Open the web interface:**
    Access the local URL provided in your terminal (usually `http://127.0.0.1:7860`).
3.  **Translate:**
    * Upload your `.docx` or `.doc` file.
    * Select the "Target Language."
    * Optionally, enter "Entities to Preserve" (comma-separated).
    * Click "Submit."
    * Download the translated document when ready. A log of the process will be displayed.

## How It Works Briefly

1.  **Input & Preprocessing**: Document uploaded via Gradio. `.doc` files are converted to `.docx`.
2.  **Content Parsing**: Text, formatting, images, and equations are extracted from the `.docx`.
3.  **Placeholder Generation**: Non-translatable elements (user entities, proper nouns, math variables, URLs) are replaced with unique placeholders.
4.  **Translation**: Text segments (with placeholders) are translated in batches using the NLLB model.
5.  **Restoration & Reassembly**: Placeholders are restored to their original values. The translated text, along with preserved formatting and elements, is reassembled into a new `.docx` document.

## Project Files

* `app.py`: Gradio web interface.
* `main.py`: Core document processing logic.
* `config.py`: Configuration (model, languages, device).
* `model_utils.py`: NLLB model loading and GPU management.
* `text_processing_utils.py`: Placeholder logic, entity/noun extraction.
* `docx_processing_utils.py`: DOCX parsing, formatting, and reconstruction.
* `translation_service.py`: Translation batching and inference.
* `file_utils.py`: `.doc` to `.docx` conversion.
* `requirements.txt`: Python dependencies.

## Limitations

* Translation quality depends on the NLLB model.
* Perfect formatting replication can be challenging for very complex layouts.
* Only OMML equations are preserved as objects; inline math text might be affected.