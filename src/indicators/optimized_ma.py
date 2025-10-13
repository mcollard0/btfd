"""
Optimized Moving Average Calculations for BTFD
Only calculates latest MA values instead of recalculating entire series
Stores and retrieves MA values from database for efficiency
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
import sqlite3

from ..config.settings import get_config, TechnicalConfig


class OptimizedMovingAverages:
    """Optimized MA calculations - only compute what we need"""
    
    def __init__(self):
        self.config = get_config();
        self._ensure_ma_table();
    
    def _ensure_ma_table(self):
        """Create moving averages table if it doesn't exist"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moving_averages (
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    ma_type TEXT NOT NULL,  -- 'EMA' or 'SMA'
                    period INTEGER NOT NULL,
                    value REAL NOT NULL,
                    PRIMARY KEY (symbol, date, ma_type, period)
                )
            """);
            
            # Create index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ma_symbol_date 
                ON moving_averages (symbol, date DESC)
            """);
            
            conn.commit();
            conn.close();
            
        except Exception as e:
            print(f"⚠️  Error creating MA table: {e}");
    
    def get_latest_ema(self, symbol: str, period: int, price_data: pd.DataFrame) -> float:
        """
        Get latest EMA value - either from cache or calculate incrementally
        
        Args:
            symbol: Stock symbol
            period: EMA period
            price_data: DataFrame with 'date' and 'close' columns (chronological order)
            
        Returns:
            Latest EMA value
        """
        return self._get_latest_ma(symbol, period, price_data, 'EMA');
    
    def get_latest_sma(self, symbol: str, period: int, price_data: pd.DataFrame) -> float:
        """
        Get latest SMA value - either from cache or calculate incrementally
        
        Args:
            symbol: Stock symbol
            period: SMA period  
            price_data: DataFrame with 'date' and 'close' columns (chronological order)
            
        Returns:
            Latest SMA value
        """
        return self._get_latest_ma(symbol, period, price_data, 'SMA');
    
    def _get_latest_ma(self, symbol: str, period: int, price_data: pd.DataFrame, ma_type: str) -> float:
        """
        Optimized MA calculation - only compute missing values
        """
        if len(price_data) < period:
            return np.nan;
        
        # Ensure data is sorted by date (oldest first)
        data_sorted = price_data.sort_values('date').copy();
        latest_date = data_sorted['date'].iloc[-1];
        
        # Check if we have the latest MA value cached
        cached_ma = self._get_cached_ma(symbol, latest_date, ma_type, period);
        if cached_ma is not None:
            print(f"📊 Using cached {ma_type}({period}) for {symbol}: {cached_ma:.4f}");
            return cached_ma;
        
        # Find the last cached MA value
        last_cached_date, last_cached_value = self._get_last_cached_ma(symbol, ma_type, period);
        
        if last_cached_date is not None:
            # Incremental calculation from last cached point
            print(f"🔄 Incremental {ma_type}({period}) calculation for {symbol} from {last_cached_date}");
            
            # Get data starting from day after last cached
            start_idx = data_sorted[data_sorted['date'] > last_cached_date].index[0];
            new_data = data_sorted.iloc[start_idx:];
            
            if ma_type == 'EMA':
                latest_value = self._calculate_incremental_ema(
                    last_cached_value, new_data['close'].values, period
                );
            else:  # SMA
                # For SMA, we need the last 'period' prices including cached ones
                end_idx = len(data_sorted) - 1;
                start_idx = max(0, end_idx - period + 1);
                sma_data = data_sorted.iloc[start_idx:end_idx + 1]['close'];
                latest_value = sma_data.mean();
        else:
            # Full calculation needed - but only for the latest value
            print(f"🆕 Full {ma_type}({period}) calculation for {symbol} (no cache)");
            
            if ma_type == 'EMA':
                latest_value = self._calculate_latest_ema_full(data_sorted['close'].values, period);
            else:  # SMA  
                # SMA: average of last 'period' prices
                latest_prices = data_sorted['close'].tail(period);
                latest_value = latest_prices.mean();
        
        # Cache the result
        self._cache_ma(symbol, latest_date, ma_type, period, latest_value);
        
        print(f"✅ Calculated {ma_type}({period}) for {symbol}: {latest_value:.4f}");
        return latest_value;
    
    def _calculate_incremental_ema(self, previous_ema: float, new_prices: np.ndarray, period: int) -> float:
        """
        Calculate EMA incrementally from previous value
        EMA formula: EMA_today = (Price_today * α) + (EMA_yesterday * (1 - α))
        where α = 2 / (period + 1)
        """
        alpha = 2.0 / (period + 1);
        current_ema = previous_ema;
        
        for price in new_prices:
            current_ema = (price * alpha) + (current_ema * (1 - alpha));
        
        return current_ema;
    
    def _calculate_latest_ema_full(self, prices: np.ndarray, period: int) -> float:
        """
        Calculate EMA from scratch - but only return the latest value
        Much more efficient than calculating entire series
        """
        if len(prices) < period:
            return np.nan;
        
        # Start with SMA for first EMA value  
        sma = np.mean(prices[:period]);
        ema = sma;
        
        # Calculate incremental EMA for remaining values
        alpha = 2.0 / (period + 1);
        
        for price in prices[period:]:
            ema = (price * alpha) + (ema * (1 - alpha));
        
        return ema;
    
    def _get_cached_ma(self, symbol: str, date_val: date, ma_type: str, period: int) -> Optional[float]:
        """Get specific cached MA value"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                SELECT value FROM moving_averages 
                WHERE symbol = ? AND date = ? AND ma_type = ? AND period = ?
            """, (symbol, date_val, ma_type, period));
            
            result = cursor.fetchone();
            conn.close();
            
            return result[0] if result else None;
            
        except Exception as e:
            print(f"⚠️  Error getting cached MA: {e}");
            return None;
    
    def _get_last_cached_ma(self, symbol: str, ma_type: str, period: int) -> Tuple[Optional[date], Optional[float]]:
        """Get the most recent cached MA value for incremental calculation"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                SELECT date, value FROM moving_averages 
                WHERE symbol = ? AND ma_type = ? AND period = ?
                ORDER BY date DESC LIMIT 1
            """, (symbol, ma_type, period));
            
            result = cursor.fetchone();
            conn.close();
            
            if result:
                return (datetime.strptime(result[0], '%Y-%m-%d').date(), result[1]);
            else:
                return (None, None);
                
        except Exception as e:
            print(f"⚠️  Error getting last cached MA: {e}");
            return (None, None);
    
    def _cache_ma(self, symbol: str, date_val: date, ma_type: str, period: int, value: float):
        """Cache MA value to database"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                INSERT OR REPLACE INTO moving_averages 
                (symbol, date, ma_type, period, value) VALUES (?, ?, ?, ?, ?)
            """, (symbol, date_val, ma_type, period, value));
            
            conn.commit();
            conn.close();
            
        except Exception as e:
            print(f"⚠️  Error caching MA: {e}");
    
    def detect_ma_crossover(self, symbol: str, fast_period: int, slow_period: int, 
                           price_data: pd.DataFrame, ma_type: str = 'EMA') -> Optional[Dict]:
        """
        Detect if there's a recent MA crossover using optimized calculations
        
        Args:
            symbol: Stock symbol
            fast_period: Fast MA period
            slow_period: Slow MA period  
            price_data: Price data (must have at least 2+ days)
            ma_type: 'EMA' or 'SMA'
            
        Returns:
            Crossover dict or None
        """
        if len(price_data) < max(fast_period, slow_period) + 1:
            return None;
        
        # Sort data by date
        data_sorted = price_data.sort_values('date').copy();
        
        # Get current (latest) MA values
        if ma_type == 'EMA':
            current_fast = self.get_latest_ema(symbol, fast_period, data_sorted);
            current_slow = self.get_latest_ema(symbol, slow_period, data_sorted);
        else:
            current_fast = self.get_latest_sma(symbol, fast_period, data_sorted);  
            current_slow = self.get_latest_sma(symbol, slow_period, data_sorted);
        
        # Get previous day MA values (subtract last day and recalculate)
        prev_data = data_sorted.iloc[:-1].copy();  # Remove last day
        
        if len(prev_data) < max(fast_period, slow_period):
            return None;
        
        if ma_type == 'EMA':
            prev_fast = self.get_latest_ema(symbol, fast_period, prev_data);
            prev_slow = self.get_latest_ema(symbol, slow_period, prev_data);
        else:
            prev_fast = self.get_latest_sma(symbol, fast_period, prev_data);
            prev_slow = self.get_latest_sma(symbol, slow_period, prev_data);
        
        # Check for crossovers
        latest_date = data_sorted['date'].iloc[-1];
        
        # Bullish crossover: fast crosses above slow
        if prev_fast <= prev_slow and current_fast > current_slow:
            result = {
                'date': latest_date,
                'type': 'bullish'
            };
            if ma_type == 'EMA':
                result.update({'fast_ema': current_fast, 'slow_ema': current_slow});
            else:
                result.update({'fast_sma': current_fast, 'slow_sma': current_slow});
            return result;
        
        # Bearish crossover: fast crosses below slow
        elif prev_fast >= prev_slow and current_fast < current_slow:
            result = {
                'date': latest_date,
                'type': 'bearish'  
            };
            if ma_type == 'EMA':
                result.update({'fast_ema': current_fast, 'slow_ema': current_slow});
            else:
                result.update({'fast_sma': current_fast, 'slow_sma': current_slow});
            return result;
        
        return None;
    
    def cleanup_old_ma_cache(self, days_to_keep: int = 60):
        """Clean up old cached MA values to keep database lean"""
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep);
            
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("DELETE FROM moving_averages WHERE date < ?", (cutoff_date,));
            deleted = cursor.rowcount;
            
            conn.commit();
            conn.close();
            
            if deleted > 0:
                print(f"🧹 Cleaned up {deleted} old MA cache entries");
                
        except Exception as e:
            print(f"⚠️  Error cleaning MA cache: {e}");


# Convenience functions
def get_latest_ema(symbol: str, period: int, price_data: pd.DataFrame) -> float:
    """Get latest EMA value using optimized calculation"""
    calculator = OptimizedMovingAverages();
    return calculator.get_latest_ema(symbol, period, price_data);

def get_latest_sma(symbol: str, period: int, price_data: pd.DataFrame) -> float:
    """Get latest SMA value using optimized calculation"""
    calculator = OptimizedMovingAverages();
    return calculator.get_latest_sma(symbol, period, price_data);

def detect_ema_crossover(symbol: str, fast_period: int, slow_period: int, price_data: pd.DataFrame) -> Optional[Dict]:
    """Detect EMA crossover using optimized calculations"""
    calculator = OptimizedMovingAverages();
    return calculator.detect_ma_crossover(symbol, fast_period, slow_period, price_data, 'EMA');

def detect_sma_crossover(symbol: str, fast_period: int, slow_period: int, price_data: pd.DataFrame) -> Optional[Dict]:
    """Detect SMA crossover using optimized calculations"""
    calculator = OptimizedMovingAverages();
    return calculator.detect_ma_crossover(symbol, fast_period, slow_period, price_data, 'SMA');