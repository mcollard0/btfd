#!/usr/bin/env python3
"""
Test KO Chart Generation Failure
Reproduce the issue with KO not generating charts during scanning
"""

import sys
import os
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.data.fetchers import DataManager;
from src.visualization.signal_charts import SignalChartGenerator;
from src.config.settings import get_config;

def setup_logging():
    """Setup comprehensive logging for debugging"""
    
    # Create logs directory
    Path( 'logs' ).mkdir( exist_ok=True );
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler( 'logs/test_ko.log' ),
            logging.StreamHandler( sys.stdout )
        ]
    );
    
    logger = logging.getLogger( __name__ );
    return logger;

def get_test_ticker_universe( max_price: float = 100.0, max_tickers: int = 50 ) -> List[str]:
    """
    Get test universe of tickers under $100, ensuring KO is included
    
    Args:
        max_price: Maximum stock price to include
        max_tickers: Maximum number of tickers to return
        
    Returns:
        List of stock symbols
    """
    
    # Base ticker list (from fetchers.py) - ensuring KO is prioritized
    priority_tickers = ['KO'];  # Ensure KO is first
    candidate_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 
        'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'PYPL', 'DIS', 'NKE',
        'BABA', 'UBER', 'LYFT', 'SNAP', 'SQ', 'ROKU', 'ZOOM',
        'BA', 'GE', 'F', 'GM', 'CAT', 'JPM', 'GS', 'V', 'MA',
        'WMT', 'TGT', 'HD', 'LOW', 'MCD', 'SBUX', 'PEP',
        
        # Additional tickers likely under $100
        'T', 'VZ', 'PFE', 'JNJ', 'WFC', 'BAC', 'XOM', 'CVX', 
        'UNH', 'PG', 'JNJ', 'MRK', 'ABT', 'TMO', 'LLY',
        'COST', 'AVGO', 'TXN', 'QCOM', 'CMCSA', 'PEP'
    ];
    
    # Combine and deduplicate
    all_candidates = priority_tickers + [t for t in candidate_tickers if t not in priority_tickers];
    
    logger = logging.getLogger( __name__ );
    logger.info( f"🔍 Testing price filtering for {len( all_candidates )} candidate tickers (max price: ${max_price})" );
    
    data_manager = DataManager();
    suitable_tickers = [];
    
    for i, symbol in enumerate( all_candidates ):
        if len( suitable_tickers ) >= max_tickers:
            break;
            
        try:
            logger.debug( f"📊 [{i+1}/{len( all_candidates )}] Checking price for {symbol}..." );
            current_price = data_manager.yahoo_fetcher.get_current_price( symbol );
            
            if current_price:
                logger.debug( f"   💰 {symbol}: ${current_price:.2f}" );
                if current_price <= max_price:
                    suitable_tickers.append( symbol );
                    logger.info( f"✅ {symbol}: ${current_price:.2f} - INCLUDED" );
                else:
                    logger.info( f"❌ {symbol}: ${current_price:.2f} - EXCLUDED (over ${max_price})" );
            else:
                logger.warning( f"⚠️  {symbol}: No price data available" );
                
        except Exception as e:
            logger.error( f"💥 Error getting price for {symbol}: {e}" );
    
    logger.info( f"🎯 Final test universe: {len( suitable_tickers )} tickers under ${max_price}" );
    logger.info( f"📋 Tickers: {suitable_tickers}" );
    
    # Ensure KO is in the list if it was supposed to be
    if 'KO' not in suitable_tickers:
        logger.warning( "⚠️  KO not in final list - adding it anyway for testing" );
        suitable_tickers.insert( 0, 'KO' );
    
    return suitable_tickers;

def test_ko_signal_detection( logger, tickers: List[str] ) -> Dict:
    """
    Test signal detection specifically for KO
    
    Args:
        logger: Logger instance
        tickers: List of tickers to scan
        
    Returns:
        Dictionary with KO signal data or None
    """
    
    logger.info( "🔍 Testing signal detection for KO..." );
    
    scanner = DailySignalScanner();
    
    # First, try to detect signals just for KO
    logger.info( "📊 Scanning KO for EMA signals..." );
    ko_ema_signal = scanner.scan_stock_for_signals( 'KO' );
    
    logger.info( "📊 Scanning KO for SMA signals..." );  
    ko_sma_signal = scanner.scan_stock_for_sma_signals( 'KO' );
    
    results = {
        'ema_signal': ko_ema_signal,
        'sma_signal': ko_sma_signal
    };
    
    if ko_ema_signal:
        logger.info( f"✅ KO EMA Signal detected: {ko_ema_signal['signal_type']} (Strength: {ko_ema_signal['signal_strength']:.1f})" );
    else:
        logger.info( "ℹ️  No KO EMA signal detected" );
        
    if ko_sma_signal:
        logger.info( f"✅ KO SMA Signal detected: {ko_sma_signal['signal_type']} (Strength: {ko_sma_signal['signal_strength']:.1f})" );
    else:
        logger.info( "ℹ️  No KO SMA signal detected" );
    
    return results;

