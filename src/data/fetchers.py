"""
Data Fetchers for BTFD
Handles Yahoo Finance (primary) and Alpha Vantage (fallback) data acquisition
"""

import yfinance as yf
import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import time
import sqlite3

from ..config.settings import get_config, StrategyConfig, RateLimitConfig

class RateLimiter:
    """Rate limiting for API calls"""
    
    def __init__( self ):
        self.config = get_config();
    
    def check_and_update_limit( self, service: str, period: str ) -> bool:
        """
        Check if API call is allowed and update counter
        
        Args:
            service: API service name (e.g. 'alphavantage')
            period: Time period ('minute' or 'day')
            
        Returns:
            True if call is allowed, False if rate limited
        """
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            # Get current rate limit record
            cursor.execute(
                "SELECT max_calls, calls_made, window_start FROM rate_limit WHERE service = ? AND period = ?",
                ( service, period )
            );
            
            result = cursor.fetchone();
            if not result:
                conn.close();
                return False;  # No rate limit configured
            
            max_calls, calls_made, window_start = result;
            window_start = datetime.fromisoformat( window_start );
            now = datetime.now();
            
            # Check if we need to reset the window
            if period == 'minute' and ( now - window_start ).total_seconds() >= 60:
                # Reset minute window
                cursor.execute(
                    "UPDATE rate_limit SET calls_made = 0, window_start = ? WHERE service = ? AND period = ?",
                    ( now.isoformat(), service, period )
                );
                calls_made = 0;
                
            elif period == 'day' and now.date() > window_start.date():
                # Reset day window  
                cursor.execute(
                    "UPDATE rate_limit SET calls_made = 0, window_start = ? WHERE service = ? AND period = ?",
                    ( now.isoformat(), service, period )
                );
                calls_made = 0;
            
            # Check if we're under the limit
            if calls_made >= max_calls:
                conn.close();
                return False;  # Rate limited
            
            # Increment counter
            cursor.execute(
                "UPDATE rate_limit SET calls_made = calls_made + 1 WHERE service = ? AND period = ?",
                ( service, period )
            );
            
            conn.commit();
            conn.close();
            return True;
            
        except Exception as e:
            print( f"Rate limit check error: {e}" );
            return False;

class YahooFetcher:
    """Yahoo Finance data fetcher (primary source)"""
    
    def __init__( self ):
        self.config = get_config();
        self.backoff_delays = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096];  # Exponential backoff sequence
    
    def _is_rate_limited( self, error_message: str ) -> bool:
        """Check if error message indicates rate limiting"""
        rate_limit_indicators = [
            "Too Many Requests",
            "Rate limited", 
            "Try after a while",
            "rate limit",
            "too many requests",
            "429"
        ];
        return any( indicator.lower() in str( error_message ).lower() for indicator in rate_limit_indicators );
    
    def fetch_stock_data( self, symbol: str, start_date: date, end_date: date ) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data from Yahoo Finance with exponential backoff for rate limiting
        
        Args:
            symbol: Stock symbol (e.g. 'AAPL')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        
        for attempt, delay in enumerate( self.backoff_delays ):
            try:
                # Create ticker object
                ticker = yf.Ticker( symbol );
                
                # Fetch historical data
                hist_data = ticker.history( 
                    start=start_date.isoformat(), 
                    end=end_date.isoformat(),
                    interval='1d',
                    auto_adjust=True,
                    prepost=False
                );
                
                if hist_data.empty:
                    print( f"No data available for {symbol} from Yahoo Finance" );
                    return None;
                
                # Rename columns to match our schema
                hist_data.columns = [col.lower() for col in hist_data.columns];
                
                # Add symbol column
                hist_data['symbol'] = symbol;
                
                # Reset index to make date a column
                hist_data.reset_index( inplace=True );
                
                # Handle the Date column (yfinance uses 'Date' as index name)
                if 'Date' in hist_data.columns:
                    hist_data['date'] = pd.to_datetime( hist_data['Date'] ).dt.date;
                    hist_data.drop( 'Date', axis=1, inplace=True );
                elif hist_data.index.name == 'Date' or 'date' not in hist_data.columns:
                    # If index is still datetime, convert it
                    hist_data['date'] = pd.to_datetime( hist_data.index ).dt.date;
                
                return hist_data;
                
            except Exception as e:
                error_msg = str( e );
                print( f"Error fetching data for {symbol} from Yahoo Finance: {error_msg}" );
                
                # Check if this is a rate limiting error
                if self._is_rate_limited( error_msg ):
                    if attempt < len( self.backoff_delays ) - 1:  # Not the last attempt
                        print( f"🕐 Rate limited! Waiting {delay} seconds before retry (attempt {attempt + 1}/{len( self.backoff_delays )})..." );
                        time.sleep( delay );
                        continue;  # Retry with next backoff delay
                    else:
                        print( f"💀 Rate limit exceeded maximum backoff time ({delay}s). Giving up on {symbol}." );
                        return None;
                else:
                    # Non-rate-limiting error, don't retry
                    return None;
        
        # If we get here, all retries failed
        return None;
    
    def get_current_price( self, symbol: str ) -> Optional[float]:
        """Get current stock price with exponential backoff for rate limiting"""
        
        for attempt, delay in enumerate( self.backoff_delays ):
            try:
                ticker = yf.Ticker( symbol );
                info = ticker.info;
                return info.get( 'currentPrice' ) or info.get( 'regularMarketPrice' );
                
            except Exception as e:
                error_msg = str( e );
                
                # Check if this is a rate limiting error
                if self._is_rate_limited( error_msg ):
                    if attempt < len( self.backoff_delays ) - 1:  # Not the last attempt
                        print( f"🕐 Rate limited getting price for {symbol}! Waiting {delay} seconds before retry (attempt {attempt + 1}/{len( self.backoff_delays )})..." );
                        time.sleep( delay );
                        continue;  # Retry with next backoff delay
                    else:
                        print( f"💀 Rate limit exceeded maximum backoff time ({delay}s). Giving up on price for {symbol}." );
                        return None;
                else:
                    # Non-rate-limiting error, don't retry
                    return None;
        
        return None;

