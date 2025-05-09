# Document Translation with Structure Preservation

This project translates DOCX (and .doc via conversion) documents from English to selected Indian languages (Hindi, Tamil, Telugu) while attempting to preserve formatting, structure, proper nouns, and mathematical variables. It can be used via an intuitive Gradio web interface or a command-line interface.

## Features

-   **DOCX Translation**: Translates text content within DOCX files.
-   **.doc Conversion**: Automatically converts .doc files to .docx using LibreOffice (if installed).
-   **Language Support**: Currently supports translation to Hindi, Tamil, and Telugu using the NLLB model.
-   **Structure Preservation**: Attempts to maintain document structure including paragraphs, tables, headers, and footers.
-   **Formatting Preservation**: Tries to keep original text formatting (bold, italic, underline, font size, color, subscript, superscript).
-   **Entity Preservation**:
    -   User-defined entities (e.g., specific project names, technical terms).
    -   Proper nouns (persons, locations, organizations, etc.) identified by spaCy.
-   **Mathematical Variable Preservation**: Identifies and preserves common mathematical variables (e.g., single uppercase letters, alphanumeric variables like `x1`, `Area`).
-   **Image Handling**: Extracts and re-inserts images from the document.
-   **Equation Handling**: Preserves OMML equation objects (does not translate text within them).
-   **GPU Acceleration**: Uses CUDA (if available) for faster translation with NLLB models from Hugging Face Transformers.
-   **Memory Management**: Includes basic GPU memory monitoring and reset capabilities to handle large documents.

## Setup

### Prerequisites

1.  **Python**: Version 3.8 or higher.
2.  **LibreOffice**: Required for converting `.doc` files to `.docx`.
    -   On Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y libreoffice libreoffice-writer`
    -   On other systems (Windows, macOS), install LibreOffice manually from [libreoffice.org](https://www.libreoffice.org/download/download/). Ensure it's added to your system's PATH or accessible via the `libreoffice` command.
3.  **CUDA Toolkit** (Optional but Highly Recommended for Speed): For GPU acceleration. Ensure your NVIDIA drivers and CUDA toolkit version are compatible with the PyTorch version specified in `requirements.txt`.

### Installation

1.  **Clone the repository (if applicable) or place all project files in a single directory.**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Linux/macOS
    source venv/bin/activate
    # On Windows
    # venv\Scripts\activate
    ```

3.  **Install Python dependencies (including Gradio for the web interface):**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download spaCy language model:**
    The script uses spaCy for proper noun detection. You need to download its English model:
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Usage

This project offers two main ways to perform translations:

### 1. Web Interface (Gradio)

The primary way to interact with the translator is through a user-friendly web interface built with Gradio.

**Prerequisites:**
- Ensure all dependencies from `requirements.txt` are installed (this includes `gradio`).
- The backend model and .doc conversion prerequisites (LibreOffice) are the same as for the CLI (see below).

**Running the Gradio App:**

Activate your virtual environment and run the `app.py` script from the project directory:

```bash
python app.py
```

This will typically start a local web server (e.g., `http://127.0.0.1:7860`). Open this URL in your web browser. If you launched it with `share=True` (default in current `app.py`), a public link will also be provided for temporary sharing.

**Interface Features:**
-   Upload your `.docx` or `.doc` file.
-   Select the target translation language from a dropdown menu.
-   Optionally, enter any comma-separated entities you wish to keep untranslated.
-   Click "Submit" to start the translation process.
-   A status/log box will show progress and any important messages.
-   Once complete, a download link for the translated `.docx` file will appear.

### 2. Command-Line Interface (CLI)

For users who prefer or require a command-line tool, the script can be run directly.

Run the `main.py` script from the terminal within the project directory (and activated virtual environment):

```bash
python main.py
```

The script will then prompt you for:
1.  **Full path to the DOCX or DOC file** you want to translate.
2.  **Target language** from the supported list (e.g., Hindi, Tamil, Telugu). If you press Enter, it defaults to Hindi.
3.  **(Optional) Comma-separated list of entities to preserve.** These are terms or phrases you want to ensure are not translated (e.g., `ProjectName, ModelX, Specific Terminology`).

The translated document will be saved in the same directory as the input file. The output filename will typically be `[original_filename]_translated_[language].docx` (e.g., `mydoc_translated_hindi.docx`).

