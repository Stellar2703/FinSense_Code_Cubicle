import asyncio
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

@dataclass
class PricePoint:
    ts: float
    price: float

@dataclass
class NewsItem:
    ts: float
    symbol: Optional[str]
    headline: str
    sentiment: str  # 'positive' | 'neutral' | 'negative'

@dataclass
class Portfolio:
    holdings: Dict[str, float]  # symbol -> quantity
    cash_balance: float = 10000.0  # Starting cash balance
    transactions: List[Dict[str, Any]] = field(default_factory=list)  # Transaction history

@dataclass
class TradeTransaction:
    timestamp: float
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: float
    price: float
    total_value: float
    transaction_id: str

class AppState:
    def __init__(self) -> None:
        # Symbols & market data
        self.symbols: List[str] = self._init_symbols()
        self.prices: Dict[str, float] = {s: 0.0 for s in self.symbols}
        self.price_history: Dict[str, List[PricePoint]] = {s: [] for s in self.symbols}
        self.news: List[NewsItem] = []

        # Portfolio & sanctions
        self.portfolio: Optional[Portfolio] = None
        self.sanctions: Dict[str, float] = {}  # name -> ts_added

        # Queues for WS streaming
        self.market_ws_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=1000)

        # Fraud / behavior tracking
        self.customer_baseline: Dict[str, Dict[str, float]] = {}  # id -> {avg, count}
        self.payments: List[Dict[str, Any]] = []  # recent payment events
        self.customer_history: Dict[str, List[float]] = {}  # rolling amounts per customer

    def _init_symbols(self) -> List[str]:
        import os
        sym = os.getenv("SYMBOLS", "TSLA,AAPL").split(",")
        return [s.strip().upper() for s in sym if s.strip()]

    async def emit_market(self, payload: Dict[str, Any]) -> None:
        # drop oldest if full
        try:
            self.market_ws_queue.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                _ = self.market_ws_queue.get_nowait()
            except Exception:
                pass
            await self.market_ws_queue.put(payload)

    async def load_portfolio_json(self, content: bytes) -> None:
        obj = json.loads(content.decode("utf-8"))
        # Accept either {"AAPL": 10, "TSLA": 5} or {"holdings": {...}}
        if isinstance(obj, dict) and "holdings" in obj:
            holdings = obj["holdings"]
        else:
            holdings = obj
        if not isinstance(holdings, dict):
            raise ValueError("Invalid portfolio JSON")
        self.portfolio = Portfolio(holdings={k.upper(): float(v) for k, v in holdings.items()})

    @staticmethod
    def now_ts() -> float:
        return datetime.now(timezone.utc).timestamp()
