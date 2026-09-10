"""
Knowledge Base Indexer for British Airways Historical Resolutions.

Embeds and indexes real historical British Airways resolutions from 
data/processed/ba_conversation_pairs.csv into ChromaDB for semantic RAG retrieval.
"""

from src.vector_store import ResolutionVectorStore
from src.config import CONVERSATION_PAIRS_FILE


def run_indexing(max_records: int = 1500):
    print("--> Initializing Vector Store...")
    vector_store = ResolutionVectorStore()
    
    current_count = vector_store.count_indexed_records()
    print(f"    Current records in vector store: {current_count}")
    
    if current_count < max_records:
        indexed = vector_store.index_historical_conversations(
            pairs_csv_path=CONVERSATION_PAIRS_FILE,
            max_records=max_records
        )
        print(f"--> Indexing completed. Total records: {indexed}")
    else:
        print(f"--> Vector store already has sufficient records ({current_count}). Ready to serve.")


if __name__ == "__main__":
    run_indexing()
