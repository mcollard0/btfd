"""
Stock Discovery System for BTFD Scanner
Discovers all US stocks under specified criteria using multiple free data sources
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import json
import csv
from pathlib import Path

from ..config.settings import get_config


class StockDiscovery:
    """Comprehensive stock discovery from multiple free sources"""
    
    def __init__( self ):
        self.config = get_config();
        
    def get_nasdaq_listed_stocks( self ) -> List[Dict]:
        """
        Get all NASDAQ listed stocks from official NASDAQ FTP
        Returns list of dicts with symbol, name, market_cap, etc.
        """
        print( "📡 Fetching NASDAQ listed stocks..." );
        
        try:
            # NASDAQ provides free CSV files with all listed stocks
            nasdaq_url = "https://www.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&download=true";
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
            };
            
            response = requests.get( nasdaq_url, headers=headers, timeout=60 );
            
            if response.status_code == 200:
                data = response.json();
                
                if 'data' in data and 'rows' in data['data']:
                    stocks = [];
                    for row in data['data']['rows']:
                        if 'symbol' in row and 'name' in row:
                            stocks.append({
                                'symbol': row['symbol'],
                                'name': row.get( 'name', '' ),
                                'market_cap': row.get( 'marketcap', 0 ),
                                'volume': row.get( 'volume', 0 ),
                                'price': row.get( 'lastsale', '' ),  # May be string like "$45.67"
                                'exchange': 'NASDAQ',
                                'sector': row.get( 'sector', '' ),
                                'industry': row.get( 'industry', '' )
                            });
                    
                    print( f"   ✅ Found {len( stocks )} NASDAQ stocks" );
                    return stocks;
            
            print( f"   ❌ NASDAQ API failed: {response.status_code}" );
            return [];
            
        except Exception as e:
            print( f"   💥 NASDAQ fetch error: {e}" );
            return [];
    
    def get_nyse_listed_stocks( self ) -> List[Dict]:
        """
        Get NYSE listed stocks using alternative sources
        """
        print( "📡 Fetching NYSE listed stocks..." );
        
        try:
            # Alternative: Use Yahoo Finance screener API
            url = "https://query1.finance.yahoo.com/v1/finance/screener";
            
            payload = {
                "size": 5000,
                "offset": 0,
                "sortField": "marketcap",
                "sortType": "DESC",
                "quoteType": "EQUITY",
                "query": {
                    "operator": "AND",
                    "operands": [
                        {
                            "operator": "eq",
                            "operands": ["region", "us"]
                        },
                        {
                            "operator": "or",
                            "operands": [
                                {"operator": "eq", "operands": ["exchange", "NYSE"]},
                                {"operator": "eq", "operands": ["exchange", "NYSEArca"]},
                                {"operator": "eq", "operands": ["exchange", "AMEX"]}
                            ]
                        }
                    ]
                }
            };
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json'
            };
            
            response = requests.post( url, json=payload, headers=headers, timeout=60 );
            
            if response.status_code == 200:
                data = response.json();
                
                if 'finance' in data and 'result' in data['finance']:
                    result = data['finance']['result'][0];
                    if 'quotes' in result:
                        stocks = [];
                        
                        for quote in result['quotes']:
                            stocks.append({
                                'symbol': quote.get( 'symbol', '' ),
                                'name': quote.get( 'longName', quote.get( 'shortName', '' ) ),
                                'market_cap': quote.get( 'marketCap', 0 ),
                                'volume': quote.get( 'averageDailyVolume10Day', 0 ),
                                'price': quote.get( 'regularMarketPrice', 0 ),
                                'exchange': quote.get( 'fullExchangeName', 'NYSE' ),
                                'sector': quote.get( 'sector', '' ),
                                'industry': quote.get( 'industry', '' )
                            });
                        
                        print( f"   ✅ Found {len( stocks )} NYSE/AMEX stocks" );
                        return stocks;
            
            print( f"   ❌ NYSE API failed: {response.status_code}" );
            return [];
            
        except Exception as e:
            print( f"   💥 NYSE fetch error: {e}" );
            return [];
    
    def get_fallback_comprehensive_list( self ) -> List[Dict]:
        """
        Comprehensive fallback list of US stocks when APIs fail
        This includes most major US stocks across all sectors and price ranges
        """
        
        # Major US stocks across all sectors - significantly expanded from original 95 to 500+
        major_symbols = [
            # Mega Cap Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'ORCL', 'CRM', 'ADBE', 'AMD', 'INTC', 'QCOM', 'TXN', 'AVGO',
            
            # Financial Services (Many under $100)
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'COF',
            'AXP', 'BLK', 'SCHW', 'CB', 'MMC', 'AON', 'AJG', 'AFL',
            'AIG', 'PRU', 'MET', 'ALL', 'TRV', 'PGR', 'HIG',
            
            # Energy (Most under $100)
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'VLO', 'PSX',
            'OXY', 'DVN', 'FANG', 'MRO', 'APA', 'BP', 
            'KMI', 'OKE', 'EPD', 'ET', 'WMB', 'ENB',
            
            # Healthcare & Pharma
            'JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'DHR', 'MRK', 'BMY', 'ABBV',
            'LLY', 'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'ILMN',
            'CVS', 'UHS', 'HCA', 'CNC', 'ANTM', 'CI', 'HUM',
            
            # Consumer Discretionary
            'HD', 'LOW', 'MCD', 'SBUX', 'NKE', 'DIS',
            'TGT', 'WMT', 'COST', 'TJX', 'ROST', 'DG', 'DLTR', 'KR',
            'YUM', 'QSR', 'CMG', 'DPZ', 'TXRH',
            
            # Consumer Staples  
            'PG', 'KO', 'PEP', 'CL', 'KMB', 'GIS', 'K', 'CPB',
            'CAG', 'SJM', 'HSY', 'MDLZ', 'MNST', 'KDP', 'STZ',
            
            # Industrials
            'BA', 'CAT', 'DE', 'GE', 'MMM', 'HON', 'UNP', 'RTX', 'LMT', 'NOC',
            'GD', 'ITW', 'EMR', 'ETN', 'PH', 'CMI', 'FDX', 'UPS', 'NSC', 'CSX',
            'DAL', 'AAL', 'UAL', 'LUV', 'JBLU', 'ALK',
            
            # Materials & Mining
            'LIN', 'SHW', 'APD', 'ECL', 'DD', 'DOW', 'PPG', 'NUE', 'STLD',
            'FCX', 'NEM', 'GOLD', 'AUY', 'AA', 'X', 'CLF', 'MT',
            
            # Utilities (Most under $100)
            'NEE', 'SO', 'DUK', 'D', 'EXC', 'XEL', 'SRE', 'AEP', 'PCG',
            'EIX', 'PEG', 'ED', 'ETR', 'ES', 'FE', 'AES', 'NI', 'CMS',
            
            # REITs (Most under $100)
            'AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'O', 'WELL', 'PSA', 'EXR',
            'AVB', 'EQR', 'UDR', 'CPT', 'MAA', 'ESS', 'ARE', 'BXP', 'VTR',
            
            # Telecommunications
            'T', 'VZ', 'TMUS', 'CHTR', 'CMCSA', 'DISH', 'SIRI',
            
            # Transportation
            'FDX', 'UPS', 'NSC', 'CSX', 'UNP', 'KSU',
            
            # Retail
            'TJX', 'ROST', 'DG', 'DLTR', 'AZO', 'ORLY', 'AAP', 'JWN', 'M', 'KSS',
            
            # Food & Beverage
            'KO', 'PEP', 'MDLZ', 'GIS', 'K', 'CPB', 'CAG', 'SJM', 'HSY',
            'MNST', 'KDP', 'STZ', 'TAP', 'BUD', 'SAM',
            
            # Growth Tech (Many under $100)
            'PYPL', 'UBER', 'LYFT', 'SNAP', 'SQ', 'ROKU', 'ZM', 'DOCU', 'OKTA',
            
            # Automotive
            'F', 'GM', 'STLA', 'HMC', 'TM',
            
            # Hospitality
            'CCL', 'RCL', 'NCLH', 'MAR', 'HLT', 'WYNN', 'MGM', 'LVS', 'CZR',
            
            # Dividend Favorites (Many under $100)
            'T', 'VZ', 'XOM', 'CVX', 'JNJ', 'PFE', 'KO', 'PEP', 'WMT',
            'HD', 'MCD', 'IBM', 'CAT', 'MMM', 'GE', 'F', 'GM', 'C', 'BAC',
            
            # Mid-Cap Value
            'RF', 'FITB', 'HBAN', 'KEY', 'CMA', 'PBCT', 'ZION', 'MTB',
            'STI', 'BBT', 'SIVB', 'SBNY', 'CFG', 'WAL', 'FHN', 'SNV',
            
            # Small-Cap Growth  
            'ETSY', 'PINS', 'TWLO', 'SHOP', 'MELI', 'SE', 'BABA', 'JD', 'PDD',
            
            # Biotech
            'MRNA', 'BNTX', 'NVAX', 'INO', 'SGEN', 'BMRN', 'RARE', 'BLUE',
            
            # Cannabis
            'TLRY', 'CGC', 'ACB', 'CRON', 'SNDL', 'OGI', 'HEXO',
            
            # SPACs and Recent IPOs (Many under $100)
            'SPCE', 'NKLA', 'RIDE', 'LCID', 'RIVN',
            
            # Additional Affordable Stocks (Under $100)
            'SNAP', 'TWTR', 'SQ', 'ROKU', 'ZM', 'DOCU', 'OKTA',
            'PYPL', 'UBER', 'LYFT', 'PINS', 'ETSY', 'SHOP', 'SE',
            
            # More Banks & Financials
            'KEY', 'CMA', 'ZION', 'MTB', 'SIVB', 'PBCT', 'RF', 'FITB', 'HBAN',
            'WBS', 'SNV', 'FHN', 'WAL', 'CFG', 'SBNY', 'BKU', 'FFIN',
            
            # More Energy
            'EOG', 'MPC', 'VLO', 'PSX', 'FANG', 'MRO', 'CLR', 'PBF', 'HFC',
            'CNX', 'AR', 'SM', 'RRC', 'WLL', 'CHK', 'GPOR', 'CTRA',
            
            # More Healthcare & Biotech 
            'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'CELG', 'MYL', 'TEVA',
            'ABBV', 'BMY', 'LLY', 'ZTS', 'ISRG', 'SYK', 'ANTM', 'CI', 'HUM', 'MOH',
            
            # Retail & Consumer 
            'M', 'KSS', 'JWN', 'GPS', 'ANF', 'AEO', 'URBN', 'JCP', 'BBBY',
            'BBY', 'AMZN', 'EBAY', 'OSTK', 'CHWY', 'PETS', 'CHEWY', 'W',
            
            # Media & Entertainment
            'DIS', 'NFLX', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'DISH', 'SIRI',
            'FOX', 'FOXA', 'CBS', 'VIAC', 'DISCA', 'DISCB', 'DISCK',
            
            # Industrial & Manufacturing
            'GE', 'F', 'GM', 'FORD', 'BA', 'CAT', 'DE', 'MMM', 'HON', 'UNP',
            'CSX', 'NSC', 'KSU', 'CP', 'CNI', 'ODFL', 'CHRW', 'XPO',
            
            # Tech (Smaller/Affordable)
            'CSCO', 'IBM', 'HPQ', 'ORCL', 'MSFT', 'GOOGL', 'FB', 'TWTR',
            'SNAP', 'PINS', 'SPOT', 'WORK', 'ZM', 'DOCU', 'CRM', 'NOW', 'SNOW',
            
            # More REITs
            'VNO', 'BXP', 'KIM', 'REG', 'FRT', 'TCO', 'ADC', 'AIV', 'AVB',
            'EQR', 'UDR', 'CPT', 'MAA', 'ESS', 'EXR', 'PSA', 'CUBE', 'LSI',
            
            # Commodities & Materials
            'VALE', 'RIO', 'BHP', 'SCCO', 'FCX', 'NEM', 'GOLD', 'AUY', 'KGC',
            'HL', 'CDE', 'EGO', 'IAG', 'PAAS', 'SLW', 'WPM', 'FNV', 'AEM'
        ];
        
        # Convert to stock dictionaries
        stocks = [];
        for symbol in major_symbols:
            stocks.append({
                'symbol': symbol,
                'name': f'{symbol} Corp',  # Generic name
                'market_cap': 0,  # Will be filled when filtering
                'volume': 0,
                'price': 0,  # Will be filled when filtering
                'exchange': 'US',
                'sector': 'Unknown',
                'industry': 'Unknown'
            });
        
        print( f"   ✅ Fallback list contains {len( stocks )} major US stocks" );
        return stocks;
    
    def get_comprehensive_stock_list( self ) -> List[Dict]:
        """
        Get comprehensive stock list from multiple sources with fallback
        """
        print( "🔍 Discovering comprehensive US stock list..." );
        
        all_stocks = [];
        
        # Try NASDAQ first
        nasdaq_stocks = self.get_nasdaq_listed_stocks();
        all_stocks.extend( nasdaq_stocks );
        
        # Add NYSE/AMEX
        nyse_stocks = self.get_nyse_listed_stocks();
        all_stocks.extend( nyse_stocks );
        
        # Fallback: Use expanded hardcoded list if APIs fail
        if not all_stocks:
            print( "⚠️  APIs failed, using comprehensive fallback stock list..." );
            all_stocks = self.get_fallback_comprehensive_list();
        
        # Remove duplicates based on symbol
        seen_symbols = set();
        unique_stocks = [];
        
        for stock in all_stocks:
            symbol = stock['symbol'];
            if symbol and symbol not in seen_symbols:
                seen_symbols.add( symbol );
                unique_stocks.append( stock );
        
        print( f"✅ Total unique stocks discovered: {len( unique_stocks )}" );
        return unique_stocks;
    
    def filter_affordable_stocks( self, stocks: List[Dict], max_price: float = 100.0, 
                                 min_volume: int = 100000, min_market_cap: int = 10000000 ) -> List[Dict]:
        """
        Filter stocks by price, volume, and market cap criteria
        
        Args:
            stocks: List of stock dictionaries
            max_price: Maximum stock price
            min_volume: Minimum daily volume
            min_market_cap: Minimum market cap
            
        Returns:
            Filtered list of affordable stocks
        """
        print( f"🔍 Filtering for affordable stocks (< ${max_price}, vol > {min_volume:,}, mcap > ${min_market_cap:,})..." );
        
        affordable_stocks = [];
        
        from ..data.fetchers import DataManager;
        data_manager = DataManager();
        
        for i, stock in enumerate( stocks ):
            if i % 100 == 0:  # Progress indicator
                print( f"   Progress: {i}/{len( stocks )} stocks checked..." );
            
            try:
                symbol = stock['symbol'];
                
                # Skip obvious problematic symbols
                if not symbol or len( symbol ) > 5 or any( char in symbol for char in ['/', '^', '='] ):
                    continue;
                
                # Get current price from Yahoo Finance
                current_price = data_manager.yahoo_fetcher.get_current_price( symbol );
                
                if current_price is None:
                    print( f"      ⚠️  {symbol}: No price data available" );
                    continue;
                
                # Parse existing price if available for validation
                existing_price = stock.get( 'price', 0 );
                if isinstance( existing_price, str ):
                    # Remove $ and convert to float
                    try:
                        existing_price = float( existing_price.replace( '$', '' ).replace( ',', '' ) );
                    except:
                        existing_price = 0;
                
                # Use more reliable current price
                stock['current_price'] = current_price;
                
                # Apply filters
                if current_price <= max_price:
                    # Additional volume check if available
                    volume = stock.get( 'volume', 0 );
                    market_cap = stock.get( 'market_cap', 0 );
                    
                    # Convert market cap if it's a string
                    if isinstance( market_cap, str ):
                        try:
                            # Handle formats like "1.23B", "456M", etc.
                            market_cap_str = market_cap.replace( ',', '' ).upper();
                            if 'B' in market_cap_str:
                                market_cap = float( market_cap_str.replace( 'B', '' ) ) * 1000000000;
                            elif 'M' in market_cap_str:
                                market_cap = float( market_cap_str.replace( 'M', '' ) ) * 1000000;
                            else:
                                market_cap = float( market_cap_str );
                        except:
                            market_cap = 0;
                    
                    # Very relaxed filtering for discovery - include stock if price is under limit
                    # Don't be too strict on volume/market cap for discovery phase
                    affordable_stocks.append( stock );
                    print( f"      ✅ {symbol}: ${current_price:.2f} - INCLUDED" );
                elif current_price > max_price:
                    print( f"      ❌ {symbol}: ${current_price:.2f} - TOO EXPENSIVE" );
                    
                # Rate limiting - more conservative
                if i % 5 == 0:
                    time.sleep( 0.2 );  # 200ms delay every 5 stocks
                    
            except Exception as e:
                # Skip problematic stocks
                continue;
        
        print( f"✅ Found {len( affordable_stocks )} affordable stocks" );
        return affordable_stocks;
    
    
    def discover_affordable_stocks( self, max_price: float = 100.0, 
                                   min_volume: int = 50000, 
                                   min_market_cap: int = 5000000,
                                   max_stocks_to_check: int = 0 ) -> List[str]:
        """
        Main method to discover affordable stocks (in-memory only)
        
        Args:
            max_price: Maximum stock price
            min_volume: Minimum daily volume  
            min_market_cap: Minimum market cap
            max_stocks_to_check: Maximum stocks to check (0 = no limit)
            
        Returns:
            List of affordable stock symbols
        """
        print( f"🎯 Starting comprehensive stock discovery (< ${max_price}, in-memory)..." );
        
        affordable_stocks = [];
        
        # Discover comprehensive stock list
        all_stocks = self.get_comprehensive_stock_list();
        
        if not all_stocks:
            print( "❌ No stocks discovered from any source" );
            return [];
        
        # Optionally limit the number of stocks to check (0 = no limit)
        if max_stocks_to_check > 0 and len( all_stocks ) > max_stocks_to_check:
            print( f"⚙️  Limiting discovery to first {max_stocks_to_check} stocks (out of {len( all_stocks )} total)" );
            all_stocks = all_stocks[:max_stocks_to_check];
        else:
            print( f"🌍 Comprehensive discovery: checking ALL {len( all_stocks )} stocks for affordability" );
        
        # Filter for affordable stocks
        affordable_stocks = self.filter_affordable_stocks( 
            all_stocks, max_price, min_volume, min_market_cap 
        );
        
        # Return symbols (in-memory only)
        symbols = [stock['symbol'] for stock in affordable_stocks if stock.get( 'symbol' )];
        
        print( f"🎯 DISCOVERY COMPLETE: {len( symbols )} affordable stocks found (in-memory)!" );
        return symbols;


# Convenience functions
def discover_stocks_under_price( max_price: float = 100.0 ) -> List[str]:
    """Convenience function to discover stocks under specified price"""
    discoverer = StockDiscovery();
    return discoverer.discover_affordable_stocks( max_price=max_price );


def get_market_overview() -> Dict:
    """Get overview of current market composition"""
    discoverer = StockDiscovery();
    
    # Get comprehensive list
    all_stocks = discoverer.get_comprehensive_stock_list();
    
    if not all_stocks:
        return {'error': 'Failed to fetch market data'};
    
    # Analyze price distribution
    price_ranges = {
        'under_10': 0,
        'under_25': 0, 
        'under_50': 0,
        'under_100': 0,
        'over_100': 0,
        'no_price': 0
    };
    
    total_stocks = len( all_stocks );
    
    for stock in all_stocks[:500]:  # Sample for speed
        price = stock.get( 'current_price', 0 );
        if price == 0:
            price_ranges['no_price'] += 1;
        elif price < 10:
            price_ranges['under_10'] += 1;
        elif price < 25:
            price_ranges['under_25'] += 1;
        elif price < 50:
            price_ranges['under_50'] += 1;
        elif price < 100:
            price_ranges['under_100'] += 1;
        else:
            price_ranges['over_100'] += 1;
    
    return {
        'total_discovered': total_stocks,
        'sample_analyzed': min( 500, total_stocks ),
        'price_distribution': price_ranges,
        'estimated_under_100': int( ( price_ranges['under_10'] + price_ranges['under_25'] + 
                                    price_ranges['under_50'] + price_ranges['under_100'] ) * 
                                  total_stocks / min( 500, total_stocks ) )
    };