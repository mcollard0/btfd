#!/usr/bin/env python3
"""
Test Enhanced Chart Generation System
Verify that every signal generates either a real or fallback chart with comprehensive logging
"""

import sys
import os
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Dict
import json

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.visualization.signal_charts import SignalChartGenerator;

def setup_test_logging():
    """Setup test logging"""
    
    Path( 'logs' ).mkdir( exist_ok=True );
    
    # Test logger
    logger = logging.getLogger( 'test_enhanced_charts' );
    logger.setLevel( logging.DEBUG );
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler( handler );
    
    # File handler
    file_handler = logging.FileHandler( 'logs/test_enhanced_charts.log' );
    file_formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' );
    file_handler.setFormatter( file_formatter );
    logger.addHandler( file_handler );
    
    # Console handler
    console_handler = logging.StreamHandler( sys.stdout );
    console_formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' );
    console_handler.setFormatter( console_formatter );
    logger.addHandler( console_handler );
    
    return logger;

def get_test_stocks_under_100() -> List[str]:
    """Get test stocks under $100"""
    
    # Manually curated list to ensure we have testable stocks
    test_stocks = [
        'KO', 'PEP', 'INTC', 'F', 'GE', 'BAC', 'WFC', 'T', 'VZ',
        'PYPL', 'UBER', 'LYFT', 'NKE', 'MCD', 'SBUX', 'WMT', 'TGT'
    ];
    
    return test_stocks;

def create_test_signal( symbol: str, signal_type: str = 'bullish' ) -> Dict:
    """Create a test signal for testing"""
    
    return {
        'symbol': symbol,
        'scan_date': date.today(),
        'signal_type': signal_type,
        'signal_date': date.today(),
        'current_price': 50.0,  # Placeholder price
        'options_recommendation': 'CALL' if signal_type == 'bullish' else 'PUT',
        'signal_source': 'EMA',
        'rsi_value': 55.0,
        'signal_strength': 65.0,
        'days_since_cross': 1,
        'ema_fast': 10,
        'ema_slow': 20,
        'ema_fast_value': 49.5,
        'ema_slow_value': 48.0
    };

def analyze_chart_verification_logs( logger ) -> Dict:
    """Analyze chart verification logs for results"""
    
    verification_log_path = 'logs/chart_verification.log';
    if not os.path.exists( verification_log_path ):
        logger.warning( "Chart verification log not found" );
        return {};
    
    results = {
        'successful_charts': [],
        'fallback_charts': [],
        'failed_charts': [],
        'total_processed': 0
    };
    
    try:
        with open( verification_log_path, 'r' ) as f:
            for line in f:
                if 'Chart generation SUCCESS:' in line:
                    try:
                        # Extract JSON from log line
                        json_start = line.find( '{' );
                        if json_start != -1:
                            chart_info = json.loads( line[json_start:] );
                            results['successful_charts'].append( chart_info );
                            results['total_processed'] += 1;
                    except json.JSONDecodeError as e:
                        logger.warning( f"Failed to parse success log: {e}" );
                
                elif 'Fallback chart generated' in line:
                    symbol_start = line.find( 'for ' ) + 4;
                    symbol_end = line.find( ':', symbol_start );
                    if symbol_start > 3 and symbol_end > symbol_start:
                        symbol = line[symbol_start:symbol_end];
                        results['fallback_charts'].append( symbol );
                        results['total_processed'] += 1;
                
                elif 'Complete failure for' in line:
                    symbol_start = line.find( 'for ' ) + 4;
                    symbol_end = line.find( ' -', symbol_start );
                    if symbol_start > 3 and symbol_end > symbol_start:
                        symbol = line[symbol_start:symbol_end];
                        results['failed_charts'].append( symbol );
                        results['total_processed'] += 1;
    
    except Exception as e:
        logger.error( f"Error analyzing verification logs: {e}" );
    
    return results;