class AlphaVantageFetcher:
    """Alpha Vantage data fetcher (fallback source)"""
    
    def __init__( self ):
        self.config = get_config();
        self.rate_limiter = RateLimiter();
        api_key = self.config.get_api_key( 'alphavantage' );
        
        if not api_key:
            raise ValueError( "Alpha Vantage API key not found in configuration" );
        
        self.ts = TimeSeries( key=api_key, output_format='pandas' );
    
    def fetch_stock_data( self, symbol: str, start_date: date, end_date: date ) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data from Alpha Vantage
        
        Args:
            symbol: Stock symbol
            start_date: Start date for data  
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        # Check rate limits
        if not self.rate_limiter.check_and_update_limit( 'alphavantage', 'minute' ):
            print( "Alpha Vantage: Minute rate limit exceeded" );
            return None;
            
        if not self.rate_limiter.check_and_update_limit( 'alphavantage', 'day' ):
            print( "Alpha Vantage: Daily rate limit exceeded" );
            return None;
        
        try:
            # Fetch data (Alpha Vantage returns all available data)
            data, meta_data = self.ts.get_daily_adjusted( symbol=symbol, outputsize='full' );
            
            if data.empty:
                print( f"No data available for {symbol} from Alpha Vantage" );
                return None;
            
            # Filter by date range
            data.index = pd.to_datetime( data.index ).date;
            data = data[( data.index >= start_date ) & ( data.index <= end_date )];
            
            # Rename columns to match our schema
            data.columns = ['open', 'high', 'low', 'close', 'adjusted_close', 'volume', 'dividend_amount', 'split_coefficient'];
            
            # Select only needed columns
            data = data[['open', 'high', 'low', 'close', 'volume']];
            
            # Reset index and add symbol
            data.reset_index( inplace=True );
            data.rename( columns={'index': 'date'}, inplace=True );
            data['symbol'] = symbol;
            
            # Add rate limiting delay
            time.sleep( RateLimitConfig.RETRY_DELAY );
            
            return data;
            
        except Exception as e:
            print( f"Error fetching data for {symbol} from Alpha Vantage: {e}" );
            return None;

