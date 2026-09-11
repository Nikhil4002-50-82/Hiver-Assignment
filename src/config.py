import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIRECTORY = Path(__file__).resolve().parent.parent

DATA_DIRECTORY = BASE_DIRECTORY / "data"
RAW_DATA_FILE = DATA_DIRECTORY / "twcs.csv"
PROCESSED_DATA_DIRECTORY = DATA_DIRECTORY / "processed"
CONVERSATION_PAIRS_FILE = PROCESSED_DATA_DIRECTORY / "ba_conversation_pairs.csv"
GOLDEN_SET_FILE = PROCESSED_DATA_DIRECTORY / "golden_set.json"
CHROMA_DATABASE_DIRECTORY = DATA_DIRECTORY / "chroma_db"

PROCESSED_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
CHROMA_DATABASE_DIRECTORY.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

TARGET_BRAND_NAME = "British_Airways"
TARGET_BRAND_TWITTER_HANDLE = "@British_Airways"
