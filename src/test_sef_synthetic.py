#!/usr/bin/env python3
"""
SEF Test with Synthetic Data
Demonstrates Strategy Optimization Framework without external API dependencies
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.optimization.parameter_sweep import ParameterSweepEngine;
from src.optimization.visualization import OptimizationVisualizer;
from src.indicators.technical import TechnicalIndicators;
from src.config.settings import get_config;

def generate_synthetic_stock_data( symbol: str, days: int = 252, 
                                  base_price: float = 50.0, volatility: float = 0.02,
                                  trend: float = 0.0005 ) -> pd.DataFrame:
    """
    Generate realistic synthetic stock data for testing
    
    Args:
        symbol: Stock symbol
        days: Number of days of data
        base_price: Starting price
        volatility: Daily volatility (std dev)
        trend: Daily trend (drift)
        
    Returns:
        DataFrame with OHLCV data
    """
    
    # Set seed for reproducible results
    np.random.seed( hash( symbol ) % 2**32 );
    
    # Generate dates
    end_date = date.today();
    start_date = end_date - timedelta( days=days );
    dates = pd.date_range( start=start_date, end=end_date, freq='D' );
    
    # Generate price series using random walk with trend
    returns = np.random.normal( trend, volatility, len( dates ) );
    
    # Create price series
    prices = [base_price];
    for ret in returns[1:]:
        new_price = prices[-1] * ( 1 + ret );
        prices.append( max( new_price, 5.0 ) );  # Keep prices above $5
    
    # Generate OHLCV data
    data = [];
    for i, ( date_val, close_price ) in enumerate( zip( dates, prices ) ):
        # Create realistic OHLC from close price
        daily_range = close_price * np.random.uniform( 0.01, 0.05 );  # 1-5% daily range
        
        high = close_price + np.random.uniform( 0, daily_range );
        low = close_price - np.random.uniform( 0, daily_range );
        
        # Ensure open is within range
        open_price = np.random.uniform( low, high );
        
        # Generate realistic volume
        volume = int( np.random.uniform( 100000, 2000000 ) );
        
        data.append({
            'date': date_val.date(),
            'symbol': symbol,
            'open': round( open_price, 2 ),
            'high': round( high, 2 ),
            'low': round( low, 2 ),
            'close': round( close_price, 2 ),
            'volume': volume
        });
    
    return pd.DataFrame( data );

def test_synthetic_optimization():
    """Test optimization with synthetic data"""
    
    print( "🧪 Testing SEF with Synthetic Data" );
    print( "=" * 60 );
    
    # Create synthetic data for multiple stocks
    synthetic_stocks = {
        'AAPL': generate_synthetic_stock_data( 'AAPL', 252, 150.0, 0.025, 0.0008 ),  # Growth stock
        'MSFT': generate_synthetic_stock_data( 'MSFT', 252, 300.0, 0.020, 0.0006 ),  # Stable growth
        'TSLA': generate_synthetic_stock_data( 'TSLA', 252, 200.0, 0.035, 0.0010 ),  # Volatile growth
        'GOOGL': generate_synthetic_stock_data( 'GOOGL', 252, 2500.0, 0.022, 0.0007 ),  # High price
        'AMD': generate_synthetic_stock_data( 'AMD', 252, 100.0, 0.030, 0.0005 )     # Volatile
    };
    
    print( f"📊 Generated synthetic data for {len( synthetic_stocks )} stocks" );
    for symbol, data in synthetic_stocks.items():
        price_range = f"${data['close'].min():.2f} - ${data['close'].max():.2f}";
        total_return = ( data['close'].iloc[-1] / data['close'].iloc[0] - 1 ) * 100;
        print( f"   {symbol}: {len( data )} days, {price_range}, {total_return:+.1f}% return" );
    
    # Test technical indicators on synthetic data
    print( "\n📈 Testing Technical Indicators..." );
    indicators = TechnicalIndicators();
    
    test_stock = synthetic_stocks['AAPL'];
    test_indicators = indicators.calculate_all_indicators( 'AAPL', test_stock.set_index( 'date' ) );
    
    print( f"✅ Calculated indicators for AAPL:" );
    for name, series in test_indicators.items():
        valid_count = series.dropna().shape[0];
        if valid_count > 0:
            latest = series.dropna().iloc[-1];
            print( f"   {name}: {valid_count} values, latest: {latest:.3f}" );
    
    # Test parameter optimization
    print( "\n🔍 Testing Parameter Optimization..." );
    engine = ParameterSweepEngine();
    
    # Generate focused parameter grid for testing
    param_grid = engine.generate_parameter_grid(
        ema_fast_range=( 8, 12 ),
        ema_slow_range=( 18, 25 ),
        step=2
    );
    
    print( f"📊 Testing {len( param_grid )} parameter combinations on each stock" );
    
    # Run optimization on synthetic data (monkey patch data fetching)
    original_get_stock_data = engine.data_manager.get_stock_data;
    
    def mock_get_stock_data( symbol, start_date, end_date, **kwargs ):
        """Mock data fetching to use synthetic data"""
        if symbol in synthetic_stocks:
            data = synthetic_stocks[symbol];
            # Filter by date range
            filtered_data = data[
                ( pd.to_datetime( data['date'] ).dt.date >= start_date ) &
                ( pd.to_datetime( data['date'] ).dt.date <= end_date )
            ].copy();
            return filtered_data if not filtered_data.empty else None;
        return None;
    
    engine.data_manager.get_stock_data = mock_get_stock_data;
    
    # Run optimization for each stock
    all_results = {};
    for symbol in ['AAPL', 'MSFT', 'TSLA']:  # Test subset for speed
        print( f"\n🔍 Optimizing {symbol}..." );
        results = engine.optimize_single_stock( symbol, param_grid[:15], days_back=180 );
        
        if results:
            best = results[0];
            print( f"✅ {symbol} best result:" );
            print( f"   EMA({best['ema_fast']},{best['ema_slow']}) = {best['total_return']:.2%}" );
            print( f"   Sharpe: {best['sharpe_ratio']:.2f}, Win Rate: {best['win_rate']:.1%}" );
            print( f"   Trades: {best['num_trades']}, Drawdown: {best['max_drawdown']:.1%}" );
            
            all_results[symbol] = results;
        else:
            print( f"❌ No results for {symbol}" );
    
    # Test visualization
    print( "\n📊 Testing Visualization..." );
    
    if all_results:
        visualizer = OptimizationVisualizer();
        
        # Create output directory
        output_dir = "/ARCHIVE/Programming/btfd/optimization_results";
        os.makedirs( output_dir, exist_ok=True );
        
        # Generate visualizations for each stock
        for symbol, results in all_results.items():
            print( f"   Creating heatmap for {symbol}..." );
            
            # Performance heatmap
            heatmap = visualizer.create_performance_heatmap( symbol, results, 'total_return' );
            heatmap_path = visualizer.save_visualization( heatmap, f"{symbol.lower()}_heatmap" );
            
            # Multi-metric dashboard
            dashboard = visualizer.create_multi_metric_dashboard( symbol, results );
            dashboard_path = visualizer.save_visualization( dashboard, f"{symbol.lower()}_dashboard" );
            
            print( f"   💾 {symbol}: Heatmap & Dashboard saved" );
        
        # Multi-stock comparison
        if len( all_results ) > 1:
            print( f"   Creating multi-stock comparison..." );
            
            # Mock saved results for comparison
            engine.get_saved_results = lambda symbol: pd.DataFrame( all_results.get( symbol, [] ) );
            
            comparison = visualizer.create_parameter_comparison( list( all_results.keys() ) );
            comparison_path = visualizer.save_visualization( comparison, "synthetic_comparison" );
            
            print( f"   💾 Multi-stock comparison saved: {os.path.basename( comparison_path )}" );
        
        print( f"\n🎉 All visualizations saved to: {output_dir}" );
    
    # Summary statistics
    print( "\n📊 Optimization Summary:" );
    
    if all_results:
        all_best = [];
        for symbol, results in all_results.items():
            if results:
                best = results[0];
                all_best.append( best );
        
        if all_best:
            avg_return = np.mean( [r['total_return'] for r in all_best] );
            avg_sharpe = np.mean( [r['sharpe_ratio'] for r in all_best] );
            avg_win_rate = np.mean( [r['win_rate'] for r in all_best] );
            
            print( f"   Average Best Return: {avg_return:.2%}" );
            print( f"   Average Sharpe Ratio: {avg_sharpe:.2f}" );
            print( f"   Average Win Rate: {avg_win_rate:.1%}" );
            
            # Show parameter distribution
            fast_emas = [r['ema_fast'] for r in all_best];
            slow_emas = [r['ema_slow'] for r in all_best];
            
            print( f"   Common Fast EMA: {max( set( fast_emas ), key=fast_emas.count )}" );
            print( f"   Common Slow EMA: {max( set( slow_emas ), key=slow_emas.count )}" );
    
    # Restore original function
    engine.data_manager.get_stock_data = original_get_stock_data;
    
    return len( all_results ) > 0;

def demonstrate_sef_capabilities():
    """Comprehensive SEF capability demonstration"""
    
    print( "\n🚀 SEF Capabilities Demonstration" );
    print( "=" * 60 );
    
    capabilities = [
        "✅ Multi-stock parameter optimization",
        "✅ Interactive P/L heatmaps (Plotly)",
        "✅ Multi-metric dashboards (Return, Sharpe, Win Rate, Drawdown)",
        "✅ Parameter comparison across stocks", 
        "✅ RSI(14) integration with crossover detection",
        "✅ EMA crossover strategy backtesting",
        "✅ Database persistence of optimization results",
        "✅ Synthetic data generation for testing",
        "✅ Comprehensive performance metrics calculation",
        "✅ HTML visualization export"
    ];
    
    for capability in capabilities:
        print( f"   {capability}" );
    
    print( "\n📋 SEF Workflow:" );
    workflow_steps = [
        "1. 📊 Generate parameter grid (EMA fast/slow combinations)",
        "2. 📡 Fetch historical stock data (Yahoo Finance + Alpha Vantage fallback)",
        "3. 📈 Calculate technical indicators (RSI, EMA, MACD)",
        "4. 🔍 Run parameter sweep optimization",
        "5. 📊 Generate performance metrics (return, Sharpe, win rate, drawdown)",
        "6. 💾 Store results in SQLite database",
        "7. 🎨 Create interactive visualizations (heatmaps, dashboards)",
        "8. 📄 Export HTML reports for analysis",
        "9. 🏆 Identify optimal parameters for production use"
    ];
    
    for step in workflow_steps:
        print( f"   {step}" );
    
    print( "\n🎯 Production Readiness:" );
    production_features = [
        "✅ Configurable parameter ranges",
        "✅ Rate limiting for API calls", 
        "✅ Data caching for performance",
        "✅ Error handling and fallback data sources",
        "✅ Modular architecture for easy extension",
        "✅ Comprehensive logging and monitoring",
        "✅ Backup system for code protection"
    ];
    
    for feature in production_features:
        print( f"   {feature}" );

def main():
    """Main demonstration function"""
    
    print( "🎯 BTFD Strategy Optimization Framework (SEF)" );
    print( "🔬 Synthetic Data Testing & Demonstration" );
    print( "=" * 60 );
    
    # Configuration check
    config = get_config();
    print( f"⚙️  Configuration:" );
    print( f"   Project Root: {config.project_root_path}" );
    print( f"   Database: {config.database_path}" );
    
    # Run synthetic data test
    try:
        success = test_synthetic_optimization();
        
        if success:
            print( "\n✅ SEF synthetic data test PASSED!" );
            demonstrate_sef_capabilities();
            
            print( "\n🚀 Next Steps:" );
            next_steps = [
                "1. Review generated visualizations in optimization_results/",
                "2. Adjust parameter ranges based on heatmap analysis",
                "3. Test with real market data when API access is available",
                "4. Integrate with Daily Scanner for production signals",
                "5. Deploy cron job for automated optimization runs"
            ];
            
            for step in next_steps:
                print( f"   {step}" );
                
        else:
            print( "\n❌ SEF synthetic data test FAILED!" );
            
    except Exception as e:
        print( f"\n❌ SEF test failed with error: {e}" );
        import traceback;
        traceback.print_exc();
    
    print( "\n🎉 SEF demonstration complete!" );

if __name__ == "__main__":
    main();