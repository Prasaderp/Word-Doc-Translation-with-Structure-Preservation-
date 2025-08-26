## Document Translator - Setup (Windows)

### Prerequisites
- Python 3.10+ installed
- An OpenAI API key

### Install
1) Open PowerShell and go to the project folder:
```powershell
cd testing - openai
```
2) Create and activate a virtual environment:
```powershell
python -m venv venv
./venv/Scripts/activate
```
3) Upgrade pip and install dependencies:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```
4) Download the spaCy model (recommended):
```powershell
python -m spacy download en_core_web_sm
```
5) Create a .env file in the project folder with your API key:
```text
OPENAI_API_KEY=your_openai_api_key_here
```

### Run
```powershell
python app.py
```
After it starts, open the URL shown in the terminal. The default url is: 0.0.0.0:7860

### Notes
- If any package is missing, install it with pip (e.g., `pip install lxml`).

