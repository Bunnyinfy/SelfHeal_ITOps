import asyncio, random
from typing import Dict, Any
from agents.supervisor import Incident

class FixerAgent:
    async def execute(self, incident: Incident) -> Dict[str, Any]:
        evt = incident.event
        hypo = (incident.hypothesis or "").lower()
        actions = []

        def add(name, ok, details):
            actions.append({"action": name, "ok": ok, "details": details})

        try:
            if "restart" in hypo or evt.type == "service.down":
                ok = await self._restart_service(evt.payload.get("service","app"))
                add("restart_service", ok, {"service": evt.payload.get("service","app")})
            elif evt.type == "metric.anomaly" and evt.payload.get("metric") == "cpu":
                ok = await self._kill_top_process(evt.payload.get("host","app-1"))
                add("kill_top_process", ok, {"host": evt.payload.get("host","app-1")})
            elif evt.type == "disk.full":
                ok = await self._clear_temp_logs(evt.payload.get("host","app-1"))
                add("clear_temp_logs", ok, {"host": evt.payload.get("host","app-1")})
            else:
                ok = await self._check_health(evt.payload.get("service","app"))
                add("check_health", ok, {})
        except Exception as e:
            add("exception", False, {"error": str(e)})

        return {"actions": actions, "all_ok": all(a["ok"] for a in actions) if actions else False}

    async def _restart_service(self, service: str) -> bool:
        await asyncio.sleep(0.4)
        return True

    async def _kill_top_process(self, host: str) -> bool:
        await asyncio.sleep(0.4)
        return random.random() < 0.8

    async def _clear_temp_logs(self, host: str) -> bool:
        await asyncio.sleep(0.4)
        return True

    async def _check_health(self, service: str) -> bool:
        await asyncio.sleep(0.2)
        return True