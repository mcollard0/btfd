"""
Interactive Visualization for BTFD Strategy Optimization
Creates P/L heatmaps and performance charts using Plotly
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple
import json

from ..config.settings import get_config
from .parameter_sweep import ParameterSweepEngine

class OptimizationVisualizer:
    """Interactive visualization for optimization results"""
    
    def __init__( self ):
        self.config = get_config();
        self.engine = ParameterSweepEngine();
    
    def create_performance_heatmap( self, symbol: str, results: List[Dict], 
                                   metric: str = 'total_return', 
                                   title: str = None ) -> go.Figure:
        """
        Create interactive heatmap of parameter performance
        
        Args:
            symbol: Stock symbol
            results: Optimization results from parameter_sweep
            metric: Performance metric to visualize
            title: Custom title for the heatmap
            
        Returns:
            Plotly Figure object
        """
        
        if not results:
            print( f"❌ No results available for {symbol}" );
            return go.Figure();
        
        # Convert results to DataFrame for easier manipulation
        df = pd.DataFrame( results );
        
        # Create pivot table for heatmap
        heatmap_data = df.pivot_table(
            index='ema_slow', 
            columns='ema_fast', 
            values=metric, 
            aggfunc='mean'
        );
        
        # Format title
        if title is None:
            metric_names = {
                'total_return': 'Total Return (%)',
                'sharpe_ratio': 'Sharpe Ratio',
                'win_rate': 'Win Rate (%)', 
                'max_drawdown': 'Max Drawdown (%)'
            };
            metric_display = metric_names.get( metric, metric.title() );
            title = f"{symbol} - {metric_display} Optimization Heatmap";
        
        # Create heatmap
        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale='RdYlGn',
                showscale=True,
                hovertemplate='<b>EMA Fast:</b> %{x}<br>' +
                             '<b>EMA Slow:</b> %{y}<br>' +
                             f'<b>{metric_display}:</b> %{{z:.2%}}<br>' +
                             '<extra></extra>',
                zmin=heatmap_data.min().min() if metric != 'max_drawdown' else None,
                zmax=heatmap_data.max().max() if metric != 'max_drawdown' else None
            )
        );
        
        # Update layout
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Fast EMA Period',
            yaxis_title='Slow EMA Period',
            width=800,
            height=600,
            font=dict( size=12 )
        );
        
        # Add best parameter annotation
        if metric != 'max_drawdown':
            best_idx = df[metric].idxmax();
        else:
            best_idx = df[metric].idxmin();  # Lower drawdown is better
            
        best_result = df.iloc[best_idx];
        
        fig.add_annotation(
            x=best_result['ema_fast'],
            y=best_result['ema_slow'],
            text="★ BEST",
            showarrow=True,
            arrowhead=2,
            arrowcolor='white',
            arrowwidth=2,
            bgcolor='rgba(0,0,0,0.8)',
            bordercolor='white',
            borderwidth=2,
            font=dict( color='white', size=10 )
        );
        
        return fig;
    
    def create_multi_metric_dashboard( self, symbol: str, results: List[Dict] ) -> go.Figure:
        """
        Create dashboard with multiple performance metrics
        
        Args:
            symbol: Stock symbol
            results: Optimization results
            
        Returns:
            Plotly Figure with subplots
        """
        
        if not results:
            return go.Figure();
        
        # Create subplot figure
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Total Return (%)', 
                'Sharpe Ratio',
                'Win Rate (%)', 
                'Max Drawdown (%)'
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        );
        
        df = pd.DataFrame( results );
        metrics = ['total_return', 'sharpe_ratio', 'win_rate', 'max_drawdown'];
        positions = [(1,1), (1,2), (2,1), (2,2)];
        
        for metric, (row, col) in zip( metrics, positions ):
            # Create pivot table
            heatmap_data = df.pivot_table(
                index='ema_slow',
                columns='ema_fast', 
                values=metric,
                aggfunc='mean'
            );
            
            # Color scale (inverted for drawdown)
            colorscale = 'RdYlGn_r' if metric == 'max_drawdown' else 'RdYlGn';
            
            fig.add_trace(
                go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale=colorscale,
                    showscale=False,
                    hovertemplate=f'<b>{metric}:</b> %{{z:.2%}}<extra></extra>'
                ),
                row=row, col=col
            );
        
        # Update layout
        fig.update_layout(
            title={
                'text': f"{symbol} - Parameter Optimization Dashboard",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            width=1000,
            height=700
        );
        
        # Update all subplot axes
        for i in range( 1, 5 ):
            fig.update_xaxes( title_text='Fast EMA', row=(i-1)//2+1, col=(i-1)%2+1 );
            fig.update_yaxes( title_text='Slow EMA', row=(i-1)//2+1, col=(i-1)%2+1 );
        
        return fig;
    
    def create_parameter_comparison( self, symbols: List[str], metric: str = 'total_return' ) -> go.Figure:
        """
        Compare best parameters across multiple stocks
        
        Args:
            symbols: List of stock symbols
            metric: Performance metric to compare
            
        Returns:
            Plotly Figure with comparison
        """
        
        best_results = [];
        
        for symbol in symbols:
            saved_results = self.engine.get_saved_results( symbol );
            if not saved_results.empty:
                # Get best result for this symbol
                if metric != 'max_drawdown':
                    best_idx = saved_results[metric].idxmax();
                else:
                    best_idx = saved_results[metric].idxmin();
                
                best_result = saved_results.iloc[best_idx];
                best_results.append({
                    'symbol': symbol,
                    'ema_fast': best_result['ema_fast'],
                    'ema_slow': best_result['ema_slow'],
                    'performance': best_result[metric]
                });
        
        if not best_results:
            return go.Figure();
        
        df = pd.DataFrame( best_results );
        
        # Create scatter plot
        fig = go.Figure();
        
        # Add scatter points
        fig.add_trace(
            go.Scatter(
                x=df['ema_fast'],
                y=df['ema_slow'],
                mode='markers+text',
                marker=dict(
                    size=15,
                    color=df['performance'],
                    colorscale='RdYlGn' if metric != 'max_drawdown' else 'RdYlGn_r',
                    showscale=True,
                    colorbar=dict( title=metric.title() )
                ),
                text=df['symbol'],
                textposition='middle center',
                textfont=dict( size=8, color='white' ),
                hovertemplate='<b>%{text}</b><br>' +
                             'Fast EMA: %{x}<br>' +
                             'Slow EMA: %{y}<br>' +
                             f'{metric}: %{{marker.color:.2%}}<br>' +
                             '<extra></extra>',
                name='Stocks'
            )
        );
        
        # Update layout
        fig.update_layout(
            title=f"Best EMA Parameters by Stock - {metric.title()}",
            xaxis_title='Fast EMA Period',
            yaxis_title='Slow EMA Period',
            width=800,
            height=600,
            showlegend=False
        );
        
        return fig;
    
    def create_equity_curve_comparison( self, symbol: str, top_n: int = 3 ) -> go.Figure:
        """
        Compare equity curves for top N parameter combinations
        
        Args:
            symbol: Stock symbol
            top_n: Number of top parameter combinations to show
            
        Returns:
            Plotly Figure with equity curves
        """
        
        # Get saved results for symbol
        saved_results = self.engine.get_saved_results( symbol );
        
        if saved_results.empty or len( saved_results ) < top_n:
            return go.Figure();
        
        # Get top N results
        top_results = saved_results.head( top_n );
        
        fig = go.Figure();
        
        # This is a simplified version - in a full implementation,
        # you'd need to store the actual equity curves during backtesting
        for i, (idx, result) in enumerate( top_results.iterrows() ):
            # Simulate an equity curve (in reality, this would be stored)
            days = 252;
            returns = np.random.normal( 0.001, 0.02, days );  # Daily returns
            equity = [10000];  # Starting capital
            
            for daily_return in returns:
                equity.append( equity[-1] * (1 + daily_return) );
            
            # Adjust final value to match stored result
            final_multiplier = result['total_return'] + 1;
            equity = [e * final_multiplier / (equity[-1]/10000) for e in equity];
            
            fig.add_trace(
                go.Scatter(
                    x=list( range( len( equity ) ) ),
                    y=equity,
                    mode='lines',
                    name=f"EMA({result['ema_fast']},{result['ema_slow']}) - {result['total_return']:.1%}",
                    line=dict( width=2 )
                )
            );
        
        fig.update_layout(
            title=f"{symbol} - Top {top_n} Parameter Combinations (Simulated Equity Curves)",
            xaxis_title='Trading Days',
            yaxis_title='Portfolio Value ($)',
            width=900,
            height=500,
            hovermode='x unified'
        );
        
        return fig;
    
    def save_visualization( self, fig: go.Figure, filename: str, 
                          format: str = 'html' ) -> str:
        """
        Save visualization to file
        
        Args:
            fig: Plotly Figure
            filename: Output filename (without extension)
            format: Output format ('html', 'png', 'pdf')
            
        Returns:
            Path to saved file
        """
        
        project_root = self.config.project_root;
        output_dir = project_root / "optimization_results";
        output_dir.mkdir( exist_ok=True );
        
        if format == 'html':
            filepath = output_dir / f"{filename}.html";
            fig.write_html( str( filepath ) );
        elif format == 'png':
            filepath = output_dir / f"{filename}.png";
            fig.write_image( str( filepath ) );
        elif format == 'pdf':
            filepath = output_dir / f"{filename}.pdf";
            fig.write_image( str( filepath ) );
        else:
            raise ValueError( f"Unsupported format: {format}" );
        
        print( f"💾 Saved visualization to {filepath}" );
        return str( filepath );

# Convenience functions
def create_quick_heatmap( symbol: str, metric: str = 'total_return' ) -> go.Figure:
    """Create quick heatmap for a symbol"""
    
    visualizer = OptimizationVisualizer();
    engine = ParameterSweepEngine();
    
    # Get saved results
    saved_results = engine.get_saved_results( symbol );
    
    if saved_results.empty:
        print( f"No optimization results found for {symbol}" );
        return go.Figure();
    
    # Convert to list of dicts for compatibility
    results = saved_results.to_dict( 'records' );
    
    return visualizer.create_performance_heatmap( symbol, results, metric );

def create_multi_stock_comparison( symbols: List[str], metric: str = 'total_return' ) -> go.Figure:
    """Create comparison chart for multiple stocks"""
    
    visualizer = OptimizationVisualizer();
    return visualizer.create_parameter_comparison( symbols, metric );

def export_optimization_summary( symbols: List[str], filename: str = "optimization_summary" ) -> str:
    """Export optimization summary to HTML"""
    
    visualizer = OptimizationVisualizer();
    engine = ParameterSweepEngine();
    
    # Create summary figure with subplots for each stock
    n_symbols = len( symbols );
    rows = (n_symbols + 1) // 2;  # 2 columns
    
    fig = make_subplots(
        rows=rows, cols=2,
        subplot_titles=symbols,
        vertical_spacing=0.1,
        horizontal_spacing=0.1
    );
    
    for i, symbol in enumerate( symbols ):
        row = (i // 2) + 1;
        col = (i % 2) + 1;
        
        saved_results = engine.get_saved_results( symbol );
        if not saved_results.empty:
            results = saved_results.to_dict( 'records' );
            df = pd.DataFrame( results );
            
            # Create mini heatmap
            heatmap_data = df.pivot_table(
                index='ema_slow',
                columns='ema_fast',
                values='total_return',
                aggfunc='mean'
            );
            
            fig.add_trace(
                go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale='RdYlGn',
                    showscale=False,
                    name=symbol
                ),
                row=row, col=col
            );
    
    fig.update_layout(
        title="Multi-Stock Optimization Summary",
        width=1200,
        height=600 * rows,
        showlegend=False
    );
    
    return visualizer.save_visualization( fig, filename );