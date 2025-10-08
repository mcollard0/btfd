#!/usr/bin/env python3
"""
Quick optimization test with extended data range
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.optimization.parameter_sweep import ParameterSweepEngine;
from src.data.fetchers import DataManager;
from src.indicators.technical import TechnicalIndicators;

def quick_optimization_test():
    """Quick test with more data"""
    
    print( "⚡ Quick SEF Optimization Test" );
    print( "=" * 50 );
    
    # Get a full year of data
    manager = DataManager();
    end_date = date.today();
    start_date = end_date - timedelta( days=365 );
    
    print( f"📡 Fetching AAPL data from {start_date} to {end_date}..." );
    data = manager.get_stock_data( 'AAPL', start_date, end_date, use_cache=False );
    
    if data is None:
        print( "❌ No data available" );
        return False;
    
    print( f"✅ Got {len( data )} days of AAPL data" );
    print( f"📅 Date range: {data['date'].min()} to {data['date'].max()}" );
    print( f"💰 Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}" );
    
    # Test indicators
    print( f"\n📈 Testing technical indicators..." );
    indicators = TechnicalIndicators();
    data_indexed = data.set_index( 'date' );
    
    rsi = indicators.calculate_rsi( data_indexed['close'] );
    ema_10 = indicators.calculate_ema( data_indexed['close'], 10 );
    ema_20 = indicators.calculate_ema( data_indexed['close'], 20 );
    
    print( f"   RSI(14): {rsi.dropna().shape[0]} valid values" );
    print( f"   EMA(10): {ema_10.dropna().shape[0]} valid values" );
    print( f"   EMA(20): {ema_20.dropna().shape[0]} valid values" );
    
    # Test backtest with simple parameters
    print( f"\n🔍 Testing backtest with EMA(10,20)..." );
    engine = ParameterSweepEngine();
    
    metrics = engine.backtest_strategy( 'AAPL', data_indexed, 10, 20 );
    
    print( f"📊 Backtest results:" );
    print( f"   Total Return: {metrics['total_return']:.2%}" );
    print( f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}" );
    print( f"   Win Rate: {metrics['win_rate']:.1%}" );
    print( f"   Max Drawdown: {metrics['max_drawdown']:.1%}" );
    print( f"   Number of Trades: {metrics['num_trades']}" );
    print( f"   Final Capital: ${metrics['final_capital']:.2f}" );
    
    if metrics['num_trades'] > 0:
        print( f"✅ Backtest successful with {metrics['num_trades']} trades!" );
        
        # Now test a small parameter sweep
        print( f"\n🔍 Testing parameter sweep..." );
        param_grid = [
            {'ema_fast': 8, 'ema_slow': 18, 'rsi_period': 14},
            {'ema_fast': 10, 'ema_slow': 20, 'rsi_period': 14},
            {'ema_fast': 12, 'ema_slow': 22, 'rsi_period': 14}
        ];
        
        results = [];
        for params in param_grid:
            metrics = engine.backtest_strategy( 
                'AAPL', data_indexed, 
                params['ema_fast'], params['ema_slow'] 
            );
            result = {**params, **metrics, 'symbol': 'AAPL'};
            results.append( result );
            
            print( f"   EMA({params['ema_fast']},{params['ema_slow']}): {metrics['total_return']:.2%} return, {metrics['num_trades']} trades" );
        
        # Sort by return
        results.sort( key=lambda x: x['total_return'], reverse=True );
        best = results[0];
        
        print( f"\n🏆 Best parameters: EMA({best['ema_fast']},{best['ema_slow']}) = {best['total_return']:.2%}" );
        
        return True;
    else:
        print( f"❌ No trades generated in backtest" );
        return False;

def main():
    """Main test"""
    
    try:
        success = quick_optimization_test();
        
        if success:
            print( f"\n🎉 Quick optimization test PASSED!" );
            print( f"✅ SEF is working correctly with real data" );
        else:
            print( f"\n❌ Quick optimization test FAILED" );
            
    except Exception as e:
        print( f"\n❌ Test failed with error: {e}" );
        import traceback;
        traceback.print_exc();

if __name__ == "__main__":
    main();