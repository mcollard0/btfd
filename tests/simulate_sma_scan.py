#!/usr/bin/env python3
"""
Simulate SMA49/200 Scanner Run
Demo script to show what the SMA scanner would find and email
"""

import sys
import os
from datetime import date, datetime, timedelta
import random

def simulate_sma_signals():
    """Simulate what SMA49/200 signals might be found"""
    
    # Simulate some realistic SMA crossover signals
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMD', 'AMZN'];
    signal_types = ['bullish', 'bearish'];
    
    signals = [];
    
    # Generate 3-7 random signals
    num_signals = random.randint( 3, 7 );
    
    for i in range( num_signals ):
        symbol = random.choice( symbols );
        signal_type = random.choice( signal_types );
        
        # Random signal date within last 14 days
        days_ago = random.randint( 1, 14 );
        signal_date = date.today() - timedelta( days=days_ago );
        
        # Generate realistic price and SMA values
        current_price = random.uniform( 15.0, 95.0 );
        
        if signal_type == 'bullish':
            # Golden cross: SMA49 recently crossed above SMA200
            sma49_value = current_price * random.uniform( 0.98, 1.02 );
            sma200_value = sma49_value * random.uniform( 0.95, 0.99 );
            options_rec = 'CALL';
            strength = random.uniform( 55, 85 );  # Generally stronger for golden cross
        else:
            # Death cross: SMA49 recently crossed below SMA200  
            sma49_value = current_price * random.uniform( 0.98, 1.02 );
            sma200_value = sma49_value * random.uniform( 1.01, 1.05 );
            options_rec = 'PUT';
            strength = random.uniform( 45, 75 );  # Mixed strength for death cross
        
        # Generate RSI
        rsi_value = random.uniform( 25, 75 );
        
        # Create signal record
        signal = {
            'symbol': symbol,
            'scan_date': date.today(),
            'signal_type': signal_type,
            'signal_date': signal_date,
            'current_price': current_price,
            'options_recommendation': options_rec,
            'options_confidence': f" ({signal_type.title()} Cross - early warning)",
            'signal_source': 'SMA',
            'rsi_value': rsi_value,
            'signal_strength': strength,
            'days_since_cross': days_ago,
            'sma_fast': 49,
            'sma_slow': 200,
            'sma_fast_value': sma49_value,
            'sma_slow_value': sma200_value
        };
        
        signals.append( signal );
        
        # Remove symbol from list to avoid duplicates
        symbols = [s for s in symbols if s != symbol];
    
    return signals;

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

def main():
    """Simulate SMA scanner run"""
    
    print( f"🎯 BTFD SMA49/200 Crossover Scanner (SIMULATION) - {date.today()}" );
    print( f"⏰ Started at {datetime.now().strftime( '%H:%M:%S' )}" );
    print( f"📊 Looking for SMA49/200 crosses in last 14 days" );
    print( "=" * 60 );
    
    print( "🔍 Scanning for SMA49/200 crossovers..." );
    
    # Simulate the scanning process
    signals = simulate_sma_signals();
    
    if signals:
        print( f"\n📊 Found {len( signals )} SMA crossover signals!" );
        print( "\n🎯 Signal Summary:" );
        
        bullish_count = sum( 1 for s in signals if s['signal_type'] == 'bullish' );
        bearish_count = len( signals ) - bullish_count;
        avg_strength = sum( s['signal_strength'] for s in signals ) / len( signals );
        
        print( f"   🟢 Golden Crosses: {bullish_count}" );
        print( f"   🔴 Death Crosses: {bearish_count}" );
        print( f"   💪 Avg Strength: {avg_strength:.1f}" );
        
        print( f"\n📋 Detailed Signals:" );
        for i, signal in enumerate( signals ):
            cross_type = "Golden" if signal['signal_type'] == 'bullish' else "Death";
            emoji = "🟢" if signal['signal_type'] == 'bullish' else "🔴";
            
            print( f"   {i+1}. {emoji} {signal['symbol']}: ${signal['current_price']:.2f} - {cross_type} Cross" );
            print( f"       Date: {signal['signal_date']} ({signal['days_since_cross']} days ago)" );
            print( f"       Strength: {signal['signal_strength']:.1f}% | Options: {signal['options_recommendation']}" );
            print( f"       SMA49: ${signal['sma_fast_value']:.2f} | SMA200: ${signal['sma_slow_value']:.2f}" );
        
        # Generate email content
        print( f"\n📧 Email content preview:" );
        email_html = format_sma_signals_for_email( signals );
        print( "   HTML email formatted and ready for sending" );
        print( f"   Content length: {len( email_html )} characters" );
        
        # Save email content for review
        email_file = f"sma_signals_email_{date.today().strftime('%Y%m%d')}.html";
        with open( email_file, 'w' ) as f:
            f.write( email_html );
        print( f"   📁 Email content saved to: {email_file}" );
        
    else:
        print( "\nℹ️  No SMA49/200 crossovers detected in the last 14 days" );
    
    print( f"\n✅ SMA scan simulation completed at {datetime.now().strftime( '%H:%M:%S' )}" );
    
    return 0;

if __name__ == "__main__":
    sys.exit( main() );
