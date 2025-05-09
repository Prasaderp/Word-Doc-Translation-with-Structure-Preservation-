# config.py
import torch

MODEL_NAME = "facebook/nllb-200-distilled-600M"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LANGUAGES = {
    "Hindi": {"code": "hin_Deva", "iso": "hi"},
    "Tamil": {"code": "tam_Taml", "iso": "ta"},
    "Telugu": {"code": "tel_Telu", "iso": "te"}
}
MEMORY_THRESHOLD = 0.8 # Percentage of GPU memory that triggers a reset
MAX_LENGTH_DEFAULT = 512 # Default max length for tokenization/generation
MATH_LIKE_CHARS = ('–', '+', '=', '(', ')', '/', '*', '^', '%', '<', '>') # Characters often found in/around math

# Words that often introduce variables or specific contexts
COMMON_VAR_INTRO_WORDS = {
    "fig", "figure", "table", "train", "point", "let", "assume", 
    "consider", "suppose", "equation"
}

# Common articles and prepositions - not currently used in the refactored placeholder logic directly
# but kept for potential future use or more nuanced NLP tasks.
COMMON_ARTICLES_PREPOSITIONS = {
    "the", "an", "is", "of", "in", "on", "at", "by", "for", "with"
} 