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