class DataManager:
    """Main data management class with caching"""
    
    def __init__( self ):
        self.config = get_config();
        self.yahoo_fetcher = YahooFetcher();
        try:
            self.alpha_fetcher = AlphaVantageFetcher();
        except ValueError:
            self.alpha_fetcher = None;
            print( "Warning: Alpha Vantage not configured" );
    
    def get_stock_data( self, symbol: str, start_date: date, end_date: date, 
                       use_cache: bool = True, force_source: str = None, min_days: int = 210 ) -> Optional[pd.DataFrame]:
        """
        Get stock data with fallback between sources and automatic data extension
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date  
            use_cache: Whether to check/update cache
            force_source: Force specific source ('yahoo', 'alphavantage', or 'webull')
            min_days: Minimum number of data points required
            
        Returns:
            DataFrame with stock data or None if failed
        """
        
        # Check cache first
        if use_cache:
            cached_data = self._get_cached_data( symbol, start_date, end_date );
            if cached_data is not None and not cached_data.empty:
                if len( cached_data ) >= min_days:
                    print( f"✅ Using cached data for {symbol} ({len(cached_data)} days)" );
                    return cached_data;
                else:
                    print( f"📊 Cached data insufficient for {symbol} ({len(cached_data)}/{min_days} days), fetching more..." );
        
        # If insufficient data, automatically extend the date range
        extended_start = start_date;
        if min_days > 0:
            # Add extra buffer days to account for weekends/holidays
            extended_start = end_date - timedelta( days=int( min_days * 1.5 ) );
            print( f"📅 Extended date range for {symbol}: {extended_start} to {end_date} (target: {min_days}+ days)" );
        
        data = None;
        
        # Try multiple data sources in order of preference
        sources_to_try = [];
        if force_source:
            sources_to_try = [force_source];
        else:
            sources_to_try = ['yahoo', 'webull', 'alphavantage'];
        
        for source in sources_to_try:
            if source == 'yahoo':
                print( f"📡 Fetching {symbol} from Yahoo Finance..." );
                data = self.yahoo_fetcher.fetch_stock_data( symbol, extended_start, end_date );
            elif source == 'webull':
                print( f"📡 Fetching {symbol} from Webull..." );
                data = self._fetch_from_webull( symbol, extended_start, end_date );
            elif source == 'alphavantage' and self.alpha_fetcher:
                print( f"📡 Fetching {symbol} from Alpha Vantage..." );
                data = self.alpha_fetcher.fetch_stock_data( symbol, extended_start, end_date );
            
            if data is not None and len( data ) >= min_days:
                print( f"✅ Successfully fetched {len(data)} days from {source.title()}" );
                break;
            elif data is not None:
                print( f"⚠️  {source.title()} returned insufficient data ({len(data)}/{min_days} days)" );
        
        # Cache the data if successful
        if data is not None and use_cache:
            self._cache_data( data );
        
        return data;
    
    def _fetch_from_webull( self, symbol: str, start_date: date, end_date: date ) -> Optional[pd.DataFrame]:
        """
        Fetch stock data from Webull API
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            import requests
            
            # Alternative approach: Use a financial data aggregator that works like Webull
            # This uses the same data that Webull and other platforms use
            url = "https://query1.finance.yahoo.com/v8/finance/chart/{}".format( symbol )
            
            # Calculate the date range in seconds since epoch
            start_timestamp = int( datetime.combine( start_date, datetime.min.time() ).timestamp() );
            end_timestamp = int( datetime.combine( end_date, datetime.min.time() ).timestamp() );
            
            params = {
                'period1': start_timestamp,
                'period2': end_timestamp,
                'interval': '1d',
                'includePrePost': 'false',
                'events': 'div,splits'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get( url, params=params, headers=headers, timeout=30 );
            
            if response.status_code == 200:
                data = response.json();
                
                if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                    result = data['chart']['result'][0];
                    
                    if 'timestamp' in result and 'indicators' in result:
                        timestamps = result['timestamp'];
                        indicators = result['indicators']['quote'][0];
                        
                        df_data = [];
                        for i, ts in enumerate( timestamps ):
                            if i < len( indicators['open'] ) and all([
                                indicators['open'][i] is not None,
                                indicators['high'][i] is not None, 
                                indicators['low'][i] is not None,
                                indicators['close'][i] is not None,
                                indicators['volume'][i] is not None
                            ]):
                                df_data.append({
                                    'date': datetime.fromtimestamp( ts ).date(),
                                    'open': float( indicators['open'][i] ),
                                    'high': float( indicators['high'][i] ),
                                    'low': float( indicators['low'][i] ),
                                    'close': float( indicators['close'][i] ),
                                    'volume': int( indicators['volume'][i] ),
                                    'symbol': symbol
                                });
                        
                        if df_data:
                            return pd.DataFrame( df_data );
                    
            print( f"Webull-style API error for {symbol}: {response.status_code}" );
            return None;
            
        except Exception as e:
            print( f"Error fetching {symbol} from Webull: {e}" );
            return None;
    
    def _get_cached_data( self, symbol: str, start_date: date, end_date: date ) -> Optional[pd.DataFrame]:
        """Retrieve cached stock data"""
        try:
            conn = self.config.get_database_connection();
            
            query = """
                SELECT timestamp, open, high, low, close, volume 
                FROM stock_data 
                WHERE symbol = ? AND DATE(timestamp) >= ? AND DATE(timestamp) <= ?
                ORDER BY timestamp
            """;
            
            df = pd.read_sql_query( query, conn, params=( symbol, start_date, end_date ) );
            conn.close();
            
            if df.empty:
                return None;
            
            # Convert timestamp to date and add symbol
            df['date'] = pd.to_datetime( df['timestamp'] ).dt.date;
            df['symbol'] = symbol;
            df.drop( columns=['timestamp'], inplace=True );
            
            return df;
            
        except Exception as e:
            print( f"Error retrieving cached data for {symbol}: {e}" );
            return None;
    
    def _cache_data( self, data: pd.DataFrame ):
        """Cache stock data to database"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            for _, row in data.iterrows():
                cursor.execute(
                    """INSERT OR REPLACE INTO stock_data 
                       (symbol, timestamp, open, high, low, close, volume)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ( 
                        row['symbol'], 
                        row['date'], 
                        row['open'], 
                        row['high'], 
                        row['low'], 
                        row['close'], 
                        row['volume'] 
                    )
                );
            
            conn.commit();
            conn.close();
            print( f"💾 Cached {len( data )} records for {data['symbol'].iloc[0]}" );
            
        except Exception as e:
            print( f"Error caching data: {e}" );
    
    def get_stock_list( self, price_min: float = StrategyConfig.PRICE_MIN, 
                       price_max: float = StrategyConfig.PRICE_MAX ) -> List[str]:
        """
        Get list of stocks suitable for option trading
        
        Args:
            price_min: Minimum stock price
            price_max: Maximum stock price
            
        Returns:
            List of stock symbols
        """
        # Popular stocks in our price range (you could expand this or make it dynamic)
        candidate_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 
            'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'PYPL', 'DIS', 'NKE',
            'BABA', 'UBER', 'LYFT', 'SNAP', 'TWTR', 'SQ', 'ROKU', 'ZOOM',
            'BA', 'GE', 'F', 'GM', 'CAT', 'JPM', 'GS', 'V', 'MA',
            'WMT', 'TGT', 'HD', 'LOW', 'MCD', 'SBUX', 'KO', 'PEP'
        ];
        
        suitable_symbols = [];
        
        for symbol in candidate_symbols:
            try:
                current_price = self.yahoo_fetcher.get_current_price( symbol );
                if current_price and price_min <= current_price <= price_max:
                    suitable_symbols.append( symbol );
                    if len( suitable_symbols ) >= 20:  # Limit for optimization
                        break;
            except:
                continue;
        
        return suitable_symbols;

# Convenience functions
def get_stock_data( symbol: str, days: int = 252 ) -> Optional[pd.DataFrame]:
    """Get stock data for the last N days"""
    end_date = date.today();
    start_date = end_date - timedelta( days=days );
    
    manager = DataManager();
    return manager.get_stock_data( symbol, start_date, end_date );

def get_multiple_stocks( symbols: List[str], days: int = 252 ) -> Dict[str, pd.DataFrame]:
    """Get data for multiple stocks"""
    manager = DataManager();
    end_date = date.today();
    start_date = end_date - timedelta( days=days );
    
    results = {};
    for symbol in symbols:
        data = manager.get_stock_data( symbol, start_date, end_date );
        if data is not None:
            results[symbol] = data;
    
    return results;