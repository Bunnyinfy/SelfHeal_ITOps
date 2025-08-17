from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
import asyncio, time, os, json
from datetime import datetime, timezone

from core.event_bus import Event, EventBus
from agents.monitor import MonitorAgent
from agents.analyzer import AnalyzerAgent
from agents.fixer import FixerAgent
from agents.supervisor import SupervisorAgent, Incident
from core.memory import IncidentMemory

app = FastAPI(title="Self-Healing ITOps Agents (LangChain + FAISS)")

# Global singletons
BUS = EventBus()
MEM = IncidentMemory()
ANALYZER = AnalyzerAgent(memory=MEM)
FIXER = FixerAgent()
SUP = SupervisorAgent(bus=BUS, analyzer=ANALYZER, fixer=FIXER, memory=MEM)
MON = MonitorAgent(bus=BUS)

@app.on_event("startup")
async def on_startup():
    # Ensure memory store is initialized
    MEM.init()
    # Start supervisor stream and synthetic monitor
    asyncio.create_task(SUP.run())
    asyncio.create_task(MON.start_synthetic_metrics(interval_s=4))

@app.on_event("shutdown")
async def on_shutdown():
    await MON.stop()

# class PublishEventIn(BaseModel):
#     type: Event.type
#     source: str = "external"
#     payload: Dict[str, Any] = {}
class PublishEventIn(BaseModel):
    type: str
    source: str = "external"
    payload: Dict[str, Any] = {}

@app.post("/events/publish", response_model=Event)
async def publish_event(body: PublishEventIn):
    evt = Event(type=body.type, source=body.source, payload=body.payload)
    await BUS.publish(evt)
    return evt

@app.get("/incidents", response_model=List[Incident])
async def list_incidents():
    return SUP.list_incidents()

@app.post("/simulate/high_cpu", response_model=Event)
async def simulate_high_cpu(host: str = Body("app-1"), value: int = Body(97)):
    evt = Event(type="metric.anomaly", source="simulate", payload={"host": host, "metric": "cpu", "value": value})
    await BUS.publish(evt)
    return evt

@app.post("/simulate/service_down", response_model=Event)
async def simulate_service_down(service: str = Body("payments-api")):
    evt = Event(type="service.down", source="simulate", payload={"service": service})
    await BUS.publish(evt)
    return evt

@app.post("/simulate/api_latency", response_model=Event)
async def simulate_api_latency(service: str = Body("orders-api"), p95_ms: int = Body(1200)):
    evt = Event(type="api.latency.high", source="simulate", payload={"service": service, "p95_ms": p95_ms})
    await BUS.publish(evt)
    return evt

@app.post("/simulate/disk_full", response_model=Event)
async def simulate_disk_full(host: str = Body("db-1"), used_pct: int = Body(92)):
    evt = Event(type="disk.full", source="simulate", payload={"host": host, "used_pct": used_pct})
    await BUS.publish(evt)
    return evt

@app.get("/logs/tail")
async def tail_logs(n: int = 50):
    try:
        with open(os.environ.get("INCIDENT_LOG_PATH", "./data/incident_logs.jsonl"), "r", encoding="utf-8") as f:
            return [json.loads(x) for x in f.readlines()[-n:]]
    except FileNotFoundError:
        return []

@app.get("/health")
async def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

# ─────────────────────────────────────────────────────────────────────────────
# FILE: core/event_bus.py
# ─────────────────────────────────────────────────────────────────────────────
import asyncio, time, random
from pydantic import BaseModel, Field
from typing import Any, Dict, Literal

class Event(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{int(time.time()*1000)}_{random.randint(1000,9999)}")
    type: Literal["metric.anomaly","service.down","api.latency.high","disk.full","custom.alert"]
    source: str = "simulator"
    payload: Dict[str, Any] = {}
    ts: float = Field(default_factory=lambda: time.time())

class EventBus:
    def __init__(self):
        self.queue: asyncio.Queue[Event] = asyncio.Queue()

    async def publish(self, event: Event):
        await self.queue.put(event)

    async def subscribe(self):
        while True:
            evt = await self.queue.get()
            yield evt

# ─────────────────────────────────────────────────────────────────────────────
# FILE: core/memory.py
# ─────────────────────────────────────────────────────────────────────────────
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
