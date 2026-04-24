import yfinance as yf
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

def fetch_stock_data(ticker: str) -> Optional[Dict[str, float]]:
    """
    Fetches the latest stock data for a given ticker using yfinance.
    For Japanese stocks, ensure the ticker has the '.T' suffix (e.g., '7203.T').
    """
    # Append .T for Japanese 4-digit tickers if not already present
    if ticker.isdigit() and len(ticker) == 4:
        ticker = f"{ticker}.T"
        
    try:
        stock = yf.Ticker(ticker)
        # Fetch data for the last 5 days to ensure we have the latest trading day
        hist = stock.history(period="5d")
        if hist.empty:
            logger.warning(f"No stock data found for ticker: {ticker}")
            return None
        
        latest_data = hist.iloc[-1]
        prev_data = hist.iloc[-2] if len(hist) > 1 else latest_data
        
        current_price = latest_data["Close"]
        prev_price = prev_data["Close"]
        change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0

        return {
            "ticker": ticker,
            "current_price": float(current_price),
            "previous_close": float(prev_price),
            "change_percent": float(change_pct),
        }
    except Exception as e:
        logger.error(f"Error fetching stock data for {ticker}: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(fetch_stock_data("7203")) # Toyota
    print(fetch_stock_data("AAPL")) # Apple
