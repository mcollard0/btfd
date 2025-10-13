# Stock Instrument Reporting Criteria - BTFD System

## Overview

This document defines the comprehensive measurements and criteria used by the BTFD (Back Testing Fever Dream) system to determine which stock instruments are reported as trading signals. The system employs a multi-layered filtering and scoring approach to identify high-probability trading opportunities suitable for options trading.

## Table of Contents

1. [Primary Filtering Criteria](#primary-filtering-criteria)
2. [Technical Analysis Requirements](#technical-analysis-requirements)
3. [Signal Strength Calculation](#signal-strength-calculation)
4. [Ranking and Selection Process](#ranking-and-selection-process)
5. [Data Quality Requirements](#data-quality-requirements)
6. [Output Limits and Thresholds](#output-limits-and-thresholds)
7. [Configuration References](#configuration-references)

---

## Primary Filtering Criteria

### 1. Price Range Filter

**Purpose**: Ensure stocks are suitable for options trading (exclude penny stocks and overly expensive stocks)

```python
# From: src/config/settings.py - StrategyConfig
PRICE_MIN = 10.0   # Minimum stock price ($10.00)
PRICE_MAX = 100.0  # Maximum stock price ($100.00)
```

**Implementation**: Applied in `scan_stock_for_signals()` method
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=85
# Filter by price range ($10-$100)
current_price = stock_data['close'].iloc[-1];
if not ( StrategyConfig.PRICE_MIN <= current_price <= StrategyConfig.PRICE_MAX ):
    return None;  # Exclude stock from reporting
```

### 2. Volume Requirements

**Purpose**: Ensure adequate liquidity for options trading

```python
# From: src/config/settings.py - StrategyConfig
VOLUME_MIN = 100000  # Minimum daily volume (100K shares)
```

**Note**: Currently defined in configuration but not actively enforced in main scanning logic. Future enhancement opportunity.

---

## Technical Analysis Requirements

### 1. EMA Crossover Detection

**Primary Signal Trigger**: Recent Exponential Moving Average crossover within lookback period

**Parameters**:
- **Fast EMA Range**: 5-15 periods (optimized per symbol)
- **Slow EMA Range**: 15-30 periods (optimized per symbol)  
- **Lookback Period**: 5 days (configurable)

**Implementation**:
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=100
# Calculate technical indicators
ema_fast = self.indicators.calculate_ema( close_prices, params['ema_fast'] );
ema_slow = self.indicators.calculate_ema( close_prices, params['ema_slow'] );

# Check for recent EMA crossovers
crossovers = self.indicators.detect_ema_crossovers( ema_fast, ema_slow, lookback_days );

if not crossovers:
    return None;  # No recent crossovers = no signal
```

**Signal Types**:
- **Bullish**: Fast EMA crosses above Slow EMA → CALL recommendation
- **Bearish**: Fast EMA crosses below Slow EMA → PUT recommendation

### 2. RSI Context Analysis

**Purpose**: Provide confirmation context for EMA signals

**Configuration**:
```python
# From: src/config/settings.py - TechnicalConfig
RSI_PERIOD = 14        # Standard 14-period RSI
RSI_OVERBOUGHT = 70    # Overbought threshold
RSI_OVERSOLD = 30      # Oversold threshold
RSI_LOOKBACK_DAYS = 5  # Days to look for RSI crosses
```

**Context Categories**:
- **Oversold Recovery** (RSI < 30): Strong bullish context
- **Overbought Reversal** (RSI > 70): Strong bearish context
- **Recent Extreme Crosses**: Additional confirmation within 5-day window

---

## Signal Strength Calculation

The system calculates a comprehensive strength score (0-100) for each qualifying signal using the following algorithm:

### Base Score: 50 Points

### RSI Confirmation Adjustments

#### For Bullish Signals:
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=184
if signal_type == 'bullish':
    if current_rsi < TechnicalConfig.RSI_OVERSOLD:
        strength += 20;  # Very strong - currently oversold
    elif current_rsi < 40:
        strength += 10;  # Strong - below midpoint
    elif rsi_crosses.get( 'oversold_cross' ):
        strength += 15;  # Strong - recent oversold cross
        
    # Weaken if RSI is overbought
    if current_rsi > TechnicalConfig.RSI_OVERBOUGHT:
        strength -= 15;
```

#### For Bearish Signals:
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=197
else:  # bearish
    if current_rsi > TechnicalConfig.RSI_OVERBOUGHT:
        strength += 20;  # Very strong - currently overbought
    elif current_rsi > 60:
        strength += 10;  # Strong - above midpoint
    elif rsi_crosses.get( 'overbought_cross' ):
        strength += 15;  # Strong - recent overbought cross
        
    # Weaken if RSI is oversold
    if current_rsi < TechnicalConfig.RSI_OVERSOLD:
        strength -= 15;
```

### Price Position Bonus: +5 Points Maximum

**Formula**: Preference for stocks around $55 (middle of price range)
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=211
# Price range bonus (middle of our range is preferred)
price_score = 1.0 - abs( current_price - 55 ) / 45;  # Normalized around $55 midpoint
strength += price_score * 5;  # Up to 5 points for good price
```

### Parameter Responsiveness: +3 Points

**Bonus**: Awarded for tighter EMA spreads indicating more responsive signals
```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=214
# Parameter confidence (tighter EMAs might be more responsive)
ema_gap = params['ema_slow'] - params['ema_fast'];
if ema_gap <= 10:
    strength += 3;  # Bonus for responsive parameters
```

### Final Score Normalization

```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=219
# Ensure strength stays in 0-100 range
return max( 0, min( 100, strength ) );
```

---

## Ranking and Selection Process

### 1. Sorting Logic

All qualifying signals are sorted by **signal strength** (highest first):

```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=254
# Sort by signal strength (strongest first)
signals.sort( key=lambda x: x['signal_strength'], reverse=True );
```

### 2. Strength Categories

Visual indicators for signal quality:

| Strength Range | Indicator | Description | Color Code |
|----------------|-----------|-------------|------------|
| 70-100% | ✅ | Strong Signal | Green |
| 50-70% | ⚠️ | Moderate Signal | Yellow/Orange |
| 0-50% | ❌ | Weak Signal | Red |

### 3. Selection Criteria

**All qualifying signals are reported**, regardless of strength level, but are:
- Ranked by strength score
- Color-coded by category  
- Limited by output constraints (see next section)

---

## Output Limits and Thresholds

### 1. Maximum Signal Limits

```python
# From: src/config/settings.py - EmailConfig
MAX_SIGNALS_EMAIL = 10;  # Max signals in email notifications

# From: src/scanner/daily_scanner.py - scan_multiple_stocks()
max_signals: int = 20    # Default maximum signals per scan (configurable)

# From: src/scanner/daily_scanner.py - format_signals_for_motd()  
motd_limit = 5          # Top 5 signals for MOTD display
```

### 2. Stock List Generation

**Candidate Pool**: Pre-defined list of popular, liquid stocks
```python path=/ARCHIVE/Programming/btfd/src/data/fetchers.py start=395
candidate_symbols = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 
    'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'PYPL', 'DIS', 'NKE',
    'BABA', 'UBER', 'LYFT', 'SNAP', 'TWTR', 'SQ', 'ROKU', 'ZOOM',
    'BA', 'GE', 'F', 'GM', 'CAT', 'JPM', 'GS', 'V', 'MA',
    'WMT', 'TGT', 'HD', 'LOW', 'MCD', 'SBUX', 'KO', 'PEP'
];
```

**Selection Process**: 
1. Filter by current price range ($10-$100)
2. Limit to first 20 qualifying stocks for optimization
3. Real-time price validation during scan

---

## Data Quality Requirements

### 1. Historical Data Requirements

**Minimum Data Period**: 30 days of historical data for technical indicator calculations

```python path=/ARCHIVE/Programming/btfd/src/scanner/daily_scanner.py start=78
# Get historical data (need extra days for technical indicators)
end_date = date.today();
start_date = end_date - timedelta( days=60 );  # 60 days for indicators + signals

stock_data = self.data_manager.get_stock_data( symbol, start_date, end_date );

if stock_data is None or len( stock_data ) < 30:
    return None;  # Insufficient data
```

### 2. Data Sources

**Primary Source**: Yahoo Finance (yfinance library)
- Free historical OHLCV data
- Real-time price quotes
- High reliability and coverage

**Fallback Source**: Alpha Vantage API
- Rate limited: 5 calls/minute, 500 calls/day
- Used when Yahoo Finance fails
- Requires API key configuration

```python path=/ARCHIVE/Programming/btfd/src/data/fetchers.py start=308
# Try Yahoo Finance first (unless forced to use Alpha Vantage)
if force_source != 'alphavantage':
    data = self.yahoo_fetcher.fetch_stock_data( symbol, start_date, end_date );

# Fallback to Alpha Vantage if Yahoo failed
if data is None and self.alpha_fetcher and force_source != 'yahoo':
    data = self.alpha_fetcher.fetch_stock_data( symbol, start_date, end_date );
```

### 3. Data Validation

**Current Price Validation**: Must have valid current price data
**Technical Indicator Validation**: Sufficient data points for RSI, EMA calculations
**Date Range Validation**: Data within required timeframe boundaries

---

## Configuration References

### File Locations

| Configuration | File Path | Purpose |
|---------------|-----------|---------|
| **Technical Settings** | `src/config/settings.py` | RSI periods, EMA ranges, thresholds |
| **Strategy Settings** | `src/config/settings.py` | Price limits, volume requirements |
| **Email Settings** | `src/config/settings.py` | Notification limits, SMTP config |
| **Scanner Logic** | `src/scanner/daily_scanner.py` | Main filtering and scoring logic |
| **Data Management** | `src/data/fetchers.py` | Data sources, caching, stock lists |

### Key Configuration Classes

```python path=/ARCHIVE/Programming/btfd/src/config/settings.py start=74
class TechnicalConfig:
    RSI_PERIOD = 14;
    RSI_OVERBOUGHT = 70;
    RSI_OVERSOLD = 30;
    RSI_LOOKBACK_DAYS = 5;
    EMA_FAST_MIN = 5;
    EMA_FAST_MAX = 15;
    EMA_SLOW_MIN = 15;
    EMA_SLOW_MAX = 30;

class StrategyConfig:
    PRICE_MIN = 10.0;
    PRICE_MAX = 100.0;
    VOLUME_MIN = 100000;
    STRIKE_RANGE_PCT = 0.40;
    TARGET_DTE = 30;
```

---

## Summary Decision Flow

A stock instrument is reported if it meets **ALL** of the following criteria:

1. ✅ **Price Filter**: $10.00 ≤ Current Price ≤ $100.00
2. ✅ **Data Quality**: ≥30 days of historical data available  
3. ✅ **Technical Signal**: Recent EMA crossover detected (within 5 days)
4. ✅ **Data Validation**: Valid current price and technical indicators

**Once qualified**, stocks are:
- Scored using the comprehensive strength algorithm (0-100)
- Ranked by strength (highest first)
- Limited by output constraints (top 5-20 signals)
- Enhanced with RSI context and options recommendations
- Formatted for email, MOTD, and database storage

---

*Document Version: 1.0*  
*Last Updated: 2025-10-13*  
*Generated from BTFD codebase analysis*