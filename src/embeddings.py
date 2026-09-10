"""
Embedding Generation for British Airways Customer Inquiries and Resolutions.

Uses Google Gemini's text-embedding-004 when GEMINI_API_KEY is available,
with an automatic, fast local fallback using Chroma's default sentence embeddings
so the pipeline is guaranteed to run even if API keys or rate limits occur.
"""

from typing import List
import os
from src.config import GEMINI_API_KEY, DEFAULT_EMBEDDING_MODEL

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class EmbeddingService:
    """Provides vector embeddings for customer queries and historical resolutions."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as error:
                print(f"[WARNING] Could not initialize Gemini Client: {error}. Using local embeddings.")

    @property
    def is_gemini_active(self) -> bool:
        """Returns True if Gemini API client is ready to use."""
        return self.client is not None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a list of strings.
        If Gemini API is configured, uses text-embedding-004.
        Otherwise, returns empty list so ChromaDB uses its built-in local embeddings.
        """
        if not texts:
            return []

        if self.is_gemini_active:
            try:
                embeddings = []
                batch_size = 20
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = self.client.models.embed_content(
                        model=self.model_name,
                        contents=batch,
                    )
                    for item in response.embeddings:
                        embeddings.append(item.values)
                return embeddings
            except Exception as error:
                print(f"[WARNING] Gemini embedding API error: {error}. Falling back to local embeddings.")
                self.client = None
                return []
        
        return []

    def embed_single_text(self, text: str) -> List[float]:
        """Generates embedding for a single string query."""
        results = self.embed_texts([text])
        if results:
            return results[0]
        return []