### Example CLI Interaction

```
Document Translation Script
------------------------------
Enter the full path to the DOCX or DOC file: /path/to/my_document.docx

========================================
Supported languages: Hindi, Tamil, Telugu
Select target language (e.g., Hindi, default is Hindi): Tamil
Target language set to: Tamil

Enter entities to preserve (comma-separated, optional, e.g., ProjectName, ModelX, Another Term): NLLB, PyTorch
User-defined entities to preserve: NLLB, PyTorch

Processing document '/path/to/my_document.docx'.
Output will be saved to: /path/to/my_document_translated_tamil.docx
Initializing translation model...
Model loaded in X.XXs
[Other processing messages...]

--- Translation to Tamil completed ---
Output saved to: /path/to/my_document_translated_tamil.docx
Total processing time: XX.XX seconds
```

## Project Structure

```
.
├── main.py                     # Main script for CLI execution
├── app.py                      # Gradio web interface application
├── config.py                   # Configuration constants (model names, languages, paths, etc.)
├── model_utils.py              # Utilities for loading the model, managing GPU memory
├── text_processing_utils.py    # Placeholder logic, entity/noun extraction, text manipulation
├── docx_processing_utils.py    # DOCX parsing, content collection, formatting application
├── translation_service.py      # Core translation batching and model inference logic
├── file_utils.py               # File system operations (e.g., .doc to .docx conversion)
├── requirements.txt            # Python package dependencies
└── README.md                   # This documentation file
```

## How it Works (High-Level)

1.  **Input**: The user provides a document through the Gradio interface (`app.py`) or as a path to the CLI (`main.py`).
2.  **Conversion (`file_utils.py`)**: If a `.doc` file is provided, it attempts conversion to `.docx` using LibreOffice.
3.  **Content Parsing (`docx_processing_utils.py`):** The DOCX document is parsed to extract text runs, images, and OMML (Office Math Markup Language) objects. Text is grouped to maintain context while respecting formatting boundaries.
4.  **Placeholder Generation (`text_processing_utils.py`):** Before translation, specific text segments (user-defined entities, proper nouns via spaCy, mathematical variables, URLs, emails etc.) are identified and replaced with unique placeholders (e.g., `__ENTITY_000001__`). This protects them from being translated.
5.  **Translation (`translation_service.py`, `model_utils.py`):** The text segments (now containing placeholders) are translated using the NLLB (No Language Left Behind) model. This is done in batches for efficiency, with GPU acceleration if available.
6.  **Restoration (`text_processing_utils.py`):** After translation, the placeholders in the translated text are replaced with their original content. Logic is included to try and fix placeholders that might have been slightly altered by the translation model.
7.  **Document Reassembly (`docx_processing_utils.py`, `main.py`):** A new DOCX document is constructed. Translated text is inserted, and an attempt is made to reapply the original formatting (bold, italic, font size, color, etc.) to the corresponding text runs. Images and OMML equations are re-inserted or preserved.
8.  **Output**: The final translated DOCX file is saved.

## Limitations & Considerations

-   **Translation Accuracy**: The quality of translation depends heavily on the NLLB model's performance for the specific English-to-target language pair and the complexity/domain of the text.
-   **Formatting Fidelity**: While the script tries to preserve formatting, very complex layouts or specific Word features might not be perfectly replicated. The process of splitting text into runs and then reassembling translated text (which may differ in length) can sometimes lead to minor layout shifts.
-   **Mathematical Content**: Simple variables are generally preserved. Complex inline mathematical text not enclosed in OMML objects might be partially translated or misidentified. Full OMML equations are preserved as objects but their internal text is not translated.
-   **Image Layouts**: Basic image insertion is handled. Complex image positioning, text wrapping, or grouped images might not be perfectly maintained.
-   **Performance**: Translating large documents, especially on a CPU, can be time-consuming. GPU is highly recommended.
-   **LibreOffice Dependency**: Conversion of `.doc` files is strictly dependent on a working LibreOffice installation accessible from the command line.
-   **Error Robustness**: The script has error handling, but very unusual or corrupted DOCX structures could still cause issues.

## Potential Future Enhancements
```
-   Finer-grained control over NLLB model parameters or selection of different model sizes.
-   Improved parsing and preservation strategies for diverse mathematical notations.
-   Advanced sentence segmentation, especially for text rich in placeholders.
``` 