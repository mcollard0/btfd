#!/usr/bin/env python3
"""
Stock Data Collection Script for BTFD
Gathers historical market data for analysis and backtesting
"""

import sys
import os
from datetime import date, timedelta, datetime
from typing import List, Dict
import time

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.data.fetchers import DataManager;
from src.config.settings import get_config;

class StockDataCollector:
    """Stock data collection and management"""
    
    def __init__( self ):
        self.data_manager = DataManager();
        self.config = get_config();
    
    def get_popular_stocks( self ) -> List[str]:
        """Get list of popular stocks for option trading"""
        
        return [
            # Large Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
            
            # Popular Trading Stocks  
            'SPY', 'QQQ', 'AMD', 'INTC', 'NFLX', 'CRM', 'ORCL',
            
            # Financial
            'JPM', 'BAC', 'WFC', 'GS', 'V', 'MA', 'PYPL', 'SQ',
            
            # Consumer/Retail
            'DIS', 'NKE', 'SBUX', 'MCD', 'WMT', 'TGT', 'HD', 'LOW',
            
            # Healthcare/Biotech
            'JNJ', 'PFE', 'MRNA', 'ABBV', 'UNH', 'CVS',
            
            # Energy/Industrial
            'XOM', 'CVX', 'CAT', 'BA', 'GE', 'F', 'GM',
            
            # Communications
            'T', 'VZ', 'CMCSA', 'NFLX',
            
            # Growth/Meme Stocks
            'GME', 'AMC', 'PLTR', 'ROKU', 'ZOOM', 'UBER', 'LYFT',
            
            # ETFs
            'IWM', 'VTI', 'EFA', 'EEM'
        ];
    
    def collect_historical_data( self, symbols: List[str], days_back: int = 365,
                                batch_size: int = 10, delay_seconds: float = 1.0 ) -> Dict[str, bool]:
        """
        Collect historical data for multiple stocks
        
        Args:
            symbols: List of stock symbols to collect
            days_back: Days of historical data to collect
            batch_size: Number of stocks to process in each batch
            delay_seconds: Delay between API calls to avoid rate limiting
            
        Returns:
            Dictionary mapping symbols to success status
        """
        
        print( f"📡 Collecting historical data for {len( symbols )} stocks" );
        print( f"📅 Date range: {days_back} days back to today" );
        print( f"⏱️  Batch size: {batch_size}, Delay: {delay_seconds}s" );
        print( "=" * 60 );
        
        end_date = date.today();
        start_date = end_date - timedelta( days=days_back );
        
        results = {};
        successful = 0;
        failed = 0;
        
        # Process in batches to avoid overwhelming the API
        for i in range( 0, len( symbols ), batch_size ):
            batch = symbols[i:i + batch_size];
            batch_num = ( i // batch_size ) + 1;
            total_batches = ( len( symbols ) + batch_size - 1 ) // batch_size;
            
            print( f"\n📦 Batch {batch_num}/{total_batches}: {batch}" );
            
            for j, symbol in enumerate( batch ):
                try:
                    print( f"  🔍 [{i+j+1}/{len( symbols )}] Fetching {symbol}..." );
                    
                    # Fetch data (will use cache if available)
                    data = self.data_manager.get_stock_data( symbol, start_date, end_date );
                    
                    if data is not None and len( data ) > 0:
                        current_price = data['close'].iloc[-1];
                        date_range = f"{data['date'].min()} to {data['date'].max()}";
                        
                        print( f"    ✅ {symbol}: {len( data )} days, ${current_price:.2f}, {date_range}" );
                        results[symbol] = True;
                        successful += 1;
                    else:
                        print( f"    ❌ {symbol}: No data received" );
                        results[symbol] = False;
                        failed += 1;
                    
                    # Delay to avoid rate limiting
                    if j < len( batch ) - 1:  # Don't delay after last item in batch
                        time.sleep( delay_seconds );
                        
                except Exception as e:
                    print( f"    ❌ {symbol}: Error - {e}" );
                    results[symbol] = False;
                    failed += 1;
            
            # Longer delay between batches
            if i + batch_size < len( symbols ):
                print( f"  ⏸️  Waiting {delay_seconds * 2}s before next batch..." );
                time.sleep( delay_seconds * 2 );
        
        # Summary
        print( f"\n📊 Data Collection Summary:" );
        print( f"   ✅ Successful: {successful}/{len( symbols )} ({successful/len(symbols)*100:.1f}%)" );
        print( f"   ❌ Failed: {failed}/{len( symbols )} ({failed/len(symbols)*100:.1f}%)" );
        
        if failed > 0:
            failed_symbols = [symbol for symbol, success in results.items() if not success];
            print( f"   Failed symbols: {failed_symbols[:10]}" );
            if len( failed_symbols ) > 10:
                print( f"   ... and {len( failed_symbols ) - 10} more" );
        
        return results;
    
    def check_data_coverage( self, symbols: List[str] ) -> Dict[str, Dict]:
        """
        Check data coverage for symbols in database
        
        Args:
            symbols: List of symbols to check
            
        Returns:
            Dictionary with coverage information for each symbol
        """
        
        print( f"📊 Checking data coverage for {len( symbols )} symbols..." );
        
        coverage = {};
        
        try:
            conn = self.config.get_database_connection();
            
            for symbol in symbols:
                cursor = conn.cursor();
                cursor.execute(
                    "SELECT COUNT(*), MIN(DATE(timestamp)), MAX(DATE(timestamp)) FROM stock_data WHERE symbol = ?",
                    ( symbol, )
                );
                
                result = cursor.fetchone();
                
                if result and result[0] > 0:
                    coverage[symbol] = {
                        'records': result[0],
                        'start_date': result[1],
                        'end_date': result[2],
                        'has_data': True
                    };
                else:
                    coverage[symbol] = {
                        'records': 0,
                        'start_date': None,
                        'end_date': None,
                        'has_data': False
                    };
            
            conn.close();
            
        except Exception as e:
            print( f"❌ Error checking data coverage: {e}" );
        
        return coverage;
    
    def show_coverage_report( self, coverage: Dict[str, Dict] ):
        """Show detailed coverage report"""
        
        print( f"\n📊 Data Coverage Report" );
        print( "=" * 60 );
        
        symbols_with_data = [s for s, info in coverage.items() if info['has_data']];
        symbols_without_data = [s for s, info in coverage.items() if not info['has_data']];
        
        print( f"✅ Symbols with data: {len( symbols_with_data )}" );
        print( f"❌ Symbols without data: {len( symbols_without_data )}" );
        
        if symbols_with_data:
            print( f"\n📈 Top symbols by record count:" );
            sorted_symbols = sorted( symbols_with_data, 
                                   key=lambda s: coverage[s]['records'], 
                                   reverse=True );
            
            for symbol in sorted_symbols[:10]:
                info = coverage[symbol];
                print( f"  {symbol}: {info['records']} records ({info['start_date']} to {info['end_date']})" );
        
        if symbols_without_data:
            print( f"\n❌ Symbols needing data collection:" );
            print( f"  {', '.join( symbols_without_data[:20] )}" );
            if len( symbols_without_data ) > 20:
                print( f"  ... and {len( symbols_without_data ) - 20} more" );
    
    def update_stale_data( self, max_age_days: int = 7 ) -> int:
        """
        Update data that is older than specified days
        
        Args:
            max_age_days: Maximum age in days before data is considered stale
            
        Returns:
            Number of symbols updated
        """
        
        cutoff_date = date.today() - timedelta( days=max_age_days );
        
        print( f"🔄 Updating data older than {cutoff_date}..." );
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            # Find symbols with stale data
            cursor.execute(
                "SELECT DISTINCT symbol FROM stock_data WHERE DATE(timestamp) < ? ORDER BY symbol",
                ( cutoff_date, )
            );
            
            stale_symbols = [row[0] for row in cursor.fetchall()];
            conn.close();
            
            if stale_symbols:
                print( f"📋 Found {len( stale_symbols )} symbols with stale data" );
                
                # Update stale data
                results = self.collect_historical_data( 
                    stale_symbols, 
                    days_back=max_age_days + 10,  # Get a bit extra to ensure coverage
                    delay_seconds=0.5  # Faster for updates
                );
                
                updated_count = sum( 1 for success in results.values() if success );
                print( f"✅ Updated {updated_count}/{len( stale_symbols )} symbols" );
                
                return updated_count;
            else:
                print( f"✅ All data is current (within {max_age_days} days)" );
                return 0;
                
        except Exception as e:
            print( f"❌ Error updating stale data: {e}" );
            return 0;

def main():
    """Main data collection function"""
    
    import argparse;
    
    parser = argparse.ArgumentParser( description='BTFD Stock Data Collector' );
    parser.add_argument( '--symbols', nargs='+', help='Specific symbols to collect' );
    parser.add_argument( '--days', type=int, default=365, help='Days of historical data to collect' );
    parser.add_argument( '--batch-size', type=int, default=10, help='Batch size for API calls' );
    parser.add_argument( '--delay', type=float, default=1.0, help='Delay between API calls in seconds' );
    parser.add_argument( '--check-coverage', action='store_true', help='Check data coverage only' );
    parser.add_argument( '--update-stale', action='store_true', help='Update stale data only' );
    parser.add_argument( '--max-age', type=int, default=7, help='Maximum age in days for stale data update' );
    
    args = parser.parse_args();
    
    collector = StockDataCollector();
    
    print( f"🗃️  BTFD Stock Data Collector" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( "=" * 60 );
    
    if args.check_coverage:
        # Just check coverage
        symbols = args.symbols if args.symbols else collector.get_popular_stocks();
        coverage = collector.check_data_coverage( symbols );
        collector.show_coverage_report( coverage );
        
    elif args.update_stale:
        # Update stale data
        updated = collector.update_stale_data( args.max_age );
        print( f"✅ Updated data for {updated} symbols" );
        
    else:
        # Collect new data
        symbols = args.symbols if args.symbols else collector.get_popular_stocks();
        
        print( f"📋 Collecting data for {len( symbols )} symbols:" );
        print( f"   Symbols: {symbols[:10]}" );
        if len( symbols ) > 10:
            print( f"   ... and {len( symbols ) - 10} more" );
        
        results = collector.collect_historical_data( 
            symbols, 
            days_back=args.days,
            batch_size=args.batch_size,
            delay_seconds=args.delay
        );
    
    print( f"\n✅ Data collection completed at {datetime.now().strftime( '%H:%M:%S' )}" );

if __name__ == "__main__":
    main();