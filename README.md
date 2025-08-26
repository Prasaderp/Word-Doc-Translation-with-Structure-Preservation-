# Word Document/Docx Translator with Structure Preservation



This project translates Microsoft Word documents (`.docx` and `.doc`) into Hindi, Tamil, or Telugu (you can add any language you want) focusing on preserving the original structure, formatting, and user-specified terms. It uses the OpenAI chatgpt-4o-mini model for translation and provides a Gradio web interface for ease of use.



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



* **Python**: 3.11+
* OpenAI key 



### Installation

1.  Clone the repository (if applicable) or place project files in a directory.

    ```bash
    git clone https://github.com/Prasaderp/Word-Doc-Translation-with-Structure-Preservation-.git
    cd Word-Doc-Translation-with-Structure-Preservation-
    ```
    

2. **Create and activate a virtual environment (recommended):**

    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Linux/macOS:
    source venv/bin/activate

    # On Windows:
    venv\Scripts\activate
    ```
    

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
    

4. **Download spaCy language model (for proper noun detection):**

    ```bash
    python -m spacy download en_core_web_sm
    ```



## Usage

The primary way to use this tool is through the Gradio Web Interface.


1. **Run the application:**

    ```bash
    python app.py
    ```

2.  **Open the web interface:**

    Access the local URL provided in your terminal (usually `http://127.0.0.1:7860`).

3.  **Translate:**

    * Upload your `.docx` or `.doc` file.

    * Select the "Target Language."

    * Optionally, enter "Entities to Preserve" (comma-separated).

    * Click "Submit."

    * Download the translated document when ready. A log of the process will be displayed.

