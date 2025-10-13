#!/usr/bin/env python3
"""
Quick EMA Scanner Run
Generate some EMA signals and charts
"""

import sys
import os
from datetime import date, datetime

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.notifications.email_sender import EmailSender;

def main():
    print( f"🎯 BTFD EMA Scanner - {date.today()}" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( "=" * 50 );
    
    # Run scanner
    scanner = DailySignalScanner();
    
    # Get some specific stocks to test
    test_stocks = ['KO', 'PYPL', 'INTC', 'F', 'GE', 'BAC', 'T', 'VZ', 'NKE', 'UBER'];
    
    print( f"📊 Scanning {len( test_stocks )} stocks for EMA signals..." );
    
    signals = scanner.scan_multiple_stocks( 
        symbols=test_stocks,
        max_signals=10,
        include_sma=False  # Only EMA
    );
    
    if signals:
        print( f"\n📧 Found {len( signals )} EMA signals!" );
        
        # Generate charts
        from src.visualization.signal_charts import create_signal_charts;
        
        print( "📈 Generating charts..." );
        chart_paths = create_signal_charts( signals, save_dir='charts' );
        
        print( f"📊 Generated {len( chart_paths )} charts" );
        
        # Format for email
        email_html = scanner.format_signals_for_email( signals, chart_paths );
        
        # Send email
        email_sender = EmailSender();
        if email_sender.is_configured():
            success = email_sender.send_daily_signals( signals, email_html );
            if success:
                print( "✅ Email sent successfully!" );
            else:
                print( "❌ Email sending failed" );
        else:
            print( "ℹ️  Email not configured" );
        
        # Save to database
        scanner.save_signals_to_database( signals );
        
    else:
        print( "\nℹ️  No EMA signals found" );
    
    print( f"\n✅ EMA scan completed at {datetime.now().strftime( '%H:%M:%S' )}" );
    return 0;

if __name__ == "__main__":
    sys.exit( main() );