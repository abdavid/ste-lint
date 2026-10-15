from pathlib import Path

__version__ = "0.1.0"
DATA_DIR = Path(__file__).parent / "data"
DICTIONARY_PATH = DATA_DIR / "dictionary.json"
RULES_PATH = DATA_DIR / "rules.json"
SPACY_MODEL = "en_core_web_sm"
