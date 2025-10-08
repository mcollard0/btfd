#!/usr/bin/env python3
"""
Strategy Optimization Framework (SEF) Test & Demo
Demonstrates parameter optimization and visualization capabilities
"""

import sys
import os
import pandas as pd
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.optimization.parameter_sweep import ParameterSweepEngine, quick_optimization, get_best_parameters;
from src.optimization.visualization import OptimizationVisualizer, create_quick_heatmap, create_multi_stock_comparison;
from src.data.fetchers import DataManager;
from src.config.settings import get_config;

def test_data_fetching():
    """Test data fetching capabilities"""
    
    print( "🧪 Testing Data Fetching..." );
    print( "=" * 50 );
    
    data_manager = DataManager();
    
    # Test single stock data fetch
    print( "📡 Fetching AAPL data (last 30 days)..." );
    aapl_data = data_manager.get_stock_data( 
        'AAPL', 
        date.today() - timedelta( days=30 ), 
        date.today()
    );
    
    if aapl_data is not None:
        print( f"✅ AAPL: Fetched {len( aapl_data )} days of data" );
        print( f"   Price range: ${aapl_data['close'].min():.2f} - ${aapl_data['close'].max():.2f}" );
        print( f"   Date range: {aapl_data['date'].min()} to {aapl_data['date'].max()}" );
    else:
        print( "❌ Failed to fetch AAPL data" );
    
    # Test stock list generation
    print( "\n📋 Getting suitable stocks for option trading..." );
    suitable_stocks = data_manager.get_stock_list();
    print( f"✅ Found {len( suitable_stocks )} suitable stocks: {suitable_stocks[:10]}" );
    
    return aapl_data is not None and len( suitable_stocks ) > 0;

def test_parameter_sweep():
    """Test parameter sweep optimization"""
    
    print( "\n🧪 Testing Parameter Sweep..." );
    print( "=" * 50 );
    
    engine = ParameterSweepEngine();
    
    # Generate parameter grid
    param_grid = engine.generate_parameter_grid(
        ema_fast_range=( 5, 12 ),
        ema_slow_range=( 15, 22 ),
        step=2  # Larger step for faster testing
    );
    
    print( f"📊 Testing with {len( param_grid )} parameter combinations" );
    
    # Test single stock optimization
    print( "\n🔍 Running single-stock optimization (AAPL)..." );
    aapl_results = engine.optimize_single_stock( 'AAPL', param_grid[:20], days_back=90 );  # Limited for testing
    
    if aapl_results:
        best_result = aapl_results[0];
        print( f"✅ Best result for AAPL:" );
        print( f"   EMA({best_result['ema_fast']}, {best_result['ema_slow']})" );
        print( f"   Total Return: {best_result['total_return']:.2%}" );
        print( f"   Sharpe Ratio: {best_result['sharpe_ratio']:.2f}" );
        print( f"   Win Rate: {best_result['win_rate']:.1%}" );
        print( f"   Max Drawdown: {best_result['max_drawdown']:.1%}" );
        print( f"   Number of Trades: {best_result['num_trades']}" );
    else:
        print( "❌ No results from optimization" );
    
    return len( aapl_results ) > 0 if aapl_results else False;

def test_visualization():
    """Test visualization capabilities"""
    
    print( "\n🧪 Testing Visualization..." );
    print( "=" * 50 );
    
    visualizer = OptimizationVisualizer();
    engine = ParameterSweepEngine();
    
    # Check if we have saved results
    saved_results = engine.get_saved_results( 'AAPL' );
    
    if saved_results.empty:
        print( "ℹ️  No saved results found, creating sample optimization first..." );
        
        # Run a quick optimization
        param_grid = engine.generate_parameter_grid(
            ema_fast_range=( 8, 12 ),
            ema_slow_range=( 18, 22 ),
            step=2
        );
        
        results = engine.optimize_single_stock( 'AAPL', param_grid[:15], days_back=60 );
        if not results:
            print( "❌ Could not generate optimization results" );
            return False;
    
    # Get results for visualization
    saved_results = engine.get_saved_results( 'AAPL' );
    if not saved_results.empty:
        results = saved_results.to_dict( 'records' );
        
        print( f"📊 Creating visualizations with {len( results )} data points..." );
        
        # Test heatmap creation
        try:
            heatmap = visualizer.create_performance_heatmap( 'AAPL', results );
            print( "✅ Performance heatmap created successfully" );
            
            # Test dashboard creation
            dashboard = visualizer.create_multi_metric_dashboard( 'AAPL', results );
            print( "✅ Multi-metric dashboard created successfully" );
            
            # Save visualizations
            output_dir = visualizer.config.project_root_path + "/optimization_results";
            os.makedirs( output_dir, exist_ok=True );
            
            heatmap_path = visualizer.save_visualization( heatmap, "aapl_heatmap" );
            dashboard_path = visualizer.save_visualization( dashboard, "aapl_dashboard" );
            
            print( f"💾 Visualizations saved:" );
            print( f"   Heatmap: {heatmap_path}" );
            print( f"   Dashboard: {dashboard_path}" );
            
            return True;
            
        except Exception as e:
            print( f"❌ Visualization error: {e}" );
            return False;
    else:
        print( "❌ No results available for visualization" );
        return False;

