"""
Comprehensive Stock Symbol Discovery for BTFD
Downloads and maintains up-to-date list of US stock symbols from multiple sources
Designed for regular automated updates
"""

import requests
import pandas as pd
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Set, Optional
from pathlib import Path
import time
import re

from ..config.settings import get_config


class StockSymbolDiscovery:
    """Discovers and maintains comprehensive list of US stock symbols"""
    
    def __init__(self):
        self.config = get_config();
        self._ensure_symbols_table();
        
    def _ensure_symbols_table(self):
        """Create symbols table if it doesn't exist"""
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    exchange TEXT,
                    market_cap REAL,
                    sector TEXT,
                    industry TEXT,
                    price REAL,
                    volume INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    last_updated DATE,
                    source TEXT
                )
            """);
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON stock_symbols (exchange)");
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_price ON stock_symbols (price)");
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_active ON stock_symbols (is_active)");
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_updated ON stock_symbols (last_updated DESC)");
            
            conn.commit();
            conn.close();
            
        except Exception as e:
            print(f"⚠️  Error creating symbols table: {e}");
    
    def discover_nasdaq_symbols(self) -> List[Dict]:
        """
        Discover symbols from NASDAQ's official screener
        Most reliable source for NASDAQ-listed stocks
        """
        print("📡 Discovering NASDAQ symbols...");
        
        symbols = [];
        
        try:
            # NASDAQ's official screener API (free, no auth required)
            url = "https://api.nasdaq.com/api/screener/stocks";
            
            params = {
                'tableonly': 'true',
                'limit': '25000',  # Get all stocks
                'download': 'true'
            };
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.nasdaq.com/market-activity/stocks/screener',
            };
            
            response = requests.get(url, params=params, headers=headers, timeout=30);
            
            if response.status_code == 200:
                data = response.json();
                
                if 'data' in data and 'rows' in data['data']:
                    for row in data['data']['rows']:
                        try:
                            # Clean up price (remove $ and convert)
                            price_str = str(row.get('lastsale', '0')).replace('$', '').replace(',', '');
                            price = float(price_str) if price_str and price_str != 'n/a' else 0.0;
                            
                            # Parse market cap
                            market_cap_str = str(row.get('marketcap', '0'));
                            market_cap = self._parse_market_cap(market_cap_str);
                            
                            # Parse volume
                            volume_str = str(row.get('volume', '0')).replace(',', '');
                            volume = int(volume_str) if volume_str.isdigit() else 0;
                            
                            symbols.append({
                                'symbol': row.get('symbol', '').strip().upper(),
                                'name': row.get('name', '').strip(),
                                'exchange': 'NASDAQ',
                                'market_cap': market_cap,
                                'sector': row.get('sector', '').strip(),
                                'industry': row.get('industry', '').strip(),
                                'price': price,
                                'volume': volume,
                                'source': 'nasdaq_api'
                            });
                            
                        except Exception as e:
                            print(f"   ⚠️  Error parsing NASDAQ row: {e}");
                            continue;
                    
                    print(f"   ✅ Discovered {len(symbols)} NASDAQ symbols");
                    
                else:
                    print(f"   ❌ Unexpected NASDAQ API response format");
                    
            else:
                print(f"   ❌ NASDAQ API failed: HTTP {response.status_code}");
                
        except Exception as e:
            print(f"   💥 NASDAQ discovery error: {e}");
            
        return symbols;
    
    def discover_sec_symbols(self) -> List[Dict]:
        """
        Discover symbols from SEC EDGAR database
        Authoritative source for all US public companies
        """
        print("📡 Discovering SEC EDGAR symbols...");
        
        symbols = [];
        
        try:
            # SEC maintains tickers.json with all registered companies
            url = "https://www.sec.gov/files/company_tickers.json";
            
            headers = {
                'User-Agent': 'BTFD Scanner michael@example.com',  # SEC requires identification
                'Accept': 'application/json',
            };
            
            response = requests.get(url, headers=headers, timeout=30);
            
            if response.status_code == 200:
                data = response.json();
                
                for item in data.values():
                    try:
                        symbol = item.get('ticker', '').strip().upper();
                        if symbol and len(symbol) <= 5:  # Filter reasonable symbols
                            symbols.append({
                                'symbol': symbol,
                                'name': item.get('title', '').strip(),
                                'exchange': 'US',  # SEC covers all US exchanges
                                'market_cap': 0.0,  # SEC doesn't provide market data
                                'sector': '',
                                'industry': '',
                                'price': 0.0,
                                'volume': 0,
                                'source': 'sec_edgar'
                            });
                            
                    except Exception as e:
                        print(f"   ⚠️  Error parsing SEC item: {e}");
                        continue;
                
                print(f"   ✅ Discovered {len(symbols)} SEC EDGAR symbols");
                
            else:
                print(f"   ❌ SEC API failed: HTTP {response.status_code}");
                
        except Exception as e:
            print(f"   💥 SEC discovery error: {e}");
            
        return symbols;
    
    def discover_finviz_symbols(self) -> List[Dict]:
        """
        Discover symbols by scraping Finviz screener
        Good for getting market data and filtering
        """
        print("📡 Discovering Finviz symbols...");
        
        symbols = [];
        
        try:
            # Finviz screener for all stocks
            base_url = "https://finviz.com/screener.ashx";
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            };
            
            # Get multiple pages
            for page in range(1, 200):  # Up to 200 pages (20 stocks each)
                params = {
                    'v': '111',  # View type
                    'r': str((page - 1) * 20 + 1)  # Start row
                };
                
                response = requests.get(base_url, params=params, headers=headers, timeout=15);
                
                if response.status_code == 200:
                    # Parse HTML table (simple approach)
                    content = response.text;
                    
                    # Find ticker links pattern
                    import re;
                    pattern = r'quote\.ashx\?t=([A-Z]{1,5})"[^>]*>([A-Z]{1,5})</a>';
                    matches = re.findall(pattern, content);
                    
                    if not matches:
                        print(f"   ⚠️  No more symbols found at page {page}");
                        break;
                    
                    for symbol_match, symbol_display in matches:
                        symbols.append({
                            'symbol': symbol_match.strip().upper(),
                            'name': '',  # Would need additional parsing
                            'exchange': 'US',
                            'market_cap': 0.0,
                            'sector': '',
                            'industry': '',
                            'price': 0.0,
                            'volume': 0,
                            'source': 'finviz'
                        });
                    
                    if page % 10 == 0:
                        print(f"   📊 Processed {page} pages, found {len(symbols)} symbols so far...");
                    
                    # Be nice to server
                    time.sleep(0.5);
                    
                else:
                    print(f"   ❌ Finviz failed at page {page}: HTTP {response.status_code}");
                    break;
            
            print(f"   ✅ Discovered {len(symbols)} Finviz symbols");
            
        except Exception as e:
            print(f"   💥 Finviz discovery error: {e}");
            
        return symbols;
    
    def discover_polygon_symbols(self) -> List[Dict]:
        """
        Discover symbols from Polygon.io (free tier)
        Good comprehensive source with market data
        """
        print("📡 Discovering Polygon.io symbols...");
        
        symbols = [];
        
        try:
            # Polygon free API (no key required for basic ticker list)
            url = "https://api.polygon.io/v3/reference/tickers";
            
            params = {
                'market': 'stocks',
                'active': 'true',
                'limit': 1000  # Free tier limit
            };
            
            headers = {
                'User-Agent': 'BTFD Scanner',
            };
            
            response = requests.get(url, params=params, headers=headers, timeout=30);
            
            if response.status_code == 200:
                data = response.json();
                
                if 'results' in data:
                    for item in data['results']:
                        try:
                            symbol = item.get('ticker', '').strip().upper();
                            if symbol and len(symbol) <= 5:
                                symbols.append({
                                    'symbol': symbol,
                                    'name': item.get('name', '').strip(),
                                    'exchange': item.get('primary_exchange', 'US'),
                                    'market_cap': item.get('market_cap', 0.0),
                                    'sector': item.get('sic_description', '').strip(),
                                    'industry': '',
                                    'price': 0.0,
                                    'volume': 0,
                                    'source': 'polygon'
                                });
                                
                        except Exception as e:
                            print(f"   ⚠️  Error parsing Polygon item: {e}");
                            continue;
                    
                    print(f"   ✅ Discovered {len(symbols)} Polygon symbols");
                    
                else:
                    print(f"   ❌ Unexpected Polygon API response");
                    
            else:
                print(f"   ❌ Polygon API failed: HTTP {response.status_code}");
                
        except Exception as e:
            print(f"   💥 Polygon discovery error: {e}");
            
        return symbols;
    
    def _parse_market_cap(self, market_cap_str: str) -> float:
        """Parse market cap string (e.g., '1.23B', '456M') to float"""
        try:
            if not market_cap_str or market_cap_str in ['n/a', 'N/A', '']:
                return 0.0;
            
            market_cap_str = market_cap_str.replace('$', '').replace(',', '').upper().strip();
            
            if 'T' in market_cap_str:
                return float(market_cap_str.replace('T', '')) * 1_000_000_000_000;
            elif 'B' in market_cap_str:
                return float(market_cap_str.replace('B', '')) * 1_000_000_000;
            elif 'M' in market_cap_str:
                return float(market_cap_str.replace('M', '')) * 1_000_000;
            elif 'K' in market_cap_str:
                return float(market_cap_str.replace('K', '')) * 1_000;
            else:
                return float(market_cap_str);
                
        except:
            return 0.0;
    
    def consolidate_symbols(self, symbol_lists: List[List[Dict]]) -> List[Dict]:
        """
        Consolidate symbols from multiple sources, removing duplicates
        and combining information
        """
        print(f"🔄 Consolidating symbols from {len(symbol_lists)} sources...");
        
        consolidated = {};
        
        for source_list in symbol_lists:
            for symbol_data in source_list:
                symbol = symbol_data.get('symbol', '').strip().upper();
                
                if not symbol or len(symbol) > 5:
                    continue;
                
                # Skip obvious junk symbols
                if any(char in symbol for char in ['.', '/', '^', '=', '+']):
                    continue;
                
                if symbol in consolidated:
                    # Merge data (prefer non-zero/non-empty values)
                    existing = consolidated[symbol];
                    
                    # Update with better data
                    if not existing['name'] and symbol_data['name']:
                        existing['name'] = symbol_data['name'];
                    if not existing['sector'] and symbol_data['sector']:
                        existing['sector'] = symbol_data['sector'];
                    if not existing['industry'] and symbol_data['industry']:
                        existing['industry'] = symbol_data['industry'];
                    if existing['market_cap'] == 0 and symbol_data['market_cap'] > 0:
                        existing['market_cap'] = symbol_data['market_cap'];
                    if existing['price'] == 0 and symbol_data['price'] > 0:
                        existing['price'] = symbol_data['price'];
                    if existing['volume'] == 0 and symbol_data['volume'] > 0:
                        existing['volume'] = symbol_data['volume'];
                    
                    # Update source to show multiple sources
                    if symbol_data['source'] not in existing['source']:
                        existing['source'] += f",{symbol_data['source']}";
                        
                else:
                    consolidated[symbol] = symbol_data.copy();
        
        result = list(consolidated.values());
        print(f"   ✅ Consolidated to {len(result)} unique symbols");
        
        return result;
    
    def save_symbols_to_database(self, symbols: List[Dict]):
        """Save discovered symbols to database"""
        if not symbols:
            return;
        
        print(f"💾 Saving {len(symbols)} symbols to database...");
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            today = date.today();
            
            for symbol_data in symbols:
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_symbols 
                    (symbol, name, exchange, market_cap, sector, industry, price, volume, is_active, last_updated, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    symbol_data['symbol'],
                    symbol_data['name'][:200] if symbol_data['name'] else '',  # Truncate long names
                    symbol_data['exchange'][:10] if symbol_data['exchange'] else '',
                    symbol_data['market_cap'],
                    symbol_data['sector'][:50] if symbol_data['sector'] else '',
                    symbol_data['industry'][:50] if symbol_data['industry'] else '',
                    symbol_data['price'],
                    symbol_data['volume'],
                    today,
                    symbol_data['source'][:50] if symbol_data['source'] else ''
                ));
            
            conn.commit();
            conn.close();
            
            print(f"   ✅ Successfully saved {len(symbols)} symbols");
            
        except Exception as e:
            print(f"   💥 Error saving symbols: {e}");
    
    def run_full_discovery(self) -> Dict[str, int]:
        """
        Run complete symbol discovery from all sources
        Returns statistics about discovery process
        """
        print("🚀 Starting comprehensive stock symbol discovery...");
        print("=" * 60);
        
        start_time = datetime.now();
        
        # Discover from all sources
        all_sources = [];
        
        # NASDAQ (most reliable)
        nasdaq_symbols = self.discover_nasdaq_symbols();
        if nasdaq_symbols:
            all_sources.append(nasdaq_symbols);
        
        # SEC EDGAR (authoritative)
        sec_symbols = self.discover_sec_symbols();
        if sec_symbols:
            all_sources.append(sec_symbols);
        
        # Finviz (comprehensive)
        finviz_symbols = self.discover_finviz_symbols();
        if finviz_symbols:
            all_sources.append(finviz_symbols);
        
        # Polygon (market data)
        polygon_symbols = self.discover_polygon_symbols();
        if polygon_symbols:
            all_sources.append(polygon_symbols);
        
        # Consolidate all sources
        if all_sources:
            consolidated_symbols = self.consolidate_symbols(all_sources);
            
            # Save to database
            self.save_symbols_to_database(consolidated_symbols);
            
            # Statistics
            duration = datetime.now() - start_time;
            
            stats = {
                'total_discovered': len(consolidated_symbols),
                'sources_used': len(all_sources),
                'nasdaq_count': len(nasdaq_symbols) if nasdaq_symbols else 0,
                'sec_count': len(sec_symbols) if sec_symbols else 0,
                'finviz_count': len(finviz_symbols) if finviz_symbols else 0,
                'polygon_count': len(polygon_symbols) if polygon_symbols else 0,
                'duration_seconds': duration.total_seconds()
            };
            
            print(f"\n✅ DISCOVERY COMPLETE!");
            print(f"📊 Statistics:");
            print(f"   Total Symbols: {stats['total_discovered']:,}");
            print(f"   Sources Used: {stats['sources_used']}");
            print(f"   Duration: {stats['duration_seconds']:.1f} seconds");
            
            return stats;
            
        else:
            print("❌ No symbols discovered from any source");
            return {'total_discovered': 0, 'sources_used': 0};
    
    def get_symbols_under_price(self, max_price: float = 100.0, min_volume: int = 10000) -> List[str]:
        """
        Get symbols under specified price from database
        Much faster than real-time discovery
        """
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("""
                SELECT symbol FROM stock_symbols 
                WHERE is_active = 1 
                AND price > 0 AND price <= ? 
                AND volume >= ?
                ORDER BY volume DESC
            """, (max_price, min_volume));
            
            results = cursor.fetchall();
            conn.close();
            
            symbols = [row[0] for row in results];
            print(f"📊 Found {len(symbols)} symbols under ${max_price} with volume >= {min_volume:,}");
            
            return symbols;
            
        except Exception as e:
            print(f"💥 Error querying symbols: {e}");
            return [];
    
    def cleanup_old_symbols(self, days_to_keep: int = 30):
        """Remove old/stale symbol entries"""
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep);
            
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute("DELETE FROM stock_symbols WHERE last_updated < ?", (cutoff_date,));
            deleted = cursor.rowcount;
            
            conn.commit();
            conn.close();
            
            if deleted > 0:
                print(f"🧹 Cleaned up {deleted} old symbol entries");
                
        except Exception as e:
            print(f"⚠️  Error cleaning symbols: {e}");


# Convenience functions
def discover_all_symbols() -> Dict[str, int]:
    """Run full symbol discovery and return stats"""
    discoverer = StockSymbolDiscovery();
    return discoverer.run_full_discovery();

def get_affordable_symbols(max_price: float = 100.0) -> List[str]:
    """Get list of symbols under specified price from database"""
    discoverer = StockSymbolDiscovery();
    return discoverer.get_symbols_under_price(max_price);