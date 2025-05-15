# Word Document Translation with Structure Preservation

## Overview

This project provides a solution for translating Microsoft Word documents (specifically `.docx`, with conversion support for `.doc`) while ensuring the original structure and formatting are maintained. It is designed to help users translate technical documents, reports, and other content where preserving elements like tables, images, headings, proper nouns, and mathematical variables is crucial.

The tool processes your document, translates the text content using the NLLB model (supporting languages like Hindi, Tamil, and Telugu), and then reconstructs the document, striving to keep the layout and formatting as close to the original as possible.

## Key Features

*   **Document Translation**: Translates text content within `.docx` files.
*   **.doc Conversion**: Can convert `.doc` files to `.docx` using LibreOffice.
*   **Language Support**: Currently supports translation from English to Hindi, Tamil, and Telugu.
*   **Structure & Formatting Preservation**: Attempts to maintain document structure (paragraphs, tables, headers, footers) and text formatting (bold, italic, font size, color).
*   **Entity Preservation**: Can preserve user-defined entities, proper nouns, and common mathematical variables from translation.
*   **Image & Equation Handling**: Extracts and re-inserts images; preserves OMML equation objects.

## Getting Started

These instructions will guide you through setting up and using the project on your local machine.

### Prerequisites

Before you begin, ensure you have the following installed:

*   Python (version 3.6 or higher recommended)
*   `pip` (Python package installer)
*   **LibreOffice**: Required for converting `.doc` files. Install it from [libreoffice.org](https://www.libreoffice.org/download/download/) and ensure it's accessible from your terminal.
*   **spaCy English Model**: Used for proper noun detection. You will download this after installing dependencies.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Prasaderp/Word-Doc-Translation-with-Structure-Preservation-.git
    cd "Word Doc (Translation with Structure Preservation)"
    ```

2.  **Install dependencies:**

    It is highly recommended to use a virtual environment.

    ```bash
# Create a virtual environment (optional but recommended)
    python -m venv .venv
    # Activate the virtual environment
    # On Windows:
    # .venv\Scripts\activate
    # On macOS/Linux:
    # source .venv/bin/activate

    # Install the required packages
    pip install -r requirements.txt
    ```
    *(Ensure you have a `requirements.txt` file listing the project's Python dependencies)*

3.  **Download spaCy language model:**

    ```bash
    python -m spacy download en_core_web_sm
    ```

### Usage

This project can be used via a web interface or a command-line interface.

#### 1. Web Interface (Gradio)

Run the `app.py` script to start the web interface:

```bash
python app.py
```

Open the provided URL in your web browser. The interface allows you to upload your document, select the target language, and specify entities to preserve.

#### 2. Command-Line Interface (CLI)

Run the `main.py` script from your terminal:

```bash
python main.py
```

Follow the prompts to provide the document path, target language, and optional entities to preserve.

## Contributing

If you wish to contribute to this project, please feel free to fork the repository and submit a pull request.

---