def demo_quick_optimization():
    """Demonstrate quick optimization workflow"""
    
    print( "\n🚀 Demo: Quick Optimization Workflow" );
    print( "=" * 50 );
    
    # Run quick optimization on a few stocks
    print( "🔄 Running quick optimization on popular stocks..." );
    
    test_symbols = ['AAPL', 'MSFT', 'GOOGL'];  # Limited for demo
    
    try:
        results = quick_optimization( test_symbols, max_stocks=2 );  # Limit to 2 for speed
        
        print( f"\n📈 Optimization Results:" );
        for symbol, symbol_results in results.items():
            if symbol_results:
                best = symbol_results[0];
                print( f"\n{symbol}:" );
                print( f"   Best EMA: ({best['ema_fast']}, {best['ema_slow']})" );
                print( f"   Return: {best['total_return']:.2%}" );
                print( f"   Sharpe: {best['sharpe_ratio']:.2f}" );
                print( f"   Trades: {best['num_trades']}" );
        
        # Create comparison visualization
        if len( results ) > 1:
            print( "\n📊 Creating multi-stock comparison..." );
            comparison_fig = create_multi_stock_comparison( list( results.keys() ) );
            
            visualizer = OptimizationVisualizer();
            comparison_path = visualizer.save_visualization( comparison_fig, "multi_stock_comparison" );
            print( f"💾 Comparison chart saved: {comparison_path}" );
        
        return True;
        
    except Exception as e:
        print( f"❌ Demo error: {e}" );
        return False;

def show_database_stats():
    """Show statistics about cached data"""
    
    print( "\n📊 Database Statistics" );
    print( "=" * 50 );
    
    config = get_config();
    
    try:
        conn = config.get_database_connection();
        cursor = conn.cursor();
        
        # Stock data statistics
        cursor.execute( "SELECT COUNT(*), COUNT(DISTINCT symbol) FROM stock_data" );
        stock_count, unique_stocks = cursor.fetchone();
        print( f"📈 Stock Data: {stock_count:,} records for {unique_stocks} symbols" );
        
        # Technical indicators statistics
        cursor.execute( "SELECT COUNT(*), COUNT(DISTINCT symbol) FROM technical_indicators" );
        indicator_count, indicator_stocks = cursor.fetchone();
        print( f"📊 Technical Indicators: {indicator_count:,} records for {indicator_stocks} symbols" );
        
        # Optimization results statistics
        cursor.execute( "SELECT COUNT(*), COUNT(DISTINCT json_extract(parameter_set, '$.symbol')) FROM optimization_results" );
        opt_count, opt_stocks = cursor.fetchone();
        print( f"🎯 Optimization Results: {opt_count:,} results for {opt_stocks} symbols" );
        
        # Top performing parameters
        cursor.execute( """
            SELECT json_extract(parameter_set, '$.symbol') as symbol,
                   json_extract(parameter_set, '$.ema_fast') as ema_fast,
                   json_extract(parameter_set, '$.ema_slow') as ema_slow,
                   total_return
            FROM optimization_results 
            ORDER BY total_return DESC 
            LIMIT 5
        """ );
        
        top_results = cursor.fetchall();
        if top_results:
            print( f"\n🏆 Top 5 Parameter Combinations:" );
            for i, (symbol, fast, slow, ret) in enumerate( top_results ):
                print( f"   {i+1}. {symbol}: EMA({fast},{slow}) = {float(ret):.2%}" );
        
        conn.close();
        
    except Exception as e:
        print( f"❌ Database error: {e}" );

def main():
    """Main test function"""
    
    print( "🎯 BTFD Strategy Optimization Framework (SEF) Test Suite" );
    print( "=" * 60 );
    
    # Test configuration
    config = get_config();
    print( f"⚙️  Configuration:" );
    print( f"   Project Root: {config.project_root_path}" );
    print( f"   Database: {config.database_path}" );
    
    api_key = config.get_api_key( 'alphavantage' );
    if api_key:
        print( f"   API Key: {api_key[:8]}..." );
    else:
        print( f"   API Key: Not found" );
    
    # Run tests
    tests = [
        ( "Data Fetching", test_data_fetching ),
        ( "Parameter Sweep", test_parameter_sweep ),
        ( "Visualization", test_visualization ),
        ( "Quick Optimization Demo", demo_quick_optimization )
    ];
    
    results = {};
    
    for test_name, test_func in tests:
        print( f"\n{'='*20} {test_name} {'='*20}" );
        try:
            results[test_name] = test_func();
        except Exception as e:
            print( f"❌ {test_name} failed with error: {e}" );
            results[test_name] = False;
    
    # Show database statistics
    show_database_stats();
    
    # Summary
    print( f"\n{'='*20} TEST SUMMARY {'='*20}" );
    passed = 0;
    total = len( tests );
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED";
        print( f"   {test_name}: {status}" );
        if passed_test:
            passed += 1;
    
    print( f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)" );
    
    if passed == total:
        print( "🎉 All tests passed! SEF is ready for production use." );
    elif passed >= total * 0.5:
        print( "⚠️  Partial success. Check failed tests and retry." );
    else:
        print( "❌ Multiple test failures. Please investigate configuration." );

if __name__ == "__main__":
    main();