def analyze_error_handling_logs( logger ) -> Dict:
    """Analyze error handling logs"""
    
    error_log_path = 'logs/error_handling.log';
    if not os.path.exists( error_log_path ):
        logger.warning( "Error handling log not found" );
        return {};
    
    error_summary = {
        'data_acquisition_errors': 0,
        'indicator_calculation_errors': 0,
        'rendering_errors': 0,
        'saving_errors': 0,
        'fallback_generations': 0,
        'unique_symbols_with_errors': set()
    };
    
    try:
        with open( error_log_path, 'r' ) as f:
            for line in f:
                if 'Data acquisition failed' in line:
                    error_summary['data_acquisition_errors'] += 1;
                elif 'indicator calculation failed' in line or 'Moving average calculation failed' in line:
                    error_summary['indicator_calculation_errors'] += 1;
                elif 'Chart plotting failed' in line or 'Chart formatting failed' in line:
                    error_summary['rendering_errors'] += 1;
                elif 'Chart saving failed' in line:
                    error_summary['saving_errors'] += 1;
                elif 'Generated fallback chart' in line:
                    error_summary['fallback_generations'] += 1;
                
                # Extract symbol from error line
                if ':' in line:
                    parts = line.split( ':' );
                    if len( parts ) > 2:
                        # Look for symbol pattern in the line
                        for part in parts:
                            if any( char.isupper() for char in part ) and len( part.strip() ) <= 6:
                                error_summary['unique_symbols_with_errors'].add( part.strip() );
                                break;
    
    except Exception as e:
        logger.error( f"Error analyzing error logs: {e}" );
    
    # Convert set to list for JSON serialization
    error_summary['unique_symbols_with_errors'] = list( error_summary['unique_symbols_with_errors'] );
    
    return error_summary;

def verify_chart_files( chart_paths: Dict[str, str], logger ) -> Dict:
    """Verify that chart files actually exist and are valid"""
    
    verification = {
        'existing_charts': 0,
        'missing_charts': 0,
        'empty_charts': 0,
        'valid_charts': 0,
        'fallback_charts': 0,
        'missing_symbols': []
    };
    
    for symbol, chart_path in chart_paths.items():
        if os.path.exists( chart_path ):
            verification['existing_charts'] += 1;
            
            file_size = os.path.getsize( chart_path );
            if file_size == 0:
                verification['empty_charts'] += 1;
                logger.warning( f"{symbol}: Chart file exists but is empty" );
            elif file_size < 1000:  # Very small file, probably broken
                verification['empty_charts'] += 1;
                logger.warning( f"{symbol}: Chart file suspiciously small ({file_size} bytes)" );
            else:
                verification['valid_charts'] += 1;
                
                # Check if it's a fallback chart
                if '_fallback.png' in chart_path:
                    verification['fallback_charts'] += 1;
                    
        else:
            verification['missing_charts'] += 1;
            verification['missing_symbols'].append( symbol );
            logger.error( f"{symbol}: Chart file missing: {chart_path}" );
    
    return verification;

