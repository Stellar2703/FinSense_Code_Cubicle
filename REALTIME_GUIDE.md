# Real-Time Data Integration Guide

## Overview
FinSense AI can ingest real-time market data, news, and payment streams through:
1. **API Integration**: Connect to market data providers (Alpha Vantage, Finnhub, Polygon.io)
2. **HTTP Webhooks**: Receive data via POST endpoints
3. **Manual Ingestion**: Push data programmatically

## Setup

### 1. Install Dependencies
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set:

```env
# Enable real-time mode
REALTIME=1

# Market data (choose one or more)
ALPHA_VANTAGE_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here

# News
NEWS_API_KEY=your_key_here

# Webhook security
REALTIME_WEBHOOK_TOKEN=your_secret_token
```

### 3. Get API Keys

**Alpha Vantage** (Free tier: 5 calls/min, 500 calls/day)
- Sign up: https://www.alphavantage.co/support/#api-key
- Good for: Basic stock quotes

**Finnhub** (Free tier: 60 calls/min)
- Sign up: https://finnhub.io/register
- Good for: Real-time prices + WebSocket + news

**Polygon.io** (Free tier: 5 calls/min)
- Sign up: https://polygon.io/
- Good for: High-quality market data

**NewsAPI** (Free tier: 1000 requests/day)
- Sign up: https://newsapi.org/register
- Good for: Financial news headlines

## Usage

### Start with Real-Time Feeds
```powershell
# Set environment
$env:REALTIME = "1"
$env:FINNHUB_API_KEY = "your_key"

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### HTTP Webhook Endpoints

**Price Data**
```bash
curl -X POST http://127.0.0.1:8000/api/realtime/price \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "price": 245.67,
    "timestamp": 1695123456.789
  }' \
  -G -d token=your_secret_token
```

**News Data**
```bash
curl -X POST http://127.0.0.1:8000/api/realtime/news \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "headline": "Apple announces new iPhone with breakthrough AI features",
    "timestamp": 1695123456.789
  }' \
  -G -d token=your_secret_token
```

**Payment Data**
```bash
curl -X POST http://127.0.0.1:8000/api/realtime/payment \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "amount": 50000.0,
    "recipient": "Suspicious Entity Ltd",
    "timestamp": 1695123456.789
  }' \
  -G -d token=your_secret_token
```

### Check Status
```bash
curl http://127.0.0.1:8000/api/realtime/status
```

## Integration Examples

### Python Script to Push Data
```python
import requests
import time

def push_price(symbol, price):
    response = requests.post(
        "http://127.0.0.1:8000/api/realtime/price",
        json={"symbol": symbol, "price": price},
        params={"token": "your_secret_token"}
    )
    return response.json()

# Example usage
while True:
    # Get price from your data source
    current_price = get_live_price("TSLA")  # Your function
    push_price("TSLA", current_price)
    time.sleep(1)
```

### Webhook Integration (Flask Example)
```python
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/market_webhook', methods=['POST'])
def handle_market_data():
    data = request.json
    # Forward to FinSense AI
    requests.post(
        "http://127.0.0.1:8000/api/realtime/price",
        json={
            "symbol": data['symbol'],
            "price": data['price']
        },
        params={"token": "your_secret_token"}
    )
    return "OK"

if __name__ == '__main__':
    app.run(port=5000)
```

### JavaScript/Node.js Integration
```javascript
const axios = require('axios');

async function pushNews(symbol, headline) {
    try {
        const response = await axios.post(
            'http://127.0.0.1:8000/api/realtime/news',
            { symbol, headline },
            { params: { token: 'your_secret_token' } }
        );
        console.log('News pushed:', response.data);
    } catch (error) {
        console.error('Error:', error.response.data);
    }
}

// Example usage
pushNews('AAPL', 'Apple beats earnings expectations');
```

## Switching Between Mock and Real-Time

**Use Mock Data (default)**
```powershell
$env:REALTIME = "0"  # or unset
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Use Real-Time Data**
```powershell
$env:REALTIME = "1"
$env:FINNHUB_API_KEY = "your_key"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Data Pipeline Flow

1. **Real-time Sources** → API calls/WebSockets/HTTP webhooks
2. **Ingestion Layer** → `realtime_sources.py` + `/api/realtime/*` endpoints
3. **Processing** → Sentiment analysis, anomaly detection, portfolio impact
4. **State Management** → `AppState` holds current prices, news, baselines
5. **Streaming** → WebSocket channels (`/ws/market`, `/ws/alerts`)
6. **Frontend** → Live updates via WebSocket connections

## Troubleshooting

**"realtime_sources could not be resolved"**
- Restart your language server/IDE after creating the file

**API Rate Limits**
- Free tiers have limits; the code includes delays and error handling
- Consider upgrading to paid plans for production use

**WebSocket Disconnections**
- Real-time feeds include reconnection logic
- Check your firewall/proxy settings

**Missing Price Updates**
- Verify API keys are correct
- Check console logs for API errors
- Some symbols may not be available on all providers

## Production Considerations

1. **Error Handling**: Add robust retry logic and monitoring
2. **Rate Limiting**: Implement proper request throttling
3. **Data Validation**: Add schema validation for incoming data
4. **Security**: Use proper authentication and input sanitization
5. **Persistence**: Add database storage for historical data
6. **Monitoring**: Add logging and metrics collection
7. **Scaling**: Consider message queues (Redis, RabbitMQ) for high-volume streams
