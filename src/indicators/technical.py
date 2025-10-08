"""
Technical Indicators Module for BTFD
Implements RSI(14), EMA, MACD, and signal detection
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
import sqlite3

from ..config.settings import get_config, TechnicalConfig

class TechnicalIndicators:
    """Technical indicator calculations and caching"""
    
    def __init__( self ):
        self.config = get_config();
    
    def calculate_rsi( self, prices: pd.Series, period: int = TechnicalConfig.RSI_PERIOD ) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            prices: Series of closing prices
            period: RSI period (default 14)
            
        Returns:
            Series of RSI values
        """
        if len( prices ) < period + 1:
            return pd.Series( [np.nan] * len( prices ), index=prices.index );
        
        # Use TA-Lib for RSI calculation
        rsi_values = talib.RSI( prices.values, timeperiod=period );
        return pd.Series( rsi_values, index=prices.index );
    
    def calculate_ema( self, prices: pd.Series, period: int ) -> pd.Series:
        """
        Calculate EMA (Exponential Moving Average)
        
        Args:
            prices: Series of closing prices  
            period: EMA period
            
        Returns:
            Series of EMA values
        """
        if len( prices ) < period:
            return pd.Series( [np.nan] * len( prices ), index=prices.index );
        
        # Use TA-Lib for EMA calculation
        ema_values = talib.EMA( prices.values, timeperiod=period );
        return pd.Series( ema_values, index=prices.index );
    
    def calculate_macd( self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9 ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: Series of closing prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line EMA period (default 9)
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' series
        """
        if len( prices ) < slow + signal:
            nan_series = pd.Series( [np.nan] * len( prices ), index=prices.index );
            return {
                'macd': nan_series,
                'signal': nan_series, 
                'histogram': nan_series
            };
        
        # Use TA-Lib for MACD calculation
        macd_line, signal_line, histogram = talib.MACD( prices.values, fastperiod=fast, slowperiod=slow, signalperiod=signal );
        
        return {
            'macd': pd.Series( macd_line, index=prices.index ),
            'signal': pd.Series( signal_line, index=prices.index ),
            'histogram': pd.Series( histogram, index=prices.index )
        };
    
    def calculate_cci( self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20 ) -> pd.Series:
        """
        Calculate CCI (Commodity Channel Index)
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of close prices
            period: CCI period (default 20)
            
        Returns:
            Series of CCI values
        """
        if len( close ) < period:
            return pd.Series( [np.nan] * len( close ), index=close.index );
        
        # Use TA-Lib for CCI calculation
        cci_values = talib.CCI( high.values, low.values, close.values, timeperiod=period );
        return pd.Series( cci_values, index=close.index );
    
    def detect_rsi_crosses( self, rsi_series: pd.Series, lookback_days: int = TechnicalConfig.RSI_LOOKBACK_DAYS ) -> Dict[str, Optional[date]]:
        """
        Detect recent RSI crosses above 70 or below 30
        
        Args:
            rsi_series: Series of RSI values
            lookback_days: Days to look back for crosses
            
        Returns:
            Dictionary with 'overbought_cross' and 'oversold_cross' dates
        """
        result = {
            'overbought_cross': None,
            'oversold_cross': None
        };
        
        if len( rsi_series ) < 2:
            return result;
        
        # Get recent data
        recent_rsi = rsi_series.tail( lookback_days + 1 );
        
        # Check for overbought cross (RSI > 70)
        for i in range( 1, len( recent_rsi ) ):
            if recent_rsi.iloc[i] > TechnicalConfig.RSI_OVERBOUGHT and recent_rsi.iloc[i-1] <= TechnicalConfig.RSI_OVERBOUGHT:
                result['overbought_cross'] = recent_rsi.index[i].date() if hasattr( recent_rsi.index[i], 'date' ) else recent_rsi.index[i];
                break;
        
        # Check for oversold cross (RSI < 30)
        for i in range( 1, len( recent_rsi ) ):
            if recent_rsi.iloc[i] < TechnicalConfig.RSI_OVERSOLD and recent_rsi.iloc[i-1] >= TechnicalConfig.RSI_OVERSOLD:
                result['oversold_cross'] = recent_rsi.index[i].date() if hasattr( recent_rsi.index[i], 'date' ) else recent_rsi.index[i];
                break;
        
        return result;
    
    def detect_ema_crossovers( self, fast_ema: pd.Series, slow_ema: pd.Series, lookback_days: int = 2 ) -> List[Dict]:
        """
        Detect EMA crossovers in recent data
        
        Args:
            fast_ema: Fast EMA series
            slow_ema: Slow EMA series  
            lookback_days: Days to check for crossovers
            
        Returns:
            List of crossover events with date, type, and values
        """
        crossovers = [];
        
        if len( fast_ema ) < 2 or len( slow_ema ) < 2:
            return crossovers;
        
        # Align series and get recent data
        aligned_fast = fast_ema.tail( lookback_days + 1 );
        aligned_slow = slow_ema.tail( lookback_days + 1 );
        
        for i in range( 1, len( aligned_fast ) ):
            prev_fast = aligned_fast.iloc[i-1];
            curr_fast = aligned_fast.iloc[i];
            prev_slow = aligned_slow.iloc[i-1];
            curr_slow = aligned_slow.iloc[i];
            
            # Skip if any value is NaN
            if pd.isna( prev_fast ) or pd.isna( curr_fast ) or pd.isna( prev_slow ) or pd.isna( curr_slow ):
                continue;
            
            # Bullish crossover: fast crosses above slow
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                crossovers.append({
                    'date': aligned_fast.index[i].date() if hasattr( aligned_fast.index[i], 'date' ) else aligned_fast.index[i],
                    'type': 'bullish',
                    'fast_ema': curr_fast,
                    'slow_ema': curr_slow
                });
            
            # Bearish crossover: fast crosses below slow  
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                crossovers.append({
                    'date': aligned_fast.index[i].date() if hasattr( aligned_fast.index[i], 'date' ) else aligned_fast.index[i],
                    'type': 'bearish',
                    'fast_ema': curr_fast,
                    'slow_ema': curr_slow
                });
        
        return crossovers;
    
    def cache_indicators( self, symbol: str, date_val: date, indicators: Dict[str, float] ):
        """
        Cache calculated indicators to database
        
        Args:
            symbol: Stock symbol
            date_val: Date for the indicators
            indicators: Dictionary of indicator names and values
        """
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            for indicator_name, value in indicators.items():
                if pd.notna( value ):  # Only store non-NaN values
                    # Extract period from indicator name if present
                    period = None;
                    if '(' in indicator_name and ')' in indicator_name:
                        period_str = indicator_name[indicator_name.find('(')+1:indicator_name.find(')')];
                        try:
                            period = int( period_str );
                        except ValueError:
                            period = None;
                    
                    cursor.execute(
                        """INSERT OR REPLACE INTO technical_indicators 
                           (symbol, date, indicator_name, period, value) 
                           VALUES (?, ?, ?, ?, ?)""",
                        ( symbol, date_val, indicator_name, period, float( value ) )
                    );
            
            conn.commit();
            conn.close();
            
        except Exception as e:
            print( f"Error caching indicators for {symbol}: {e}" );
    
    def get_cached_indicators( self, symbol: str, start_date: Optional[date] = None, end_date: Optional[date] = None ) -> pd.DataFrame:
        """
        Retrieve cached indicators from database
        
        Args:
            symbol: Stock symbol
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            
        Returns:
            DataFrame with cached indicator values
        """
        try:
            conn = self.config.get_database_connection();
            
            query = "SELECT date, indicator_name, period, value FROM technical_indicators WHERE symbol = ?";
            params = [symbol];
            
            if start_date:
                query += " AND date >= ?";
                params.append( start_date );
                
            if end_date:
                query += " AND date <= ?";
                params.append( end_date );
            
            query += " ORDER BY date, indicator_name";
            
            df = pd.read_sql_query( query, conn, params=params );
            conn.close();
            
            return df;
            
        except Exception as e:
            print( f"Error retrieving cached indicators for {symbol}: {e}" );
            return pd.DataFrame();
    
    def calculate_all_indicators( self, symbol: str, price_data: pd.DataFrame, 
                                ema_fast: int = 10, ema_slow: int = 20 ) -> Dict[str, pd.Series]:
        """
        Calculate all technical indicators for a stock
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            
        Returns:
            Dictionary of indicator series
        """
        if 'close' not in price_data.columns:
            raise ValueError( "Price data must contain 'close' column" );
        
        close_prices = price_data['close'];
        
        # Calculate indicators
        indicators = {
            f'rsi_{TechnicalConfig.RSI_PERIOD}': self.calculate_rsi( close_prices ),
            f'ema_{ema_fast}': self.calculate_ema( close_prices, ema_fast ),
            f'ema_{ema_slow}': self.calculate_ema( close_prices, ema_slow )
        };
        
        # Add MACD
        macd_data = self.calculate_macd( close_prices );
        indicators.update({
            'macd': macd_data['macd'],
            'macd_signal': macd_data['signal'],
            'macd_histogram': macd_data['histogram']
        });
        
        return indicators;

# Convenience functions
def calculate_rsi( prices: pd.Series, period: int = 14 ) -> pd.Series:
    """Calculate RSI with default parameters"""
    calculator = TechnicalIndicators();
    return calculator.calculate_rsi( prices, period );

def calculate_ema( prices: pd.Series, period: int ) -> pd.Series:
    """Calculate EMA with specified period"""
    calculator = TechnicalIndicators();
    return calculator.calculate_ema( prices, period );

def detect_recent_rsi_crosses( rsi_series: pd.Series ) -> Dict[str, Optional[date]]:
    """Detect recent RSI crosses with default lookback"""
    calculator = TechnicalIndicators();
    return calculator.detect_rsi_crosses( rsi_series );