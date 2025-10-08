#!/usr/bin/env python3
"""
Quick test for BTFD technical indicators
Tests RSI and EMA calculations with sample data
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path for imports
import os
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.indicators.technical import TechnicalIndicators;
from src.config.settings import get_config;

def generate_sample_data( days: int = 30 ) -> pd.DataFrame:
    """Generate sample stock price data"""
    
    # Create date range
    dates = pd.date_range( start=datetime.now() - timedelta( days=days ), periods=days, freq='D' );
    
    # Generate realistic-looking price data
    np.random.seed( 42 );  # For reproducible results
    base_price = 50.0;
    
    prices = [];
    current_price = base_price;
    
    for i in range( days ):
        # Add some trend and noise
        trend = 0.1 if i > 15 else -0.1;  # Trend change
        noise = np.random.normal( 0, 2 );
        current_price = max( current_price + trend + noise, 10 );  # Keep above $10
        prices.append( current_price );
    
    # Create OHLCV data
    df = pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices], 
        'close': prices,
        'volume': np.random.randint( 100000, 1000000, days )
    });
    
    df.set_index( 'date', inplace=True );
    return df;

def test_technical_indicators():
    """Test RSI and EMA calculations"""
    
    print( "🧪 Testing BTFD Technical Indicators" );
    print( "=" * 50 );
    
    # Generate sample data
    print( "📊 Generating sample price data..." );
    sample_data = generate_sample_data( 30 );
    print( f"   Created {len( sample_data )} days of data" );
    print( f"   Price range: ${sample_data['close'].min():.2f} - ${sample_data['close'].max():.2f}" );
    
    # Initialize technical indicators
    indicators = TechnicalIndicators();
    
    # Test RSI calculation
    print( "\n📈 Testing RSI(14) calculation..." );
    rsi_series = indicators.calculate_rsi( sample_data['close'] );
    
    valid_rsi = rsi_series.dropna();
    if len( valid_rsi ) > 0:
        print( f"   ✅ RSI calculated for {len( valid_rsi )} periods" );
        print( f"   📊 RSI range: {valid_rsi.min():.1f} - {valid_rsi.max():.1f}" );
        print( f"   📊 Latest RSI: {valid_rsi.iloc[-1]:.1f}" );
        
        # Check for RSI crosses
        rsi_crosses = indicators.detect_rsi_crosses( rsi_series );
        if rsi_crosses['overbought_cross']:
            print( f"   ⚠️  Overbought cross detected: {rsi_crosses['overbought_cross']}" );
        if rsi_crosses['oversold_cross']:
            print( f"   ✅ Oversold cross detected: {rsi_crosses['oversold_cross']}" );
        if not rsi_crosses['overbought_cross'] and not rsi_crosses['oversold_cross']:
            print( f"   ℹ️  No recent RSI crosses detected" );
    else:
        print( "   ❌ No valid RSI values calculated" );
    
    # Test EMA calculations
    print( "\n📈 Testing EMA calculations..." );
    ema_10 = indicators.calculate_ema( sample_data['close'], 10 );
    ema_20 = indicators.calculate_ema( sample_data['close'], 20 );
    
    valid_ema10 = ema_10.dropna();
    valid_ema20 = ema_20.dropna();
    
    if len( valid_ema10 ) > 0 and len( valid_ema20 ) > 0:
        print( f"   ✅ EMA(10): {len( valid_ema10 )} values, latest: ${valid_ema10.iloc[-1]:.2f}" );
        print( f"   ✅ EMA(20): {len( valid_ema20 )} values, latest: ${valid_ema20.iloc[-1]:.2f}" );
        
        # Check for EMA crossovers
        crossovers = indicators.detect_ema_crossovers( ema_10, ema_20 );
        if crossovers:
            for cross in crossovers:
                signal_type = "🟢 Bullish" if cross['type'] == 'bullish' else "🔴 Bearish";
                print( f"   {signal_type} crossover on {cross['date']}" );
        else:
            print( f"   ℹ️  No recent EMA crossovers detected" );
    else:
        print( "   ❌ EMA calculations failed" );
    
    # Test all indicators together
    print( "\n📊 Testing complete indicator calculation..." );
    all_indicators = indicators.calculate_all_indicators( 'TEST', sample_data, ema_fast=10, ema_slow=20 );
    
    print( f"   ✅ Calculated {len( all_indicators )} indicator series:" );
    for name, series in all_indicators.items():
        valid_count = series.dropna().shape[0];
        if valid_count > 0:
            latest_value = series.dropna().iloc[-1];
            print( f"      {name}: {valid_count} values, latest: {latest_value:.3f}" );
    
    # Test configuration
    print( "\n⚙️  Testing configuration..." );
    config = get_config();
    print( f"   ✅ Project root: {config.project_root_path}" );
    print( f"   ✅ Database path: {config.database_path}" );
    
    api_key = config.get_api_key( 'alphavantage' );
    if api_key:
        print( f"   ✅ Alpha Vantage API key loaded: {api_key[:8]}..." );
    else:
        print( f"   ⚠️  Alpha Vantage API key not found" );
    
    print( "\n🎉 All tests completed!" );

if __name__ == "__main__":
    test_technical_indicators();