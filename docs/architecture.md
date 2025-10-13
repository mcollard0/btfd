# BTFD (Back Testing Fever Dream) Architecture

## System Overview
A Python-based stock option backtesting platform with two primary operational modes:
1. **Optimization Phase**: Generate P/L heatmaps and parameter optimization
2. **Daily Scanner Phase**: Real-time signal detection with cron job automation

---

## Architecture Layers

### 1. Configuration Layer
**Purpose**: Environment management and API configuration
- **Environment Variables**: `ALPHAVANTAGE_API_KEY` loaded from `~/.bashrc`  
- **SQLite Configuration**: API keys, rate limits, email settings stored in `btfd/data/btfd.db`
- **Toggleable Data Sources**: Primary (Yahoo Finance) vs Fallback (Alpha Vantage)

### 2. Data Layer
**Purpose**: Multi-source market data acquisition with rate limiting

#### Data Sources
- **YahooFetcher** (Primary): `yfinance` library for free historical data
- **AlphaVantageFetcher** (Fallback): Alpha Vantage API with 5 calls/min, 500 calls/day limits
- **Rate Limiting**: Tracked in SQLite, prevents API quota exhaustion

#### Data Normalization & Caching
- **Stock Data Cache**: `stock_data` table with OHLCV + timestamp
- **Technical Indicators Cache**: `technical_indicators` table (RSI, EMA, MACD)
- **Option Chain Cache**: `option_chain` table with theoretical pricing

### 3. Technical Analysis Layer
**Purpose**: Calculate indicators and detect signal crossovers

#### Indicators
- **RSI(14)**: Relative Strength Index with overbought/oversold detection (70/30 levels)  
- **EMA Crossovers**: Exponential Moving Averages with optimizable parameters
- **MACD**: Moving Average Convergence Divergence for trend confirmation
- **Price Filtering**: Stock price range $10-$100

#### Signal Detection
- **EMA Cross Detection**: Bullish/bearish crossovers since last trading day
- **RSI Context Flagging**: Recent crosses above 70 or below 30 (3-5 day window)
- **Multi-timeframe Analysis**: Daily bars with intraday confirmation

### 4. Option Pricing Models Layer
**Purpose**: Theoretical option price calculation

#### Pricing Models
- **Black-Scholes Model**: European option pricing with Greeks calculation
- **Binomial Tree Model**: American option pricing (early exercise)
- **Implied Volatility Surface**: IV calibration and interpolation

#### Greeks Calculation
- **Delta, Gamma, Theta, Vega, Rho**: Risk metrics for position analysis
- **Portfolio-level Greeks**: Aggregate exposure calculations

### 5. Backtesting Engine Layer
**Purpose**: Historical strategy simulation using Backtrader framework

#### Custom Feeds
- **Stock Data Feed**: Historical OHLCV with technical indicators
- **Option Data Feed**: Theoretical option prices with Greeks
- **Event Handling**: `on_bar`, `on_option_expiry`, `on_order_fill`

#### Broker Simulation
- **Commission Structure**: Configurable per-contract and per-share fees
- **Spread Costs**: Bid/ask spread simulation
- **Margin Requirements**: Option strategy margin calculations

### 6. Strategy Layer
**Purpose**: Trading logic and signal generation

#### Stock Filtering
- **Price Range**: $10-$100 at market open
- **Volume Threshold**: Minimum daily volume requirements
- **Market Cap Filter**: Optional large/mid/small cap filtering

#### Option Strategy Rules
- **Expiration Selection**: Target 3rd Friday of month
- **Strike Selection**: ITM underlying, OTM strikes within ±40%
- **Position Sizing**: Risk-based position allocation

#### Signal Rules
- **EMA Crossovers**: 
  - Fast EMA (5-15 period range) 
  - Slow EMA (15-30 period range)
  - Optimizable via parameter sweep
- **RSI Confirmation**: 
  - Recent oversold (RSI < 30) for bullish signals
  - Recent overbought (RSI > 70) for bearish signals
- **MACD Confirmation**: Secondary trend validation

### 7. Optimization Framework Layer
**Purpose**: Parameter tuning and performance analysis

#### Parameter Sweep System
- **EMA Parameter Grid**: Test combinations (5-15)/(15-25), (8-12)/(18-22), etc.
- **RSI Period Optimization**: Test RSI periods 10, 12, 14, 16, 18
- **Lookback Window Testing**: Signal confirmation periods (3-7 days)

#### Performance Metrics
- **Return Metrics**: Total return, annualized return, Sharpe ratio
- **Risk Metrics**: Maximum drawdown, volatility, Value at Risk
- **Trade Statistics**: Win rate, average win/loss, profit factor

