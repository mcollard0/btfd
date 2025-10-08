#!/usr/bin/env python3
"""
Quick test for Yahoo Finance data fetching
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.data.fetchers import YahooFetcher, DataManager;

def test_yahoo_fetcher():
    """Test direct Yahoo Finance fetching"""
    
    print( "🧪 Testing Yahoo Finance Data Fetcher" );
    print( "=" * 50 );
    
    fetcher = YahooFetcher();
    
    # Test with AAPL for last 30 days
    end_date = date.today();
    start_date = end_date - timedelta( days=30 );
    
    print( f"📡 Fetching AAPL data from {start_date} to {end_date}..." );
    
    data = fetcher.fetch_stock_data( 'AAPL', start_date, end_date );
    
    if data is not None:
        print( f"✅ Success! Fetched {len( data )} days of AAPL data" );
        print( f"📊 Columns: {list( data.columns )}" );
        print( f"💰 Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}" );
        print( f"📅 Date range: {data['date'].min()} to {data['date'].max()}" );
        
        print( f"\n📋 Sample data (first 3 rows):" );
        print( data.head( 3 ).to_string( index=False ) );
        
        return True;
    else:
        print( "❌ Failed to fetch AAPL data" );
        return False;

def test_data_manager():
    """Test DataManager class"""
    
    print( "\n🧪 Testing DataManager" );
    print( "=" * 50 );
    
    manager = DataManager();
    
    # Test single stock fetch
    end_date = date.today();
    start_date = end_date - timedelta( days=30 );
    
    print( f"📡 Fetching MSFT data via DataManager..." );
    
    data = manager.get_stock_data( 'MSFT', start_date, end_date );
    
    if data is not None:
        print( f"✅ Success! DataManager fetched {len( data )} days of MSFT data" );
        print( f"💰 Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}" );
        
        # Test caching by fetching again
        print( f"\n🔄 Testing cache by fetching again..." );
        cached_data = manager.get_stock_data( 'MSFT', start_date, end_date );
        
        if cached_data is not None:
            print( f"✅ Cache test successful!" );
        
        return True;
    else:
        print( "❌ DataManager failed to fetch data" );
        return False;

def test_multiple_stocks():
    """Test fetching multiple stocks"""
    
    print( "\n🧪 Testing Multiple Stocks" );
    print( "=" * 50 );
    
    manager = DataManager();
    symbols = ['AAPL', 'MSFT', 'GOOGL'];
    
    end_date = date.today();
    start_date = end_date - timedelta( days=14 );  # Last 2 weeks
    
    results = {};
    
    for symbol in symbols:
        print( f"📡 Fetching {symbol}..." );
        data = manager.get_stock_data( symbol, start_date, end_date );
        
        if data is not None:
            results[symbol] = {
                'days': len( data ),
                'price_range': f"${data['close'].min():.2f} - ${data['close'].max():.2f}",
                'latest_price': data['close'].iloc[-1]
            };
            print( f"   ✅ {symbol}: {len( data )} days, latest: ${data['close'].iloc[-1]:.2f}" );
        else:
            print( f"   ❌ {symbol}: Failed" );
    
    print( f"\n📊 Summary: Successfully fetched {len( results )}/{len( symbols )} stocks" );
    return len( results ) > 0;

def main():
    """Run all tests"""
    
    print( "🎯 Yahoo Finance Data Fetching Test" );
    print( "=" * 60 );
    
    tests = [
        ( "Yahoo Fetcher", test_yahoo_fetcher ),
        ( "Data Manager", test_data_manager ), 
        ( "Multiple Stocks", test_multiple_stocks )
    ];
    
    results = {};
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func();
        except Exception as e:
            print( f"❌ {test_name} failed with error: {e}" );
            import traceback;
            traceback.print_exc();
            results[test_name] = False;
    
    # Summary
    print( f"\n{'='*20} TEST SUMMARY {'='*20}" );
    passed = sum( results.values() );
    total = len( results );
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED";
        print( f"   {test_name}: {status}" );
    
    print( f"\n🎯 Overall: {passed}/{total} tests passed" );
    
    if passed == total:
        print( "🎉 All data fetching tests passed! Ready for optimization." );
    else:
        print( "⚠️  Some tests failed. Check your network connection and try again." );

if __name__ == "__main__":
    main();