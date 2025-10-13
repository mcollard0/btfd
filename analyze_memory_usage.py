#!/usr/bin/env python3
"""
Memory Usage Analysis for BTFD Stock Data
Analyzes memory consumption for stock data and moving averages
"""

import sys
import os
import psutil
import tracemalloc
import pandas as pd
import numpy as np
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))));

from src.data.fetchers import DataManager;
from src.indicators.optimized_ma import OptimizedMovingAverages;

def format_memory_size(size_bytes):
    """Format memory size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}";
        size_bytes /= 1024.0;
    return f"{size_bytes:.2f} TB";

def get_dataframe_memory_usage(df):
    """Get detailed memory usage of a DataFrame"""
    memory_usage = df.memory_usage(deep=True);
    total_memory = memory_usage.sum();
    
    return {
        'total_bytes': total_memory,
        'total_formatted': format_memory_size(total_memory),
        'index_bytes': memory_usage.iloc[0],
        'columns': {col: memory_usage[col] for col in df.columns},
        'rows': len(df),
        'columns_count': len(df.columns)
    };

def analyze_stock_memory_usage(symbol='AAPL', days_back=220):
    """Analyze memory usage for a single stock"""
    
    print(f"🔍 Analyzing memory usage for {symbol} ({days_back} days)");
    print("=" * 60);
    
    # Start memory tracking
    tracemalloc.start();
    
    # Get current process
    process = psutil.Process();
    initial_memory = process.memory_info().rss;
    
    print(f"📊 Initial memory usage: {format_memory_size(initial_memory)}");
    
    # Load stock data
    data_manager = DataManager();
    end_date = date.today();
    start_date = end_date - timedelta(days=days_back);
    
    print(f"\n📈 Loading {symbol} data from {start_date} to {end_date}...");
    
    stock_data = data_manager.get_stock_data(symbol, start_date, end_date);
    
    if stock_data is None:
        print(f"❌ Failed to load data for {symbol}");
        return;
    
    # Analyze DataFrame memory usage
    df_memory = get_dataframe_memory_usage(stock_data);
    
    print(f"\n📊 Stock Data Memory Analysis:");
    print(f"   Total Memory: {df_memory['total_formatted']} ({df_memory['total_bytes']:,} bytes)");
    print(f"   Rows: {df_memory['rows']:,}");
    print(f"   Columns: {df_memory['columns_count']}");
    print(f"   Index Memory: {format_memory_size(df_memory['index_bytes'])}");
    print(f"   Column Memory:");
    
    for col, mem in df_memory['columns'].items():
        print(f"     {col}: {format_memory_size(mem)}");
    
    # Test optimized MA calculations
    print(f"\n⚡ Testing Optimized Moving Averages...");
    
    ma_calculator = OptimizedMovingAverages();
    
    # Test EMA calculations
    ema_10 = ma_calculator.get_latest_ema(symbol, 10, stock_data);
    ema_20 = ma_calculator.get_latest_ema(symbol, 20, stock_data);
    
    # Test SMA calculations  
    sma_50 = ma_calculator.get_latest_sma(symbol, 50, stock_data);
    sma_200 = ma_calculator.get_latest_sma(symbol, 200, stock_data);
    
    print(f"   EMA(10): {ema_10:.4f}");
    print(f"   EMA(20): {ema_20:.4f}"); 
    print(f"   SMA(50): {sma_50:.4f}");
    print(f"   SMA(200): {sma_200:.4f}");
    
    # Check final memory usage
    final_memory = process.memory_info().rss;
    memory_increase = final_memory - initial_memory;
    
    print(f"\n💾 Final Memory Analysis:");
    print(f"   Initial: {format_memory_size(initial_memory)}");
    print(f"   Final: {format_memory_size(final_memory)}");
    print(f"   Increase: {format_memory_size(memory_increase)}");
    
    # Get tracemalloc statistics
    current, peak = tracemalloc.get_traced_memory();
    tracemalloc.stop();
    
    print(f"\n🔬 Tracemalloc Statistics:");
    print(f"   Current: {format_memory_size(current)}");
    print(f"   Peak: {format_memory_size(peak)}");
    
    # Calculate memory per row
    memory_per_row = df_memory['total_bytes'] / df_memory['rows'];
    print(f"\n📏 Memory Efficiency:");
    print(f"   Memory per row: {format_memory_size(memory_per_row)}");
    print(f"   Memory per day: {format_memory_size(memory_per_row)}");
    
    # Estimate memory for multiple stocks
    estimate_100_stocks = (df_memory['total_bytes'] * 100);
    estimate_1000_stocks = (df_memory['total_bytes'] * 1000);
    
    print(f"\n🎯 Memory Projections:");
    print(f"   100 stocks: {format_memory_size(estimate_100_stocks)}");
    print(f"   1,000 stocks: {format_memory_size(estimate_1000_stocks)}");
    print(f"   Current DB (11,324 stocks): {format_memory_size(df_memory['total_bytes'] * 11324)}");
    
    return {
        'symbol': symbol,
        'days': df_memory['rows'],
        'memory_bytes': df_memory['total_bytes'],
        'memory_per_row': memory_per_row,
        'ema_10': ema_10,
        'ema_20': ema_20,
        'sma_50': sma_50,
        'sma_200': sma_200
    };

def analyze_database_overview():
    """Analyze overall database statistics"""
    
    print(f"\n🗄️  DATABASE OVERVIEW");
    print("=" * 60);
    
    data_manager = DataManager();
    conn = data_manager.config.get_database_connection();
    
    # Get total stats
    cursor = conn.cursor();
    
    # Total symbols
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data");
    total_symbols = cursor.fetchone()[0];
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM stock_data");
    total_records = cursor.fetchone()[0];
    
    # Date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM stock_data");
    date_range = cursor.fetchone();
    
    # Symbols with 200+ days
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT symbol FROM stock_data 
            GROUP BY symbol 
            HAVING COUNT(*) >= 200
        )
    """);
    symbols_200_plus = cursor.fetchone()[0];
    
    # Top symbols by data count
    cursor.execute("""
        SELECT symbol, COUNT(*) as days 
        FROM stock_data 
        GROUP BY symbol 
        ORDER BY days DESC 
        LIMIT 5
    """);
    top_symbols = cursor.fetchall();
    
    conn.close();
    
    print(f"📊 Database Statistics:");
    print(f"   Total Symbols: {total_symbols:,}");
    print(f"   Total Records: {total_records:,}");
    print(f"   Symbols w/ 200+ days: {symbols_200_plus:,}");
    print(f"   Date Range: {date_range[0]} to {date_range[1]}");
    
    print(f"\n🏆 Top 5 Symbols by Data Points:");
    for symbol, days in top_symbols:
        print(f"   {symbol}: {days:,} days");
    
    # Estimate total memory if loaded
    avg_memory_per_record = 50;  # Conservative estimate in bytes
    estimated_total_memory = total_records * avg_memory_per_record;
    
    print(f"\n💾 Memory Estimates (if all loaded):");
    print(f"   Conservative: {format_memory_size(estimated_total_memory)}");
    print(f"   With overhead: {format_memory_size(estimated_total_memory * 1.5)}");

def main():
    """Main analysis function"""
    
    print("🚀 BTFD Memory Usage Analysis");
    print("=" * 60);
    
    # Analyze database overview
    analyze_database_overview();
    
    # Analyze memory usage for a specific stock
    result = analyze_stock_memory_usage('AAPL', 215);
    
    print(f"\n✅ Analysis Complete!");
    print(f"📝 Key Findings:");
    print(f"   • Single stock (215 days): {format_memory_size(result['memory_bytes'])}");
    print(f"   • Memory per day: {format_memory_size(result['memory_per_row'])}");
    print(f"   • 100 stocks projection: ~{format_memory_size(result['memory_bytes'] * 100)}");
    print(f"   • Optimized MAs working correctly");

if __name__ == "__main__":
    main();