#### Visualization
- **Interactive Heatmaps**: Plotly-based P/L parameter surfaces
- **Equity Curves**: Portfolio value over time
- **Drawdown Analysis**: Peak-to-trough decline periods

### 8. Daily Scanner Layer
**Purpose**: Production signal detection and notification

#### Scanner Logic
- **Market Data Update**: Fetch latest prices and calculate indicators
- **Signal Detection**: Identify new crossovers since last trading day
- **RSI Context Addition**: Flag recent RSI extremes with timing
- **Ranking System**: Score signals by strength and confluence
- **Filtering Criteria**: See `docs/stock_reporting_criteria.md` for comprehensive measurement details

#### Output Formatting
- **Email Format**: HTML table with signal details, charts
- **MOTD Format**: Plain text summary for terminal display
- **JSON Export**: Machine-readable signal data

### 9. Notification & Persistence Layer
**Purpose**: Results delivery and historical tracking

#### Email System
- **SMTP Configuration**: Gmail/Outlook integration via SQLite config
- **HTML Templates**: Rich formatting with embedded charts
- **Attachment Support**: CSV/PDF reports

#### MOTD Integration
- **System Integration**: Write to `/etc/motd` or `~/.motd`
- **Permission Handling**: Graceful fallback if no write access
- **Formatting**: Clean terminal-friendly output

#### Historical Tracking
- **Signal History**: `daily_signals` table with full context
- **Performance Tracking**: Real-world vs backtested results
- **Model Drift Detection**: Signal effectiveness over time

---

## Database Schema

### Core Tables
```sql
-- API Configuration
CREATE TABLE api_keys( 
    id INTEGER PRIMARY KEY, 
    service TEXT, 
    api_key TEXT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

-- Rate Limiting
CREATE TABLE rate_limit( 
    id INTEGER PRIMARY KEY, 
    service TEXT, 
    period TEXT, 
    max_calls INTEGER, 
    calls_made INTEGER, 
    window_start TIMESTAMP 
);

-- Market Data Cache
CREATE TABLE stock_data( 
    symbol TEXT, 
    timestamp DATETIME, 
    open REAL, 
    high REAL, 
    low REAL, 
    close REAL, 
    volume INTEGER, 
    PRIMARY KEY(symbol, timestamp) 
);

-- Technical Indicators
CREATE TABLE technical_indicators( 
    symbol TEXT, 
    date DATE, 
    indicator_name TEXT, 
    period INTEGER, 
    value REAL, 
    PRIMARY KEY(symbol, date, indicator_name, period) 
);

-- Option Chain Data
CREATE TABLE option_chain( 
    symbol TEXT, 
    expiry DATE, 
    strike REAL, 
    option_type TEXT, 
    bid REAL, 
    ask REAL, 
    theoretical_price REAL, 
    implied_volatility REAL, 
    delta REAL, 
    gamma REAL, 
    theta REAL, 
    vega REAL, 
    PRIMARY KEY(symbol, expiry, strike, option_type) 
);

-- Backtesting Results
CREATE TABLE backtest_runs( 
    run_id INTEGER PRIMARY KEY, 
    start_date DATE, 
    end_date DATE, 
    strategy_params JSON, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE trades( 
    trade_id INTEGER PRIMARY KEY, 
    run_id INTEGER, 
    timestamp DATETIME, 
    symbol TEXT, 
    action TEXT, 
    quantity INTEGER, 
    price REAL, 
    commission REAL, 
    FOREIGN KEY(run_id) REFERENCES backtest_runs(run_id) 
);

CREATE TABLE performance_metrics( 
    run_id INTEGER, 
    metric_name TEXT, 
    metric_value REAL, 
    PRIMARY KEY(run_id, metric_name), 
    FOREIGN KEY(run_id) REFERENCES backtest_runs(run_id) 
);

-- Daily Operations
CREATE TABLE daily_signals( 
    signal_id INTEGER PRIMARY KEY, 
    date DATE, 
    symbol TEXT, 
    signal_type TEXT, 
    ema_fast INTEGER, 
    ema_slow INTEGER, 
    rsi_value REAL, 
    rsi_cross_date DATE, 
    price REAL, 
    strength_score REAL 
);

CREATE TABLE optimization_results( 
    optimization_id INTEGER PRIMARY KEY, 
    parameter_set JSON, 
    backtest_period TEXT, 
    total_return REAL, 
    sharpe_ratio REAL, 
    max_drawdown REAL, 
    win_rate REAL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

-- Email Configuration
CREATE TABLE email_config( 
    config_id INTEGER PRIMARY KEY, 
    smtp_server TEXT, 
    smtp_port INTEGER, 
    username TEXT, 
    password TEXT, 
    recipients TEXT, 
    enabled BOOLEAN DEFAULT 1 
);
```

