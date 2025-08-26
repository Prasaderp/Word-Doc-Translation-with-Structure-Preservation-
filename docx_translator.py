import zipfile
import threading
import re
from lxml import etree
import translation_handler
import utils

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/office/2006/math',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

XML_NS = 'http://www.w3.org/XML/1998/namespace'

PLACEHOLDER_PREFIX = "__MATH_OBJ_"
PLACEHOLDER_SUFFIX = "__"

PLACEHOLDER_TAB = "__TAB__"
PLACEHOLDER_BR = "__BR__"
PLACEHOLDER_CR = "__CR__"

RUN_TOKEN_PREFIX = "__RUN_SEG_"
RUN_TOKEN_SUFFIX = "__"

def _iter_paragraph_sequence(para, math_counter_start):
    sequence = []
    parts = []
    math_counter = math_counter_start
    run_counter = 0

    def append_text_node(t_node):
        sequence.append({'type': 'text', 'node': t_node})
        parts.append(t_node.text if t_node.text is not None else "")

    def append_token(token):
        sequence.append({'type': 'ph', 'token': token})
        parts.append(token)

    for node in para.iter():
        tag = node.tag
        if tag == f"{{{NS['w']}}}t":
            append_text_node(node)
        elif tag == f"{{{NS['w']}}}r":
            run_token = f"{RUN_TOKEN_PREFIX}{run_counter}{RUN_TOKEN_SUFFIX}"
            run_counter += 1
            append_token(run_token)
        elif tag == f"{{{NS['m']}}}oMath" or tag == f"{{{NS['m']}}}oMathPara":
            placeholder = f"{PLACEHOLDER_PREFIX}{math_counter}{PLACEHOLDER_SUFFIX}"
            math_counter += 1
            append_token(placeholder)
        elif tag == f"{{{NS['w']}}}tab":
            append_token(PLACEHOLDER_TAB)
        elif tag == f"{{{NS['w']}}}br":
            append_token(PLACEHOLDER_BR)
        elif tag == f"{{{NS['w']}}}cr":
            append_token(PLACEHOLDER_CR)

    full_text = "".join(parts)
    return sequence, full_text, math_counter

def _extract_paragraphs(root, math_counter_start):
    paragraphs_data = []
    math_counter = math_counter_start
    ph_regex = re.compile(
        rf"({PLACEHOLDER_PREFIX}\d+{PLACEHOLDER_SUFFIX}|{re.escape(PLACEHOLDER_TAB)}|{re.escape(PLACEHOLDER_BR)}|{re.escape(PLACEHOLDER_CR)}|{RUN_TOKEN_PREFIX}\d+{RUN_TOKEN_SUFFIX})"
    )

    for para in root.xpath('.//w:p', namespaces=NS):
        sequence, full_text, math_counter = _iter_paragraph_sequence(para, math_counter)
        clean_text = ph_regex.sub("", full_text)
        if utils.is_translatable(clean_text):
            paragraphs_data.append({
                'para_element': para,
                'sequence': sequence,
                'original_text': full_text
            })

    return paragraphs_data, math_counter

def _write_back_paragraph(para, sequence, translated_text):
    ph_regex = re.compile(
        rf"({PLACEHOLDER_PREFIX}\d+{PLACEHOLDER_SUFFIX}|{re.escape(PLACEHOLDER_TAB)}|{re.escape(PLACEHOLDER_BR)}|{re.escape(PLACEHOLDER_CR)}|{RUN_TOKEN_PREFIX}\d+{RUN_TOKEN_SUFFIX})"
    )
    parts = ph_regex.split(translated_text)
    seg_iter = iter(parts)

    def next_text_segment():
        return next(seg_iter, "")

    pending_text_nodes = []
    current_segment = next_text_segment()

    def flush_text_nodes(segment_text, nodes):
        if not nodes:
            return
        nodes[0].text = segment_text
        if segment_text.startswith(" ") or segment_text.endswith(" "):
            nodes[0].set(f"{{{XML_NS}}}space", "preserve")
        else:
            if f"{{{XML_NS}}}space" in nodes[0].attrib:
                del nodes[0].attrib[f"{{{XML_NS}}}space"]
        for node in nodes[1:]:
            node.text = ""
            if f"{{{XML_NS}}}space" in node.attrib:
                del node.attrib[f"{{{XML_NS}}}space"]

    for item in sequence:
        if item['type'] == 'text':
            pending_text_nodes.append(item['node'])
        else:
            flush_text_nodes(current_segment, pending_text_nodes)
            pending_text_nodes = []
            _ = next(seg_iter, None)
            current_segment = next_text_segment()

    flush_text_nodes(current_segment, pending_text_nodes)

