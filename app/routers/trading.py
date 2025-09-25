from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import Dict, Any
import time
from ..services.state import AppState
from ..services.alerts import AlertBroker

router = APIRouter(prefix="/trading", tags=["trading"])

# Global references (these will be set in main.py)
state: AppState = None
alerts: AlertBroker = None

class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    quantity: float
    price: float = None  # If None, use current market price

class TradeResponse(BaseModel):
    success: bool
    message: str
    transaction_id: str = None
    executed_price: float = None
    portfolio_value: float = None

@router.get("/test")
async def test_trading():
    """Test endpoint to verify trading system is working"""
    return {
        "status": "ok",
        "message": "Trading system is operational",
        "state_initialized": state is not None,
        "alerts_initialized": alerts is not None,
        "symbols": list(state.prices.keys()) if state else []
    }

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """Execute a buy or sell order"""
    if not state:
        raise HTTPException(status_code=500, detail="App state not initialized")
    
    symbol = trade.symbol.upper()
    action = trade.action.lower()
    
    if action not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
    
    if trade.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
    # Get current market price if not provided
    current_price = trade.price or state.prices.get(symbol, 0)

    # If we still don't have a price (e.g. feed hasn't started), fall back to demo defaults
    if current_price <= 0:
        fallback_prices = {
            "TSLA": 400.0,
            "AAPL": 250.0,
            "GOOGL": 250.0,
            "MSFT": 500.0,
            "NVDA": 175.0
        }
        if symbol in fallback_prices:
            current_price = fallback_prices[symbol]
            # Seed state so portfolio valuations aren't zero after first trade
            state.prices[symbol] = current_price
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid price for {symbol} (no market data yet)"
            )
    
    # Initialize portfolio if it doesn't exist
    if not state.portfolio:
        from ..services.state import Portfolio
        state.portfolio = Portfolio(holdings={})
    
    # Calculate transaction
    current_holding = state.portfolio.holdings.get(symbol, 0)
    transaction_id = f"{action}_{symbol}_{int(time.time())}"
    
    try:
        if action == "buy":
            new_holding = current_holding + trade.quantity
            state.portfolio.holdings[symbol] = new_holding
            # Update cash balance
            total_cost = trade.quantity * current_price
            state.portfolio.cash_balance -= total_cost
            message = f"Bought {trade.quantity} shares of {symbol} at ${current_price:.2f}"
        else:  # sell
            if current_holding < trade.quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient shares. You have {current_holding} shares of {symbol}"
                )
            new_holding = current_holding - trade.quantity
            if new_holding == 0:
                del state.portfolio.holdings[symbol]
            else:
                state.portfolio.holdings[symbol] = new_holding
            # Update cash balance
            total_proceeds = trade.quantity * current_price
            state.portfolio.cash_balance += total_proceeds
            message = f"Sold {trade.quantity} shares of {symbol} at ${current_price:.2f}"
        
        # Record transaction
        transaction = {
            "transaction_id": transaction_id,
            "timestamp": time.time(),
            "symbol": symbol,
            "action": action,
            "quantity": trade.quantity,
            "price": current_price,
            "total_value": trade.quantity * current_price
        }
        state.portfolio.transactions.append(transaction)
        
        # Calculate portfolio value
        portfolio_value = sum(
            qty * state.prices.get(sym, 0) 
            for sym, qty in state.portfolio.holdings.items()
        )
        
        # Emit trade event to WebSocket
        await state.emit_market({
            "type": "trade",
            "symbol": symbol,
            "action": action,
            "quantity": trade.quantity,
            "price": current_price,
            "portfolio_value": portfolio_value,
            "ts": time.time()
        })
        
        # Send alert about the trade
        if alerts:
            await alerts.publish({
                "channel": "trading",
                "kind": "trade-executed",
                "symbol": symbol,
                "action": action,
                "quantity": trade.quantity,
                "price": current_price,
                "message": message,
                "ts": time.time()
            })
        
        return TradeResponse(
            success=True,
            message=message,
            transaction_id=transaction_id,
            executed_price=current_price,
            portfolio_value=portfolio_value
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")

@router.get("/portfolio")
async def get_portfolio():
    """Get current portfolio holdings and values with P&L calculations"""
    if not state or not state.portfolio:
        return {
            "holdings": {}, 
            "total_value": 0, 
            "cash_balance": 10000.0,
            "total_portfolio_value": 10000.0,
            "total_pnl": 0.0,
            "total_pnl_percentage": 0.0,
            "daily_pnl": 0.0,
            "daily_pnl_percentage": 0.0,
            "positions": []
        }
    
    positions = []
    total_holdings_value = 0
    total_invested = 0  # Total amount invested in current holdings
    
    for symbol, quantity in state.portfolio.holdings.items():
        current_price = state.prices.get(symbol, 0)
        position_value = quantity * current_price
        total_holdings_value += position_value
        
        # Calculate average cost basis from transactions
        symbol_transactions = [
            t for t in state.portfolio.transactions 
            if t.get('symbol') == symbol
        ]
        
        # Calculate cost basis (simplified - using last purchase price as average)
        avg_cost = current_price  # Default to current price if no transaction history
        total_invested_in_symbol = position_value  # Default
        
        if symbol_transactions:
            total_bought = sum(t['quantity'] for t in symbol_transactions if t['action'] == 'buy')
            total_cost = sum(t['quantity'] * t['price'] for t in symbol_transactions if t['action'] == 'buy')
            if total_bought > 0:
                avg_cost = total_cost / total_bought
                total_invested_in_symbol = quantity * avg_cost
        
        total_invested += total_invested_in_symbol
        
        # Calculate P&L for this position
        position_pnl = position_value - total_invested_in_symbol
        position_pnl_percentage = (position_pnl / total_invested_in_symbol * 100) if total_invested_in_symbol > 0 else 0
        
        positions.append({
            "symbol": symbol,
            "quantity": quantity,
            "current_price": current_price,
            "avg_cost": avg_cost,
            "position_value": position_value,
            "cost_basis": total_invested_in_symbol,
            "pnl": position_pnl,
            "pnl_percentage": position_pnl_percentage,
            "percentage": 0  # Will be calculated after total_value is known
        })
    
    # Calculate percentages of total portfolio
    for position in positions:
        position["percentage"] = (position["position_value"] / total_holdings_value * 100) if total_holdings_value > 0 else 0
    
    # Portfolio totals
    cash_balance = state.portfolio.cash_balance
    total_portfolio_value = total_holdings_value + cash_balance
    starting_cash = 10000.0  # Initial cash balance
    
    # Overall P&L calculations
    total_pnl = total_holdings_value - total_invested
    total_pnl_percentage = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # For daily P&L, we'd need yesterday's prices (simplified for now)
    daily_pnl = 0.0  # TODO: Calculate based on previous day's portfolio value
    daily_pnl_percentage = 0.0  # TODO: Calculate daily percentage change
    
    return {
        "holdings": state.portfolio.holdings,
        "total_value": total_holdings_value,
        "cash_balance": cash_balance,
        "total_portfolio_value": total_portfolio_value,
        "total_invested": total_invested,
        "total_pnl": total_pnl,
        "total_pnl_percentage": total_pnl_percentage,
        "daily_pnl": daily_pnl,
        "daily_pnl_percentage": daily_pnl_percentage,
        "positions": positions
    }

@router.get("/transactions")
async def get_transaction_history():
    """Get recent transaction history"""
    if not state or not state.portfolio:
        return {"transactions": []}
    
    # Get last 10 transactions
    recent_transactions = state.portfolio.transactions[-10:] if state.portfolio.transactions else []
    
    # Format transactions for display
    formatted_transactions = []
    for transaction in recent_transactions:
        formatted_transactions.append({
            "transaction_id": transaction.get("transaction_id", ""),
            "timestamp": transaction.get("timestamp", 0),
            "symbol": transaction.get("symbol", ""),
            "action": transaction.get("action", ""),
            "quantity": transaction.get("quantity", 0),
            "price": transaction.get("price", 0),
            "total_value": transaction.get("total_value", 0),
            "date": time.strftime("%m/%d %H:%M", time.localtime(transaction.get("timestamp", 0)))
        })
    
    return {"transactions": formatted_transactions}

@router.get("/market-data/{symbol}")
async def get_market_data(symbol: str):
    """Get current market data for a symbol"""
    symbol = symbol.upper()
    
    if not state:
        raise HTTPException(status_code=500, detail="App state not initialized")
    
    price = state.prices.get(symbol, 0)
    if price == 0:
        raise HTTPException(status_code=404, detail=f"No price data available for {symbol}")
    
    # Get recent price history
    price_history = state.price_history.get(symbol, [])
    recent_prices = price_history[-20:] if len(price_history) > 20 else price_history
    
    # Calculate basic stats
    change_24h = 0
    if len(recent_prices) > 1:
        old_price = recent_prices[0].price
        change_24h = ((price - old_price) / old_price * 100) if old_price > 0 else 0
    
    return {
        "symbol": symbol,
        "current_price": price,
        "change_24h": change_24h,
        "price_history": [{"ts": p.ts, "price": p.price} for p in recent_prices],
        "volume": 0,  # Mock volume for now
        "market_cap": 0  # Mock market cap for now
    }

@router.post("/quick-trade")
async def quick_trade(
    symbol: str = Form(...),
    action: str = Form(...),
    amount: str = Form(...)  # Can be quantity or dollar amount
):
    """Quick trade endpoint for simple buy/sell operations"""
    symbol = symbol.upper()
    action = action.lower()
    
    current_price = state.prices.get(symbol, 0)
    if current_price <= 0:
        raise HTTPException(status_code=400, detail=f"Invalid price for {symbol}")
    
    try:
        # Parse amount - could be shares or dollar amount
        if amount.startswith("$"):
            # Dollar amount - calculate shares
            dollar_amount = float(amount[1:])
            quantity = dollar_amount / current_price
        else:
            # Share quantity
            quantity = float(amount)
        
        trade_request = TradeRequest(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=current_price
        )
        
        return await execute_trade(trade_request)
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amount format")