def test_enhanced_chart_system( logger, test_stocks: List[str] ):
    """Run comprehensive test of enhanced chart system"""
    
    logger.info( f"🚀 Starting enhanced chart system test with {len( test_stocks )} stocks" );
    
    # Initialize scanner and chart generator
    scanner = DailySignalScanner();
    chart_generator = SignalChartGenerator();
    
    # Step 1: Run scanner to get real signals
    logger.info( "📊 Step 1: Running scanner for real signals..." );
    real_signals = scanner.scan_multiple_stocks( symbols=test_stocks, max_signals=20, include_sma=True );
    
    logger.info( f"   Found {len( real_signals )} real signals" );
    
    # Step 2: Create some test signals to ensure we have data to work with
    logger.info( "📋 Step 2: Creating additional test signals..." );
    test_signals = [];
    
    # Add test signals for stocks that didn't have real signals
    real_symbols = {s['symbol'] for s in real_signals};
    for stock in test_stocks[:10]:  # Test first 10 stocks
        if stock not in real_symbols:
            test_signals.append( create_test_signal( stock, 'bullish' ) );
            test_signals.append( create_test_signal( stock, 'bearish' ) );
    
    # Add some intentionally problematic test signals
    test_signals.append( create_test_signal( 'BADSTOCK1', 'bullish' ) );  # Non-existent stock
    test_signals.append( create_test_signal( 'BADSTOCK2', 'bearish' ) );  # Non-existent stock
    
    all_signals = real_signals + test_signals;
    logger.info( f"   Total signals for testing: {len( all_signals )} ({len( real_signals )} real + {len( test_signals )} test)" );
    
    # Step 3: Generate charts for all signals
    logger.info( "📈 Step 3: Generating charts for all signals..." );
    
    chart_paths = chart_generator.generate_charts_for_signals( all_signals, save_dir='charts' );
    
    logger.info( f"   Chart generation completed: {len( chart_paths )} charts created" );
    
    # Step 4: Analyze results
    logger.info( "🔍 Step 4: Analyzing results..." );
    
    # Analyze verification logs
    verification_results = analyze_chart_verification_logs( logger );
    
    # Analyze error logs  
    error_results = analyze_error_handling_logs( logger );
    
    # Verify chart files
    file_verification = verify_chart_files( chart_paths, logger );
    
    # Step 5: Generate comprehensive report
    logger.info( "📊 Step 5: Generating test report..." );
    
    test_report = {
        'test_timestamp': datetime.now().isoformat(),
        'test_parameters': {
            'test_stocks': test_stocks,
            'total_signals_tested': len( all_signals ),
            'real_signals': len( real_signals ),
            'test_signals': len( test_signals )
        },
        'chart_generation_results': {
            'total_charts_requested': len( all_signals ),
            'total_charts_generated': len( chart_paths ),
            'success_rate_percent': (len( chart_paths ) / len( all_signals ) * 100) if all_signals else 0
        },
        'verification_log_analysis': verification_results,
        'error_log_analysis': error_results,
        'file_verification': file_verification
    };
    
    # Save detailed report
    report_file = f"logs/enhanced_chart_test_report_{date.today().strftime('%Y%m%d')}.json";
    with open( report_file, 'w' ) as f:
        json.dump( test_report, f, indent=2 );
    
    logger.info( f"📋 Detailed test report saved: {report_file}" );
    
    return test_report;

def main():
    """Main test function"""
    
    logger = setup_test_logging();
    
    logger.info( "🎯 Enhanced Chart Generation System Test - Starting" );
    logger.info( f"⏰ Test started at {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" );
    logger.info( "=" * 70 );
    
    try:
        # Get test stocks
        test_stocks = get_test_stocks_under_100();
        logger.info( f"📋 Test stocks: {test_stocks}" );
        
        # Run comprehensive test
        test_report = test_enhanced_chart_system( logger, test_stocks );
        
        # Print summary
        logger.info( "\n📊 TEST SUMMARY" );
        logger.info( "=" * 50 );
        logger.info( f"✅ Signals tested: {test_report['chart_generation_results']['total_charts_requested']}" );
        logger.info( f"📊 Charts generated: {test_report['chart_generation_results']['total_charts_generated']}" );
        logger.info( f"🎯 Success rate: {test_report['chart_generation_results']['success_rate_percent']:.1f}%" );
        
        verification = test_report['file_verification'];
        logger.info( f"📈 Valid charts: {verification['valid_charts']}" );
        logger.info( f"🔧 Fallback charts: {verification['fallback_charts']}" );
        logger.info( f"❌ Missing charts: {verification['missing_charts']}" );
        
        error_analysis = test_report['error_log_analysis'];
        logger.info( f"⚠️  Unique symbols with errors: {len( error_analysis['unique_symbols_with_errors'] )}" );
        logger.info( f"🔧 Fallback generations: {error_analysis['fallback_generations']}" );
        
        # Determine test result
        if test_report['chart_generation_results']['success_rate_percent'] >= 90:
            logger.info( "✅ TEST PASSED: Chart generation system is robust" );
            return 0;
        elif test_report['chart_generation_results']['success_rate_percent'] >= 75:
            logger.warning( "⚠️  TEST WARNING: Chart generation needs improvement" );
            return 1;
        else:
            logger.error( "❌ TEST FAILED: Chart generation system needs significant fixes" );
            return 2;
    
    except Exception as e:
        logger.error( f"💥 Test failed with exception: {e}" );
        import traceback;
        logger.error( f"Stack trace: {traceback.format_exc()}" );
        return 1;
    
    finally:
        logger.info( f"\n⏰ Test completed at {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" );

if __name__ == "__main__":
    sys.exit( main() );