#!/usr/bin/env python3
"""
BTFD Unified Trading Scanner
Scans for both EMA and SMA signals, downloads fresh data, generates charts, sends emails
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.notifications.email_sender import EmailSender;
from src.notifications.motd_writer import MOTDWriter;
from src.visualization.signal_charts import create_signal_charts;
from src.data.fetchers import DataManager;
from src.data.stock_discovery import StockDiscovery;

def ensure_fresh_data( symbols, min_days=210, days_back=320 ):
    """
    Smart data gathering: only fetch missing data points from database
    
    Args:
        symbols: List of stock symbols
        min_days: Minimum days of data required
        days_back: Days back to fetch
    """
    
    print( f"📥 Smart data gathering for {len( symbols )} symbols (min {min_days} days)..." );
    
    data_manager = DataManager();
    end_date = date.today();
    start_date = end_date - timedelta( days=days_back );
    
    success_count = 0;
    failed_symbols = [];
    cached_count = 0;
    fresh_count = 0;
    
    for i, symbol in enumerate( symbols ):
        print( f"📊 [{i+1}/{len( symbols )}] Analyzing data coverage for {symbol}..." );
        
        try:
            # First check what we have in cache/database
            cached_data = data_manager._get_cached_data( symbol, start_date, end_date );
            
            if cached_data is not None and len( cached_data ) >= min_days:
                print( f"   💾 {symbol}: {len( cached_data )} days cached - USING EXISTING DATA" );
                success_count += 1;
                cached_count += 1;
            else:
                # Need to fetch fresh data
                existing_days = len( cached_data ) if cached_data is not None else 0;
                print( f"   💾 {symbol}: Only {existing_days}/{min_days} days cached - FETCHING FRESH DATA" );
                
                data = data_manager.get_stock_data( 
                    symbol, 
                    start_date, 
                    end_date, 
                    use_cache=False,  # Force fresh download to fill gaps
                    min_days=min_days 
                );
                
                if data is not None and len( data ) >= min_days:
                    print( f"   ✅ {symbol}: {len( data )} days now available (FRESH DOWNLOAD)" );
                    success_count += 1;
                    fresh_count += 1;
                else:
                    print( f"   ❌ {symbol}: Still insufficient data ({len( data ) if data is not None else 0}/{min_days} days)" );
                    failed_symbols.append( symbol );
                    
        except Exception as e:
            print( f"   💥 {symbol}: Error fetching data - {e}" );
            failed_symbols.append( symbol );
    
    print( f"\n📊 Smart Data Gathering Summary:" );
    print( f"   ✅ Total Success: {success_count}/{len( symbols )} symbols" );
    print( f"   💾 Used Cached: {cached_count} symbols (no download needed)" );
    print( f"   📶 Fresh Downloads: {fresh_count} symbols (new data fetched)" );
    print( f"   ❌ Failed: {len( failed_symbols )} symbols" );
    
    if failed_symbols:
        print( f"   Failed symbols: {failed_symbols}" );
    
    return [s for s in symbols if s not in failed_symbols];

def get_affordable_stocks( max_price=100.0, use_comprehensive=True ):
    """Get list of stocks under the specified price using comprehensive discovery"""
    
    print( f"🔍 Finding stocks under ${max_price} {'(COMPREHENSIVE DISCOVERY)' if use_comprehensive else '(LEGACY MODE)'}..." );
    
    if use_comprehensive:
        # Use comprehensive stock discovery
        discoverer = StockDiscovery();
        symbols = discoverer.discover_affordable_stocks( 
            max_price=max_price,
            min_volume=10000,   # Lower volume requirement for broader coverage
            min_market_cap=1000000,  # Lower $1M minimum market cap for broader coverage
            use_cache=True,
            max_cache_age_hours=24,  # Refresh daily for comprehensive coverage
            max_stocks_to_check=0  # NO LIMIT - check ALL stocks
        );
        
        print( f"🎯 COMPREHENSIVE DISCOVERY: Found {len( symbols )} affordable stocks!" );
        return symbols;
    
    else:
        # Legacy hardcoded method (fallback)
        print( "⚠️  Using legacy hardcoded stock list as fallback..." );
        
        candidate_symbols = [
            # Original list
            'KO', 'PEP', 'INTC', 'F', 'GE', 'BAC', 'WFC', 'T', 'VZ',
            'PYPL', 'UBER', 'LYFT', 'NKE', 'MCD', 'SBUX', 'WMT', 'TGT',
            
            # Additional affordable stocks
            'C', 'JPM', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'COF',  # Banks
            'XOM', 'CVX', 'BP', 'SHEL', 'COP', 'OXY',  # Energy
            'PFE', 'JNJ', 'MRK', 'ABT', 'BMY', 'LLY',  # Healthcare
            'HD', 'LOW', 'COST', 'WMT', 'TJX', 'DG',  # Retail
            'CSCO', 'IBM', 'HPQ', 'ORCL',  # Tech (older/cheaper)
            'CAT', 'DE', 'MMM', 'HON', 'RTX', 'LMT',  # Industrials
            'SO', 'NEE', 'DUK', 'EXC', 'AEP',  # Utilities
            'REIT', 'O', 'SPG', 'PLD', 'AMT',  # REITs
            'GOLD', 'NEM', 'FCX', 'AA',  # Materials
            'AFL', 'AIG', 'PRU', 'MET'  # Insurance
        ];
        
        data_manager = DataManager();
        suitable_symbols = [];
        
        for i, symbol in enumerate( candidate_symbols ):
            try:
                print( f"   [{i+1}/{len( candidate_symbols )}] Checking {symbol}..." );
                current_price = data_manager.yahoo_fetcher.get_current_price( symbol );
                
                if current_price and current_price <= max_price:
                    suitable_symbols.append( symbol );
                    print( f"      ✅ ${current_price:.2f} - INCLUDED" );
                elif current_price:
                    print( f"      ❌ ${current_price:.2f} - TOO EXPENSIVE" );
                else:
                    print( f"      ⚠️  No price data" );
                    
            except Exception as e:
                print( f"      💥 Error: {e}" );
        
        print( f"\n🎯 Found {len( suitable_symbols )} affordable stocks: {suitable_symbols}" );
        return suitable_symbols;

def main():
    """Main scanner function"""
    
    parser = argparse.ArgumentParser( description='BTFD Unified Trading Scanner' );
    parser.add_argument( '--max-price', type=float, default=100.0, help='Maximum stock price to include' );
    parser.add_argument( '--max-signals', type=int, default=20, help='Maximum signals to return' );
    parser.add_argument( '--ema-only', action='store_true', help='Scan for EMA signals only' );
    parser.add_argument( '--sma-only', action='store_true', help='Scan for SMA signals only' );
    parser.add_argument( '--no-email', action='store_true', help='Skip email notification' );
    parser.add_argument( '--no-motd', action='store_true', help='Skip MOTD update' );
    parser.add_argument( '--no-db', action='store_true', help='Skip database save' );
    parser.add_argument( '--symbols', nargs='+', help='Specific symbols to scan' );
    parser.add_argument( '--legacy-discovery', action='store_true', help='Use legacy hardcoded stock list instead of comprehensive discovery' );
    parser.add_argument( '--market-overview', action='store_true', help='Show market overview and exit' );
    
    args = parser.parse_args();
    
    print( f"🎯 BTFD Unified Trading Scanner - {date.today()}" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( f"💰 Max price: ${args.max_price}" );
    print( f"📊 Max signals: {args.max_signals}" );
    print( "=" * 60 );
    
    # Handle market overview request
    if args.market_overview:
        print( f"\n🌍 MARKET OVERVIEW ANALYSIS" );
        print( "=" * 40 );
        
        from src.data.stock_discovery import get_market_overview;
        overview = get_market_overview();
        
        if 'error' in overview:
            print( f"❌ {overview['error']}" );
            return 1;
        
        print( f"📊 Total stocks discovered: {overview['total_discovered']:,}" );
        print( f"📈 Sample analyzed: {overview['sample_analyzed']:,}" );
        print( f"📊 Estimated under $100: {overview['estimated_under_100']:,}" );
        
        dist = overview['price_distribution'];
        print( f"\n💰 Price Distribution (sample):" );
        print( f"   💎 Under $10:  {dist['under_10']:3d} ({dist['under_10']/overview['sample_analyzed']*100:.1f}%)" );
        print( f"   💵 $10-$25:   {dist['under_25']:3d} ({dist['under_25']/overview['sample_analyzed']*100:.1f}%)" );
        print( f"   💸 $25-$50:   {dist['under_50']:3d} ({dist['under_50']/overview['sample_analyzed']*100:.1f}%)" );
        print( f"   💰 $50-$100:  {dist['under_100']:3d} ({dist['under_100']/overview['sample_analyzed']*100:.1f}%)" );
        print( f"   🚀 Over $100:  {dist['over_100']:3d} ({dist['over_100']/overview['sample_analyzed']*100:.1f}%)" );
        print( f"   ❓ No price:   {dist['no_price']:3d} ({dist['no_price']/overview['sample_analyzed']*100:.1f}%)" );
        
        print( f"\n🎯 CONCLUSION: ~{overview['estimated_under_100']:,} stocks are under $100 (vs. our previous 37)" );
        return 0;
    
    try:
        # Step 1: Get symbols to scan
        if args.symbols:
            symbols = args.symbols;
            print( f"📋 Using specified symbols: {symbols}" );
        else:
            use_comprehensive = not args.legacy_discovery;
            symbols = get_affordable_stocks( args.max_price, use_comprehensive );
        
        if not symbols:
            print( "❌ No suitable symbols found to scan" );
            return 1;
        
        # Step 2: Ensure fresh data
        print( f"\n📥 STEP 1: Ensuring fresh data..." );
        symbols_with_data = ensure_fresh_data( symbols );
        
        if not symbols_with_data:
            print( "❌ No symbols have sufficient data" );
            return 1;
        
        print( f"✅ Ready to scan {len( symbols_with_data )} symbols with sufficient data" );
        
        # Step 3: Initialize scanner
        print( f"\n🔍 STEP 2: Running signal detection..." );
        scanner = DailySignalScanner();
        
        all_signals = [];
        
        # Scan for EMA signals (unless SMA-only)
        if not args.sma_only:
            print( f"📈 Scanning for EMA signals..." );
            ema_signals = scanner.scan_multiple_stocks( 
                symbols=symbols_with_data,
                max_signals=args.max_signals,
                include_sma=False  # EMA only
            );
            if ema_signals:
                all_signals.extend( ema_signals );
                print( f"   Found {len( ema_signals )} EMA signals" );
        
        # Scan for SMA signals (unless EMA-only)
        if not args.ema_only:
            print( f"📊 Scanning for SMA signals..." );
            sma_signals = scanner.scan_multiple_stocks_sma_only( 
                symbols=symbols_with_data,
                max_signals=args.max_signals
            );
            if sma_signals:
                all_signals.extend( sma_signals );
                print( f"   Found {len( sma_signals )} SMA signals" );
        
        # Remove duplicates and limit to max signals
        if all_signals:
            # Remove duplicate symbols (keep highest strength)
            seen_symbols = {};
            unique_signals = [];
            
            for signal in sorted( all_signals, key=lambda x: x['signal_strength'], reverse=True ):
                symbol = signal['symbol'];
                if symbol not in seen_symbols:
                    seen_symbols[symbol] = True;
                    unique_signals.append( signal );
            
            # Limit to max signals
            if len( unique_signals ) > args.max_signals:
                unique_signals = unique_signals[:args.max_signals];
            
            all_signals = unique_signals;
        
        print( f"\n📊 STEP 3: Processing {len( all_signals )} total signals..." );
        
        if all_signals:
            # Generate charts
            print( f"📈 Generating charts..." );
            chart_paths = create_signal_charts( all_signals, save_dir='charts' );
            
            # Format signals for email
            email_html = scanner.format_signals_for_email( all_signals, chart_paths );
            motd_text = scanner.format_signals_for_motd( all_signals );
            
            # Send email notification
            if not args.no_email:
                print( f"📧 Sending email notification..." );
                email_sender = EmailSender();
                if email_sender.is_configured():
                    success = email_sender.send_daily_signals( all_signals, email_html );
                    if success:
                        print( "✅ Email notification sent" );
                    else:
                        print( "❌ Email notification failed" );
                else:
                    print( "ℹ️  Email not configured, skipping notification" );
            
            # Update MOTD
            if not args.no_motd:
                print( f"📝 Updating MOTD..." );
                motd_writer = MOTDWriter();
                success = motd_writer.write_signals_to_motd( motd_text );
                if success:
                    print( "✅ MOTD updated" );
                else:
                    print( "❌ MOTD update failed" );
            
            # Save to database
            if not args.no_db:
                print( f"💾 Saving to database..." );
                scanner.save_signals_to_database( all_signals );
            
            # Summary
            print( f"\n🎯 SCAN COMPLETED SUCCESSFULLY" );
            print( f"=" * 40 );
            print( f"📊 Symbols scanned: {len( symbols_with_data )}" );
            print( f"📈 Signals found: {len( all_signals )}" );
            print( f"📊 Charts generated: {len( chart_paths )}" );
            
            # Show top signals
            print( f"\n🏆 Top Signals:" );
            for i, signal in enumerate( all_signals[:5] ):
                emoji = "📈" if signal['signal_type'] == 'bullish' else "📉";
                source = signal['signal_source'];
                print( f"   {i+1}. {emoji} {signal['symbol']}: ${signal['current_price']:.2f} ({source}) - Strength: {signal['signal_strength']:.1f}%" );
        
        else:
            print( f"\nℹ️  No trading signals detected" );
            
            # Still update MOTD with no signals message
            if not args.no_motd:
                motd_writer = MOTDWriter();
                no_signals_text = f"📊 BTFD Scanner ({date.today()}): No signals detected.";
                motd_writer.write_signals_to_motd( no_signals_text );
        
        print( f"\n✅ Scanner completed at {datetime.now().strftime( '%H:%M:%S' )}" );
        return 0;
        
    except Exception as e:
        print( f"\n❌ Scanner failed: {e}" );
        import traceback;
        traceback.print_exc();
        return 1;

if __name__ == "__main__":
    sys.exit( main() );