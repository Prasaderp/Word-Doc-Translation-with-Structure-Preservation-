import torch

MODEL_NAME = "facebook/nllb-200-distilled-1.3B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LANGUAGES = {
    "Hindi": {"code": "hin_Deva", "iso": "hi"},
    "Tamil": {"code": "tam_Taml", "iso": "ta"},
    "Telugu": {"code": "tel_Telu", "iso": "te"}
}
MEMORY_THRESHOLD = 0.8
MAX_LENGTH_DEFAULT = 512
MATH_LIKE_CHARS = ('–', '+', '=', '(', ')', '/', '*', '^', '%', '<', '>')

COMMON_VAR_INTRO_WORDS = {"fig", "figure", "table", "train", "point", "let", "assume", "consider", "suppose", "equation"}
COMMON_ARTICLES_PREPOSITIONS = {"the", "an", "is", "of", "in", "on", "at", "by", "for", "with"}