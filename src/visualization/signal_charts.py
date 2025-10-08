"""
Signal Chart Generation for BTFD
Creates professional trading charts with price, EMA, and RSI indicators
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyBboxPatch
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Optional
import os
from pathlib import Path

from ..config.settings import get_config
from ..data.fetchers import DataManager
from ..indicators.technical import TechnicalIndicators

class SignalChartGenerator:
    """Generate professional trading charts for signals"""
    
    def __init__(self):
        self.config = get_config();
        self.data_manager = DataManager();
        self.indicators = TechnicalIndicators();
        
        # Chart styling
        plt.style.use('dark_background');
        self.colors = {
            'price': '#00D4AA',
            'ema_fast': '#FFD700', 
            'ema_slow': '#FF6B6B',
            'rsi': '#4ECDC4',
            'rsi_overbought': '#FF6B6B',
            'rsi_oversold': '#00D4AA',
            'volume': '#666666',
            'bullish_signal': '#00D4AA',
            'bearish_signal': '#FF6B6B',
            'grid': '#333333',
            'background': '#1a1a1a'
        };
    
    def generate_signal_chart(self, signal: Dict, days_back: int = 60, 
                            save_dir: str = None) -> Optional[str]:
        """
        Generate a comprehensive trading chart for a signal
        
        Args:
            signal: Signal dictionary with symbol and parameters
            days_back: Number of days of historical data to show
            save_dir: Directory to save chart (defaults to charts/)
            
        Returns:
            Path to saved chart file or None if failed
        """
        
        try:
            symbol = signal['symbol'];
            print(f"📊 Generating chart for {symbol}...");
            
            # Get historical data
            end_date = date.today();
            start_date = end_date - timedelta(days=days_back + 30);  # Extra for indicators
            
            stock_data = self.data_manager.get_stock_data(symbol, start_date, end_date);
            
            if stock_data is None or len(stock_data) < 30:
                print(f"⚠️  Insufficient data for {symbol} chart");
                return None;
            
            # Prepare data
            stock_data_indexed = stock_data.set_index('date');
            stock_data_indexed = stock_data_indexed.sort_index();
            
            # Calculate indicators using same parameters as signal detection
            close_prices = stock_data_indexed['close'];
            high_prices = stock_data_indexed['high'];
            low_prices = stock_data_indexed['low'];
            volume = stock_data_indexed['volume'];
            
            ema_fast = self.indicators.calculate_ema(close_prices, signal['ema_fast']);
            ema_slow = self.indicators.calculate_ema(close_prices, signal['ema_slow']);
            rsi = self.indicators.calculate_rsi(close_prices, 14);
            macd_data = self.indicators.calculate_macd(close_prices);
            cci = self.indicators.calculate_cci(high_prices, low_prices, close_prices, 20);
            
            # Limit to display period
            display_start = end_date - timedelta(days=days_back);
            mask = stock_data_indexed.index >= display_start;
            
            dates = stock_data_indexed.index[mask];
            prices = close_prices[mask];
            vol = volume[mask];
            ema_f = ema_fast[mask];
            ema_s = ema_slow[mask];
            rsi_vals = rsi[mask];
            macd_vals = macd_data['macd'][mask];
            macd_signal = macd_data['signal'][mask];
            macd_hist = macd_data['histogram'][mask];
            cci_vals = cci[mask];
            
            # Create figure with 5 subplots: Price+EMA, Volume, RSI, MACD, CCI
            fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(14, 16), 
                                               gridspec_kw={'height_ratios': [4, 1, 1.5, 1.5, 1.5]},
                                               facecolor=self.colors['background']);
            
            fig.suptitle(f'{symbol} - Trading Signal Analysis', 
                        fontsize=16, fontweight='bold', color='white');
            
            # Main price chart
            self._plot_price_chart(ax1, dates, prices, ema_f, ema_s, signal);
            
            # Volume chart
            self._plot_volume_chart(ax2, dates, vol);
            
            # RSI chart
            self._plot_rsi_chart(ax3, dates, rsi_vals);
            
            # MACD chart
            self._plot_macd_chart(ax4, dates, macd_vals, macd_signal, macd_hist);
            
            # CCI chart
            self._plot_cci_chart(ax5, dates, cci_vals);
            
            # Add signal annotation
            self._add_signal_annotation(ax1, signal, dates, prices);
            
            # Formatting
            for ax in [ax1, ax2, ax3, ax4, ax5]:
                ax.set_facecolor(self.colors['background']);
                ax.grid(True, color=self.colors['grid'], alpha=0.3);
                ax.tick_params(colors='white');
            
            # Date formatting (only on bottom chart)
            ax5.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'));
            ax5.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1));
            plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45);
            
            # Save chart
            if save_dir is None:
                save_dir = os.path.join(os.getcwd(), 'charts');
            
            Path(save_dir).mkdir(exist_ok=True);
            
            chart_filename = f"{symbol}_signal_{date.today().strftime('%Y%m%d')}.png";
            chart_path = os.path.join(save_dir, chart_filename);
            
            plt.tight_layout();
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', 
                       facecolor=self.colors['background']);
            plt.close(fig);
            
            print(f"✅ Chart saved: {chart_path}");
            return chart_path;
            
        except Exception as e:
            print(f"❌ Error generating chart for {signal.get('symbol', 'unknown')}: {e}");
            return None;
    
    def _plot_price_chart(self, ax, dates, prices, ema_fast, ema_slow, signal):
        """Plot main price chart with EMAs"""
        
        # Price line
        ax.plot(dates, prices, color=self.colors['price'], linewidth=2, 
                label=f"Price (${prices.iloc[-1]:.2f})");
        
        # EMA lines
        ax.plot(dates, ema_fast, color=self.colors['ema_fast'], linewidth=1.5,
                label=f"EMA({signal['ema_fast']})");
        ax.plot(dates, ema_slow, color=self.colors['ema_slow'], linewidth=1.5,
                label=f"EMA({signal['ema_slow']})");
        
        # Fill between EMAs to show crossover areas
        ax.fill_between(dates, ema_fast, ema_slow, 
                       where=(ema_fast > ema_slow), alpha=0.1, 
                       color=self.colors['bullish_signal'], label='Bullish Zone');
        ax.fill_between(dates, ema_fast, ema_slow, 
                       where=(ema_fast <= ema_slow), alpha=0.1, 
                       color=self.colors['bearish_signal'], label='Bearish Zone');
        
        ax.set_ylabel('Price ($)', color='white', fontweight='bold');
        ax.legend(loc='upper left', facecolor='black', edgecolor='white');
        ax.set_title(f"Price & EMA Analysis", color='white', fontweight='bold');
    
    def _plot_volume_chart(self, ax, dates, volume):
        """Plot volume chart"""
        
        ax.bar(dates, volume, color=self.colors['volume'], alpha=0.7, width=0.8);
        ax.set_ylabel('Volume', color='white', fontweight='bold');
        ax.set_title('Volume', color='white', fontweight='bold');
        
        # Format volume labels
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'
        ));
    
    def _plot_rsi_chart(self, ax, dates, rsi_values):
        """Plot RSI chart with overbought/oversold levels"""
        
        ax.plot(dates, rsi_values, color=self.colors['rsi'], linewidth=2, label='RSI(14)');
        
        # Overbought and oversold lines
        ax.axhline(70, color=self.colors['rsi_overbought'], linestyle='--', alpha=0.7, label='Overbought (70)');
        ax.axhline(30, color=self.colors['rsi_oversold'], linestyle='--', alpha=0.7, label='Oversold (30)');
        
        # Fill overbought/oversold areas
        ax.fill_between(dates, 70, 100, alpha=0.1, color=self.colors['rsi_overbought']);
        ax.fill_between(dates, 0, 30, alpha=0.1, color=self.colors['rsi_oversold']);
        
        ax.set_ylabel('RSI', color='white', fontweight='bold');
        ax.set_xlabel('Date', color='white', fontweight='bold');
        ax.set_ylim(0, 100);
        ax.legend(loc='upper left', facecolor='black', edgecolor='white');
        ax.set_title(f"RSI - Current: {rsi_values.iloc[-1]:.1f}", color='white', fontweight='bold');
    
    def _create_thermometer_gauge(self, ax, x, y, strength, signal_type, width=0.15, height=0.03):
        """Create a horizontal thermometer gauge showing signal strength"""
        
        # Gauge colors
        fill_color = self.colors['bullish_signal'] if signal_type == 'bullish' else self.colors['bearish_signal'];
        outline_color = 'black';
        
        # Convert strength to 0-1 range
        fill_ratio = strength / 100.0;
        
        # Create the outline (black border)
        outline = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.002",
            facecolor='none',
            edgecolor=outline_color,
            linewidth=2,
            transform=ax.transAxes
        );
        ax.add_patch(outline);
        
        # Create the filled portion 
        if fill_ratio > 0:
            fill = FancyBboxPatch(
                (x + 0.001, y + 0.001), width * fill_ratio - 0.002, height - 0.002,
                boxstyle="round,pad=0.001",
                facecolor=fill_color,
                edgecolor='none',
                alpha=0.8,
                transform=ax.transAxes
            );
            ax.add_patch(fill);
    
    def _plot_macd_chart(self, ax, dates, macd_vals, macd_signal, macd_hist):
        """Plot MACD chart with signal line and histogram"""
        
        # MACD line
        ax.plot(dates, macd_vals, color='#4ECDC4', linewidth=2, label='MACD');
        
        # Signal line
        ax.plot(dates, macd_signal, color='#FF6B6B', linewidth=1.5, label='Signal');
        
        # Histogram
        colors = ['#00D4AA' if x >= 0 else '#FF6B6B' for x in macd_hist];
        ax.bar(dates, macd_hist, color=colors, alpha=0.6, width=0.8, label='Histogram');
        
        # Zero line
        ax.axhline(0, color='white', linestyle='-', alpha=0.3);
        
        ax.set_ylabel('MACD', color='white', fontweight='bold');
        ax.legend(loc='upper left', facecolor='black', edgecolor='white');
        ax.set_title('MACD (12,26,9)', color='white', fontweight='bold');
    
    def _plot_cci_chart(self, ax, dates, cci_values):
        """Plot CCI chart with overbought/oversold levels"""
        
        ax.plot(dates, cci_values, color='#FFD700', linewidth=2, label='CCI(20)');
        
        # Overbought and oversold lines
        ax.axhline(100, color=self.colors['rsi_overbought'], linestyle='--', alpha=0.7, label='Overbought (+100)');
        ax.axhline(-100, color=self.colors['rsi_oversold'], linestyle='--', alpha=0.7, label='Oversold (-100)');
        ax.axhline(0, color='white', linestyle='-', alpha=0.3);
        
        # Fill overbought/oversold areas
        ax.fill_between(dates, 100, 300, alpha=0.1, color=self.colors['rsi_overbought']);
        ax.fill_between(dates, -300, -100, alpha=0.1, color=self.colors['rsi_oversold']);
        
        ax.set_ylabel('CCI', color='white', fontweight='bold');
        ax.set_xlabel('Date', color='white', fontweight='bold');
        ax.set_ylim(-300, 300);
        ax.legend(loc='upper left', facecolor='black', edgecolor='white');
        ax.set_title(f"CCI - Current: {cci_values.iloc[-1]:.1f}", color='white', fontweight='bold');
    
    def _add_signal_annotation(self, ax, signal, dates, prices):
        """Add signal annotation to chart"""
        
        signal_date = pd.to_datetime(signal['signal_date']);
        
        # Find closest date in our data 
        try:
            signal_date_ts = pd.Timestamp(signal_date);  # Ensure it's a pandas Timestamp
            if hasattr(dates, 'values'):
                closest_idx = np.abs(dates.values - signal_date_ts.value).argmin();
            else:
                closest_idx = (pd.Series(dates) - signal_date_ts).abs().argmin();
        except Exception as e:
            print(f"⚠️  Using last data point for signal annotation due to date error: {e}");
            closest_idx = len(dates) - 1;
        signal_price = prices.iloc[closest_idx];
        signal_x = dates[closest_idx];
        
        # Signal arrow and annotation
        signal_color = self.colors['bullish_signal'] if signal['signal_type'] == 'bullish' else self.colors['bearish_signal'];
        arrow_direction = '↑' if signal['signal_type'] == 'bullish' else '↓';
        
        # Create the thermometer gauge in the annotation
        annotation_text = (f"{arrow_direction} {signal['signal_type'].upper()} SIGNAL\n"
                          f"{signal['options_recommendation']}\n"
                          f"Strength: {signal['signal_strength']:.0f}%");
        
        ann = ax.annotate(annotation_text,
                         xy=(signal_x, signal_price), 
                         xytext=(10, 20 if signal['signal_type'] == 'bullish' else -20),
                         textcoords='offset points',
                         bbox=dict(boxstyle='round,pad=0.5', facecolor=signal_color, alpha=0.8),
                         arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', 
                                       color=signal_color, lw=2),
                         fontsize=10, fontweight='bold', color='white');
        
        # Add thermometer gauge next to the annotation
        # Get the annotation position in axes coordinates
        ann_bbox = ann.get_window_extent();
        ax_bbox = ax.get_window_extent();
        
        # Position thermometer slightly below the annotation
        gauge_x = 0.02;  # Left side of chart area
        gauge_y = 0.95 if signal['signal_type'] == 'bullish' else 0.05;  # Top for bullish, bottom for bearish
        
        self._create_thermometer_gauge(ax, gauge_x, gauge_y, 
                                     signal['signal_strength'], 
                                     signal['signal_type']);
        
        # Mark the signal point
        ax.scatter(signal_x, signal_price, color=signal_color, s=100, 
                  marker='o', edgecolor='white', linewidth=2, zorder=5);
    
    def generate_charts_for_signals(self, signals: List[Dict], save_dir: str = None) -> Dict[str, str]:
        """
        Generate charts for multiple signals
        
        Args:
            signals: List of signal dictionaries
            save_dir: Directory to save charts
            
        Returns:
            Dictionary mapping symbol to chart file path
        """
        
        chart_paths = {};
        
        for signal in signals:
            chart_path = self.generate_signal_chart(signal, save_dir=save_dir);
            if chart_path:
                chart_paths[signal['symbol']] = chart_path;
        
        print(f"📊 Generated {len(chart_paths)} charts");
        return chart_paths;

def create_signal_charts(signals: List[Dict], save_dir: str = None) -> Dict[str, str]:
    """
    Convenience function to generate charts for signals
    
    Args:
        signals: List of signal dictionaries
        save_dir: Directory to save charts
        
    Returns:
        Dictionary mapping symbol to chart file path
    """
    
    generator = SignalChartGenerator();
    return generator.generate_charts_for_signals(signals, save_dir);