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

## Next Steps
1. Implement extended database schema with new tables
2. Create basic data fetcher framework
3. Build RSI and EMA calculation modules  
4. Develop signal detection and caching system
5. Begin optimization framework development

This architecture provides a solid foundation for both research (optimization) and production (daily scanning) use cases while maintaining security, scalability, and reliability.