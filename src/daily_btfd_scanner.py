#!/usr/bin/env python3
"""
BTFD Daily Scanner - Main Production Script
Complete daily signal detection and notification system
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime
import argparse

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from src.scanner.daily_scanner import DailySignalScanner;
from src.notifications.email_sender import EmailSender;
from src.notifications.motd_writer import MOTDWriter;
from src.config.settings import get_config;

def main():
    """Main daily scanner function"""
    
    parser = argparse.ArgumentParser( description='BTFD Daily Signal Scanner' );
    parser.add_argument( '--symbols', nargs='+', help='Specific symbols to scan' );
    parser.add_argument( '--max-signals', type=int, default=20, help='Maximum signals to return' );
    parser.add_argument( '--no-email', action='store_true', help='Skip email notification' );
    parser.add_argument( '--no-motd', action='store_true', help='Skip MOTD update' );
    parser.add_argument( '--no-db', action='store_true', help='Skip database save' );
    parser.add_argument( '--test-mode', action='store_true', help='Run in test mode with limited stocks' );
    
    args = parser.parse_args();
    
    print( f"🚀 BTFD Daily Scanner - {date.today()}" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( "=" * 60 );
    
    # Initialize scanner
    scanner = DailySignalScanner();
    
    # Determine which symbols to scan
    symbols_to_scan = args.symbols;
    if args.test_mode:
        symbols_to_scan = symbols_to_scan[:5] if symbols_to_scan else None;
        print( "🧪 Running in test mode (limited stocks)" );
    
    # Run the daily scan
    try:
        signals = scanner.run_daily_scan( 
            symbols=symbols_to_scan, 
            save_to_db=not args.no_db 
        );
        
        if signals:
            print( f"\n📧 Processing {len( signals )} signals for notifications..." );
            
            # Generate formatted content (with charts if available)
            chart_paths = getattr( scanner, '_last_chart_paths', {} );
            email_html = scanner.format_signals_for_email( signals, chart_paths );
            motd_text = scanner.format_signals_for_motd( signals );
            
            # Send email notification
            if not args.no_email:
                email_sender = EmailSender();
                if email_sender.is_configured():
                    success = email_sender.send_daily_signals( signals, email_html, chart_paths );
                    if success:
                        print( "✅ Email notification sent" );
                    else:
                        print( "❌ Email notification failed" );
                else:
                    print( "ℹ️  Email not configured, skipping email notification" );
            
            # Update MOTD
            if not args.no_motd:
                motd_writer = MOTDWriter();
                success = motd_writer.write_signals_to_motd( motd_text );
                if success:
                    print( "✅ MOTD updated with signals" );
                else:
                    print( "❌ MOTD update failed" );
            
        else:
            print( "\nℹ️  No signals detected today" );
            
            # Still update MOTD with "no signals" message
            if not args.no_motd:
                motd_writer = MOTDWriter();
                no_signals_text = f"🎯 BTFD Scanner ({date.today()}): No signals detected today.";
                motd_writer.write_signals_to_motd( no_signals_text );
        
        print( f"\n✅ Daily scan completed at {datetime.now().strftime( '%H:%M:%S' )}" );
        return 0;
        
    except Exception as e:
        print( f"\n❌ Daily scan failed: {e}" );
        import traceback;
        traceback.print_exc();
        return 1;

if __name__ == "__main__":
    sys.exit( main() );