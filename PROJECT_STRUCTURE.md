# Project Structure

```
fintech/
├── .env                    # Environment variables (not tracked)
├── .env.example           # Template for environment variables
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
├── pytest.ini            # Pytest configuration
├── README.md             # Project documentation
├── PATHWAY_INTEGRATION.md # Pathway integration guide
├── REALTIME_GUIDE.md     # Real-time data guide
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI application entry point
│   ├── routers/          # API route handlers
│   │   ├── demo.py       # Demo endpoints
│   │   ├── realtime.py   # Real-time data endpoints
│   │   └── trading.py    # Trading endpoints
│   ├── services/         # Business logic services
│   │   ├── __init__.py
│   │   ├── alerts.py     # Alert system
│   │   ├── mock_sources.py # Mock data sources
│   │   ├── pathway_integration.py # Pathway integration
│   │   ├── pathway_pipelines.py # Pathway data pipelines
│   │   ├── realtime_sources.py # Real-time data sources
│   │   ├── state.py      # Application state management
│   │   ├── trading_buddy.py # Trading assistant logic
│   │   ├── trading_buddy_ai.py # AI-powered trading assistant
│   │   └── utils.py      # Utility functions
│   └── web/              # Frontend assets
│       ├── index-new.html # Main HTML template
│       └── static/
│           ├── app-new.js # JavaScript application
│           └── styles-new.css # CSS styles
├── data/                 # Data files
└── tests/               # Test files
    ├── test_anomaly.py  # Anomaly detection tests
    └── test_pathway.py  # Pathway integration tests
```

## Removed Files

The following unnecessary files were removed during cleanup:
- `debug.html` (empty debug file)
- `app/web/static/app.js` (old version, replaced by app-new.js)
- `app/web/static/styles.css` (old version, replaced by styles-new.css)
- `__pycache__/` directories (Python cache files)
- `.pytest_cache/` directory (pytest cache)
- `test_*.py` files in root directory (moved to tests/ or removed if redundant)

## Key Components

- **FastAPI Backend**: Handles API endpoints, WebSocket connections, and business logic
- **Real-time Data**: Multiple data sources (Finnhub, Alpha Vantage, NewsAPI, etc.)
- **Trading System**: Portfolio management and trade execution
- **AI Assistant**: Powered by Gemini AI for trading advice and market analysis
- **Frontend**: Modern HTML/CSS/JS interface with real-time updates
- **Pathway Integration**: Data processing and analytics pipeline
