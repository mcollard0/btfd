"""
Comprehensive NYSE/NASDAQ Symbol Fetcher for BTFD
Gets ALL publicly traded stocks from multiple authoritative sources
"""

import requests
import pandas as pd
import json
import csv
from typing import List, Dict, Set
from datetime import date
import time
import sqlite3
from io import StringIO
import yfinance as yf
from pathlib import Path

from ..config.settings import get_config

class ComprehensiveSymbolFetcher:
    """Fetches ALL NYSE and NASDAQ symbols using multiple comprehensive sources"""
    
    def __init__(self):
        self.config = get_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.all_symbols = set()
    
    def fetch_from_nasdaq_ftp(self) -> List[Dict[str, str]]:
        """
        Fetch from NASDAQ's official FTP listings
        This is the most comprehensive source
        """
        print("📡 Fetching from NASDAQ official FTP listings...")
        
        symbols = []
        
        # NASDAQ provides comprehensive symbol lists
        ftp_sources = [
            # Main NASDAQ listing
            "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            # Other NASDAQ listings  
            "http://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        ]
        
        for source_url in ftp_sources:
            try:
                print(f"  📥 Downloading {source_url}")
                response = self.session.get(source_url, timeout=30)
                response.raise_for_status()
                
                # Parse pipe-delimited format
                lines = response.text.strip().split('\n')
                
                for line in lines[1:]:  # Skip header
                    if line.strip() and not line.startswith('File Creation Time'):
                        fields = line.split('|')
                        
                        if len(fields) >= 2:
                            symbol = fields[0].strip()
                            name = fields[1].strip() if len(fields) > 1 else 'Unknown'
                            
                            # Determine exchange
                            if 'otherlisted' in source_url:
                                # This file contains NYSE, AMEX, etc.
                                exchange = fields[2].strip() if len(fields) > 2 else 'NYSE'
                                # Map exchange codes
                                if exchange in ['N', 'NYSE']:
                                    exchange = 'NYSE'
                                elif exchange in ['A', 'AMEX']:
                                    exchange = 'AMEX'  
                                elif exchange in ['P', 'ARCA']:
                                    exchange = 'ARCA'
                                else:
                                    exchange = 'NYSE'  # Default
                            else:
                                exchange = 'NASDAQ'
                            
                            if symbol and len(symbol) <= 5 and symbol.isalnum():
                                symbols.append({
                                    'symbol': symbol,
                                    'name': name,
                                    'exchange': exchange,
                                    'sector': 'Unknown',
                                    'industry': 'Unknown',
                                    'market_cap': 0,
                                    'volume': 0,
                                    'last_price': 0
                                })
                                self.all_symbols.add(symbol)
                
                print(f"  ✅ Found {len([s for s in symbols if source_url.split('/')[-1] in ['nasdaqlisted.txt', 'otherlisted.txt']])} symbols")
                
            except Exception as e:
                print(f"  ❌ Error with {source_url}: {e}")
                continue
        
        print(f"✅ NASDAQ FTP: {len(symbols)} total symbols")
        return symbols
    
    def fetch_from_sec_edgar_full(self) -> List[Dict[str, str]]:
        """
        Fetch ALL companies from SEC EDGAR database
        This includes every public company filing with SEC
        """
        print("📡 Fetching ALL companies from SEC EDGAR...")
        
        try:
            # SEC company tickers JSON (comprehensive)
            sec_url = "https://www.sec.gov/files/company_tickers.json"
            response = self.session.get(sec_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            symbols = []
            
            for key, company in data.items():
                if isinstance(company, dict) and 'ticker' in company:
                    symbol = company['ticker']
                    
                    if symbol and len(symbol) <= 5:  # Filter reasonable symbols
                        symbols.append({
                            'symbol': symbol,
                            'name': company.get('title', 'Unknown'),
                            'exchange': 'Unknown',  # SEC doesn't specify exchange
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'market_cap': 0,
                            'volume': 0,
                            'last_price': 0
                        })
                        self.all_symbols.add(symbol)
            
            print(f"✅ SEC EDGAR: {len(symbols)} companies")
            return symbols
            
        except Exception as e:
            print(f"❌ SEC EDGAR error: {e}")
            return []
    
    def fetch_from_yahoo_screener(self) -> List[Dict[str, str]]:
        """
        Use Yahoo Finance screener to get comprehensive stock lists
        """
        print("📡 Fetching from Yahoo Finance screener...")
        
        try:
            # Yahoo Finance screener endpoint
            screener_url = "https://query1.finance.yahoo.com/v1/finance/screener"
            
            # Parameters for comprehensive screening
            payload = {
                "size": 2500,  # Maximum allowed
                "offset": 0,
                "sortField": "intradaymarketcap", 
                "sortType": "DESC",
                "quoteType": "EQUITY",  # Only stocks
                "query": {
                    "operator": "AND",
                    "operands": [
                        {"operator": "eq", "operands": ["region", "us"]},  # US only
                        {"operator": "gte", "operands": ["intradaymarketcap", 1000000]}  # Min $1M market cap
                    ]
                }
            }
            
            response = self.session.post(screener_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            symbols = []
            
            if 'finance' in data and 'result' in data['finance'] and data['finance']['result']:
                quotes = data['finance']['result'][0].get('quotes', [])
                
                for quote in quotes:
                    symbol = quote.get('symbol', '')
                    if symbol and '.' not in symbol and len(symbol) <= 5:  # Filter out foreign stocks
                        symbols.append({
                            'symbol': symbol,
                            'name': quote.get('longName', quote.get('shortName', 'Unknown')),
                            'exchange': quote.get('fullExchangeName', 'Unknown'),
                            'sector': quote.get('sector', 'Unknown'),
                            'industry': quote.get('industry', 'Unknown'),
                            'market_cap': quote.get('marketCap', 0),
                            'volume': quote.get('averageVolume', 0),
                            'last_price': quote.get('regularMarketPrice', 0)
                        })
                        self.all_symbols.add(symbol)
            
            print(f"✅ Yahoo screener: {len(symbols)} stocks")
            return symbols
            
        except Exception as e:
            print(f"❌ Yahoo screener error: {e}")
            return []
    
    def fetch_from_polygon_api(self) -> List[Dict[str, str]]:
        """
        Fetch from Polygon.io API (if available)
        Note: This requires an API key, but has free tier
        """
        print("📡 Trying Polygon.io API...")
        
        try:
            # Free tier endpoint for reference data
            polygon_url = "https://api.polygon.io/v3/reference/tickers"
            
            # Parameters for US stocks
            params = {
                "market": "stocks",
                "exchange": "XNAS,XNYS",  # NASDAQ and NYSE
                "active": "true",
                "limit": 1000,  # Free tier limit
                "apikey": "demo"  # Try with demo key first
            }
            
            response = self.session.get(polygon_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                symbols = []
                
                if 'results' in data:
                    for ticker in data['results']:
                        symbol = ticker.get('ticker', '')
                        if symbol:
                            symbols.append({
                                'symbol': symbol,
                                'name': ticker.get('name', 'Unknown'),
                                'exchange': 'NYSE' if ticker.get('primary_exchange') == 'XNYS' else 'NASDAQ',
                                'sector': 'Unknown',
                                'industry': 'Unknown', 
                                'market_cap': 0,
                                'volume': 0,
                                'last_price': 0
                            })
                            self.all_symbols.add(symbol)
                
                print(f"✅ Polygon.io: {len(symbols)} symbols")
                return symbols
            else:
                print("ℹ️  Polygon.io: Demo key limited, skipping")
                return []
                
        except Exception as e:
            print(f"❌ Polygon.io error: {e}")
            return []
    
    def fetch_comprehensive_symbols(self) -> List[Dict[str, str]]:
        """
        Fetch from ALL available comprehensive sources
        """
        print("🚀 FETCHING ALL NYSE/NASDAQ SYMBOLS FROM COMPREHENSIVE SOURCES")
        print("=" * 70)
        
        all_symbols = []
        
        # Method 1: NASDAQ FTP (Most comprehensive)
        nasdaq_symbols = self.fetch_from_nasdaq_ftp()
        all_symbols.extend(nasdaq_symbols)
        time.sleep(1)  # Rate limiting
        
        # Method 2: SEC EDGAR (All public companies)
        sec_symbols = self.fetch_from_sec_edgar_full()
        all_symbols.extend(sec_symbols)
        time.sleep(1)
        
        # Method 3: Yahoo Finance screener  
        yahoo_symbols = self.fetch_from_yahoo_screener()
        all_symbols.extend(yahoo_symbols)
        time.sleep(1)
        
        # Method 4: Polygon.io (if available)
        polygon_symbols = self.fetch_from_polygon_api()
        all_symbols.extend(polygon_symbols)
        
        # Remove duplicates while preserving best data
        unique_symbols = {}
        for symbol_data in all_symbols:
            symbol = symbol_data['symbol']
            
            # Keep the most complete record for each symbol
            if symbol not in unique_symbols or symbol_data.get('market_cap', 0) > 0:
                unique_symbols[symbol] = symbol_data
        
        final_list = list(unique_symbols.values())
        
        print(f"\n📊 COMPREHENSIVE RESULTS:")
        print(f"NASDAQ FTP: {len(nasdaq_symbols)} symbols")
        print(f"SEC EDGAR: {len(sec_symbols)} symbols") 
        print(f"Yahoo Screener: {len(yahoo_symbols)} symbols")
        print(f"Polygon.io: {len(polygon_symbols)} symbols")
        print(f"Total unique symbols: {len(final_list)}")
        print(f"Expected range: 4,000-6,000 (all US public companies)")
        
        return final_list
    
    def filter_active_stocks(self, symbols: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Enhanced filtering for active, tradeable stocks"""
        
        print(f"\n🔍 FILTERING {len(symbols)} SYMBOLS TO ACTIVE STOCKS")
        print("=" * 50)
        
        filtered = []
        excluded_count = 0
        
        for stock in symbols:
            symbol = stock['symbol']
            
            # Skip problematic symbols
            if any(char in symbol for char in ['.', '-', '^', '~', '+', '/', ' ']):
                excluded_count += 1
                continue
                
            # Skip if too long (likely not regular stock)
            if len(symbol) > 5:
                excluded_count += 1
                continue
                
            # Skip if contains only numbers or special patterns
            if symbol.isdigit() or symbol.startswith('$'):
                excluded_count += 1
                continue
            
            # Skip test/placeholder symbols
            if symbol.upper() in ['TEST', 'TEMP', 'PLACEHOLDER']:
                excluded_count += 1
                continue
                
            filtered.append(stock)
        
        print(f"✅ Kept {len(filtered)} active symbols")
        print(f"❌ Excluded {excluded_count} inactive/invalid symbols")
        
        return filtered
    
    def save_comprehensive_symbols(self, symbols: List[Dict[str, str]]):
        """Save comprehensive symbol list to database"""
        
        print(f"\n💾 SAVING {len(symbols)} COMPREHENSIVE SYMBOLS")
        print("=" * 50)
        
        try:
            conn = self.config.get_database_connection()
            cursor = conn.cursor()
            
            # Clear existing symbols to do fresh import
            cursor.execute("DELETE FROM stock_symbols")
            print("🗑️  Cleared existing symbol database")
            
            # Insert all new symbols
            for stock in symbols:
                cursor.execute('''
                    INSERT INTO stock_symbols 
                    (symbol, name, exchange, sector, industry, market_cap, volume, last_price, added_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    stock['symbol'],
                    stock['name'][:100],  # Limit length
                    stock['exchange'], 
                    stock['sector'][:50],
                    stock['industry'][:50],
                    stock.get('market_cap', 0),
                    stock.get('volume', 0), 
                    stock.get('last_price', 0),
                    date.today()
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Successfully saved {len(symbols)} symbols")
            
            # Show breakdown by exchange
            exchange_counts = {}
            for stock in symbols:
                exchange = stock['exchange']
                exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
            
            print(f"\n📊 Breakdown by Exchange:")
            for exchange, count in sorted(exchange_counts.items()):
                print(f"  {exchange}: {count:,} symbols")
            
        except Exception as e:
            print(f"❌ Error saving symbols: {e}")

def fetch_all_us_stocks() -> int:
    """
    Fetch ALL US stocks from comprehensive sources
    
    Returns:
        Number of symbols fetched and saved
    """
    
    fetcher = ComprehensiveSymbolFetcher()
    
    # Fetch from all sources
    all_symbols = fetcher.fetch_comprehensive_symbols()
    
    if not all_symbols:
        print("❌ No symbols fetched from any source")
        return 0
    
    # Filter to active stocks
    active_symbols = fetcher.filter_active_stocks(all_symbols)
    
    # Save to database
    fetcher.save_comprehensive_symbols(active_symbols)
    
    return len(active_symbols)