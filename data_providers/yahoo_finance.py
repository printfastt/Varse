"""
Enhanced Yahoo Finance Data Provider for comprehensive stock information
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, Tuple


class YahooFinanceProvider:
    """
    Comprehensive Yahoo Finance data provider that fetches:
    - Historical price data (OHLCV)
    - Real-time quotes
    - Company information and fundamentals
    - Market cap, P/E ratio, 52-week ranges
    - Volume and other key metrics
    - Technical indicators
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        
    def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical stock data (OHLCV)
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'SPY')
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
                
            # Clean up column names if multi-level
            if data.columns.nlevels > 1:
                data.columns = data.columns.droplevel(1)
                
            return data
            
        except Exception as e:
            print(f"Error fetching stock data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive stock information including fundamentals
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with stock information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get current price data
            current_data = self.get_current_price(symbol)
            
            # Extract key metrics
            stock_info = {
                'symbol': symbol.upper(),
                'company_name': info.get('longName', info.get('shortName', symbol)),
                'current_price': current_data.get('current_price', 0),
                'change': current_data.get('change', 0),
                'change_percent': current_data.get('change_percent', 0),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'week_52_high': info.get('fiftyTwoWeekHigh'),
                'week_52_low': info.get('fiftyTwoWeekLow'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'dividend_yield': info.get('dividendYield'),
                'eps_ttm': info.get('trailingEps'),
                'eps_forward': info.get('forwardEps'),
                'book_value': info.get('bookValue'),
                'price_to_book': info.get('priceToBook'),
                'enterprise_value': info.get('enterpriseValue'),
                'ebitda': info.get('ebitda'),
                'revenue': info.get('totalRevenue'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website'),
                'employees': info.get('fullTimeEmployees'),
                'city': info.get('city'),
                'country': info.get('country'),
                'exchange': info.get('exchange'),
                'currency': info.get('currency', 'USD'),
                'previous_close': info.get('previousClose'),
                'open_price': info.get('open'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'beta': info.get('beta'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'float_shares': info.get('floatShares'),
            }
            
            return stock_info
            
        except Exception as e:
            print(f"Error fetching stock info for {symbol}: {e}")
            return self._get_empty_stock_info(symbol)
    
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Get current price and change information
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with current price data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", interval="1d")
            
            if len(hist) >= 2:
                current_price = float(hist['Close'].iloc[-1])
                previous_close = float(hist['Close'].iloc[-2])
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
                
                return {
                    'current_price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'previous_close': previous_close
                }
            else:
                return {'current_price': 0, 'change': 0, 'change_percent': 0, 'previous_close': 0}
                
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
            return {'current_price': 0, 'change': 0, 'change_percent': 0, 'previous_close': 0}
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate technical indicators for stock data
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary of technical indicators
        """
        indicators = {}
        
        if data.empty or 'Close' not in data.columns:
            return indicators
            
        try:
            close = data['Close']
            high = data['High'] if 'High' in data.columns else close
            low = data['Low'] if 'Low' in data.columns else close
            volume = data['Volume'] if 'Volume' in data.columns else pd.Series(index=data.index, data=0)
            
            # Simple Moving Averages
            indicators['SMA_20'] = close.rolling(window=20).mean()
            indicators['SMA_50'] = close.rolling(window=50).mean()
            indicators['SMA_200'] = close.rolling(window=200).mean()
            
            # Exponential Moving Averages
            indicators['EMA_12'] = close.ewm(span=12).mean()
            indicators['EMA_26'] = close.ewm(span=26).mean()
            
            # RSI (Relative Strength Index)
            indicators['RSI'] = self._calculate_rsi(close)
            
            # MACD
            macd_line = indicators['EMA_12'] - indicators['EMA_26']
            signal_line = macd_line.ewm(span=9).mean()
            indicators['MACD'] = macd_line
            indicators['MACD_Signal'] = signal_line
            indicators['MACD_Histogram'] = macd_line - signal_line
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(close)
            indicators.update(bb_data)
            
            # Stochastic Oscillator
            stoch_data = self._calculate_stochastic(high, low, close)
            indicators.update(stoch_data)
            
            # Volume Moving Average
            indicators['Volume_MA'] = volume.rolling(window=20).mean()
            
        except Exception as e:
            print(f"Error calculating technical indicators: {e}")
            
        return indicators
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, close: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        return {
            'BB_Upper': sma + (std * std_dev),
            'BB_Middle': sma,
            'BB_Lower': sma - (std * std_dev)
        }
    
    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                            k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'Stoch_K': k_percent,
            'Stoch_D': d_percent
        }
    
    def format_number(self, value: Optional[float], format_type: str = 'currency') -> str:
        """
        Format numbers for display
        
        Args:
            value: Number to format
            format_type: 'currency', 'percent', 'number', 'large_number'
            
        Returns:
            Formatted string
        """
        if value is None or pd.isna(value):
            return "-"
            
        try:
            if format_type == 'currency':
                return f"${value:,.2f}"
            elif format_type == 'percent':
                return f"{value:.2f}%"
            elif format_type == 'large_number':
                if value >= 1e12:
                    return f"${value/1e12:.2f}T"
                elif value >= 1e9:
                    return f"${value/1e9:.2f}B"
                elif value >= 1e6:
                    return f"${value/1e6:.2f}M"
                elif value >= 1e3:
                    return f"${value/1e3:.2f}K"
                else:
                    return f"${value:.2f}"
            elif format_type == 'volume':
                if value >= 1e9:
                    return f"{value/1e9:.2f}B"
                elif value >= 1e6:
                    return f"{value/1e6:.2f}M"
                elif value >= 1e3:
                    return f"{value/1e3:.2f}K"
                else:
                    return f"{value:,.0f}"
            else:  # number
                return f"{value:,.2f}"
                
        except (ValueError, TypeError):
            return "-"
    
    def _get_empty_stock_info(self, symbol: str) -> Dict[str, Any]:
        """Return empty stock info structure"""
        return {
            'symbol': symbol.upper(),
            'company_name': symbol,
            'current_price': 0,
            'change': 0,
            'change_percent': 0,
            'market_cap': None,
            'pe_ratio': None,
            'forward_pe': None,
            'week_52_high': None,
            'week_52_low': None,
            'volume': None,
            'avg_volume': None,
            'dividend_yield': None,
            'eps_ttm': None,
            'eps_forward': None,
            'book_value': None,
            'price_to_book': None,
            'enterprise_value': None,
            'ebitda': None,
            'revenue': None,
            'sector': None,
            'industry': None,
            'description': '',
            'website': None,
            'employees': None,
            'city': None,
            'country': None,
            'exchange': None,
            'currency': 'USD',
            'previous_close': None,
            'open_price': None,
            'day_high': None,
            'day_low': None,
            'beta': None,
            'shares_outstanding': None,
            'float_shares': None,
        }


# Global instance for easy access
yahoo_provider = YahooFinanceProvider()
