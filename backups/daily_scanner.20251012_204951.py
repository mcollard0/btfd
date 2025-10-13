"""
Daily Signal Detection System for BTFD
Scans for EMA crossovers with RSI context and generates trading signals
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sqlite3
import json

from ..config.settings import get_config, TechnicalConfig, StrategyConfig
from ..data.fetchers import DataManager
from ..indicators.technical import TechnicalIndicators
from ..optimization.parameter_sweep import ParameterSweepEngine
from ..visualization.signal_charts import create_signal_charts

class DailySignalScanner:
    """Main daily signal scanning engine"""
    
    def __init__( self ):
        self.config = get_config();
        self.data_manager = DataManager();
        self.indicators = TechnicalIndicators();
        self.optimization_engine = ParameterSweepEngine();
    
    def get_optimized_parameters( self, symbol: str = None ) -> Dict[str, int]:
        """
        Get optimized EMA parameters from previous optimization runs
        
        Args:
            symbol: Specific symbol to get parameters for, or None for best overall
            
        Returns:
            Dictionary with ema_fast, ema_slow, rsi_period
        """
        
        try:
            results = self.optimization_engine.get_saved_results( symbol );
            
            if not results.empty:
                # Get best result (highest total return)
                best_result = results.iloc[0];
                return {
                    'ema_fast': int( best_result['ema_fast'] ),
                    'ema_slow': int( best_result['ema_slow'] ),
                    'rsi_period': TechnicalConfig.RSI_PERIOD
                };
            else:
                print( f"ℹ️  No optimization results found for {symbol or 'any symbol'}, using defaults" );
        except Exception as e:
            print( f"⚠️  Error retrieving optimized parameters: {e}" );
        
        # Default parameters if no optimization results
        return {
            'ema_fast': 10,
            'ema_slow': 20,
            'rsi_period': TechnicalConfig.RSI_PERIOD
        };
    
    def scan_stock_for_signals( self, symbol: str, lookback_days: int = 5 ) -> Optional[Dict]:
        """
        Scan a single stock for trading signals
        
        Args:
            symbol: Stock symbol to scan
            lookback_days: Days to look back for recent crossovers
            
        Returns:
            Signal dictionary or None if no signal
        """
        
        # Get historical data (need extra days for technical indicators)
        end_date = date.today();
        start_date = end_date - timedelta( days=60 );  # 60 days for indicators + signals
        
        try:
            stock_data = self.data_manager.get_stock_data( symbol, start_date, end_date );
            
            if stock_data is None or len( stock_data ) < 30:
                print( f"⚠️  Insufficient data for {symbol}" );
                return None;
            
            # Filter by price range ($10-$100)
            current_price = stock_data['close'].iloc[-1];
            if not ( StrategyConfig.PRICE_MIN <= current_price <= StrategyConfig.PRICE_MAX ):
                print( f"ℹ️  {symbol} price ${current_price:.2f} outside range ${StrategyConfig.PRICE_MIN}-${StrategyConfig.PRICE_MAX}" );
                return None;
            
            # Get optimized parameters for this symbol
            params = self.get_optimized_parameters( symbol );
            
            # Set date as index
            stock_data_indexed = stock_data.set_index( 'date' );
            
            # Calculate technical indicators
            close_prices = stock_data_indexed['close'];
            rsi = self.indicators.calculate_rsi( close_prices, params['rsi_period'] );
            ema_fast = self.indicators.calculate_ema( close_prices, params['ema_fast'] );
            ema_slow = self.indicators.calculate_ema( close_prices, params['ema_slow'] );
            
            # Check for recent EMA crossovers
            crossovers = self.indicators.detect_ema_crossovers( ema_fast, ema_slow, lookback_days );
            
            if not crossovers:
                return None;  # No recent crossovers
            
            # Get most recent crossover
            latest_crossover = crossovers[-1];
            
            # Get RSI context
            current_rsi = rsi.dropna().iloc[-1] if not rsi.dropna().empty else 50;
            rsi_crosses = self.indicators.detect_rsi_crosses( rsi, TechnicalConfig.RSI_LOOKBACK_DAYS );
            
            # Calculate signal strength
            signal_strength = self._calculate_signal_strength(
                latest_crossover['type'], current_rsi, rsi_crosses,
                current_price, params
            );
            
            # Determine options recommendation
            options_recommendation = 'CALL' if latest_crossover['type'] == 'bullish' else 'PUT';
            
            # Add confidence level based on RSI context
            rsi_confirmation = "";
            if latest_crossover['type'] == 'bullish':
                if current_rsi < 40:
                    rsi_confirmation = " (RSI oversold - strong CALL setup)";
                elif current_rsi > 70:
                    rsi_confirmation = " (RSI overbought - weaker CALL)";
            else:  # bearish
                if current_rsi > 60:
                    rsi_confirmation = " (RSI overbought - strong PUT setup)";
                elif current_rsi < 30:
                    rsi_confirmation = " (RSI oversold - weaker PUT)";
            
            # Create signal record
            signal = {
                'symbol': symbol,
                'scan_date': date.today(),
                'signal_type': latest_crossover['type'],
                'signal_date': latest_crossover['date'],
                'current_price': current_price,
                'options_recommendation': options_recommendation,
                'options_confidence': rsi_confirmation,
                'ema_fast': params['ema_fast'],
                'ema_slow': params['ema_slow'],
                'ema_fast_value': latest_crossover['fast_ema'],
                'ema_slow_value': latest_crossover['slow_ema'],
                'rsi_value': current_rsi,
                'rsi_overbought_cross': rsi_crosses.get( 'overbought_cross' ),
                'rsi_oversold_cross': rsi_crosses.get( 'oversold_cross' ),
                'signal_strength': signal_strength,
                'days_since_cross': ( date.today() - latest_crossover['date'] ).days
            };
            
            return signal;
            
        except Exception as e:
            print( f"❌ Error scanning {symbol}: {e}" );
            return None;
    
    def _calculate_signal_strength( self, signal_type: str, current_rsi: float, 
                                   rsi_crosses: Dict, current_price: float, 
                                   params: Dict ) -> float:
        """
        Calculate signal strength score (0-100)
        
        Args:
            signal_type: 'bullish' or 'bearish'
            current_rsi: Current RSI value
            rsi_crosses: RSI cross information
            current_price: Current stock price
            params: EMA parameters used
            
        Returns:
            Signal strength score (0-100)
        """
        
        strength = 50.0;  # Base strength
        
        # RSI confirmation strength
        if signal_type == 'bullish':
            # Bullish signals stronger when RSI is oversold or recovering from oversold
            if current_rsi < TechnicalConfig.RSI_OVERSOLD:
                strength += 20;  # Very strong - currently oversold
            elif current_rsi < 40:
                strength += 10;  # Strong - below midpoint
            elif rsi_crosses.get( 'oversold_cross' ):
                strength += 15;  # Strong - recent oversold cross
                
            # Weaken if RSI is overbought
            if current_rsi > TechnicalConfig.RSI_OVERBOUGHT:
                strength -= 15;
                
        else:  # bearish
            # Bearish signals stronger when RSI is overbought
            if current_rsi > TechnicalConfig.RSI_OVERBOUGHT:
                strength += 20;  # Very strong - currently overbought
            elif current_rsi > 60:
                strength += 10;  # Strong - above midpoint
            elif rsi_crosses.get( 'overbought_cross' ):
                strength += 15;  # Strong - recent overbought cross
                
            # Weaken if RSI is oversold
            if current_rsi < TechnicalConfig.RSI_OVERSOLD:
                strength -= 15;
        
        # Price range bonus (middle of our range is preferred)
        price_score = 1.0 - abs( current_price - 55 ) / 45;  # Normalized around $55 midpoint
        strength += price_score * 5;  # Up to 5 points for good price
        
        # Parameter confidence (tighter EMAs might be more responsive)
        ema_gap = params['ema_slow'] - params['ema_fast'];
        if ema_gap <= 10:
            strength += 3;  # Bonus for responsive parameters
        
        # Ensure strength stays in 0-100 range
        return max( 0, min( 100, strength ) );
    
    def scan_multiple_stocks( self, symbols: List[str] = None, 
                            max_signals: int = 20 ) -> List[Dict]:
        """
        Scan multiple stocks for signals
        
        Args:
            symbols: List of symbols to scan, or None for auto-generated list
            max_signals: Maximum number of signals to return
            
        Returns:
            List of signal dictionaries, sorted by strength
        """
        
        if symbols is None:
            # Get suitable stocks automatically
            symbols = self.data_manager.get_stock_list();
            print( f"📋 Auto-selected {len( symbols )} stocks for scanning" );
        else:
            print( f"📋 Scanning {len( symbols )} specified stocks" );
        
        signals = [];
        
        for i, symbol in enumerate( symbols ):
            print( f"🔍 [{i+1}/{len( symbols )}] Scanning {symbol}..." );
            
            signal = self.scan_stock_for_signals( symbol );
            if signal:
                signals.append( signal );
                print( f"   ✅ {signal['signal_type'].upper()} signal - Strength: {signal['signal_strength']:.1f}" );
            else:
                print( f"   ℹ️  No signal" );
        
        # Sort by signal strength (strongest first)
        signals.sort( key=lambda x: x['signal_strength'], reverse=True );
        
        # Limit to max_signals
        if len( signals ) > max_signals:
            signals = signals[:max_signals];
            print( f"📊 Limiting to top {max_signals} signals" );
        
        return signals;
    
    def save_signals_to_database( self, signals: List[Dict] ):
        """
        Save detected signals to database
        
        Args:
            signals: List of signal dictionaries
        """
        
        if not signals:
            return;
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            for signal in signals:
                cursor.execute(
                    """INSERT OR REPLACE INTO daily_signals 
                       (date, symbol, signal_type, ema_fast, ema_slow, rsi_value, rsi_cross_date, price, strength_score)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal['scan_date'],
                        signal['symbol'],
                        signal['signal_type'],
                        signal['ema_fast'],
                        signal['ema_slow'],
                        signal['rsi_value'],
                        signal.get( 'rsi_oversold_cross' ) or signal.get( 'rsi_overbought_cross' ),
                        signal['current_price'],
                        signal['signal_strength']
                    )
                );
            
            conn.commit();
            conn.close();
            
            print( f"💾 Saved {len( signals )} signals to database" );
            
        except Exception as e:
            print( f"❌ Error saving signals to database: {e}" );
    
    def format_signals_for_email( self, signals: List[Dict], chart_paths: Dict[str, str] = None ) -> str:
        """
        Format signals for email notification
        
        Args:
            signals: List of signal dictionaries
            chart_paths: Dictionary mapping symbol to chart file path
            
        Returns:
            HTML formatted string
        """
        
        if not signals:
            return "<p>No trading signals detected today.</p>";
        
        html = f"""
        
        <h2>🎯 BTFD Daily Trading Signals - {date.today()}</h2>
        <p>Found <strong>{len( signals )}</strong> signals today:</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th>Symbol</th>
                <th>Chart</th>
                <th>Signal</th>
                <th>Options</th>
                <th>Price</th>
                <th>Strength</th>
                <th>EMA</th>
                <th>RSI</th>
                <th>RSI Context</th>
                <th>Days Since Cross</th>
            </tr>
        """;
        
        for signal in signals:
            signal_color = "#90EE90" if signal['signal_type'] == 'bullish' else "#FFB6C1";
            strength_color = "#006400" if signal['signal_strength'] >= 70 else "#FF8C00" if signal['signal_strength'] >= 50 else "#8B0000";
            
            # RSI context
            rsi_context = "";
            if signal.get( 'rsi_overbought_cross' ):
                rsi_context = f"⚠️ Overbought cross: {signal['rsi_overbought_cross']}";
            elif signal.get( 'rsi_oversold_cross' ):
                rsi_context = f"✅ Oversold cross: {signal['rsi_oversold_cross']}";
            else:
                rsi_context = "No recent crosses";
            
            # Options recommendation with styling
            options_color = "#006400" if signal['options_recommendation'] == 'CALL' else "#8B0000";
            
            # Generate Stockcharts URL
            stockcharts_url = f"https://stockcharts.com/sc3/ui/?s={signal['symbol']}"
            
            # Simple emoji strength indicator
            strength_value = int(signal['signal_strength']);
            
            # Determine emoji based on strength
            if strength_value >= 70:
                strength_emoji = "✅";  # Green checkmark for strong signals
                strength_desc = "Strong";
            elif strength_value >= 50:
                strength_emoji = "⚠️";   # Warning for moderate signals  
                strength_desc = "Moderate";
            else:
                strength_emoji = "❌";  # Red X for weak signals
                strength_desc = "Weak";
            
            html += f"""
            <tr style="background-color: {signal_color};">
                <td><strong>{signal['symbol']}</strong></td>
                <td><a href="{stockcharts_url}" target="_blank" style="text-decoration: none; background-color: #007bff; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">📊 Chart</a></td>
                <td>{signal['signal_type'].upper()}</td>
                <td style="color: {options_color}; font-weight: bold;">{signal['options_recommendation']}{signal.get('options_confidence', '')}</td>
                <td>${signal['current_price']:.2f}</td>
                <td style="text-align: center;">
                    {strength_emoji} <strong style="color: {strength_color};">{strength_value}%</strong><br/>
                    <small>{strength_desc}</small>
                </td>
                <td>EMA({signal['ema_fast']},{signal['ema_slow']})</td>
                <td>{signal['rsi_value']:.1f}</td>
                <td>{rsi_context}</td>
                <td>{signal['days_since_cross']}</td>
            </tr>""";
        
        html += """
        </table>
        """;
        
        # Add charts section if charts were generated
        if chart_paths and any(symbol in chart_paths for symbol in [s['symbol'] for s in signals]):
            html += """
            <h3>📊 Technical Analysis Charts:</h3>
            <p><em>Professional technical analysis charts showing price action, EMA crossovers, RSI analysis, and volume. Charts are embedded below for each signal.</em></p>
            """;
            
            for signal in signals:
                symbol = signal['symbol'];
                if symbol in chart_paths:
                    chart_name = f"{symbol}_signal_{date.today().strftime('%Y%m%d')}.png";
                    # Calculate strength values for emoji display
                    detail_strength_value = int(signal['signal_strength']);
                    detail_strength_color = "#006400" if signal['signal_strength'] >= 70 else "#FF8C00" if signal['signal_strength'] >= 50 else "#8B0000";
                    
                    # Determine emoji for detailed view
                    if detail_strength_value >= 70:
                        detail_emoji = "✅";
                        detail_desc = "Strong Signal";
                    elif detail_strength_value >= 50:
                        detail_emoji = "⚠️";
                        detail_desc = "Moderate Signal";
                    else:
                        detail_emoji = "❌";
                        detail_desc = "Weak Signal";
                    
                    html += f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9;">
                        <h4 style="margin-top: 0; color: #007bff;">{symbol} - {signal['signal_type'].upper()} {signal['options_recommendation']} Signal</h4>
                        <p><strong>Price:</strong> ${signal['current_price']:.2f} | <strong>EMA:</strong> ({signal['ema_fast']},{signal['ema_slow']}) | <strong>RSI:</strong> {signal['rsi_value']:.1f}</p>
                        <p><strong>Signal Strength:</strong> {detail_emoji} <span style="color: {detail_strength_color}; font-weight: bold; font-size: 18px;">{detail_strength_value}%</span> <em>({detail_desc})</em></p>
                        <img src="cid:{symbol}_chart" alt="{symbol} Technical Analysis Chart" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 5px; margin: 10px 0; display: block;"/>
                        <p style="font-size: 12px; color: #666; text-align: center;"><em>Professional technical analysis chart showing 5 indicators: Price/EMA, Volume, RSI, MACD, CCI</em></p>
                    </div>
                    """;
            
            html += "<p style='font-size: 12px; color: #666;'><em>Charts will be embedded as images in supported email clients.</em></p>";
        
        # Generate timestamp
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S');
        
        html += f"""
        <h3>📊 Signal Strength Guide:</h3>
        <ul>
            <li>✅ <strong>70-100%:</strong> Strong Signal (Green checkmark)</li>
            <li>⚠️ <strong>50-70%:</strong> Moderate Signal (Yellow warning)</li>
            <li>❌ <strong>0-50%:</strong> Weak Signal (Red X)</li>
        </ul>
        
        <h3>🔍 RSI Context:</h3>
        <ul>
            <li><strong>Oversold Cross:</strong> RSI recently crossed below 30 (bullish context)</li>
            <li><strong>Overbought Cross:</strong> RSI recently crossed above 70 (bearish context)</li>
        </ul>
        
        <p><em>Generated by BTFD Daily Scanner at {current_timestamp}</em></p>
        """;
        
        return html;
    
    def format_signals_for_motd( self, signals: List[Dict] ) -> str:
        """
        Format signals for MOTD (Message of the Day)
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            Plain text formatted string
        """
        
        if not signals:
            return f"🎯 BTFD Scanner ({date.today()}): No signals detected today.";
        
        motd = f"🎯 BTFD Daily Signals ({date.today()}) - {len( signals )} signals:\n";
        
        for signal in signals[:5]:  # Limit MOTD to top 5 signals
            signal_emoji = "📈" if signal['signal_type'] == 'bullish' else "📉";
            options_emoji = "📞" if signal.get('options_recommendation') == 'CALL' else "📱" if signal.get('options_recommendation') == 'PUT' else "";
            
            # Simple emoji strength indicator
            if signal['signal_strength'] >= 70:
                strength_emoji = "✅";  # Green checkmark for strong
            elif signal['signal_strength'] >= 50:
                strength_emoji = "⚠️";   # Warning for moderate
            else:
                strength_emoji = "❌";  # Red X for weak
            
            # Build options display
            options_display = f" {options_emoji}{signal.get('options_recommendation', '')}" if signal.get('options_recommendation') else "";
            
            rsi_context = "";
            if signal.get( 'rsi_oversold_cross' ):
                rsi_context = " (RSI oversold)";
            elif signal.get( 'rsi_overbought_cross' ):
                rsi_context = " (RSI overbought)";
            
            motd += f"  {signal_emoji} {signal['symbol']}: ${signal['current_price']:.2f}{options_display} {strength_emoji}{signal['signal_strength']:.0f}{rsi_context}\n";
        
        if len( signals ) > 5:
            motd += f"  ... and {len( signals ) - 5} more signals\n";
        
        motd += f"Generated: {datetime.now().strftime('%H:%M')}\n";
        
        return motd;
    
    def run_daily_scan( self, symbols: List[str] = None, save_to_db: bool = True ) -> List[Dict]:
        """
        Run complete daily scan workflow
        
        Args:
            symbols: Symbols to scan (None for auto-selection)
            save_to_db: Whether to save results to database
            
        Returns:
            List of detected signals
        """
        
        print( f"🚀 BTFD Daily Scanner - {date.today()}" );
        print( "=" * 50 );
        
        # Run the scan
        signals = self.scan_multiple_stocks( symbols );
        
        print( f"\n📊 Scan Results:" );
        print( f"   🎯 Total Signals: {len( signals )}" );
        
        if signals:
            bullish_count = sum( 1 for s in signals if s['signal_type'] == 'bullish' );
            bearish_count = len( signals ) - bullish_count;
            avg_strength = sum( s['signal_strength'] for s in signals ) / len( signals );
            
            print( f"   📈 Bullish: {bullish_count}" );
            print( f"   📉 Bearish: {bearish_count}" );
            print( f"   💪 Avg Strength: {avg_strength:.1f}" );
            
            # Show top 3 signals
            print( f"\n🏆 Top Signals:" );
            for i, signal in enumerate( signals[:3] ):
                emoji = "📈" if signal['signal_type'] == 'bullish' else "📉";
                print( f"   {i+1}. {emoji} {signal['symbol']}: ${signal['current_price']:.2f} (Strength: {signal['signal_strength']:.1f})" );
        
        # Generate charts for signals
        chart_paths = {};
        if signals:
            print( f"\n📊 Generating charts for signals..." );
            try:
                chart_paths = create_signal_charts( signals );
                if chart_paths:
                    print( f"✅ Generated {len(chart_paths)} charts" );
            except Exception as e:
                print( f"⚠️  Chart generation failed: {e}" );
        
        # Save to database
        if save_to_db:
            self.save_signals_to_database( signals );
        
        # Store chart paths for use by notification system
        if hasattr( self, '_last_chart_paths' ):
            self._last_chart_paths = chart_paths;
        else:
            setattr( self, '_last_chart_paths', chart_paths );
        
        return signals;

# Convenience functions
def run_quick_scan( max_stocks: int = 10 ) -> List[Dict]:
    """Run quick daily scan on limited stocks"""
    
    scanner = DailySignalScanner();
    data_manager = DataManager();
    
    # Get limited stock list for quick testing
    symbols = data_manager.get_stock_list()[:max_stocks];
    
    return scanner.run_daily_scan( symbols );

def get_recent_signals( days_back: int = 7 ) -> pd.DataFrame:
    """Get recent signals from database"""
    
    config = get_config();
    
    try:
        conn = config.get_database_connection();
        
        query = """
            SELECT date, symbol, signal_type, price, strength_score, 
                   ema_fast, ema_slow, rsi_value 
            FROM daily_signals 
            WHERE date >= date('now', '-{} days')
            ORDER BY date DESC, strength_score DESC
        """.format( days_back );
        
        df = pd.read_sql_query( query, conn );
        conn.close();
        
        return df;
        
    except Exception as e:
        print( f"Error retrieving recent signals: {e}" );
        return pd.DataFrame();