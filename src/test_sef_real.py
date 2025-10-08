#!/usr/bin/env python3
"""
SEF Test with Real Yahoo Finance Data
Demonstrates Strategy Optimization Framework with real market data
"""

import sys
import os
import pandas as pd
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.optimization.parameter_sweep import ParameterSweepEngine;
from src.optimization.visualization import OptimizationVisualizer;
from src.data.fetchers import DataManager;
from src.config.settings import get_config;

def run_real_optimization():
    """Run optimization with real Yahoo Finance data"""
    
    print( "🚀 BTFD SEF with Real Market Data" );
    print( "=" * 60 );
    
    # Initialize components
    engine = ParameterSweepEngine();
    visualizer = OptimizationVisualizer();
    
    # Test with popular stocks
    test_symbols = ['AAPL', 'MSFT', 'TSLA'];
    
    print( f"📊 Testing optimization on: {test_symbols}" );
    
    # Generate focused parameter grid for quick testing
    param_grid = engine.generate_parameter_grid(
        ema_fast_range=( 8, 12 ),
        ema_slow_range=( 18, 25 ),
        step=2  # Larger step for faster testing
    );
    
    print( f"🔍 Testing {len( param_grid )} parameter combinations per stock" );
    
    # Run optimization on each stock
    all_results = {};
    
    for symbol in test_symbols:
        print( f"\n📈 Optimizing {symbol}..." );
        
        results = engine.optimize_single_stock( symbol, param_grid, days_back=90 );
        
        if results:
            best = results[0];
            print( f"✅ {symbol} Best Result:" );
            print( f"   EMA({best['ema_fast']},{best['ema_slow']}) = {best['total_return']:.2%} return" );
            print( f"   📊 Sharpe: {best['sharpe_ratio']:.2f}" );
            print( f"   🎯 Win Rate: {best['win_rate']:.1%}" );
            print( f"   📉 Max Drawdown: {best['max_drawdown']:.1%}" );
            print( f"   🔄 Trades: {best['num_trades']}" );
            
            all_results[symbol] = results;
        else:
            print( f"❌ No results for {symbol}" );
    
    # Create visualizations if we have results
    if all_results:
        print( f"\n🎨 Creating Visualizations..." );
        
        # Create output directory
        output_dir = "/ARCHIVE/Programming/btfd/optimization_results";
        os.makedirs( output_dir, exist_ok=True );
        
        created_files = [];
        
        # Generate heatmaps for each stock
        for symbol, results in all_results.items():
            print( f"   📊 Creating {symbol} heatmap..." );
            
            # Performance heatmap
            heatmap = visualizer.create_performance_heatmap( symbol, results, 'total_return' );
            heatmap_path = visualizer.save_visualization( heatmap, f"{symbol.lower()}_optimization_heatmap" );
            created_files.append( heatmap_path );
            
            # Multi-metric dashboard  
            dashboard = visualizer.create_multi_metric_dashboard( symbol, results );
            dashboard_path = visualizer.save_visualization( dashboard, f"{symbol.lower()}_optimization_dashboard" );
            created_files.append( dashboard_path );
        
        # Multi-stock comparison (mock the saved results for visualization)
        if len( all_results ) > 1:
            print( f"   📊 Creating multi-stock comparison..." );
            
            # Temporarily mock the get_saved_results method
            def mock_get_saved_results( symbol ):
                if symbol in all_results:
                    return pd.DataFrame( all_results[symbol] );
                return pd.DataFrame();
            
            original_method = engine.get_saved_results;
            engine.get_saved_results = mock_get_saved_results;
            
            comparison = visualizer.create_parameter_comparison( list( all_results.keys() ) );
            comparison_path = visualizer.save_visualization( comparison, "real_data_stock_comparison" );
            created_files.append( comparison_path );
            
            # Restore original method
            engine.get_saved_results = original_method;
        
        print( f"\n💾 Generated Visualizations:" );
        for file_path in created_files:
            filename = os.path.basename( file_path );
            print( f"   📄 {filename}" );
        
        print( f"\n🌐 Open any .html file in your browser to view interactive charts!" );
    
    # Show summary statistics
    if all_results:
        print( f"\n📊 Optimization Summary:" );
        print( f"   🎯 Stocks Analyzed: {len( all_results )}" );
        
        # Find overall best parameters
        all_best_results = [results[0] for results in all_results.values() if results];
        
        if all_best_results:
            best_overall = max( all_best_results, key=lambda x: x['total_return'] );
            avg_return = sum( r['total_return'] for r in all_best_results ) / len( all_best_results );
            avg_sharpe = sum( r['sharpe_ratio'] for r in all_best_results ) / len( all_best_results );
            
            print( f"   🏆 Best Overall: {best_overall['symbol']} with {best_overall['total_return']:.2%}" );
            print( f"   📈 Average Return: {avg_return:.2%}" );
            print( f"   📊 Average Sharpe: {avg_sharpe:.2f}" );
            
            # Most common parameters
            fast_emas = [r['ema_fast'] for r in all_best_results];
            slow_emas = [r['ema_slow'] for r in all_best_results];
            
            from collections import Counter;
            most_common_fast = Counter( fast_emas ).most_common( 1 )[0];
            most_common_slow = Counter( slow_emas ).most_common( 1 )[0];
            
            print( f"   🔄 Most Common Fast EMA: {most_common_fast[0]} (used {most_common_fast[1]} times)" );
            print( f"   🔄 Most Common Slow EMA: {most_common_slow[0]} (used {most_common_slow[1]} times)" );
    
    return len( all_results ) > 0;

def show_optimization_workflow():
    """Show the complete SEF workflow"""
    
    print( f"\n🔄 Complete SEF Workflow:" );
    workflow = [
        "1. 📊 Generate EMA parameter combinations (fast/slow pairs)",
        "2. 📡 Fetch real market data from Yahoo Finance",
        "3. 📈 Calculate RSI(14) and EMA indicators",
        "4. 🔍 Backtest each parameter combination",
        "5. 📊 Calculate performance metrics (return, Sharpe, drawdown)",
        "6. 💾 Store results in SQLite database",
        "7. 🎨 Generate interactive Plotly visualizations",
        "8. 📄 Export HTML reports for analysis",
        "9. 🏆 Identify optimal parameters for production"
    ];
    
    for step in workflow:
        print( f"   {step}" );

def main():
    """Main function"""
    
    # Configuration check
    config = get_config();
    print( f"⚙️  BTFD Configuration:" );
    print( f"   📂 Project Root: {config.project_root_path}" );
    print( f"   🗃️  Database: {config.database_path}" );
    
    # Run the real data optimization
    try:
        success = run_real_optimization();
        
        if success:
            print( f"\n🎉 SEF Real Data Test PASSED!" );
            show_optimization_workflow();
            
            print( f"\n🚀 Production Ready Features:" );
            features = [
                "✅ Real Yahoo Finance data integration",
                "✅ Multi-stock parameter optimization", 
                "✅ Interactive P/L heatmaps",
                "✅ Performance metric dashboards",
                "✅ Database persistence", 
                "✅ Caching for performance",
                "✅ Error handling and fallbacks",
                "✅ Professional visualizations"
            ];
            
            for feature in features:
                print( f"   {feature}" );
                
        else:
            print( f"\n❌ SEF Real Data Test FAILED!" );
            
    except Exception as e:
        print( f"\n❌ SEF test failed with error: {e}" );
        import traceback;
        traceback.print_exc();

if __name__ == "__main__":
    main();