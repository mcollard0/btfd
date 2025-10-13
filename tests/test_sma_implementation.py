#!/usr/bin/env python3
"""
Test SMA Implementation
Quick test to verify SMA calculations and crossover detection
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), 'src' ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.indicators.technical import TechnicalIndicators;
from src.data.fetchers import DataManager;
from datetime import date, timedelta;

def test_sma_calculation():
    """Test basic SMA calculation"""
    print( "🧪 Testing SMA calculation..." );
    
    indicators = TechnicalIndicators();
    data_manager = DataManager();
    
    # Get some test data
    end_date = date.today();
    start_date = end_date - timedelta( days=250 );
    
    try:
        test_data = data_manager.get_stock_data( 'AAPL', start_date, end_date );
        if test_data is None or len( test_data ) < 200:
            print( "❌ Insufficient test data" );
            return False;
        
        # Calculate SMAs
        test_data_indexed = test_data.set_index( 'date' );
        close_prices = test_data_indexed['close'];
        
        sma49 = indicators.calculate_sma( close_prices, 49 );
        sma200 = indicators.calculate_sma( close_prices, 200 );
        
        print( f"✅ SMA49 calculated: {len( sma49.dropna() )} valid values" );
        print( f"✅ SMA200 calculated: {len( sma200.dropna() )} valid values" );
        print( f"   Latest SMA49: ${sma49.dropna().iloc[-1]:.2f}" );
        print( f"   Latest SMA200: ${sma200.dropna().iloc[-1]:.2f}" );
        
        # Test crossover detection
        crossovers = indicators.detect_sma_crossovers( sma49, sma200, 14 );
        print( f"✅ SMA crossover detection: {len( crossovers )} crossovers found in last 14 days" );
        
        if crossovers:
            latest = crossovers[-1];
            print( f"   Latest crossover: {latest['type']} on {latest['date']}" );
        
        return True;
        
    except Exception as e:
        print( f"❌ SMA calculation test failed: {e}" );
        return False;

def test_sma_scanning():
    """Test SMA signal scanning"""
    print( "\n🧪 Testing SMA signal scanning..." );
    
    scanner = DailySignalScanner();
    
    try:
        # Test with a few symbols
        test_symbols = ['AAPL', 'MSFT', 'GOOGL'];
        
        print( f"Testing SMA scanning on {test_symbols}..." );
        
        signals = scanner.scan_multiple_stocks_sma_only( test_symbols, max_signals=5 );
        
        print( f"✅ SMA scanning completed: {len( signals )} signals found" );
        
        for signal in signals:
            print( f"   📊 {signal['symbol']}: {signal['signal_type']} SMA49/200 cross" );
            print( f"       Strength: {signal['signal_strength']:.1f}, Date: {signal['signal_date']}" );
            print( f"       Price: ${signal['current_price']:.2f}, Days ago: {signal['days_since_cross']}" );
        
        return True;
        
    except Exception as e:
        print( f"❌ SMA scanning test failed: {e}" );
        import traceback;
        traceback.print_exc();
        return False;

def main():
    """Run SMA implementation tests"""
    print( "🚀 Testing SMA Implementation" );
    print( "=" * 50 );
    
    test1_result = test_sma_calculation();
    test2_result = test_sma_scanning();
    
    print( "\n" + "=" * 50 );
    if test1_result and test2_result:
        print( "✅ All SMA tests passed!" );
        return 0;
    else:
        print( "❌ Some SMA tests failed!" );
        return 1;

if __name__ == "__main__":
    sys.exit( main() );