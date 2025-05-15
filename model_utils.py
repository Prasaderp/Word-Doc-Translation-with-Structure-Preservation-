import torch
import time
import gc
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from config import MODEL_NAME, DEVICE, MEMORY_THRESHOLD

tokenizer = None
model = None

def initialize_model():
    global tokenizer, model
    start_time = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
    ).to(DEVICE).eval()
    return tokenizer, model

def get_model_and_tokenizer():
    global tokenizer, model
    if tokenizer is None or model is None:
        initialize_model()
    return tokenizer, model

def reset_gpu_memory():
    global model, tokenizer
    if DEVICE == "cuda":
        if 'model' in globals() and model is not None: del model
        if 'tokenizer' in globals() and tokenizer is not None: del tokenizer
        model = None
        tokenizer = None
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        tokenizer, model = initialize_model()

def check_memory_and_reset(total_segments_to_translate):
    if DEVICE != "cuda" or total_segments_to_translate <= 100:
        return False
    try:
        total_memory = torch.cuda.get_device_properties(0).total_memory
        allocated_memory = torch.cuda.memory_allocated()
        reserved_memory = torch.cuda.memory_reserved()
        usage_percent_reserved = reserved_memory / total_memory
        if usage_percent_reserved > MEMORY_THRESHOLD:
            reset_gpu_memory()
            return True
    except Exception as e:
        try:
            if DEVICE == "cuda" and not torch.cuda.is_available():
                initialize_model()
        except Exception as reinit_e:
            pass
        return False
    return False