### Indexes for Performance
```sql
-- Fast signal queries
CREATE INDEX idx_stock_data_symbol_date ON stock_data(symbol, timestamp);
CREATE INDEX idx_technical_indicators_symbol_date ON technical_indicators(symbol, date);
CREATE INDEX idx_daily_signals_date ON daily_signals(date);

-- Optimization queries
CREATE INDEX idx_optimization_results_params ON optimization_results(json_extract(parameter_set, '$.ema_fast'), json_extract(parameter_set, '$.ema_slow'));
```

---

## File Structure
```
btfd/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration management
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetchers.py          # Yahoo/Alpha Vantage fetchers
│   │   ├── cache.py             # SQLite data caching
│   │   └── rate_limiter.py      # API rate limiting
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── technical.py         # RSI, EMA, MACD calculations
│   │   └── signals.py           # Crossover detection
│   ├── pricing/
│   │   ├── __init__.py
│   │   ├── black_scholes.py     # Option pricing models
│   │   └── greeks.py            # Greeks calculations
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py            # Backtrader integration
│   │   ├── strategies.py        # Trading strategies
│   │   └── feeds.py             # Custom data feeds
│   ├── optimization/
│   │   ├── __init__.py
│   │   ├── parameter_sweep.py   # Grid search optimization
│   │   └── visualization.py     # Plotly heatmaps
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── daily_scanner.py     # Main scanning logic
│   │   └── ranking.py           # Signal scoring
│   └── notifications/
│       ├── __init__.py
│       ├── email_sender.py      # SMTP integration
│       └── motd_writer.py       # System message integration
├── btfd/data/
│   └── btfd.db                  # SQLite database (gitignored)
├── docs/
│   ├── architecture.md          # This document
│   ├── stock_reporting_criteria.md # Stock instrument reporting measurements and criteria
│   └── api_documentation.md     # Code API docs
├── tests/
│   ├── test_data_fetchers.py
│   ├── test_indicators.py
│   └── test_strategies.py
├── backups/                     # Automated code snapshots
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Development Phases

### Phase 1: Foundation (Current)
- [x] Project structure setup
- [x] API key management
- [x] Dependencies installation
- [x] Architecture documentation
- [ ] Database schema implementation
- [ ] Basic data fetcher classes

### Phase 2: Technical Analysis
- [ ] RSI(14) indicator implementation
- [ ] EMA crossover detection
- [ ] MACD calculation
- [ ] Signal caching and persistence

### Phase 3: Backtesting Framework
- [ ] Backtrader integration
- [ ] Option pricing models
- [ ] Strategy implementation
- [ ] Performance metrics calculation

### Phase 4: Optimization System
- [ ] Parameter sweep framework
- [ ] P/L heatmap generation
- [ ] Interactive visualization
- [ ] Results persistence

### Phase 5: Daily Scanner
- [ ] Real-time signal detection
- [ ] RSI context flagging
- [ ] Signal ranking and scoring
- [ ] Output formatting

### Phase 6: Production Automation
- [ ] Email notification system
- [ ] MOTD integration
- [ ] Cron job setup
- [ ] Error handling and logging

### Phase 7: Backup and Monitoring
- [ ] Automated backup system
- [ ] Performance monitoring
- [ ] Model drift detection
- [ ] Production deployment

---

## Risk Management Considerations

### Data Quality
- **Multiple Source Validation**: Cross-check Yahoo vs Alpha Vantage data
- **Missing Data Handling**: Graceful degradation when data unavailable
- **Outlier Detection**: Flag suspicious price movements

### API Management
- **Rate Limit Compliance**: Strict adherence to Alpha Vantage limits
- **Failover Logic**: Automatic fallback between data sources
- **Error Recovery**: Retry logic with exponential backoff

### Financial Risk
- **Paper Trading First**: No real money until proven strategies
- **Position Sizing**: Risk-based allocation (1-2% per trade)
- **Stop Loss Integration**: Automatic risk management rules

### System Reliability
- **Error Logging**: Comprehensive logging for debugging
- **Graceful Degradation**: System continues with reduced functionality
- **Data Backup**: Regular SQLite database backups

---

## Development Environment Setup

### Virtual Environment Usage
**CRITICAL**: Always use the virtual environment when running BTFD components.

```bash
# Activate virtual environment
cd /ARCHIVE/Programming/btfd
source venv/bin/activate

# Verify dependencies are available
python -c "import yfinance, talib, pandas; print('Dependencies OK')"

