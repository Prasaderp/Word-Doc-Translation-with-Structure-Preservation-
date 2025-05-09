# file_utils.py
import os
import subprocess
import tempfile
import shutil

def convert_doc_to_docx(doc_path):
    if not doc_path.lower().endswith('.doc'):
        return doc_path

    base_name = os.path.splitext(doc_path)[0]
    docx_path = base_name + '.docx'

    try:
        subprocess.run(['libreoffice', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError:
        print("LibreOffice not found. Attempting to install (requires sudo and apt)...")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libreoffice', 'libreoffice-writer'], check=True)
            print("LibreOffice installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install LibreOffice: {e}")
            raise Exception("LibreOffice is required for .doc conversion but could not be installed automatically. Please install it manually.")
        except FileNotFoundError: 
             raise Exception("LibreOffice is required. Could not find 'sudo' or 'apt-get' to attempt installation. Please install LibreOffice manually.")
    except subprocess.CalledProcessError as e:
        print(f"LibreOffice version check failed: {e}. Assuming it's installed and proceeding.")
        pass 

    if os.path.exists(docx_path):
        try:
            os.remove(docx_path)
        except OSError as e:
            print(f"Warning: Could not remove existing file at {docx_path}: {e}.")
            pass

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Converting {doc_path} to .docx using LibreOffice (output to temp dir: {tmpdir})...")
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'docx', '--outdir', tmpdir, doc_path],
                check=True, 
                timeout=120 
            )
            
            converted_file_name = os.path.basename(base_name + '.docx')
            temp_docx_path = os.path.join(tmpdir, converted_file_name)

            if os.path.exists(temp_docx_path):
                shutil.move(temp_docx_path, docx_path)
                print(f"Successfully converted and moved to {docx_path}")
                return docx_path
            else:
                raise FileNotFoundError(f"Converted file {temp_docx_path} not found after LibreOffice conversion.")
    except subprocess.CalledProcessError as e:
        error_message = f"Error during .doc to .docx conversion using LibreOffice: {e}"
        if e.stderr:
            error_message += f"\nLibreOffice stderr: {e.stderr.decode(errors='ignore')}"
        raise Exception(error_message)
    except subprocess.TimeoutExpired:
        raise Exception("LibreOffice .doc to .docx conversion timed out after 120 seconds.")
    except FileNotFoundError as e: 
        raise Exception(f"File system error during LibreOffice conversion: {e}") 