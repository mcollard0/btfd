"""
Configuration Management for BTFD
Handles environment variables, database connections, and API configuration
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

class BTFDConfig:
    """Main configuration class for BTFD system"""
    
    def __init__( self ):
        self.project_root = self._find_project_root();
        self.db_path = self.project_root / "btfd" / "data" / "btfd.db";
        self._api_keys = {};
        self._load_api_keys();
    
    def _find_project_root( self ) -> Path:
        """Find the BTFD project root directory"""
        current = Path.cwd();
        while current != current.parent:
            if ( current / "btfd" ).exists() and ( current / "src" ).exists():
                return current;
            current = current.parent;
        
        # Fallback to current directory
        return Path.cwd();
    
    def _load_api_keys( self ):
        """Load API keys from database and environment"""
        
        # Load from environment first
        if "ALPHAVANTAGE_API_KEY" in os.environ:
            self._api_keys["alphavantage"] = os.environ["ALPHAVANTAGE_API_KEY"];
        
        # Load from database
        if self.db_path.exists():
            try:
                conn = sqlite3.connect( str( self.db_path ) );
                cursor = conn.cursor();
                cursor.execute( "SELECT service, api_key FROM api_keys" );
                
                for service, api_key in cursor.fetchall():
                    self._api_keys[service] = api_key;
                
                conn.close();
            except Exception as e:
                print( f"Warning: Could not load API keys from database: {e}" );
    
    def get_api_key( self, service: str ) -> Optional[str]:
        """Get API key for specified service"""
        return self._api_keys.get( service );
    
    def get_database_connection( self ) -> sqlite3.Connection:
        """Get SQLite database connection"""
        return sqlite3.connect( str( self.db_path ) );
    
    @property
    def database_path( self ) -> str:
        """Database file path"""
        return str( self.db_path );
    
    @property 
    def project_root_path( self ) -> str:
        """Project root directory path"""
        return str( self.project_root );

# Global configuration instance
config = BTFDConfig();

# Configuration constants
class TechnicalConfig:
    """Technical analysis configuration"""
    RSI_PERIOD = 14;
    RSI_OVERBOUGHT = 70;
    RSI_OVERSOLD = 30;
    RSI_LOOKBACK_DAYS = 5;  # Look for RSI crosses in last N days
    
    # EMA optimization ranges
    EMA_FAST_MIN = 5;
    EMA_FAST_MAX = 15;
    EMA_SLOW_MIN = 15;
    EMA_SLOW_MAX = 30;

class StrategyConfig:
    """Trading strategy configuration"""
    PRICE_MIN = 10.0;   # Minimum stock price
    PRICE_MAX = 100.0;  # Maximum stock price
    VOLUME_MIN = 100000;  # Minimum daily volume
    
    # Option selection
    STRIKE_RANGE_PCT = 0.40;  # ±40% from current price
    TARGET_DTE = 30;  # Days to expiration target

class RateLimitConfig:
    """API rate limiting configuration"""
    ALPHAVANTAGE_CALLS_PER_MINUTE = 5;
    ALPHAVANTAGE_CALLS_PER_DAY = 500;
    
    # Retry configuration
    MAX_RETRIES = 3;
    RETRY_DELAY = 1.0;  # seconds
    
class EmailConfig:
    """Email notification configuration"""
    DEFAULT_SMTP_PORT = 587;
    MAX_SIGNALS_EMAIL = 10;  # Max signals to include in email
    
def get_config() -> BTFDConfig:
    """Get global configuration instance"""
    return config;