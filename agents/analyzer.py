from typing import Optional
from core.event_bus import Event
from core.llm_utils import get_llm, root_cause_prompt
from core.memory import IncidentMemory

class AnalyzerAgent:
    """Analyzer using RAG over past incidents (FAISS). Falls back to rules if no LLM."""
    def __init__(self, memory: IncidentMemory):
        self.memory = memory
        self.llm = get_llm()

    async def analyze(self, event: Event) -> str:
        # Basic typed heuristics first
        if event.type == "metric.anomaly" and event.payload.get("metric") == "cpu":
            val = event.payload.get("value", 0)
            host = event.payload.get("host", "host")
            rule = (
                f"CPU {val}% on {host}. Likely runaway process. Kill top CPU proc and restart service."
                if val >= 95 else
                f"CPU spike on {host}. Consider throttling heavy jobs or scaling."
            )
        elif event.type == "service.down":
            svc = event.payload.get("service","app")
            rule = f"{svc} is down, likely bad deploy. Attempt restart, check health, consider rollback."
        elif event.type == "api.latency.high":
            svc = event.payload.get("service","api")
            rule = f"{svc} latency high, possible DB lock or upstream slowdown. Inspect slow queries and dependencies."
        elif event.type == "disk.full":
            host = event.payload.get("host","host")
            rule = f"Disk nearly full on {host}. Rotate logs, clear temp, or expand volume."
        else:
            rule = "No clear hypothesis; request human triage."

        # Retrieve similar incidents
        sims = self.memory.search(f"{event.type} {event.payload}", k=3)
        sims_text = "\n".join([f"- {d.page_content}" for d in sims]) if sims else "(none)"

        if self.llm is None:
            # No LLM: return rule enriched with top similar
            return rule + (f" Similar past: {sims[0].page_content}" if sims else "")

        # LLM reasoning with prompt + similar cases
        prompt = root_cause_prompt.format(event=str(event.model_dump()), similar=sims_text)
        rsp = self.llm.invoke(prompt)
        return rsp.content.strip() if hasattr(rsp, "content") else str(rsp)

