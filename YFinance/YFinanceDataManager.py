import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional, Tuple


class YFinanceDataManager:
    """
    manages data fetching from yfinance.
    """
    
    def __init__(self):
        self.timeframe_intervals = {
            "1d": "1m",
            "5d": "5m",
            "1mo": "1h",
            "3mo": "1h",
            "1y": "1d",
            "2y": "1d",
            "5y": "1wk",
            "max": "1wk",
        }
    
    def get_symbol_data(self, symbol: str, period: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """
        purpose: fetch historical price data, ticker info for symbol input
        
        arguments:
            symbol: Stock symbol (STR)
            period: Time period for historical data (STR)
                ex: 1d, 1mo, 1y, 5y, max
                defined in self.timeframe_intervals
        returns:
            tuple: (price_data, ticker_info) or (None, None) in error case.
        
        note: learned Optional is from typing module; union type of None and other type.
        """

        try:
            #translation from ui to yfinance interval
            interval = self.timeframe_intervals.get(period, "1d")
            
            symbol_data = yf.download(symbol, period=period, interval=interval)
            
            if symbol_data.empty:
                return None, None
                
            # drop na's from the close prices
            symbol_closes = symbol_data[['Close']].dropna()
            if 'Ticker' in symbol_closes.columns.names:
                #drop irrelevant ticker column
                symbol_closes.columns = symbol_closes.columns.droplevel('Ticker')
            
            # fetch ticker info
            ticker = yf.Ticker(symbol)
            ticker_info = self._get_ticker_info(ticker)
            
            return symbol_closes, ticker_info
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None, None
    
    def _get_ticker_info(self, ticker: yf.Ticker) -> Dict[str, Any]:
        """
        purpose: get relevant ticker information safely
        arguments:
            ticker: yfinance ticker object
        returns:
            dict w/ the relevant ticker information
        note: learned Dict[str, Any] return can be key str and value any
        """
        try:
            info = ticker.info
            
            return {
                'open': self._safe_get_info(info, 'open', 0),
                'dayHigh': self._safe_get_info(info, 'dayHigh', 0),
                'dayLow': self._safe_get_info(info, 'dayLow', 0),
                'marketCap': self._safe_get_info(info, 'marketCap', 0),
                'fiftyTwoWeekLow': self._safe_get_info(info, 'fiftyTwoWeekLow', 0),
                'fiftyTwoWeekHigh': self._safe_get_info(info, 'fiftyTwoWeekHigh', 0)
            }
        except Exception as e:
            print(f"Error getting ticker info: {e}")
            return {
                'open': 0,
                'dayHigh': 0,
                'dayLow': 0,
                'marketCap': 0,
                'fiftyTwoWeekLow': 0,
                'fiftyTwoWeekHigh': 0
            }
    
    def _safe_get_info(self, ticker_info: Dict, key: str, default: Any = "N/A") -> Any:
        """
        purpose: prevent key errors when getting info from ticker_info dict
        arguments:
            ticker_info: dict containing ticker information
            key: keyto retrieve
            default: default value if key not found or None
        returns:
            value from ticker_info or default
        """
        try:
            value = ticker_info.get(key, default)
            return value if value is not None else default
        except:
            return default
    
    def format_large_number(self, num: float) -> str:
        """
        purpose: format large numbers for market cap display
        arguments:
            num: number to format
        returns:
            formatted string 
        """
        if num is None or num == 0:
            return "N/A"
        if abs(num) >= 1e12:
            return f"{num/1e12:.1f}T"
        elif abs(num) >= 1e9:
            return f"{num/1e9:.1f}B"
        elif abs(num) >= 1e6:
            return f"{num/1e6:.0f}M"
        else:
            return f"{num:.2f}"
    
    def create_chart_title(self, symbol: str, ticker_info: Dict[str, Any]) -> str:
        """
        purpose: create a formatted chart title with ticker information.
        arguments:
            symbol: stock symbol
            ticker_info: dict containing ticker information
        returns:
            formatted title string
        """
        open_price = ticker_info['open']
        day_high = ticker_info['dayHigh']
        day_low = ticker_info['dayLow']
        market_cap = ticker_info['marketCap']
        week52_low = ticker_info['fiftyTwoWeekLow']
        week52_high = ticker_info['fiftyTwoWeekHigh']
        
        return (f"{symbol} |  Open:{open_price:.2f}  High:{day_high:.2f}  Low:{day_low:.2f} "
                f" CAP:{self.format_large_number(market_cap)}  52L:{week52_low:.2f}  52H:{week52_high:.2f}")
