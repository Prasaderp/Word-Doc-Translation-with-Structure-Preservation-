import os
import subprocess
import tempfile
import shutil

def convert_doc_to_docx(doc_path):
    if not doc_path.endswith('.doc'):
        return doc_path
    base_name = os.path.splitext(doc_path)[0]
    docx_path = base_name + '.docx'
    try:
        subprocess.run(['libreoffice', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError:
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libreoffice', 'libreoffice-writer'], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception("LibreOffice is required for .doc conversion but could not be installed.")
    except subprocess.CalledProcessError as e:
        pass
    if os.path.exists(docx_path):
        try:
            os.remove(docx_path)
        except OSError as e:
            pass
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'docx', '--outdir', tmpdir, doc_path],
                check=True, timeout=120
            )
            converted_file_name = os.path.basename(base_name + '.docx')
            temp_docx_path = os.path.join(tmpdir, converted_file_name)
            if os.path.exists(temp_docx_path):
                shutil.move(temp_docx_path, docx_path)
                return docx_path
            else:
                raise FileNotFoundError(f"Converted file {temp_docx_path} not found.")
    except subprocess.CalledProcessError as e:
        if e.stderr: pass
        raise
    except subprocess.TimeoutExpired:
        raise
    except FileNotFoundError as e:
        raise
    return docx_path