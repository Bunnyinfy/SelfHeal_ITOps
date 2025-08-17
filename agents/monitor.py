import random, asyncio, time
from core.event_bus import Event, EventBus

class MonitorAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.running = False

    async def start_synthetic_metrics(self, interval_s: int = 5):
        self.running = True
        while self.running:
            if random.random() < 0.35:
                evt = Event(type="metric.anomaly", source="monitor.cpu", payload={"host": "app-1", "metric": "cpu", "value": random.randint(90,100)})
                await self.bus.publish(evt)
            await asyncio.sleep(interval_s)

    async def stop(self):
        self.running = False