"""
Comprehensive EMA Optimization System for BTFD
Tests common professional trading EMA combinations across all target stocks
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import json
import time

from ..config.settings import get_config
from ..indicators.technical import TechnicalIndicators
from ..data.fetchers import DataManager
from .parameter_sweep import ParameterSweepEngine

class ComprehensiveEMAOptimizer:
    """
    Professional EMA optimization using common trading combinations
    """
    
    def __init__(self):
        self.config = get_config()
        self.data_manager = DataManager()
        self.indicators = TechnicalIndicators()
        self.parameter_engine = ParameterSweepEngine()
        
        # Professional EMA combinations used by traders
        self.common_ema_pairs = [
            # Fast scalping pairs
            (5, 13), (8, 21), (9, 21),
            
            # Common short-term pairs  
            (10, 20), (12, 26), (10, 30),
            
            # Medium-term trending pairs
            (20, 50), (21, 55), (15, 50),
            
            # Long-term trend following
            (50, 100), (50, 200), (100, 200),
            
            # Fibonacci-based pairs
            (8, 13), (13, 21), (21, 34), (34, 55),
            
            # Popular day trading pairs
            (5, 15), (9, 18), (12, 24),
            
            # Swing trading favorites
            (20, 40), (25, 50), (30, 60),
            
            # Professional momentum pairs
            (3, 8), (5, 8), (8, 34), (13, 48)
        ]
    
    def get_optimization_candidates(self, min_data_points: int = 50) -> List[Dict]:
        """
        Get stocks suitable for optimization with sufficient historical data
        
        Args:
            min_data_points: Minimum days of data required
            
        Returns:
            List of candidate stocks with metadata
        """
        
        print(f"🔍 Finding optimization candidates with at least {min_data_points} days of data...")
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            # Get stocks in target range with sufficient data
            cursor.execute('''
                SELECT ss.symbol, ss.exchange, ss.sector, 
                       sd.close as current_price, 
                       COUNT(*) as data_points,
                       MIN(sd.timestamp) as earliest_date,
                       MAX(sd.timestamp) as latest_date
                FROM stock_symbols ss
                JOIN stock_data sd ON ss.symbol = sd.symbol
                WHERE sd.close BETWEEN 10 AND 100
                GROUP BY ss.symbol, ss.exchange, ss.sector, sd.close
                HAVING COUNT(*) >= ?
                ORDER BY COUNT(*) DESC, sd.close
            ''', (min_data_points,))
            
            candidates = []
            for row in cursor.fetchall():
                symbol, exchange, sector, price, points, earliest, latest = row
                
                candidates.append({
                    'symbol': symbol,
                    'exchange': exchange, 
                    'sector': sector or 'Unknown',
                    'current_price': price,
                    'data_points': points,
                    'earliest_date': earliest,
                    'latest_date': latest
                })
            
            conn.close()
            
            print(f"✅ Found {len(candidates)} optimization candidates")
            
            if candidates:
                print(f"\nTop candidates:")
                print("Symbol | Exchange | Price   | Days | Sector")
                print("-" * 50)
                for candidate in candidates[:10]:
                    print(f"{candidate['symbol']:6} | {candidate['exchange']:8} | ${candidate['current_price']:6.2f} | {candidate['data_points']:4} | {candidate['sector'][:12]}")
            
            return candidates
            
        except Exception as e:
            print(f"❌ Error getting optimization candidates: {e}")
            return []
    
    def optimize_single_stock_comprehensive(self, symbol: str, days_back: int = 252) -> Dict:
        """
        Run comprehensive optimization for a single stock using common EMA pairs
        
        Args:
            symbol: Stock symbol to optimize
            days_back: Historical data period to use
            
        Returns:
            Optimization results dictionary
        """
        
        print(f"🔬 Optimizing {symbol} with {len(self.common_ema_pairs)} professional EMA combinations...")
        
        # Get historical data
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        stock_data = self.data_manager.get_stock_data(symbol, start_date, end_date)
        
        if stock_data is None or len(stock_data) < 50:
            print(f"❌ Insufficient data for {symbol}")
            return {'symbol': symbol, 'error': 'Insufficient data'}
        
        stock_data = stock_data.set_index('date')
        results = []
        
        # Test each EMA combination
        for fast, slow in self.common_ema_pairs:
            if fast >= slow:  # Skip invalid combinations
                continue
                
            try:
                # Run backtest for this combination
                metrics = self.parameter_engine.backtest_strategy(
                    symbol, stock_data, fast, slow
                )
                
                result = {
                    'symbol': symbol,
                    'ema_fast': fast,
                    'ema_slow': slow,
                    'combination_name': f'EMA({fast},{slow})',
                    **metrics
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"   ❌ Error testing EMA({fast},{slow}): {e}")
                continue
        
        # Sort by total return (best first)
        results.sort(key=lambda x: x.get('total_return', -999), reverse=True)
        
        if results:
            best = results[0]
            print(f"   🏆 Best: EMA({best['ema_fast']},{best['ema_slow']}) = {best['total_return']:.1%} return")
            return {
                'symbol': symbol,
                'best_combination': best,
                'all_results': results,
                'total_combinations_tested': len(results)
            }
        else:
            print(f"   ❌ No valid results for {symbol}")
            return {'symbol': symbol, 'error': 'No valid results'}
    
    def run_comprehensive_optimization(self, max_stocks: int = 20, 
                                     parallel_workers: int = 3) -> Dict:
        """
        Run comprehensive EMA optimization across multiple stocks
        
        Args:
            max_stocks: Maximum number of stocks to optimize
            parallel_workers: Number of parallel optimization threads
            
        Returns:
            Comprehensive optimization results
        """
        
        print("🚀 COMPREHENSIVE EMA OPTIMIZATION")
        print("=" * 50)
        print(f"Testing {len(self.common_ema_pairs)} professional EMA combinations")
        print(f"Parallel workers: {parallel_workers}")
        print(f"Maximum stocks: {max_stocks}")
        print()
        
        # Get candidates
        candidates = self.get_optimization_candidates(min_data_points=30)
        
        if not candidates:
            return {'error': 'No suitable candidates for optimization'}
        
        # Limit to requested number
        candidates = candidates[:max_stocks]
        
        print(f"\n🎯 Optimizing {len(candidates)} stocks...")
        print("=" * 40)
        
        # Run optimization in parallel
        optimization_results = {}
        
        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            # Submit optimization tasks
            future_to_symbol = {
                executor.submit(self.optimize_single_stock_comprehensive, candidate['symbol']): candidate['symbol']
                for candidate in candidates
            }
            
            # Process completed optimizations
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                try:
                    result = future.result()
                    optimization_results[symbol] = result
                    
                    if 'error' not in result:
                        print(f"✅ {symbol}: Completed")
                    else:
                        print(f"❌ {symbol}: {result['error']}")
                        
                except Exception as e:
                    print(f"💥 {symbol}: Exception - {e}")
                    optimization_results[symbol] = {'symbol': symbol, 'error': str(e)}
        
        # Analyze results
        successful_optimizations = {k: v for k, v in optimization_results.items() 
                                  if 'error' not in v}
        
        print(f"\n📊 OPTIMIZATION COMPLETE")
        print("=" * 30)
        print(f"✅ Successful optimizations: {len(successful_optimizations)}")
        print(f"❌ Failed optimizations: {len(optimization_results) - len(successful_optimizations)}")
        
        if successful_optimizations:
            # Find best performing combinations overall
            all_best_results = []
            for result in successful_optimizations.values():
                if 'best_combination' in result:
                    all_best_results.append(result['best_combination'])
            
            # Sort by performance
            all_best_results.sort(key=lambda x: x.get('total_return', -999), reverse=True)
            
            print(f"\n🏆 TOP 10 OPTIMIZED STOCKS:")
            print("Rank | Symbol | Best EMA      | Return  | Sharpe | Win Rate")
            print("-" * 65)
            
            for i, best in enumerate(all_best_results[:10], 1):
                return_pct = best.get('total_return', 0) * 100
                sharpe = best.get('sharpe_ratio', 0)
                win_rate = best.get('win_rate', 0) * 100
                
                print(f"{i:4} | {best['symbol']:6} | EMA({best['ema_fast']:2},{best['ema_slow']:2})     | {return_pct:6.1f}% | {sharpe:6.2f} | {win_rate:6.1f}%")
            
            # Analyze most popular EMA combinations
            ema_popularity = {}
            for result in successful_optimizations.values():
                if 'best_combination' in result:
                    best = result['best_combination']
                    pair = (best['ema_fast'], best['ema_slow'])
                    ema_popularity[pair] = ema_popularity.get(pair, 0) + 1
            
            print(f"\n📈 MOST SUCCESSFUL EMA COMBINATIONS:")
            print("EMA Pair    | Stocks | Description")
            print("-" * 40)
            
            for (fast, slow), count in sorted(ema_popularity.items(), 
                                            key=lambda x: x[1], reverse=True)[:8]:
                # Categorize the combination
                if fast <= 10 and slow <= 25:
                    description = "Short-term/Scalping"
                elif fast <= 25 and slow <= 60:
                    description = "Medium-term/Swing"
                elif slow >= 100:
                    description = "Long-term/Trend"
                else:
                    description = "General trading"
                
                print(f"EMA({fast:2},{slow:2})   | {count:6} | {description}")
        
        return {
            'total_stocks': len(candidates),
            'successful_optimizations': len(successful_optimizations),
            'failed_optimizations': len(optimization_results) - len(successful_optimizations),
            'optimization_results': optimization_results,
            'best_performers': all_best_results[:10] if 'all_best_results' in locals() else [],
            'ema_combinations_tested': len(self.common_ema_pairs),
            'summary_stats': self._generate_summary_stats(successful_optimizations)
        }
    
    def _generate_summary_stats(self, successful_optimizations: Dict) -> Dict:
        """Generate summary statistics from optimization results"""
        
        if not successful_optimizations:
            return {}
        
        all_returns = []
        all_sharpe = []
        all_win_rates = []
        
        for result in successful_optimizations.values():
            if 'best_combination' in result:
                best = result['best_combination']
                all_returns.append(best.get('total_return', 0))
                all_sharpe.append(best.get('sharpe_ratio', 0))
                all_win_rates.append(best.get('win_rate', 0))
        
        return {
            'avg_return': np.mean(all_returns) if all_returns else 0,
            'median_return': np.median(all_returns) if all_returns else 0,
            'avg_sharpe': np.mean(all_sharpe) if all_sharpe else 0,
            'avg_win_rate': np.mean(all_win_rates) if all_win_rates else 0,
            'profitable_strategies': sum(1 for r in all_returns if r > 0),
            'total_strategies': len(all_returns)
        }
    
    def save_optimization_results(self, results: Dict):
        """Save comprehensive optimization results to database"""
        
        if 'optimization_results' not in results:
            return
        
        print(f"\n💾 Saving optimization results to database...")
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            # Clear existing optimization results for fresh run
            cursor.execute("DELETE FROM optimization_results")
            print("🗑️  Cleared previous optimization results")
            
            saved_count = 0
            for symbol, optimization_result in results['optimization_results'].items():
                if 'error' in optimization_result:
                    continue
                
                if 'all_results' in optimization_result:
                    for result in optimization_result['all_results']:
                        # Create parameter set JSON
                        param_set = json.dumps({
                            'ema_fast': result['ema_fast'],
                            'ema_slow': result['ema_slow'],
                            'symbol': result['symbol'],
                            'combination_name': result['combination_name']
                        })
                        
                        cursor.execute('''
                            INSERT INTO optimization_results 
                            (parameter_set, backtest_period, total_return, sharpe_ratio, max_drawdown, win_rate)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            param_set,
                            '252_days',
                            result.get('total_return', 0),
                            result.get('sharpe_ratio', 0),
                            result.get('max_drawdown', 0),
                            result.get('win_rate', 0)
                        ))
                        saved_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Saved {saved_count} optimization results")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

# Convenience function
def run_comprehensive_ema_optimization(max_stocks: int = 20) -> Dict:
    """
    Run comprehensive EMA optimization on target stocks
    
    Args:
        max_stocks: Maximum number of stocks to optimize
        
    Returns:
        Optimization results dictionary
    """
    
    optimizer = ComprehensiveEMAOptimizer()
    results = optimizer.run_comprehensive_optimization(max_stocks=max_stocks)
    
    # Save results to database
    optimizer.save_optimization_results(results)
    
    return results