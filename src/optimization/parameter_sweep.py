"""
Parameter Sweep System for BTFD
Grid search optimization for EMA crossover strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Iterator
from datetime import date, datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import sqlite3
from itertools import product

from ..config.settings import get_config, TechnicalConfig
from ..indicators.technical import TechnicalIndicators  
from ..data.fetchers import DataManager

class ParameterSweepEngine:
    """Main parameter optimization engine"""
    
    def __init__( self ):
        self.config = get_config();
        self.data_manager = DataManager();
        self.indicators = TechnicalIndicators();
    
    def generate_parameter_grid( self, 
                               ema_fast_range: Tuple[int, int] = (TechnicalConfig.EMA_FAST_MIN, TechnicalConfig.EMA_FAST_MAX),
                               ema_slow_range: Tuple[int, int] = (TechnicalConfig.EMA_SLOW_MIN, TechnicalConfig.EMA_SLOW_MAX),
                               step: int = 1 ) -> List[Dict[str, int]]:
        """
        Generate grid of parameter combinations
        
        Args:
            ema_fast_range: (min, max) for fast EMA period
            ema_slow_range: (min, max) for slow EMA period  
            step: Step size for parameter increments
            
        Returns:
            List of parameter dictionaries
        """
        fast_params = range( ema_fast_range[0], ema_fast_range[1] + 1, step );
        slow_params = range( ema_slow_range[0], ema_slow_range[1] + 1, step );
        
        param_combinations = [];
        for fast, slow in product( fast_params, slow_params ):
            if fast < slow:  # Ensure fast < slow for meaningful crossovers
                param_combinations.append({
                    'ema_fast': fast,
                    'ema_slow': slow,
                    'rsi_period': TechnicalConfig.RSI_PERIOD
                });
        
        print( f"📊 Generated {len( param_combinations )} parameter combinations" );
        return param_combinations;
    
    def backtest_strategy( self, symbol: str, price_data: pd.DataFrame, 
                          ema_fast: int, ema_slow: int, 
                          initial_capital: float = 10000.0 ) -> Dict[str, float]:
        """
        Backtest single parameter combination
        
        Args:
            symbol: Stock symbol
            price_data: Historical price data
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            initial_capital: Starting capital
            
        Returns:
            Performance metrics dictionary
        """
        
        if len( price_data ) < max( ema_slow + 10, 30 ):  # Need sufficient data
            return self._create_empty_metrics();
        
        try:
            # Calculate indicators
            close_prices = price_data['close'];
            fast_ema = self.indicators.calculate_ema( close_prices, ema_fast );
            slow_ema = self.indicators.calculate_ema( close_prices, ema_slow );
            rsi = self.indicators.calculate_rsi( close_prices );
            
            # Detect crossovers
            signals = [];
            position = 0;  # 0 = no position, 1 = long, -1 = short
            
            for i in range( 1, len( fast_ema ) ):
                if pd.isna( fast_ema.iloc[i] ) or pd.isna( slow_ema.iloc[i] ):
                    continue;
                
                prev_fast = fast_ema.iloc[i-1];
                curr_fast = fast_ema.iloc[i];
                prev_slow = slow_ema.iloc[i-1];
                curr_slow = slow_ema.iloc[i];
                
                # Skip if previous values are NaN
                if pd.isna( prev_fast ) or pd.isna( prev_slow ):
                    continue;
                
                current_price = close_prices.iloc[i];
                signal_date = price_data.index[i];
                
                # Bullish crossover: Enter long position
                if prev_fast <= prev_slow and curr_fast > curr_slow and position != 1:
                    # Optional RSI filter: only enter if RSI < 70 (not overbought)
                    rsi_value = rsi.iloc[i] if not pd.isna( rsi.iloc[i] ) else 50;
                    if rsi_value < 70:
                        signals.append({
                            'date': signal_date,
                            'type': 'BUY',
                            'price': current_price,
                            'rsi': rsi_value
                        });
                        position = 1;
                
                # Bearish crossover: Enter short or exit long
                elif prev_fast >= prev_slow and curr_fast < curr_slow and position != -1:
                    # Optional RSI filter: only enter short if RSI > 30 (not oversold)
                    rsi_value = rsi.iloc[i] if not pd.isna( rsi.iloc[i] ) else 50;
                    if rsi_value > 30:
                        signal_type = 'SELL' if position == 1 else 'SHORT';
                        signals.append({
                            'date': signal_date,
                            'type': signal_type,
                            'price': current_price,
                            'rsi': rsi_value
                        });
                        position = -1;
            
            # Calculate performance metrics
            return self._calculate_performance( signals, price_data, initial_capital );
            
        except Exception as e:
            print( f"Error in backtest for {symbol}: {e}" );
            return self._create_empty_metrics();
    
    def _calculate_performance( self, signals: List[Dict], price_data: pd.DataFrame, 
                              initial_capital: float ) -> Dict[str, float]:
        """Calculate performance metrics from trading signals"""
        
        if len( signals ) < 2:
            return self._create_empty_metrics();
        
        capital = initial_capital;
        position_size = 0;
        trades = [];
        equity_curve = [initial_capital];
        
        for signal in signals:
            if signal['type'] == 'BUY':
                # Enter long position
                position_size = capital / signal['price'];
                capital = 0;  # All capital invested
                
            elif signal['type'] in ['SELL', 'SHORT']:
                if position_size > 0:
                    # Close long position
                    capital = position_size * signal['price'];
                    trade_return = ( signal['price'] - signals[signals.index( signal ) - 1]['price'] ) / signals[signals.index( signal ) - 1]['price'] if signals else 0;
                    trades.append( trade_return );
                    position_size = 0;
                    equity_curve.append( capital );
        
        # Calculate metrics
        if not trades:
            return self._create_empty_metrics();
        
        total_return = ( capital - initial_capital ) / initial_capital;
        win_rate = sum( 1 for t in trades if t > 0 ) / len( trades ) if trades else 0;
        avg_return = np.mean( trades );
        
        # Calculate maximum drawdown
        peak = initial_capital;
        max_drawdown = 0;
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity;
            drawdown = ( peak - equity ) / peak;
            max_drawdown = max( max_drawdown, drawdown );
        
        # Calculate Sharpe ratio (simplified, assuming daily data)
        if len( trades ) > 1:
            returns_std = np.std( trades );
            sharpe_ratio = ( avg_return / returns_std ) * np.sqrt( 252 ) if returns_std > 0 else 0;
        else:
            sharpe_ratio = 0;
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'num_trades': len( trades ),
            'final_capital': capital
        };
    
    def _create_empty_metrics( self ) -> Dict[str, float]:
        """Create empty metrics for failed backtests"""
        return {
            'total_return': 0.0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'num_trades': 0,
            'final_capital': 0.0
        };
    
    def optimize_single_stock( self, symbol: str, param_grid: List[Dict[str, int]], 
                              days_back: int = 252 ) -> List[Dict]:
        """
        Optimize parameters for a single stock
        
        Args:
            symbol: Stock symbol to optimize
            param_grid: List of parameter combinations
            days_back: Number of days of historical data
            
        Returns:
            List of results with parameters and metrics
        """
        
        print( f"🔍 Optimizing parameters for {symbol}..." );
        
        # Get historical data
        price_data = self.data_manager.get_stock_data( 
            symbol, 
            date.today() - pd.Timedelta( days=days_back ), 
            date.today() 
        );
        
        if price_data is None or len( price_data ) < 50:
            print( f"❌ Insufficient data for {symbol}" );
            return [];
        
        # Set date as index for easier processing
        price_data = price_data.set_index( 'date' );
        
        results = [];
        total_combinations = len( param_grid );
        
        for i, params in enumerate( param_grid ):
            if i % 10 == 0:  # Progress update
                print( f"   Progress: {i}/{total_combinations} ({i/total_combinations*100:.1f}%)" );
            
            # Run backtest
            metrics = self.backtest_strategy(
                symbol, price_data, 
                params['ema_fast'], params['ema_slow']
            );
            
            # Combine parameters and metrics
            result = {
                'symbol': symbol,
                'ema_fast': params['ema_fast'],
                'ema_slow': params['ema_slow'],
                'rsi_period': params['rsi_period'],
                **metrics
            };
            
            results.append( result );
        
        # Sort by total return (best first)
        results.sort( key=lambda x: x['total_return'], reverse=True );
        
        print( f"✅ Completed optimization for {symbol}" );
        if results:
            best = results[0];
            print( f"   Best: EMA({best['ema_fast']},{best['ema_slow']}) = {best['total_return']:.2%} return" );
        
        return results;
    
    def optimize_multiple_stocks( self, symbols: List[str], param_grid: List[Dict[str, int]],
                                 days_back: int = 252 ) -> Dict[str, List[Dict]]:
        """
        Optimize parameters for multiple stocks
        
        Args:
            symbols: List of stock symbols
            param_grid: Parameter combinations to test
            days_back: Days of historical data
            
        Returns:
            Dictionary mapping symbols to optimization results
        """
        
        print( f"🚀 Starting multi-stock optimization for {len( symbols )} stocks..." );
        print( f"📊 Testing {len( param_grid )} parameter combinations each" );
        
        all_results = {};
        
        for i, symbol in enumerate( symbols ):
            print( f"\n📈 [{i+1}/{len( symbols )}] Optimizing {symbol}..." );
            
            results = self.optimize_single_stock( symbol, param_grid, days_back );
            all_results[symbol] = results;
            
            # Save intermediate results to database
            self._save_optimization_results( results );
        
        print( f"\n🎉 Multi-stock optimization complete!" );
        return all_results;
    
    def _save_optimization_results( self, results: List[Dict] ):
        """Save optimization results to database"""
        
        if not results:
            return;
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            for result in results:
                # Create parameter set JSON
                param_set = json.dumps({
                    'ema_fast': result['ema_fast'],
                    'ema_slow': result['ema_slow'],
                    'rsi_period': result['rsi_period'],
                    'symbol': result['symbol']
                });
                
                cursor.execute(
                    """INSERT INTO optimization_results 
                       (parameter_set, backtest_period, total_return, sharpe_ratio, max_drawdown, win_rate)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        param_set,
                        f"252_days",  # Could be made configurable
                        result['total_return'],
                        result['sharpe_ratio'],
                        result['max_drawdown'],
                        result['win_rate']
                    )
                );
            
            conn.commit();
            conn.close();
            
            print( f"💾 Saved {len( results )} optimization results to database" );
            
        except Exception as e:
            print( f"Error saving optimization results: {e}" );
    
    def get_saved_results( self, symbol: str = None ) -> pd.DataFrame:
        """Retrieve saved optimization results"""
        
        try:
            conn = self.config.get_database_connection();
            
            if symbol:
                query = """
                    SELECT parameter_set, total_return, sharpe_ratio, max_drawdown, win_rate, created_at
                    FROM optimization_results 
                    WHERE json_extract(parameter_set, '$.symbol') = ?
                    ORDER BY total_return DESC
                """;
                params = ( symbol, );
            else:
                query = """
                    SELECT parameter_set, total_return, sharpe_ratio, max_drawdown, win_rate, created_at
                    FROM optimization_results 
                    ORDER BY total_return DESC
                """;
                params = ();
            
            df = pd.read_sql_query( query, conn, params=params );
            conn.close();
            
            # Parse parameter_set JSON
            if not df.empty:
                df['params'] = df['parameter_set'].apply( json.loads );
                df['symbol'] = df['params'].apply( lambda x: x.get( 'symbol', 'Unknown' ) );
                df['ema_fast'] = df['params'].apply( lambda x: x.get( 'ema_fast', 0 ) );
                df['ema_slow'] = df['params'].apply( lambda x: x.get( 'ema_slow', 0 ) );
            
            return df;
            
        except Exception as e:
            print( f"Error retrieving optimization results: {e}" );
            return pd.DataFrame();

# Convenience functions for quick optimization
def quick_optimization( symbols: List[str] = None, max_stocks: int = 5 ) -> Dict[str, List[Dict]]:
    """Run quick optimization on popular stocks"""
    
    engine = ParameterSweepEngine();
    
    if symbols is None:
        # Get suitable stocks automatically
        data_manager = DataManager();
        symbols = data_manager.get_stock_list()[:max_stocks];
        print( f"📋 Auto-selected stocks: {symbols}" );
    
    # Generate focused parameter grid (smaller for speed)
    param_grid = engine.generate_parameter_grid(
        ema_fast_range=( 5, 12 ),
        ema_slow_range=( 15, 25 ),
        step=1
    );
    
    return engine.optimize_multiple_stocks( symbols, param_grid );

def get_best_parameters( symbol: str, top_n: int = 5 ) -> pd.DataFrame:
    """Get best parameter combinations for a stock"""
    
    engine = ParameterSweepEngine();
    results = engine.get_saved_results( symbol );
    
    return results.head( top_n ) if not results.empty else pd.DataFrame();