def process_translation(source_path, output_path, target_language, api_key, user_terms=None, progress_callback=None):
    xml_content_map = {}
    all_paragraphs_data = []
    math_obj_counter = 0

    with zipfile.ZipFile(source_path, 'r') as source_zip:
        # Process only main document XML files; skip headers and footers
        xml_files_to_process = [
            name for name in source_zip.namelist()
            if name.startswith('word/') and name.endswith('.xml')
            and not re.search(r'/header\d*\.xml$', name)
            and not re.search(r'/footer\d*\.xml$', name)
        ]
        
        for filename in xml_files_to_process:
            try:
                xml_content = source_zip.read(filename)
                root = etree.fromstring(xml_content)
                xml_content_map[filename] = root

                paragraphs_data, math_obj_counter = _extract_paragraphs(root, math_obj_counter)
                if paragraphs_data:
                    all_paragraphs_data.extend(paragraphs_data)
            except etree.XMLSyntaxError:
                print(f"[WARNING] Skipping non-XML or corrupted file: {filename}")
                xml_content_map[filename] = source_zip.read(filename)

    unique_texts = list(dict.fromkeys([p['original_text'] for p in all_paragraphs_data]))
    
    print(f"[INFO] Text extraction complete. Found {len(unique_texts)} unique text segments.")
    print(f"[INFO] Math/inline control placeholders encountered: {math_obj_counter}")

    translated_cache = {}
    if unique_texts:
        progress_counter = [0]
        progress_lock = threading.Lock()
        total_texts = len(unique_texts)
        
        print(f"[INFO] Starting translation to {target_language}...")
        max_threads = 10 
        for i in range(0, total_texts, max_threads):
            batch = unique_texts[i:i+max_threads]
            thread_batch = []
            for text in batch:
                if text in translated_cache:
                    with progress_lock:
                        progress_counter[0] += 1
                    continue
                thread = threading.Thread(
                    target=translation_handler.translate_segment,
                    args=(text, target_language, translated_cache, api_key, user_terms or [], progress_counter, progress_lock, total_texts, progress_callback)
                )
                thread_batch.append(thread)
                thread.start()
            for thread in thread_batch:
                thread.join()
        print("\n[INFO] All translations complete.")

    print("[INFO] Writing translations back into document...")
    para_data_by_id = {id(p['para_element']): p for p in all_paragraphs_data}
    for root in xml_content_map.values():
        if not isinstance(root, etree._Element):
            continue
        for para in root.xpath('.//w:p', namespaces=NS):
            pdata = para_data_by_id.get(id(para))
            if not pdata:
                continue
            original = pdata['original_text']
            translated = translated_cache.get(original)
            if not translated:
                continue
            _write_back_paragraph(para, pdata['sequence'], translated)

    with zipfile.ZipFile(source_path, 'r') as source_zip, zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as output_zip:
        for item in source_zip.infolist():
            if item.filename in xml_content_map:
                content = xml_content_map[item.filename]
                if isinstance(content, etree._Element):
                    output_zip.writestr(item.filename, etree.tostring(content, encoding='UTF-8', xml_declaration=True))
                else:
                    output_zip.writestr(item.filename, content)
            else:
                output_zip.writestr(item, source_zip.read(item.filename))
                
    print(f"[SUCCESS] Translated document saved to {output_path}")