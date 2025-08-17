import os, json, time
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

VECTOR_DIR = os.environ.get("VECTOR_DIR", "./data/vector_store")
LOG_PATH = os.environ.get("INCIDENT_LOG_PATH", "./data/incident_logs.jsonl")

class IncidentMemory:
    def __init__(self):
        self.embeddings = None
        self.store: Optional[FAISS] = None
        self.vector_dir = Path(VECTOR_DIR)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

    def init(self):
        # Load local embedding model (no API key required)
        if self.embeddings is None:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        # Load/create FAISS index
        index_path = self.vector_dir / "index.faiss"
        store_path = self.vector_dir / "index.pkl"
        if index_path.exists() and store_path.exists():
            self.store = FAISS.load_local(str(self.vector_dir), self.embeddings, allow_dangerous_deserialization=True)
        else:
            # bootstrap with a few seeds
            texts = [
                "High CPU on service fixed by killing runaway process and restarting service",
                "Service down after deploy fixed by rollback",
                "API latency due to DB lock mitigated by clearing long-running queries",
                "Disk almost full mitigated by log rotation and cleanup"
            ]
            self.store = FAISS.from_texts(texts=texts, embedding=self.embeddings)
            self.store.save_local(str(self.vector_dir))

    def add_incident(self, summary: str, meta: Dict[str, Any]):
        if not self.store:
            self.init()
        self.store.add_texts([summary], metadatas=[meta])
        self.store.save_local(str(self.vector_dir))
        # Also append to JSONL for auditability
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "summary": summary, "meta": meta})+"\n")

    def search(self, query: str, k: int = 3):
        if not self.store:
            self.init()
        return self.store.similarity_search(query, k=k)