# Run scanner
python src/daily_btfd_scanner.py
```

### Dependencies
The system requires these key packages (installed in `./venv/`):
- **yfinance**: Primary data source for stock prices
- **TA-Lib**: Technical analysis calculations (RSI, EMA, SMA, MACD)
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **requests**: API calls and HTTP requests
- **sqlite3**: Database operations (built-in)

### Running the System

#### Daily EMA + SMA Scanner (Default)
```bash
source venv/bin/activate
python src/daily_btfd_scanner.py
```

#### SMA-Only Scanner
```bash
source venv/bin/activate
python run_sma_scanner.py --test-mode
```

#### Test Mode
```bash
source venv/bin/activate
python src/daily_btfd_scanner.py --test-mode
```

---

## Production Deployment Notes

### Cron Job Setup
For automated daily scanning, add to crontab:
```bash
# Run BTFD scanner at 9:30 AM EST (after market open)
30 9 * * 1-5 cd /ARCHIVE/Programming/btfd && source venv/bin/activate && python src/daily_btfd_scanner.py

# Run SMA scanner at 4:30 PM EST (after market close)
30 16 * * 1-5 cd /ARCHIVE/Programming/btfd && source venv/bin/activate && python run_sma_scanner.py
```

### Database Location
- **Path**: `/ARCHIVE/Programming/btfd/btfd/data/btfd.db`
- **Backup**: Automatic timestamped backups in `./backups/` directory
- **Schema**: See database schema section above

### Configuration Files
- **Settings**: `src/config/settings.py`
- **API Keys**: Stored in database `api_keys` table
- **Environment Variables**: `ALPHAVANTAGE_API_KEY` in `~/.bashrc`

### Email Configuration
Email notifications require SMTP configuration in the database:
```sql
INSERT INTO email_config (smtp_server, smtp_port, username, password, recipients)
VALUES ('smtp.gmail.com', 587, 'your_email@gmail.com', 'app_password', 'recipient@example.com');
```

---

## Signal Types and Scanning

### Default Behavior (Both EMA + SMA)
The system now scans for both signal types by default:
- **EMA Signals**: Short-term crossovers (5-15 day periods)
- **SMA Signals**: Long-term crossovers (SMA49/200 for early warning)

### Signal Strength Scoring
- **EMA Signals**: Base 50 + RSI context + price position + parameter responsiveness
- **SMA Signals**: Base 60 (+10 for rarity) + RSI context + momentum confirmation

### Lookback Periods
- **EMA**: 5 days (configurable)
- **SMA**: 14 days (configurable) 
- **RSI Context**: 5 days for extreme crosses

---

## File Structure and Key Components

### Core Scanner Files
- `src/daily_btfd_scanner.py` - Main production scanner (EMA + SMA)
- `run_sma_scanner.py` - SMA-only scanner
- `src/scanner/daily_scanner.py` - Core scanning logic

### Technical Analysis
- `src/indicators/technical.py` - RSI, EMA, SMA calculations
- `src/config/settings.py` - All configuration parameters

### Data Management
- `src/data/fetchers.py` - Yahoo Finance and Alpha Vantage integration
- `btfd/data/btfd.db` - SQLite database

### Notifications
- `src/notifications/email_sender.py` - Email notifications
- `src/notifications/motd_writer.py` - Terminal message updates

---

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Always activate venv first
   ```bash
   source venv/bin/activate
   ```

2. **API Rate Limits**: System automatically handles Alpha Vantage limits
   - 5 calls per minute
   - 500 calls per day
   - Automatic fallback to Yahoo Finance

3. **Database Locked**: SQLite connection issues
   ```bash
   # Check for hung processes
   ps aux | grep python
   ```

4. **Missing Data**: Insufficient historical data for indicators
   - SMA200 requires 200+ trading days
   - RSI requires 14+ days
   - System automatically handles with graceful degradation

### Debug Mode
```bash
source venv/bin/activate
python -c "from src.scanner.daily_scanner import *; scanner=DailySignalScanner(); print('Scanner initialized')"
```

---

## Next Steps
1. ✅ Virtual environment setup and dependency management
2. ✅ EMA signal detection and optimization
3. ✅ SMA49/200 early warning system
4. ✅ Email notification system
5. ✅ Database schema and caching
6. [ ] Real-time monitoring and alerting
7. [ ] Performance analytics and backtesting
8. [ ] Web dashboard for signal visualization

This architecture provides a production-ready foundation for both research (optimization) and production (daily scanning) use cases while maintaining security, scalability, and reliability.

**Remember: Always use the virtual environment when running any BTFD components!**
