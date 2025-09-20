import asyncio
from typing import Dict, Any

class AlertBroker:
    def __init__(self) -> None:
        self.ws_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=1000)

    async def publish(self, alert: Dict[str, Any]) -> None:
        try:
            self.ws_queue.put_nowait(alert)
        except asyncio.QueueFull:
            # drop oldest by getting one and then putting the new one
            try:
                _ = self.ws_queue.get_nowait()
            except Exception:
                pass
            await self.ws_queue.put(alert)
