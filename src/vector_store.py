
import csv
from pathlib import Path
from typing import List, Optional
from src.config import (
    CHROMA_DATABASE_DIRECTORY, 
    CONVERSATION_PAIRS_FILE, 
    PROCESSED_DATA_DIRECTORY
)
from src.schemas import HistoricalResolution
from src.embeddings import EmbeddingService

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class ResolutionVectorStore:

    def __init__(
        self, 
        storage_path: Path = CHROMA_DATABASE_DIRECTORY, 
        collection_name: str = "ba_resolutions"
    ):
        self.storage_path = storage_path
        self.collection_name = collection_name
        self.embedding_service = EmbeddingService()
        self.collection = None
        self.client = None

        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=str(self.storage_path))
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "British Airways historical resolved customer tweets"}
                )
            except Exception as error:
                print(f"[WARNING] Could not initialize persistent ChromaDB: {error}")

    def is_ready(self) -> bool:
        return self.collection is not None

    def count_indexed_records(self) -> int:
        if self.collection:
            return self.collection.count()
        return 0

    def index_historical_conversations(
        self, 
        pairs_csv_path: Path = CONVERSATION_PAIRS_FILE, 
        max_records: int = 2000
    ) -> int:
        if not self.is_ready():
            print("[ERROR] Vector store is not initialized.")
            return 0

        current_count = self.count_indexed_records()
        if current_count >= max_records:
            print(f"[INFO] Vector store already contains {current_count} indexed records. Skipping re-indexing.")
            return current_count

        if not pairs_csv_path.exists():
            print(f"[ERROR] Conversation pairs file not found: {pairs_csv_path}")
            return 0

        print(f"--> Indexing up to {max_records} historical resolutions into ChromaDB...")

        documents = []
        metadatas = []
        ids = []

        with open(pairs_csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader):
                if index >= max_records:
                    break

                cust_text = row.get("customer_text", "").strip()
                agent_reply = row.get("agent_reply", "").strip()
                agent_id = row.get("agent_tweet_id", f"BA-{index}")

                if len(cust_text) >= 15 and len(agent_reply) >= 15:
                    documents.append(cust_text)
                    metadatas.append({
                        "agent_reply": agent_reply,
                        "customer_text": cust_text,
                        "agent_tweet_id": agent_id
                    })
                    ids.append(f"doc_{agent_id}_{index}")

        batch_size = 250
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            gemini_embeddings = self.embedding_service.embed_texts(batch_docs)

            if gemini_embeddings and len(gemini_embeddings) == len(batch_docs):
                self.collection.upsert(
                    documents=batch_docs,
                    embeddings=gemini_embeddings,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
            else:
                self.collection.upsert(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )

        total = self.count_indexed_records()
        print(f"[SUCCESS] Vector store now contains {total} indexed British Airways resolutions.")
        return total

    def search_similar_resolutions(
        self, 
        query_text: str, 
        top_k: int = 3
    ) -> List[HistoricalResolution]:
        if not self.is_ready() or self.count_indexed_records() == 0:
            return []

        try:
            try:
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=top_k
                )
            except Exception:
                query_embedding = self.embedding_service.embed_single_text(query_text)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )

            resolutions: List[HistoricalResolution] = []
            
            if results and results.get("documents") and results["documents"][0]:
                for idx in range(len(results["documents"][0])):
                    doc_text = results["documents"][0][idx]
                    metadata = results["metadatas"][0][idx]
                    doc_id = results["ids"][0][idx]
                    distance = results["distances"][0][idx] if "distances" in results and results["distances"] else None
                    relevance = max(0.0, 1.0 - (distance / 2.0)) if distance is not None else 0.85

                    resolutions.append(HistoricalResolution(
                        tweet_id=doc_id,
                        customer_issue=doc_text,
                        agent_solution=metadata.get("agent_reply", ""),
                        relevance_score=round(relevance, 3)
                    ))

            return resolutions

        except Exception as error:
            print(f"[WARNING] Vector retrieval error: {error}")
            return []
