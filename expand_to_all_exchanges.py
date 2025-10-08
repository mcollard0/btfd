#!/usr/bin/env python3
"""
Complete NYSE/NASDAQ Database Expansion Script for BTFD
Fetches all exchange symbols and collects historical data
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), 'src' ) )

from src.data.exchange_symbols import fetch_and_save_all_symbols, ExchangeSymbolFetcher
from src.data.batch_collector import collect_all_exchange_data, BatchStockCollector
import sqlite3

def main():
    """Main expansion process"""
    
    print( "🚀 BTFD NYSE/NASDAQ COMPLETE EXPANSION" )
    print( "=" * 60 )
    print( "This will expand your database from ~56 stocks to potentially hundreds!" )
    print()
    
    # Step 1: Fetch all exchange symbols
    print( "📡 STEP 1: FETCHING ALL EXCHANGE SYMBOLS" )
    print( "-" * 45 )
    
    symbols_count = fetch_and_save_all_symbols()
    
    if symbols_count == 0:
        print( "❌ Failed to fetch any symbols. Exiting." )
        return
    
    print( f"✅ Successfully fetched {symbols_count} symbols" )
    
    # Get exchange breakdown
    fetcher = ExchangeSymbolFetcher()
    exchange_counts = fetcher.get_symbol_count_by_exchange()
    
    print( "\n📊 Exchange Breakdown:" )
    for exchange, count in exchange_counts.items():
        print( f"   {exchange}: {count:,} symbols" )
    
    # Step 2: Collect historical data
    print( f"\n📈 STEP 2: COLLECTING HISTORICAL DATA" )
    print( "-" * 45 )
    print( "Starting with high-priority symbols (major indices, ETFs, S&P components)" )
    
    # Start with reasonable batch size
    max_symbols_initial = min( 100, symbols_count )
    
    print( f"🔄 Phase 1: Collecting data for {max_symbols_initial} high-priority symbols" )
    
    results = collect_all_exchange_data( max_symbols=max_symbols_initial )
    
    # Step 3: Show results and database stats
    print( f"\n📊 STEP 3: EXPANSION RESULTS" )
    print( "-" * 35 )
    
    if 'error' not in results:
        print( f"✅ Data collection completed!" )
        print( f"📊 Symbols processed: {results.get( 'symbols_processed', 0 )}" )
        print( f"✅ Successfully collected: {results.get( 'success_count', 0 )}" )
        print( f"❌ Failed: {results.get( 'failed_count', 0 )}" )
        print( f"📈 Success rate: {results.get( 'success_rate', 0 ):.1f}%" )
    else:
        print( f"❌ Error during data collection: {results['error']}" )
        return
    
    # Step 4: Database statistics
    print( f"\n📈 STEP 4: UPDATED DATABASE STATISTICS" )
    print( "-" * 45 )
    
    collector = BatchStockCollector()
    stats = collector.get_database_stats()
    
    if stats:
        print( f"📊 Total stock records: {stats.get( 'total_records', 0 ):,}" )
        print( f"🎯 Unique symbols: {stats.get( 'unique_symbols', 0 ):,}" )
        print( f"📅 Latest data: {stats.get( 'latest_date', 'Unknown' )}" )
        
        if 'by_exchange' in stats:
            print( f"\n📈 Records by Exchange:" )
            for exchange, count in stats['by_exchange'].items():
                print( f"   {exchange}: {count:,} records" )
    
    # Step 5: Target range analysis
    print( f"\n🎯 STEP 5: YOUR TARGET RANGE (\$10-\$100) ANALYSIS" )
    print( "-" * 55 )
    
    try:
        # Connect to database to analyze price ranges
        from src.config.settings import get_config
        config = get_config()
        conn = config.get_database_connection()
        cursor = conn.cursor()
        
        # Get current prices and categorize
        cursor.execute( '''
            SELECT ss.symbol, ss.exchange, sd.close
            FROM stock_symbols ss
            LEFT JOIN stock_data sd ON ss.symbol = sd.symbol
            WHERE sd.timestamp = (SELECT MAX(timestamp) FROM stock_data WHERE symbol = ss.symbol)
            ORDER BY sd.close
        ''' )
        
        stock_prices = cursor.fetchall()
        conn.close()
        
        target_range = []
        under_10 = []
        over_100 = []
        no_price = []
        
        for symbol, exchange, price in stock_prices:
            if price is None:
                no_price.append( symbol )
            elif price < 10:
                under_10.append( symbol )
            elif 10 <= price <= 100:
                target_range.append( symbol )
            else:
                over_100.append( symbol )
        
        print( f"✅ TARGET STOCKS (\$10-\$100): {len( target_range )} symbols" )
        print( f"❌ Under \$10: {len( under_10 )} symbols" )
        print( f"⚠️  Over \$100: {len( over_100 )} symbols" )
        print( f"❓ No price data yet: {len( no_price )} symbols" )
        
        print( f"\n🎯 Your daily scanner will focus on the {len( target_range )} target stocks!" )
        
        if len( target_range ) > 21:  # Original was 21
            improvement = len( target_range ) - 21
            print( f"📈 Expansion added {improvement} new tradeable stocks to your target range!" )
    
    except Exception as e:
        print( f"❌ Error analyzing target range: {e}" )
    
    # Step 6: Next steps
    print( f"\n🚀 STEP 6: NEXT STEPS" )
    print( "-" * 25 )
    print( "1. ✅ Symbol fetching: Complete" )
    print( "2. ✅ Initial data collection: Complete" )
    print( "3. 🔄 Continue collecting remaining symbols:" )
    print( "   python -c \"from src.data.batch_collector import collect_all_exchange_data; collect_all_exchange_data()\"" )
    print( "4. 🔄 Run daily scanner on expanded database:" )
    print( "   python src/daily_btfd_scanner.py" )
    print( "5. ⚙️  Optimize EMA parameters for new stocks (optional):" )
    print( "   python -c \"from src.optimization.parameter_sweep import ParameterSweepEngine; ...\"" )
    
    print( f"\n🎉 NYSE/NASDAQ EXPANSION SUCCESSFUL!" )
    print( f"Your BTFD database now contains symbols from both major US exchanges!" )
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print( f"\n✅ Expansion completed successfully!" )
            sys.exit( 0 )
        else:
            print( f"\n❌ Expansion failed!" )
            sys.exit( 1 )
    except KeyboardInterrupt:
        print( f"\n⏹️  Expansion interrupted by user" )
        sys.exit( 1 )
    except Exception as e:
        print( f"\n💥 Unexpected error: {e}" )
        import traceback
        traceback.print_exc()
        sys.exit( 1 )