def test_ko_chart_generation( logger, ko_signals: Dict ) -> Dict[str, str]:
    """
    Test chart generation specifically for KO signals
    
    Args:
        logger: Logger instance
        ko_signals: Dictionary with KO signal data
        
    Returns:
        Dictionary with chart paths
    """
    
    logger.info( "📊 Testing chart generation for KO signals..." );
    
    chart_generator = SignalChartGenerator();
    chart_paths = {};
    
    # Test EMA signal chart
    if ko_signals['ema_signal']:
        logger.info( "📈 Generating chart for KO EMA signal..." );
        try:
            ema_chart_path = chart_generator.generate_signal_chart( 
                ko_signals['ema_signal'],
                days_back=60,
                save_dir='charts'
            );
            
            if ema_chart_path:
                chart_paths['KO_EMA'] = ema_chart_path;
                logger.info( f"✅ KO EMA chart generated: {ema_chart_path}" );
            else:
                logger.error( "❌ KO EMA chart generation returned None" );
                
        except Exception as e:
            logger.error( f"💥 KO EMA chart generation failed: {e}" );
            import traceback;
            logger.error( f"Stack trace: {traceback.format_exc()}" );
    
    # Test SMA signal chart  
    if ko_signals['sma_signal']:
        logger.info( "📈 Generating chart for KO SMA signal..." );
        try:
            sma_chart_path = chart_generator.generate_signal_chart(
                ko_signals['sma_signal'], 
                days_back=60,
                save_dir='charts'
            );
            
            if sma_chart_path:
                chart_paths['KO_SMA'] = sma_chart_path;
                logger.info( f"✅ KO SMA chart generated: {sma_chart_path}" );
            else:
                logger.error( "❌ KO SMA chart generation returned None" );
                
        except Exception as e:
            logger.error( f"💥 KO SMA chart generation failed: {e}" );
            import traceback;
            logger.error( f"Stack trace: {traceback.format_exc()}" );
    
    return chart_paths;

def test_full_scanner_run( logger, tickers: List[str] ) -> List[Dict]:
    """
    Test full scanner run on ticker universe
    
    Args:
        logger: Logger instance
        tickers: List of tickers to scan
        
    Returns:
        List of detected signals
    """
    
    logger.info( f"🚀 Running full scanner on {len( tickers )} tickers..." );
    
    scanner = DailySignalScanner();
    
    try:
        # Run both EMA and SMA scans
        signals = scanner.scan_multiple_stocks( 
            symbols=tickers,
            max_signals=20,
            include_sma=True
        );
        
        logger.info( f"📊 Scanner completed: {len( signals )} total signals detected" );
        
        # Check specifically for KO signals
        ko_signals = [s for s in signals if s['symbol'] == 'KO'];
        if ko_signals:
            logger.info( f"🎯 KO signals found: {len( ko_signals )}" );
            for ko_signal in ko_signals:
                logger.info( f"   📈 {ko_signal['signal_type']} {ko_signal['signal_source']} signal (Strength: {ko_signal['signal_strength']:.1f})" );
        else:
            logger.warning( "⚠️  No KO signals found in full scan" );
        
        return signals;
        
    except Exception as e:
        logger.error( f"💥 Full scanner run failed: {e}" );
        import traceback;
        logger.error( f"Stack trace: {traceback.format_exc()}" );
        return [];

