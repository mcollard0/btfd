"""
Batch Stock Data Collection System for BTFD
Handles large-scale data collection with rate limiting, parallel processing, and error handling
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
import pandas as pd
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json
from pathlib import Path

from .fetchers import DataManager
from .exchange_symbols import get_all_tradeable_symbols
from ..config.settings import get_config

# Configure logging
logging.basicConfig( level=logging.INFO )
logger = logging.getLogger( __name__ )

class BatchStockCollector:
    """
    Enhanced batch stock data collection system
    """
    
    def __init__( self, max_workers: int = 8, batch_size: int = 50, delay_between_batches: float = 2.0 ):
        self.config = get_config()
        self.data_manager = DataManager()
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        
        # Rate limiting
        self.request_count = 0
        self.start_time = time.time()
        self.max_requests_per_minute = 100  # Conservative limit
        
        # Progress tracking
        self.processed_symbols = []
        self.failed_symbols = []
        self.success_count = 0
        self.total_symbols = 0
    
    def get_data_collection_priority( self ) -> List[str]:
        """
        Get symbols prioritized by trading importance
        
        Returns:
            List of symbols in priority order
        """
        
        # Get all tradeable symbols
        all_symbols = get_all_tradeable_symbols()
        
        if not all_symbols:
            print( "⚠️  No symbols found in database. Run symbol fetcher first." )
            return []
        
        # Priority categories
        priority_symbols = []
        
        # 1. High priority - Major indices and ETFs
        high_priority = [
            'SPY', 'QQQ', 'IWM', 'VTI', 'EFA', 'EEM',
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'
        ]
        
        # 2. Medium priority - S&P 500 components (those we have)
        medium_priority = [
            'JPM', 'V', 'UNH', 'HD', 'PG', 'MA', 'BAC', 'DIS', 'ADBE', 'CRM',
            'NFLX', 'XOM', 'CVX', 'KO', 'PFE', 'TMO', 'ABBV', 'ACN', 'NKE'
        ]
        
        # 3. Your current target range stocks
        target_range_priority = [
            'BAC', 'CMCSA', 'CVS', 'EEM', 'EFA', 'F', 'GM', 'GME', 'INTC', 'LYFT',
            'MRNA', 'NKE', 'PFE', 'PYPL', 'SBUX', 'T', 'TGT', 'UBER', 'VZ', 'WFC', 'KO'
        ]
        
        # Add symbols in priority order (avoiding duplicates)
        added_symbols = set()
        
        for priority_list in [high_priority, target_range_priority, medium_priority]:
            for symbol in priority_list:
                if symbol in all_symbols and symbol not in added_symbols:
                    priority_symbols.append( symbol )
                    added_symbols.add( symbol )
        
        # Add remaining symbols
        for symbol in all_symbols:
            if symbol not in added_symbols:
                priority_symbols.append( symbol )
        
        print( f"📊 Prioritized {len( priority_symbols )} symbols for collection" )
        return priority_symbols
    
    def check_existing_data( self, symbols: List[str] ) -> Tuple[List[str], List[str]]:
        """
        Check which symbols already have recent data
        
        Args:
            symbols: List of symbols to check
            
        Returns:
            Tuple of (symbols_needing_data, symbols_with_recent_data)
        """
        
        need_data = []
        have_recent_data = []
        cutoff_date = date.today() - timedelta( days=7 )  # Consider data older than 7 days as stale
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            for symbol in symbols:
                cursor.execute( '''
                    SELECT MAX(timestamp) FROM stock_data WHERE symbol = ?
                ''', (symbol,) )
                
                result = cursor.fetchone()
                latest_date = result[0] if result and result[0] else None
                
                if latest_date:
                    latest_date_obj = datetime.strptime( latest_date, '%Y-%m-%d' ).date()
                    if latest_date_obj >= cutoff_date:
                        have_recent_data.append( symbol )
                    else:
                        need_data.append( symbol )
                else:
                    need_data.append( symbol )
            
            conn.close()
            
        except Exception as e:
            logger.error( f"Error checking existing data: {e}" )
            # If error, assume all symbols need data
            need_data = symbols
        
        print( f"📊 Data status: {len( need_data )} need updates, {len( have_recent_data )} have recent data" )
        return need_data, have_recent_data
    
    def collect_symbol_data( self, symbol: str, days_back: int = 180 ) -> bool:
        """
        Collect data for a single symbol
        
        Args:
            symbol: Stock symbol
            days_back: Days of historical data to collect
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            end_date = date.today()
            start_date = end_date - timedelta( days=days_back )
            
            # Use existing data manager
            stock_data = self.data_manager.get_stock_data( symbol, start_date, end_date )
            
            if stock_data is not None and len( stock_data ) > 0:
                self.success_count += 1
                logger.info( f"✅ {symbol}: {len( stock_data )} records collected" )
                return True
            else:
                logger.warning( f"❌ {symbol}: No data retrieved" )
                return False
                
        except Exception as e:
            logger.error( f"❌ {symbol}: Error collecting data - {e}" )
            return False
    
    def process_batch( self, symbols_batch: List[str], batch_num: int, total_batches: int ) -> Dict[str, bool]:
        """
        Process a batch of symbols using parallel processing
        
        Args:
            symbols_batch: Batch of symbols to process
            batch_num: Current batch number
            total_batches: Total number of batches
            
        Returns:
            Dictionary mapping symbols to success status
        """
        
        print( f"\n🔄 Processing batch {batch_num}/{total_batches} ({len( symbols_batch )} symbols)" )
        print( f"   Symbols: {', '.join( symbols_batch )}" )
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor( max_workers=self.max_workers ) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit( self.collect_symbol_data, symbol ): symbol
                for symbol in symbols_batch
            }
            
            # Process completed tasks
            for future in as_completed( future_to_symbol ):
                symbol = future_to_symbol[future]
                
                try:
                    success = future.result()
                    results[symbol] = success
                    
                    if success:
                        self.processed_symbols.append( symbol )
                    else:
                        self.failed_symbols.append( symbol )
                        
                except Exception as e:
                    logger.error( f"❌ {symbol}: Exception during processing - {e}" )
                    results[symbol] = False
                    self.failed_symbols.append( symbol )
        
        # Show batch results
        successful = sum( 1 for success in results.values() if success )
        print( f"   ✅ Batch {batch_num} complete: {successful}/{len( symbols_batch )} successful" )
        
        return results
    
    def collect_all_symbols( self, max_symbols: Optional[int] = None, 
                           force_update: bool = False ) -> Dict[str, any]:
        """
        Collect data for all symbols with intelligent batching
        
        Args:
            max_symbols: Maximum number of symbols to process (None for all)
            force_update: Whether to update symbols that already have recent data
            
        Returns:
            Collection statistics dictionary
        """
        
        print( "🚀 STARTING COMPREHENSIVE STOCK DATA COLLECTION" )
        print( "=" * 60 )
        
        # Get prioritized symbol list
        all_symbols = self.get_data_collection_priority()
        
        if not all_symbols:
            return {"error": "No symbols available for collection"}
        
        # Limit symbols if requested
        if max_symbols:
            all_symbols = all_symbols[:max_symbols]
            print( f"📊 Limited to first {max_symbols} symbols" )
        
        # Check existing data unless forced
        if not force_update:
            symbols_to_process, symbols_with_data = self.check_existing_data( all_symbols )
        else:
            symbols_to_process = all_symbols
            symbols_with_data = []
        
        if not symbols_to_process:
            print( "✅ All symbols already have recent data!" )
            return {
                "total_symbols": len( all_symbols ),
                "symbols_with_recent_data": len( symbols_with_data ),
                "symbols_processed": 0,
                "success_count": 0,
                "failed_count": 0
            }
        
        self.total_symbols = len( symbols_to_process )
        print( f"📊 Processing {self.total_symbols} symbols in batches of {self.batch_size}" )
        
        # Process in batches
        batches = [symbols_to_process[i:i + self.batch_size] 
                  for i in range( 0, len( symbols_to_process ), self.batch_size )]
        
        total_batches = len( batches )
        
        for batch_num, batch in enumerate( batches, 1 ):
            # Process batch
            batch_results = self.process_batch( batch, batch_num, total_batches )
            
            # Rate limiting delay between batches (except for last batch)
            if batch_num < total_batches:
                print( f"   ⏳ Waiting {self.delay_between_batches}s before next batch..." )
                time.sleep( self.delay_between_batches )
        
        # Final statistics
        failed_count = len( self.failed_symbols )
        
        print( f"\n📈 COLLECTION COMPLETE!" )
        print( f"=" * 30 )
        print( f"📊 Total symbols processed: {self.total_symbols}" )
        print( f"✅ Successfully collected: {self.success_count}" )
        print( f"❌ Failed: {failed_count}" )
        print( f"📈 Success rate: {(self.success_count/self.total_symbols)*100:.1f}%" )
        
        if self.failed_symbols:
            print( f"❌ Failed symbols: {', '.join( self.failed_symbols[:10] )}" )
            if len( self.failed_symbols ) > 10:
                print( f"   ... and {len( self.failed_symbols ) - 10} more" )
        
        return {
            "total_symbols": self.total_symbols,
            "symbols_with_recent_data": len( symbols_with_data ),
            "symbols_processed": self.total_symbols,
            "success_count": self.success_count,
            "failed_count": failed_count,
            "success_rate": (self.success_count/self.total_symbols)*100,
            "processed_symbols": self.processed_symbols,
            "failed_symbols": self.failed_symbols
        }
    
    def get_database_stats( self ) -> Dict[str, any]:
        """Get current database statistics"""
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            # Total records
            cursor.execute( 'SELECT COUNT(*) FROM stock_data' )
            total_records = cursor.fetchone()[0]
            
            # Unique symbols
            cursor.execute( 'SELECT COUNT(DISTINCT symbol) FROM stock_data' )
            unique_symbols = cursor.fetchone()[0]
            
            # Latest data date
            cursor.execute( 'SELECT MAX(timestamp) FROM stock_data' )
            latest_date = cursor.fetchone()[0]
            
            # Records by exchange
            cursor.execute( '''
                SELECT ss.exchange, COUNT(*) as records
                FROM stock_data sd
                JOIN stock_symbols ss ON sd.symbol = ss.symbol
                GROUP BY ss.exchange
            ''' )
            by_exchange = dict( cursor.fetchall() )
            
            conn.close()
            
            return {
                "total_records": total_records,
                "unique_symbols": unique_symbols,
                "latest_date": latest_date,
                "by_exchange": by_exchange
            }
            
        except Exception as e:
            logger.error( f"Error getting database stats: {e}" )
            return {}

# Convenience functions
def collect_all_exchange_data( max_symbols: int = 200 ) -> Dict:
    """
    Collect data for all exchange symbols
    
    Args:
        max_symbols: Maximum symbols to process
        
    Returns:
        Collection statistics
    """
    
    collector = BatchStockCollector(
        max_workers=6,  # Moderate parallelism
        batch_size=25,  # Smaller batches for better rate limiting
        delay_between_batches=1.5
    )
    
    return collector.collect_all_symbols( max_symbols=max_symbols )

def update_stale_data( days_threshold: int = 7 ) -> Dict:
    """
    Update symbols with stale data
    
    Args:
        days_threshold: Consider data stale after N days
        
    Returns:
        Update statistics
    """
    
    collector = BatchStockCollector( batch_size=20, delay_between_batches=2.0 )
    
    # This will automatically skip symbols with recent data
    return collector.collect_all_symbols( force_update=False )