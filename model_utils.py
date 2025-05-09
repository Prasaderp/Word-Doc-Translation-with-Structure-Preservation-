# model_utils.py
import torch
import time
import gc
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from config import MODEL_NAME, DEVICE, MEMORY_THRESHOLD

# Global model and tokenizer, initialized once
tokenizer = None
model = None

def initialize_model():
    global tokenizer, model
    print("Initializing translation model...")
    start_time = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
    ).to(DEVICE).eval()
    print(f"Model loaded in {time.time() - start_time:.2f}s")
    return tokenizer, model

def get_model_and_tokenizer():
    global tokenizer, model
    if tokenizer is None or model is None:
        initialize_model()
    return tokenizer, model

def reset_gpu_memory():
    global model, tokenizer
    if DEVICE == "cuda":
        if model is not None:
            del model
            model = None
        if tokenizer is not None:
            del tokenizer
            tokenizer = None
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        print("GPU memory reset. Re-initializing model...")
        initialize_model() # Re-initialize after clearing

def check_memory_and_reset(total_segments_to_translate):
    if DEVICE != "cuda" or total_segments_to_translate <= 100: # Only check for CUDA and significant load
        return False
    try:
        total_memory = torch.cuda.get_device_properties(0).total_memory
        allocated_memory = torch.cuda.memory_allocated()
        if (allocated_memory / total_memory) > MEMORY_THRESHOLD:
            print(f"High memory usage detected ({allocated_memory/total_memory*100:.1f}%). Resetting GPU memory and model...")
            reset_gpu_memory()
            return True
    except Exception as e:
        print(f"Error during memory check: {e}")
        try:
            if DEVICE == "cuda" and not torch.cuda.is_available(): # Check if CUDA became unavailable
                print("CUDA seems to have become unavailable. Attempting re-initialization.")
                initialize_model()
        except Exception as reinit_e:
            print(f"Failed to re-initialize model after memory check error: {reinit_e}")
        return False # Error occurred, assume no reset happened or was needed
    return False 