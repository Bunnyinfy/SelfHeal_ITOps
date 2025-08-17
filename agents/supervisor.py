import time, json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import os
from core.event_bus import Event, EventBus
from core.memory import IncidentMemory

class Incident(BaseModel):
    id: str = Field(default_factory=lambda: f"inc_{int(time.time()*1000)}")
    status: str = "open"  # open | mitigating | resolved | failed
    event: Event
    hypothesis: Optional[str] = None
    remediation_attempts: int = 0
    actions: List[Dict[str, Any]] = []
    notes: List[str] = []
    opened_at: float = Field(default_factory=time.time)
    closed_at: Optional[float] = None

class SupervisorAgent:
    def __init__(self, bus: EventBus, analyzer, fixer, memory: IncidentMemory):
        self.bus = bus
        self.analyzer = analyzer
        self.fixer = fixer
        self.memory = memory
        self.incidents: Dict[str, Incident] = {}

    async def run(self):
        async for evt in self.bus.subscribe():
            inc = Incident(event=evt)
            self.incidents[inc.id] = inc
            self._log({"stage": "incident_opened", "incident": inc.model_dump()})
            import asyncio
            asyncio.create_task(self._mitigate(inc.id))

    async def _mitigate(self, inc_id: str):
        import asyncio, random
        inc = self.incidents[inc_id]
        inc.status = "mitigating"

        # 1) Analyze
        hypothesis = await self.analyzer.analyze(inc.event)
        inc.hypothesis = hypothesis
        inc.notes.append(f"Hypothesis: {hypothesis}")
        self._log({"stage": "analyzed", "incident_id": inc.id, "hypothesis": hypothesis})

        # 2) Up to 2 remediation attempts
        for attempt in range(1, 3):
            inc.remediation_attempts = attempt
            result = await self.fixer.execute(inc)
            inc.actions.extend(result["actions"])
            self._log({"stage": "remediation_attempt", "attempt": attempt, "incident_id": inc.id, "result": result})

            # 3) Verify
            ok = await self._verify(inc)
            if ok:
                inc.status = "resolved"
                inc.closed_at = time.time()
                inc.notes.append("Resolution verified.")
                self._log({"stage": "resolved", "incident_id": inc.id})
                # Persist to memory store for future retrieval
                self.memory.add_incident(
                    summary=f"{inc.event.type} on {inc.event.payload} → resolved via { [a['action'] for a in inc.actions] }",
                    meta={"hypothesis": inc.hypothesis, "actions": inc.actions, "ts": time.time()}
                )
                return
            else:
                inc.notes.append(f"Attempt {attempt} failed; retrying…")

        # 4) Escalate
        inc.status = "failed"
        inc.closed_at = time.time()
        inc.notes.append("Escalated to human on-call.")
        self._log({"stage": "escalated", "incident_id": inc.id})

    async def _verify(self, inc: Incident) -> bool:
        import asyncio, random
        evt = inc.event
        await asyncio.sleep(0.4)
        if evt.type == "service.down":
            return any(a["action"] == "restart_service" and a["ok"] for a in inc.actions)
        if evt.type == "metric.anomaly" and evt.payload.get("metric") == "cpu":
            return random.random() < 0.7
        if evt.type == "disk.full":
            return any(a["action"] == "clear_temp_logs" and a["ok"] for a in inc.actions)
        if evt.type == "api.latency.high":
            return random.random() < 0.6
        return False

    def list_incidents(self) -> List[Incident]:
        return sorted(self.incidents.values(), key=lambda x: x.opened_at, reverse=True)

    # def _log(self, record: Dict[str, Any]):
    #     path = os.environ.get("INCIDENT_LOG_PATH", "./data/incident_logs.jsonl")
    #     import os, json, time
    #     os.makedirs(os.path.dirname(path), exist_ok=True)
    #     with open(path, "a", encoding="utf-8") as f:
    #         f.write(json.dumps({"ts": time.time(), **record})+"\n")
    def _log(self, record: Dict[str, Any]):
        path = os.environ.get("INCIDENT_LOG_PATH", "./data/incident_logs.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **record}) + "\n")

