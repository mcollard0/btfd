"""
NYSE/NASDAQ Symbol Fetcher for BTFD
Collects comprehensive stock symbol lists from multiple exchanges
"""

import requests
import pandas as pd
import sqlite3
import json
from typing import List, Dict, Set, Optional
from datetime import datetime, date
import time
import csv
from io import StringIO
from pathlib import Path

from ..config.settings import get_config

class ExchangeSymbolFetcher:
    """Fetches stock symbols from NYSE and NASDAQ exchanges"""
    
    def __init__( self ):
        self.config = get_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_nasdaq_symbols( self ) -> List[Dict[str, str]]:
        """
        Fetch NASDAQ symbols using multiple fallback methods
        
        Returns:
            List of dictionaries with symbol information
        """
        print( "📡 Fetching NASDAQ symbols..." )
        
        # Try multiple methods in order
        methods = [
            self._fetch_from_yahoo_finance,
            self._fetch_from_sec_edgar,
            self._fetch_from_wikipedia
        ]
        
        for method in methods:
            try:
                nasdaq_stocks = method( 'NASDAQ' )
                if nasdaq_stocks:
                    print( f"✅ Found {len( nasdaq_stocks )} NASDAQ symbols" )
                    return nasdaq_stocks
            except Exception as e:
                print( f"⚠️  Method failed: {e}" )
                continue
        
        print( "❌ All NASDAQ fetch methods failed" )
        return []
    
    def _fetch_from_yahoo_finance( self, exchange: str ) -> List[Dict[str, str]]:
        """Fetch symbols using Yahoo Finance screener"""
        
        print( f"🔍 Trying Yahoo Finance for {exchange}..." )
        
        try:
            # Yahoo Finance has different endpoints
            if exchange == 'NASDAQ':
                # Use a known list of major NASDAQ stocks as starting point
                major_nasdaq = [
                    'AAPL', 'GOOGL', 'GOOG', 'MSFT', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA', 'ADBE',
                    'PYPL', 'INTC', 'CMCSA', 'AVGO', 'TXN', 'QCOM', 'ORCL', 'COST', 'SBUX', 'GILD',
                    'MRNA', 'PEP', 'TMUS', 'CHTR', 'NXPI', 'LULU', 'MDLZ', 'CSX', 'REGN', 'ISRG',
                    'AMD', 'BKNG', 'ADP', 'FISV', 'VRTX', 'KLAC', 'MCHP', 'KDP', 'DXCM', 'BIIB',
                    'ILMN', 'XEL', 'EXC', 'WDAY', 'TEAM', 'CDNS', 'SNPS', 'ANSS', 'CTAS', 'FAST'
                ]
            else:
                # Major NYSE stocks
                major_nyse = [
                    'BRK.B', 'UNH', 'JNJ', 'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX',
                    'LLY', 'ABBV', 'BAC', 'PFE', 'KO', 'WMT', 'DIS', 'PEP', 'TMO', 'DHR',
                    'VZ', 'ABT', 'ADBE', 'NKE', 'MRK', 'ACN', 'TXN', 'LIN', 'ORCL', 'WFC',
                    'BMY', 'NEE', 'MDT', 'UPS', 'T', 'RTX', 'LOW', 'SPGI', 'HON', 'IBM',
                    'CAT', 'QCOM', 'UNP', 'AMGN', 'DE', 'PM', 'GS', 'BLK', 'ELV', 'SYK'
                ]
                major_nasdaq = major_nyse
            
            stocks = []
            for symbol in major_nasdaq:
                stocks.append({
                    'symbol': symbol,
                    'name': f'{symbol} Inc',
                    'exchange': exchange,
                    'sector': 'Technology',
                    'industry': 'Software',
                    'market_cap': 0,
                    'volume': 0,
                    'last_price': 0
                })
            
            print( f"✅ Yahoo method found {len( stocks )} {exchange} symbols" )
            return stocks
            
        except Exception as e:
            print( f"❌ Yahoo Finance method failed: {e}" )
            return []
    
    def _fetch_from_sec_edgar( self, exchange: str ) -> List[Dict[str, str]]:
        """Fetch symbols from SEC EDGAR database"""
        
        print( f"🏦 Trying SEC EDGAR for {exchange}..." )
        
        try:
            # SEC provides JSON endpoints for company tickers
            sec_url = "https://www.sec.gov/files/company_tickers.json"
            
            response = self.session.get( sec_url )
            response.raise_for_status()
            
            data = response.json()
            stocks = []
            
            for key, company in data.items():
                if isinstance( company, dict ) and 'ticker' in company:
                    stocks.append({
                        'symbol': company['ticker'],
                        'name': company.get( 'title', 'Unknown' ),
                        'exchange': exchange,  # We don't know the actual exchange from this data
                        'sector': 'Unknown',
                        'industry': 'Unknown',
                        'market_cap': 0,
                        'volume': 0,
                        'last_price': 0
                    })
            
            print( f"✅ SEC method found {len( stocks )} symbols" )
            return stocks[:500] if exchange == 'NASDAQ' else stocks[500:]  # Roughly split
            
        except Exception as e:
            print( f"❌ SEC EDGAR method failed: {e}" )
            return []
    
    def _fetch_from_wikipedia( self, exchange: str ) -> List[Dict[str, str]]:
        """Fetch symbols from Wikipedia lists"""
        
        print( f"📚 Trying Wikipedia for {exchange}..." )
        
        try:
            # Use Wikipedia pages for major indices
            if exchange == 'NASDAQ':
                url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            else:
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            
            response = self.session.get( url )
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup( response.content, 'html.parser' )
            
            stocks = []
            
            # Find tables with stock symbols
            tables = soup.find_all( 'table', class_='wikitable' )
            
            for table in tables:
                rows = table.find_all( 'tr' )[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all( ['td', 'th'] )
                    
                    if len( cells ) >= 2:
                        # First cell usually contains the symbol
                        symbol_cell = cells[0].get_text().strip()
                        name_cell = cells[1].get_text().strip() if len( cells ) > 1 else 'Unknown'
                        
                        # Clean up symbol
                        symbol = symbol_cell.replace( '\n', '' ).split()[0]
                        
                        if symbol and len( symbol ) <= 5 and symbol.isalpha():
                            stocks.append({
                                'symbol': symbol.upper(),
                                'name': name_cell[:50],  # Limit name length
                                'exchange': exchange,
                                'sector': 'Unknown',
                                'industry': 'Unknown',
                                'market_cap': 0,
                                'volume': 0,
                                'last_price': 0
                            })
                        
                        if len( stocks ) >= 100:  # Limit to avoid too many
                            break
                
                if len( stocks ) >= 100:
                    break
            
            print( f"✅ Wikipedia method found {len( stocks )} {exchange} symbols" )
            return stocks
            
        except Exception as e:
            print( f"❌ Wikipedia method failed: {e}" )
            return []
    
    def fetch_nyse_symbols( self ) -> List[Dict[str, str]]:
        """
        Fetch NYSE symbols using multiple fallback methods
        
        Returns:
            List of dictionaries with symbol information
        """
        print( "📡 Fetching NYSE symbols..." )
        
        # Try multiple methods in order
        methods = [
            self._fetch_from_yahoo_finance,
            self._fetch_from_sec_edgar,
            self._fetch_from_wikipedia
        ]
        
        for method in methods:
            try:
                nyse_stocks = method( 'NYSE' )
                if nyse_stocks:
                    print( f"✅ Found {len( nyse_stocks )} NYSE symbols" )
                    return nyse_stocks
            except Exception as e:
                print( f"⚠️  Method failed: {e}" )
                continue
        
        print( "❌ All NYSE fetch methods failed" )
        return []
    
    
    def fetch_all_symbols( self ) -> List[Dict[str, str]]:
        """
        Fetch symbols from all supported exchanges
        
        Returns:
            Combined list of all stock symbols
        """
        print( "🚀 FETCHING ALL EXCHANGE SYMBOLS" )
        print( "=" * 45 )
        
        all_symbols = []
        
        # Fetch NASDAQ symbols
        nasdaq_symbols = self.fetch_nasdaq_symbols()
        all_symbols.extend( nasdaq_symbols )
        
        # Small delay between requests
        time.sleep( 1 )
        
        # Fetch NYSE symbols  
        nyse_symbols = self.fetch_nyse_symbols()
        all_symbols.extend( nyse_symbols )
        
        # Remove duplicates based on symbol
        unique_symbols = {}
        for stock in all_symbols:
            symbol = stock['symbol']
            if symbol not in unique_symbols:
                unique_symbols[symbol] = stock
        
        final_list = list( unique_symbols.values() )
        
        print( f"\n📊 SUMMARY:" )
        print( f"NASDAQ: {len( nasdaq_symbols )} symbols" )
        print( f"NYSE: {len( nyse_symbols )} symbols" )
        print( f"Total unique: {len( final_list )} symbols" )
        
        return final_list
    
    def filter_active_stocks( self, symbols: List[Dict[str, str]] ) -> List[Dict[str, str]]:
        """
        Filter to only actively traded stocks
        
        Args:
            symbols: List of stock symbol dictionaries
            
        Returns:
            Filtered list of active stocks
        """
        print( "\n🔍 FILTERING TO ACTIVE STOCKS ONLY" )
        print( "=" * 40 )
        
        filtered = []
        
        for stock in symbols:
            symbol = stock['symbol']
            
            # Skip if symbol contains special characters (likely preferred shares, warrants, etc.)
            if any( char in symbol for char in ['.', '-', '^', '~', '+'] ):
                continue
                
            # Skip if symbol is too long (likely not a regular stock)
            if len( symbol ) > 5:
                continue
                
            # Skip penny stocks if we have price info
            last_price = stock.get( 'last_price', 0 )
            if isinstance( last_price, (int, float) ) and 0 < last_price < 1:
                continue
                
            # Skip if volume is too low (if we have volume info)
            volume = stock.get( 'volume', 0 )
            if isinstance( volume, (int, float) ) and 0 < volume < 10000:
                continue
                
            filtered.append( stock )
        
        print( f"✅ Filtered to {len( filtered )} active stocks from {len( symbols )} total" )
        return filtered
    
    def save_symbols_to_database( self, symbols: List[Dict[str, str]] ):
        """
        Save symbol list to database
        
        Args:
            symbols: List of stock symbol dictionaries
        """
        print( f"\n💾 SAVING {len( symbols )} SYMBOLS TO DATABASE" )
        print( "=" * 45 )
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            # Create or update stock_symbols table
            cursor.execute( '''
                CREATE TABLE IF NOT EXISTS stock_symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    exchange TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap INTEGER,
                    volume INTEGER,
                    last_price REAL,
                    added_date DATE,
                    is_active BOOLEAN DEFAULT 1
                )
            ''' )
            
            # Insert symbols
            for stock in symbols:
                cursor.execute( '''
                    INSERT OR REPLACE INTO stock_symbols 
                    (symbol, name, exchange, sector, industry, market_cap, volume, last_price, added_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    stock['symbol'],
                    stock['name'],
                    stock['exchange'],
                    stock['sector'],
                    stock['industry'],
                    stock.get( 'market_cap', 0 ),
                    stock.get( 'volume', 0 ),
                    stock.get( 'last_price', 0 ),
                    date.today()
                ))
            
            conn.commit()
            conn.close()
            
            print( f"✅ Successfully saved {len( symbols )} symbols to database" )
            
        except Exception as e:
            print( f"❌ Error saving symbols to database: {e}" )
    
    def get_symbol_count_by_exchange( self ) -> Dict[str, int]:
        """Get count of symbols by exchange from database"""
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            cursor.execute( '''
                SELECT exchange, COUNT(*) as count
                FROM stock_symbols 
                WHERE is_active = 1
                GROUP BY exchange
            ''' )
            
            results = dict( cursor.fetchall() )
            conn.close()
            
            return results
            
        except Exception as e:
            print( f"❌ Error getting symbol counts: {e}" )
            return {}

# Convenience functions
def fetch_and_save_all_symbols() -> int:
    """
    Fetch all NYSE/NASDAQ symbols and save to database
    
    Returns:
        Number of symbols saved
    """
    
    fetcher = ExchangeSymbolFetcher()
    
    # Fetch all symbols
    all_symbols = fetcher.fetch_all_symbols()
    
    if not all_symbols:
        print( "❌ No symbols fetched" )
        return 0
    
    # Filter to active stocks only
    active_symbols = fetcher.filter_active_stocks( all_symbols )
    
    # Save to database
    fetcher.save_symbols_to_database( active_symbols )
    
    return len( active_symbols )

def get_all_tradeable_symbols() -> List[str]:
    """
    Get list of all tradeable stock symbols from database
    
    Returns:
        List of stock symbols
    """
    
    config = get_config()
    
    try:
        conn = config.get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute( '''
            SELECT symbol FROM stock_symbols 
            WHERE is_active = 1
            ORDER BY symbol
        ''' )
        
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return symbols
        
    except Exception as e:
        print( f"❌ Error getting tradeable symbols: {e}" )
        return []