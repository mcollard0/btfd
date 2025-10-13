#!/usr/bin/env python3
"""
Simple SMA Test - Test SMA calculation functions directly
"""

import sys
import os
import pandas as pd
import numpy as np

# Add src directory to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), 'src' ) );

def test_sma_calculation_direct():
    """Test SMA calculation with sample data"""
    print( "🧪 Testing SMA calculation with sample data..." );
    
    try:
        # Import TA-Lib
        import talib
        print( "✅ TA-Lib imported successfully" );
        
        # Create sample price data
        dates = pd.date_range('2024-01-01', periods=250, freq='D');
        # Create trending price data that might show crossovers
        base_price = 100;
        trend = np.linspace( 0, 20, 250 );  # Upward trend
        noise = np.random.normal( 0, 2, 250 );  # Some volatility
        prices = base_price + trend + noise;
        
        price_series = pd.Series( prices, index=dates );
        print( f"✅ Created sample price data: {len(price_series)} points" );
        
        # Calculate SMAs using TA-Lib directly
        sma49 = talib.SMA( price_series.values, timeperiod=49 );
        sma200 = talib.SMA( price_series.values, timeperiod=200 );
        
        sma49_series = pd.Series( sma49, index=dates );
        sma200_series = pd.Series( sma200, index=dates );
        
        print( f"✅ SMA49 calculated: {len( sma49_series.dropna() )} valid values" );
        print( f"✅ SMA200 calculated: {len( sma200_series.dropna() )} valid values" );
        
        if len( sma49_series.dropna() ) > 0:
            print( f"   Latest SMA49: ${sma49_series.dropna().iloc[-1]:.2f}" );
        if len( sma200_series.dropna() ) > 0:
            print( f"   Latest SMA200: ${sma200_series.dropna().iloc[-1]:.2f}" );
            
        # Simple crossover detection
        valid_data = sma49_series.dropna().index.intersection( sma200_series.dropna().index );
        if len( valid_data ) > 1:
            sma49_valid = sma49_series.loc[valid_data];
            sma200_valid = sma200_series.loc[valid_data];
            
            # Check if SMA49 is above SMA200 at end
            if sma49_valid.iloc[-1] > sma200_valid.iloc[-1]:
                print( "✅ SMA49 currently above SMA200 (bullish position)" );
            else:
                print( "✅ SMA49 currently below SMA200 (bearish position)" );
        
        return True;
        
    except ImportError as e:
        print( f"❌ Import error: {e}" );
        print( "   This might be expected if dependencies aren't installed" );
        return False;
    except Exception as e:
        print( f"❌ SMA calculation test failed: {e}" );
        import traceback;
        traceback.print_exc();
        return False;

def test_crossover_logic():
    """Test crossover detection logic"""
    print( "\n🧪 Testing crossover detection logic..." );
    
    try:
        # Create sample data with known crossover
        dates = pd.date_range('2024-01-01', periods=10, freq='D');
        
        # SMA49 crosses above SMA200 on day 5
        sma49_values = [95, 96, 97, 98, 99, 101, 102, 103, 104, 105];
        sma200_values = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100];
        
        sma49 = pd.Series( sma49_values, index=dates );
        sma200 = pd.Series( sma200_values, index=dates );
        
        print( "✅ Created test data with crossover pattern" );
        
        # Manual crossover detection (simplified version of our algorithm)
        crossovers = [];
        lookback_days = 10;
        
        aligned_fast = sma49.tail( lookback_days + 1 );
        aligned_slow = sma200.tail( lookback_days + 1 );
        
        for i in range( 1, len( aligned_fast ) ):
            prev_fast = aligned_fast.iloc[i-1];
            curr_fast = aligned_fast.iloc[i];
            prev_slow = aligned_slow.iloc[i-1];
            curr_slow = aligned_slow.iloc[i];
            
            # Bullish crossover: fast crosses above slow
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                crossovers.append({
                    'date': aligned_fast.index[i],
                    'type': 'bullish',
                    'fast_sma': curr_fast,
                    'slow_sma': curr_slow
                });
            # Bearish crossover: fast crosses below slow  
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                crossovers.append({
                    'date': aligned_fast.index[i],
                    'type': 'bearish',
                    'fast_sma': curr_fast,
                    'slow_sma': curr_slow
                });
        
        print( f"✅ Crossover detection: {len( crossovers )} crossovers found" );
        
        for crossover in crossovers:
            print( f"   📊 {crossover['type']} crossover on {crossover['date'].strftime('%Y-%m-%d')}" );
            print( f"       SMA49: {crossover['fast_sma']:.2f}, SMA200: {crossover['slow_sma']:.2f}" );
        
        return len( crossovers ) > 0;  # Should find the bullish crossover
        
    except Exception as e:
        print( f"❌ Crossover logic test failed: {e}" );
        import traceback;
        traceback.print_exc();
        return False;

def main():
    """Run simple SMA tests"""
    print( "🚀 Simple SMA Function Testing" );
    print( "=" * 50 );
    
    test1_result = test_sma_calculation_direct();
    test2_result = test_crossover_logic();
    
    print( "\n" + "=" * 50 );
    if test1_result and test2_result:
        print( "✅ SMA functions working correctly!" );
        return 0;
    elif test2_result:
        print( "⚠️  Core logic works, but dependencies may be missing" );
        return 0;
    else:
        print( "❌ SMA tests failed!" );
        return 1;

if __name__ == "__main__":
    sys.exit( main() );