# BTFD Stock Reporting - Quick Reference Card

## 🎯 Primary Criteria (ALL must be met)

✅ **Price Range**: $10.00 - $100.00  
✅ **Historical Data**: ≥30 days available  
✅ **EMA Crossover**: Recent crossover within 5 days  
✅ **Data Quality**: Valid current price & indicators  

## 📊 Signal Strength Scoring (0-100)

**Base**: 50 points  
**RSI Context**: ±15 to ±20 points  
**Price Position**: Up to +5 points (prefers ~$55)  
**EMA Responsiveness**: +3 points (gap ≤10 periods)  

## 🚦 Strength Categories

| Range | Icon | Level | Action |
|-------|------|-------|--------|
| 70-100% | ✅ | Strong | High confidence |
| 50-70% | ⚠️ | Moderate | Standard signals |
| 0-50% | ❌ | Weak | Lower priority |

## ⚙️ Key Parameters

**RSI**: 14-period, 30/70 thresholds  
**EMA**: Fast(5-15)/Slow(15-30), optimized per stock  
**Lookback**: 5 days for crossovers & RSI extremes  

## 📈 Signal Types

**Bullish** (CALL): Fast EMA crosses above Slow EMA  
**Bearish** (PUT): Fast EMA crosses below Slow EMA  

## 📊 Output Limits

- **Email**: Top 10 signals  
- **MOTD**: Top 5 signals  
- **Scan**: Top 20 signals (default)  

---
*Full details: `docs/stock_reporting_criteria.md`*