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
import logging
import traceback
import json
from datetime import datetime

from ..config.settings import get_config
from ..data.fetchers import DataManager
from ..indicators.technical import TechnicalIndicators

class SignalChartGenerator:
    """Generate professional trading charts for signals"""
    
    def __init__(self):
        self.config = get_config();
        self.data_manager = DataManager();
        self.indicators = TechnicalIndicators();
        
        # Setup logging
        self._setup_logging();
        
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
        
    def _setup_logging(self):
        """Setup dedicated loggers for chart generation"""
        
        # Create logs directory
        Path('logs').mkdir(exist_ok=True);
        
        # Chart verification logger
        self.chart_logger = logging.getLogger('chart_verification');
        self.chart_logger.setLevel(logging.DEBUG);
        
        # Remove existing handlers to prevent duplicates
        for handler in self.chart_logger.handlers[:]:
            self.chart_logger.removeHandler(handler);
        
        chart_handler = logging.FileHandler('logs/chart_verification.log');
        chart_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s');
        chart_handler.setFormatter(chart_formatter);
        self.chart_logger.addHandler(chart_handler);
        
        # Error handling logger
        self.error_logger = logging.getLogger('chart_error_handling');
        self.error_logger.setLevel(logging.DEBUG);
        
        # Remove existing handlers
        for handler in self.error_logger.handlers[:]:
            self.error_logger.removeHandler(handler);
        
        error_handler = logging.FileHandler('logs/error_handling.log');
        error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s');
        error_handler.setFormatter(error_formatter);
        self.error_logger.addHandler(error_handler);
        
    def _generate_fallback_chart(self, signal: Dict, error_msg: str, save_dir: str) -> Optional[str]:
        """
        Generate a minimal fallback chart when main chart generation fails
        
        Args:
            signal: Signal dictionary
            error_msg: Error message from failed generation
            save_dir: Directory to save chart
            
        Returns:
            Path to saved fallback chart or None if failed
        """
        
        try:
            symbol = signal.get('symbol', 'UNKNOWN');
            
            # Create simple fallback chart
            fig, ax = plt.subplots(1, 1, figsize=(10, 6), facecolor=self.colors['background']);
            
            # Set background
            ax.set_facecolor(self.colors['background']);
            
            # Add error message
            ax.text(0.5, 0.6, f"Chart Generation Failed", 
                   ha='center', va='center', fontsize=20, color='white', fontweight='bold');
            ax.text(0.5, 0.5, f"Symbol: {symbol}", 
                   ha='center', va='center', fontsize=16, color='white');
            ax.text(0.5, 0.4, f"Signal: {signal.get('signal_type', 'unknown').upper()}", 
                   ha='center', va='center', fontsize=14, color='white');
            ax.text(0.5, 0.3, f"Price: ${signal.get('current_price', 'N/A')}", 
                   ha='center', va='center', fontsize=12, color='white');
            ax.text(0.5, 0.2, "Data Unavailable - See logs for details", 
                   ha='center', va='center', fontsize=10, color='#FF6B6B', style='italic');
            
            # Remove axes
            ax.set_xlim(0, 1);
            ax.set_ylim(0, 1);
            ax.axis('off');
            
            # Title
            fig.suptitle(f'{symbol} - Signal Chart (Fallback)', 
                        fontsize=16, fontweight='bold', color='white');
            
            # Save fallback chart
            Path(save_dir).mkdir(exist_ok=True);
            chart_filename = f"{symbol}_signal_{date.today().strftime('%Y%m%d')}_fallback.png";
            chart_path = os.path.join(save_dir, chart_filename);
            
            plt.tight_layout();
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', 
                       facecolor=self.colors['background']);
            plt.close(fig);
            
            self.error_logger.info(f"Generated fallback chart for {symbol}: {chart_path}");
            return chart_path;
            
        except Exception as fallback_error:
            self.error_logger.error(f"Fallback chart generation failed for {symbol}: {fallback_error}");
            return None;
    
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
        
        symbol = signal.get('symbol', 'UNKNOWN');
        start_time = datetime.now();
        
        # Log chart generation attempt
        self.chart_logger.info(f"Starting chart generation for {symbol}");
        
        # Set default save directory
        if save_dir is None:
            save_dir = os.path.join(os.getcwd(), 'charts');
        
        try:
            print(f"📊 Generating chart for {symbol}...");
            
            # Get historical data
            end_date = date.today();
            start_date = end_date - timedelta(days=days_back + 30);  # Extra for indicators
            
            # Data acquisition with error handling
            try:
                stock_data = self.data_manager.get_stock_data(symbol, start_date, end_date);
                self.chart_logger.debug(f"Retrieved {len(stock_data) if stock_data is not None else 0} data points for {symbol}");
            except Exception as data_error:
                error_msg = f"Data acquisition failed: {data_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            if stock_data is None or len(stock_data) < 30:
                error_msg = f"Insufficient data: {len(stock_data) if stock_data is not None else 0} points (need 30+)";
                self.error_logger.warning(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Prepare data
            stock_data_indexed = stock_data.set_index('date');
            stock_data_indexed = stock_data_indexed.sort_index();
            
            # Technical indicator calculations with error handling
            try:
                close_prices = stock_data_indexed['close'];
                high_prices = stock_data_indexed['high'];
                low_prices = stock_data_indexed['low'];
                volume = stock_data_indexed['volume'];
                self.chart_logger.debug(f"{symbol}: Extracted price data series");
            except Exception as extract_error:
                error_msg = f"Price data extraction failed: {extract_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Handle both EMA and SMA signals
            try:
                if 'ema_fast' in signal:
                    # EMA signal
                    ma_fast = self.indicators.calculate_ema(close_prices, signal['ema_fast']);
                    ma_slow = self.indicators.calculate_ema(close_prices, signal['ema_slow']);
                    ma_type = 'EMA';
                    ma_fast_period = signal['ema_fast'];
                    ma_slow_period = signal['ema_slow'];
                else:
                    # SMA signal 
                    ma_fast = self.indicators.calculate_sma(close_prices, signal['sma_fast']);
                    ma_slow = self.indicators.calculate_sma(close_prices, signal['sma_slow']);
                    ma_type = 'SMA';
                    ma_fast_period = signal['sma_fast'];
                    ma_slow_period = signal['sma_slow'];
                    
                self.chart_logger.debug(f"{symbol}: Calculated {ma_type} indicators");
            except Exception as ma_error:
                error_msg = f"Moving average calculation failed: {ma_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Calculate additional indicators
            try:
                rsi = self.indicators.calculate_rsi(close_prices, 14);
                macd_data = self.indicators.calculate_macd(close_prices);
                cci = self.indicators.calculate_cci(high_prices, low_prices, close_prices, 20);
                self.chart_logger.debug(f"{symbol}: Calculated RSI, MACD, CCI indicators");
            except Exception as indicator_error:
                error_msg = f"Technical indicator calculation failed: {indicator_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Limit to display period
            display_start = end_date - timedelta(days=days_back);
            mask = stock_data_indexed.index >= display_start;
            
            dates = stock_data_indexed.index[mask];
            prices = close_prices[mask];
            vol = volume[mask];
            ma_f = ma_fast[mask];
            ma_s = ma_slow[mask];
            rsi_vals = rsi[mask];
            macd_vals = macd_data['macd'][mask];
            macd_signal = macd_data['signal'][mask];
            macd_hist = macd_data['histogram'][mask];
            cci_vals = cci[mask];
            
            # Chart rendering with error handling
            try:
                # Create figure with 5 subplots: Price+EMA, Volume, RSI, MACD, CCI
                fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(14, 16), 
                                                   gridspec_kw={'height_ratios': [4, 1, 1.5, 1.5, 1.5]},
                                                   facecolor=self.colors['background']);
                
                fig.suptitle(f'{symbol} - Trading Signal Analysis', 
                            fontsize=16, fontweight='bold', color='white');
                
                self.chart_logger.debug(f"{symbol}: Created figure and subplots");
            except Exception as figure_error:
                error_msg = f"Figure creation failed: {figure_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Plot individual charts with error handling
            try:
                # Main price chart
                self._plot_price_chart(ax1, dates, prices, ma_f, ma_s, signal, ma_type, ma_fast_period, ma_slow_period);
                
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
                
                self.chart_logger.debug(f"{symbol}: Completed individual chart plotting");
            except Exception as plot_error:
                plt.close(fig);  # Clean up figure
                error_msg = f"Chart plotting failed: {plot_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Formatting with error handling
            try:
                for ax in [ax1, ax2, ax3, ax4, ax5]:
                    ax.set_facecolor(self.colors['background']);
                    ax.grid(True, color=self.colors['grid'], alpha=0.3);
                    ax.tick_params(colors='white');
                
                # Date formatting (only on bottom chart)
                ax5.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'));
                ax5.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1));
                plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45);
                
                self.chart_logger.debug(f"{symbol}: Applied formatting");
            except Exception as format_error:
                plt.close(fig);  # Clean up figure
                error_msg = f"Chart formatting failed: {format_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
            # Save chart with error handling
            try:
                Path(save_dir).mkdir(exist_ok=True);
                
                chart_filename = f"{symbol}_signal_{date.today().strftime('%Y%m%d')}.png";
                chart_path = os.path.join(save_dir, chart_filename);
                
                plt.tight_layout();
                plt.savefig(chart_path, dpi=150, bbox_inches='tight', 
                           facecolor=self.colors['background']);
                plt.close(fig);
                
                # Verify file was created
                if os.path.exists(chart_path) and os.path.getsize(chart_path) > 0:
                    end_time = datetime.now();
                    duration = (end_time - start_time).total_seconds();
                    
                    # Log successful chart generation
                    chart_info = {
                        'symbol': symbol,
                        'timestamp': end_time.isoformat(),
                        'chart_file_path': chart_path,
                        'status': 'SUCCESS',
                        'duration_seconds': duration,
                        'file_size_bytes': os.path.getsize(chart_path),
                        'signal_type': signal.get('signal_type', 'unknown'),
                        'signal_strength': signal.get('signal_strength', 0)
                    };
                    
                    self.chart_logger.info(f"Chart generation SUCCESS: {json.dumps(chart_info)}");
                    print(f"✅ Chart saved: {chart_path}");
                    return chart_path;
                else:
                    error_msg = "Chart file was not created or is empty";
                    self.error_logger.error(f"{symbol}: {error_msg}");
                    return self._generate_fallback_chart(signal, error_msg, save_dir);
                
            except Exception as save_error:
                # Clean up any partial figure
                try:
                    plt.close(fig);
                except:
                    pass;
                
                error_msg = f"Chart saving failed: {save_error}";
                self.error_logger.error(f"{symbol}: {error_msg}");
                return self._generate_fallback_chart(signal, error_msg, save_dir);
            
        except Exception as e:
            end_time = datetime.now();
            duration = (end_time - start_time).total_seconds();
            
            # Log comprehensive error information
            error_info = {
                'symbol': symbol,
                'timestamp': end_time.isoformat(),
                'status': 'FAILURE',
                'error_message': str(e),
                'duration_seconds': duration,
                'traceback': traceback.format_exc()
            };
            
            self.error_logger.error(f"Chart generation FAILURE: {json.dumps(error_info, indent=2)}");
            print(f"❌ Error generating chart for {symbol}: {e}");
            
            # Try fallback chart generation
            return self._generate_fallback_chart(signal, str(e), save_dir);
    
    def _plot_price_chart(self, ax, dates, prices, ma_fast, ma_slow, signal, ma_type, ma_fast_period, ma_slow_period):
        """Plot main price chart with moving averages (EMA or SMA)"""
        
        # Price line
        ax.plot(dates, prices, color=self.colors['price'], linewidth=2, 
                label=f"Price (${prices.iloc[-1]:.2f})");
        
        # MA lines
        ax.plot(dates, ma_fast, color=self.colors['ema_fast'], linewidth=1.5,
                label=f"{ma_type}({ma_fast_period})");
        ax.plot(dates, ma_slow, color=self.colors['ema_slow'], linewidth=1.5,
                label=f"{ma_type}({ma_slow_period})");
        
        # Fill between MAs to show crossover areas
        ax.fill_between(dates, ma_fast, ma_slow, 
                       where=(ma_fast > ma_slow), alpha=0.1, 
                       color=self.colors['bullish_signal'], label='Bullish Zone');
        ax.fill_between(dates, ma_fast, ma_slow, 
                       where=(ma_fast <= ma_slow), alpha=0.1, 
                       color=self.colors['bearish_signal'], label='Bearish Zone');
        
        ax.set_ylabel('Price ($)', color='white', fontweight='bold');
        ax.legend(loc='upper left', facecolor='black', edgecolor='white');
        ax.set_title(f"Price & {ma_type} Analysis", color='white', fontweight='bold');
    
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
        Generate charts for multiple signals with comprehensive logging
        
        Args:
            signals: List of signal dictionaries
            save_dir: Directory to save charts
            
        Returns:
            Dictionary mapping symbol to chart file path
        """
        
        start_time = datetime.now();
        chart_paths = {};
        success_count = 0;
        fallback_count = 0;
        failure_count = 0;
        
        self.chart_logger.info(f"Starting batch chart generation for {len(signals)} signals");
        
        for i, signal in enumerate(signals):
            symbol = signal.get('symbol', f'UNKNOWN_{i}');
            self.chart_logger.debug(f"Processing signal {i+1}/{len(signals)}: {symbol}");
            
            chart_path = self.generate_signal_chart(signal, save_dir=save_dir);
            
            if chart_path:
                chart_paths[symbol] = chart_path;
                
                # Check if it's a fallback chart
                if '_fallback.png' in chart_path:
                    fallback_count += 1;
                    self.chart_logger.warning(f"Fallback chart generated for {symbol}: {chart_path}");
                else:
                    success_count += 1;
            else:
                failure_count += 1;
                self.chart_logger.error(f"Complete failure for {symbol} - no chart generated");
        
        end_time = datetime.now();
        duration = (end_time - start_time).total_seconds();
        
        # Log batch summary
        batch_summary = {
            'timestamp': end_time.isoformat(),
            'total_signals': len(signals),
            'successful_charts': success_count,
            'fallback_charts': fallback_count,
            'complete_failures': failure_count,
            'total_charts_generated': len(chart_paths),
            'duration_seconds': duration,
            'charts_per_second': len(chart_paths) / duration if duration > 0 else 0
        };
        
        self.chart_logger.info(f"Batch chart generation completed: {json.dumps(batch_summary)}");
        
        print(f"📊 Generated {len(chart_paths)} charts ({success_count} success, {fallback_count} fallback, {failure_count} failed)");
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