def test_chart_generation_for_all_signals( logger, signals: List[Dict] ) -> Dict[str, str]:
    """
    Test chart generation for all detected signals
    
    Args:
        logger: Logger instance
        signals: List of signal dictionaries
        
    Returns:
        Dictionary mapping symbol to chart path
    """
    
    logger.info( f"📊 Testing chart generation for {len( signals )} signals..." );
    
    chart_generator = SignalChartGenerator();
    
    try:
        chart_paths = chart_generator.generate_charts_for_signals( signals, save_dir='charts' );
        
        logger.info( f"📈 Chart generation completed: {len( chart_paths )} charts created" );
        
        # Check specifically for KO
        ko_charts = {k: v for k, v in chart_paths.items() if k == 'KO'};
        if ko_charts:
            logger.info( f"✅ KO charts generated: {ko_charts}" );
        else:
            logger.error( "❌ No KO charts generated!" );
            
            # Check if KO had signals but no chart
            ko_signals = [s for s in signals if s['symbol'] == 'KO'];
            if ko_signals:
                logger.error( f"💥 PROBLEM: KO had {len( ko_signals )} signals but no charts generated!" );
                for ko_signal in ko_signals:
                    logger.error( f"   Missing chart for: {ko_signal['signal_type']} {ko_signal['signal_source']} signal" );
        
        return chart_paths;
        
    except Exception as e:
        logger.error( f"💥 Chart generation for all signals failed: {e}" );
        import traceback;
        logger.error( f"Stack trace: {traceback.format_exc()}" );
        return {};

def main():
    """Main test function"""
    
    logger = setup_logging();
    
    logger.info( "🎯 KO Chart Generation Test - Starting" );
    logger.info( f"⏰ Test started at {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" );
    logger.info( "=" * 60 );
    
    try:
        # Step 1: Get test ticker universe
        logger.info( "📋 Step 1: Building test ticker universe..." );
        tickers = get_test_ticker_universe( max_price=100.0, max_tickers=50 );
        
        if not tickers:
            logger.error( "❌ No suitable tickers found for testing" );
            return 1;
        
        if 'KO' not in tickers:
            logger.error( "❌ KO not in ticker universe - cannot test KO issue" );
            return 1;
        
        logger.info( f"✅ Test universe ready: {len( tickers )} tickers (KO position: {tickers.index( 'KO' ) + 1})" );
        
        # Step 2: Test KO signal detection in isolation
        logger.info( "\n📊 Step 2: Testing KO signal detection..." );
        ko_signals = test_ko_signal_detection( logger, tickers );
        
        # Step 3: Test KO chart generation in isolation
        logger.info( "\n📈 Step 3: Testing KO chart generation..." );
        ko_charts = test_ko_chart_generation( logger, ko_signals );
        
        # Step 4: Run full scanner
        logger.info( "\n🚀 Step 4: Running full scanner..." );
        all_signals = test_full_scanner_run( logger, tickers );
        
        # Step 5: Test chart generation for all signals
        logger.info( "\n📊 Step 5: Testing chart generation for all signals..." );
        all_charts = test_chart_generation_for_all_signals( logger, all_signals );
        
        # Summary
        logger.info( "\n📊 TEST SUMMARY" );
        logger.info( "=" * 40 );
        logger.info( f"✅ Tickers tested: {len( tickers )}" );
        logger.info( f"📈 Total signals: {len( all_signals )}" );
        logger.info( f"📊 Total charts: {len( all_charts )}" );
        
        # KO specific results
        ko_signals_found = [s for s in all_signals if s['symbol'] == 'KO'];
        ko_charts_found = {k: v for k, v in all_charts.items() if k == 'KO'};
        
        logger.info( f"\n🎯 KO SPECIFIC RESULTS:" );
        logger.info( f"   📈 KO signals detected: {len( ko_signals_found )}" );
        logger.info( f"   📊 KO charts generated: {len( ko_charts_found )}" );
        
        if ko_signals_found and not ko_charts_found:
            logger.error( "💥 ISSUE REPRODUCED: KO had signals but no charts!" );
            logger.error( "   This confirms the chart generation failure for KO" );
            return 2;  # Issue reproduced
        elif ko_signals_found and ko_charts_found:
            logger.info( "✅ KO charts generated successfully - issue may be intermittent" );
            return 0;  # Success
        else:
            logger.info( "ℹ️  No KO signals detected - cannot test chart generation" );
            return 3;  # No signals to test
        
    except Exception as e:
        logger.error( f"💥 Test failed with exception: {e}" );
        import traceback;
        logger.error( f"Stack trace: {traceback.format_exc()}" );
        return 1;
    
    finally:
        logger.info( f"\n⏰ Test completed at {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" );

if __name__ == "__main__":
    sys.exit( main() );