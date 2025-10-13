#!/usr/bin/env python3
"""
SMA49/200 CrossoverScanner - Production Script
Scan for SMA49/200 crossovers in the last 14 days and send email notifications
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
    """Main SMA scanner function"""
    
    parser = argparse.ArgumentParser( description='BTFD SMA49/200 Crossover Scanner' );
    parser.add_argument( '--symbols', nargs='+', help='Specific symbols to scan' );
    parser.add_argument( '--max-signals', type=int, default=20, help='Maximum signals to return' );
    parser.add_argument( '--no-email', action='store_true', help='Skip email notification' );
    parser.add_argument( '--no-motd', action='store_true', help='Skip MOTD update' );
    parser.add_argument( '--no-db', action='store_true', help='Skip database save' );
    parser.add_argument( '--test-mode', action='store_true', help='Run in test mode with limited stocks' );
    
    args = parser.parse_args();
    
    print( f"🎯 BTFD SMA49/200 Crossover Scanner - {date.today()}" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( f"📊 Looking for SMA49/200 crosses in last 14 days" );
    print( "=" * 60 );
    
    # Initialize scanner
    scanner = DailySignalScanner();
    
    # Determine which symbols to scan
    symbols_to_scan = args.symbols;
    if args.test_mode:
        symbols_to_scan = symbols_to_scan[:5] if symbols_to_scan else ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'];
        print( "🧪 Running in test mode (limited stocks)" );
        print( f"   Test symbols: {symbols_to_scan}" );
    
    # Run the SMA scan
    try:
        print( f"🔍 Scanning for SMA49/200 crossovers..." );
        signals = scanner.scan_multiple_stocks_sma_only( 
            symbols=symbols_to_scan, 
            max_signals=args.max_signals
        );
        
        if signals:
            print( f"\\n📧 Found {len( signals )} SMA signals for processing..." );
            
            # Format signals for notifications
            email_html = format_sma_signals_for_email( signals );
            motd_text = format_sma_signals_for_motd( signals );
            
            # Send email notification
            if not args.no_email:
                email_sender = EmailSender();
                if email_sender.is_configured():
                    success = email_sender.send_daily_signals( signals, email_html );
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
                    print( "✅ MOTD updated with SMA signals" );
                else:
                    print( "❌ MOTD update failed" );
            
            # Save to database
            if not args.no_db:
                scanner.save_signals_to_database( signals );
                
        else:
            print( "\nℹ️  No SMA49/200 crossovers detected in the last 14 days" );
            
            # Still update MOTD with "no signals" message
            if not args.no_motd:
                motd_writer = MOTDWriter();
                no_signals_text = f"📊 SMA49/200 Scanner ({date.today()}): No crossovers detected in last 14 days.";
                motd_writer.write_signals_to_motd( no_signals_text );
        
        print( f"\n✅ SMA scan completed at {datetime.now().strftime( '%H:%M:%S' )}" );
        return 0;
        
    except Exception as e:
        print( f"\n❌ SMA scan failed: {e}" );
        import traceback;
        traceback.print_exc();
        return 1;

def format_sma_signals_for_email( signals: list ) -> str:
    """Format SMA signals for email notification"""
    
    if not signals:
        return "<p>No SMA49/200 crossovers detected.</p>";
    
    html = f"""
    <h2>📊 SMA49/200 Crossover Signals - {date.today()}</h2>
    <p><strong>Early Golden/Death Cross Detection</strong></p>
    <p>Found <strong>{len( signals )}</strong> SMA49/200 crossovers in the last 14 days:</p>
    
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f0f0f0;">
            <th>Symbol</th>
            <th>Cross Type</th>
            <th>Signal Date</th>
            <th>Days Ago</th>
            <th>Current Price</th>
            <th>Options Rec</th>
            <th>Strength</th>
            <th>SMA49</th>
            <th>SMA200</th>
            <th>RSI</th>
        </tr>
    """;
    
    for signal in signals:
        signal_color = "#90EE90" if signal['signal_type'] == 'bullish' else "#FFB6C1";
        strength_color = "#006400" if signal['signal_strength'] >= 70 else "#FF8C00" if signal['signal_strength'] >= 50 else "#8B0000";
        
        # Cross type with emoji
        cross_emoji = "🟢" if signal['signal_type'] == 'bullish' else "🔴";
        cross_name = "Golden Cross (Early)" if signal['signal_type'] == 'bullish' else "Death Cross (Early)";
        
        # Options recommendation with styling
        options_color = "#006400" if signal['options_recommendation'] == 'CALL' else "#8B0000";
        
        # Strength indicator
        strength_value = int( signal['signal_strength'] );
        if strength_value >= 70:
            strength_emoji = "✅";
            strength_desc = "Strong";
        elif strength_value >= 50:
            strength_emoji = "⚠️";
            strength_desc = "Moderate";
        else:
            strength_emoji = "❌";
            strength_desc = "Weak";
            
        html += f"""
        <tr style="background-color: {signal_color};">
            <td><strong>{signal['symbol']}</strong></td>
            <td>{cross_emoji} {cross_name}</td>
            <td>{signal['signal_date']}</td>
            <td>{signal['days_since_cross']}</td>
            <td>${signal['current_price']:.2f}</td>
            <td style="color: {options_color}; font-weight: bold;">{signal['options_recommendation']}</td>
            <td style="text-align: center;">
                {strength_emoji} <strong style="color: {strength_color};">{strength_value}%</strong><br/>
                <small>{strength_desc}</small>
            </td>
            <td>${signal.get('sma_fast_value', 0):.2f}</td>
            <td>${signal.get('sma_slow_value', 0):.2f}</td>
            <td>{signal['rsi_value']:.1f}</td>
        </tr>""";
    
    html += """
    </table>
    
    <h3>📈 About SMA49/200 Crossovers:</h3>
    <ul>
        <li><strong>Golden Cross:</strong> SMA49 crosses above SMA200 - traditionally bullish long-term signal</li>
        <li><strong>Death Cross:</strong> SMA49 crosses below SMA200 - traditionally bearish long-term signal</li>
        <li><strong>Early Warning:</strong> Using SMA49 instead of SMA50 gives you ~1 day advance notice</li>
        <li><strong>Lookback:</strong> Signals from last 14 days to catch recent crossovers</li>
    </ul>
    
    <h3>📊 Signal Strength Guide:</h3>
    <ul>
        <li>✅ <strong>70-100%:</strong> Strong Signal</li>
        <li>⚠️ <strong>50-70%:</strong> Moderate Signal</li>
        <li>❌ <strong>0-50%:</strong> Weak Signal</li>
    </ul>
    
    <p><em>Generated by BTFD SMA Scanner at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    """;
    
    return html;

def format_sma_signals_for_motd( signals: list ) -> str:
    """Format SMA signals for MOTD"""
    
    if not signals:
        return f"📊 SMA49/200 Scanner ({date.today()}): No crossovers in last 14 days.";
    
    motd = f"📊 SMA49/200 Crossovers ({date.today()}) - {len( signals )} signals:\n";
    
    for signal in signals[:5]:  # Limit MOTD to top 5 signals
        signal_emoji = "🟢" if signal['signal_type'] == 'bullish' else "🔴";
        cross_type = "Golden" if signal['signal_type'] == 'bullish' else "Death";
        options_emoji = "📞" if signal.get('options_recommendation') == 'CALL' else "📱" if signal.get('options_recommendation') == 'PUT' else "";
        
        # Strength indicator
        if signal['signal_strength'] >= 70:
            strength_emoji = "✅";
        elif signal['signal_strength'] >= 50:
            strength_emoji = "⚠️";
        else:
            strength_emoji = "❌";
        
        motd += f"  {signal_emoji} {signal['symbol']}: ${signal['current_price']:.2f} {cross_type} Cross {options_emoji} {strength_emoji}{signal['signal_strength']:.0f}% ({signal['days_since_cross']}d ago)\n";
    
    if len( signals ) > 5:
        motd += f"  ... and {len( signals ) - 5} more crossovers\n";
    
    motd += f"Generated: {datetime.now().strftime('%H:%M')}\n";
    
    return motd;

if __name__ == "__main__":
    sys.exit( main() );