#!/usr/bin/env python3
"""
Test comprehensive stock discovery with a small subset
"""

import sys
import os
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.data.stock_discovery import StockDiscovery;

def test_small_discovery():
    """Test discovery with just a few known stocks"""
    
    print( "🧪 Testing comprehensive stock discovery..." );
    
    discoverer = StockDiscovery();
    
    # Override the fallback list with just a few known good symbols
    def get_small_fallback_list():
        symbols = ['AAPL', 'KO', 'F', 'T', 'GE', 'BAC', 'PFE', 'XOM', 'C', 'INTC'];
        
        stocks = [];
        for symbol in symbols:
            stocks.append({
                'symbol': symbol,
                'name': f'{symbol} Corp',
                'market_cap': 0,
                'volume': 0,
                'price': 0,
                'exchange': 'US',
                'sector': 'Test',
                'industry': 'Test'
            });
        
        print( f"   ✅ Small test list contains {len( stocks )} stocks: {symbols}" );
        return stocks;
    
    # Temporarily replace the method
    discoverer.get_fallback_comprehensive_list = get_small_fallback_list;
    
    # Test discovery
    affordable_symbols = discoverer.discover_affordable_stocks( 
        max_price=100.0,
        min_volume=0,  # No volume requirement for testing
        min_market_cap=0,  # No market cap requirement for testing
        use_cache=False  # Force fresh discovery
    );
    
    print( f"\n🎯 TEST RESULTS:" );
    print( f"   Total affordable stocks found: {len( affordable_symbols )}" );
    print( f"   Symbols: {affordable_symbols[:10]}" );  # Show first 10
    
    return len( affordable_symbols );

if __name__ == "__main__":
    count = test_small_discovery();
    print( f"\n✅ Test completed: {count} stocks discovered" );