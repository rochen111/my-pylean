# Risk and Trade Management Features in Lean

## Overview

Lean provides comprehensive risk and trade management capabilities for algorithmic trading. This document outlines the key features available in the `pylean` folder.

## Core Risk Management Libraries

### 1. **Risk Management Models** (`Algorithm/Risk/`)

Built-in risk management models that can be used in framework algorithms:

#### Available Models:
- **`MaximumDrawdownPercentPortfolio`** - Liquidates when portfolio drawdown exceeds threshold
- **`MaximumDrawdownPercentPerSecurity`** - Monitors drawdown per individual security
- **`MaximumUnrealizedProfitPercentPerSecurity`** - Takes profit when target is reached
- **`MaximumSectorExposureRiskManagementModel`** - Limits exposure to specific sectors
- **`TrailingStopRiskManagementModel`** - Implements trailing stop loss
- **`CompositeRiskManagementModel`** - Combines multiple risk models
- **`NullRiskManagementModel`** - No-op model for framework completeness

#### Usage Example:
```python
from AlgorithmImports import *
from Risk.TrailingStopRiskManagementModel import TrailingStopRiskManagementModel

class MyAlgorithm(QCAlgorithm):
    def initialize(self):
        # Set 2% trailing stop
        self.set_risk_management(TrailingStopRiskManagementModel(0.02))
```

### 2. **Order Types for Risk Management**

#### Stop Orders:
- **`stop_market_order()`** - Exit when price hits stop level
- **`stop_limit_order()`** - Stop with limit price protection
- **`trailing_stop_order()`** - Dynamic stop that trails price

#### Limit Orders:
- **`limit_order()`** - Take profit at specific price
- **`limit_if_touched_order()`** - Conditional limit order

#### Example:
```python
# Long position with stop loss and take profit
entry_price = self.securities[symbol].price
quantity = 100

# Enter position
self.market_order(symbol, quantity)

# Set stop loss 2% below entry
stop_price = entry_price * 0.98
self.stop_market_order(symbol, -quantity, stop_price)

# Set take profit 4% above entry
take_profit_price = entry_price * 1.04
self.limit_order(symbol, -quantity, take_profit_price)
```

### 3. **Portfolio Management**

#### Position Sizing:
```python
# Risk-based position sizing
risk_per_trade = 0.02  # 2% risk
portfolio_value = self.portfolio.total_portfolio_value
risk_amount = portfolio_value * risk_per_trade

# Calculate position size based on stop distance
stop_distance = entry_price - stop_price
position_size = risk_amount / stop_distance
```

#### Portfolio Metrics:
```python
# Access portfolio statistics
self.portfolio.total_portfolio_value
self.portfolio.total_margin_used
self.portfolio.margin_remaining
self.portfolio.total_unrealized_profit
self.portfolio.total_profit
```

### 4. **Technical Indicators** (`Indicators/`)

Risk management often relies on technical indicators:

- **ATR (Average True Range)** - Volatility-based stop placement
- **Bollinger Bands** - Volatility channels
- **RSI** - Overbought/oversold conditions
- **Moving Averages** - Trend following and stops
- **Standard Deviation** - Volatility measurement

```python
# ATR for dynamic stop loss
atr = self.atr(symbol, 14)
stop_distance = atr.current.value * 2  # 2 ATR stop
```

### 5. **Charting and Visualization**

```python
# Create custom charts
chart = Chart('Risk Metrics')
chart.add_series(Series('Portfolio Value', SeriesType.LINE, 0))
chart.add_series(Series('Drawdown %', SeriesType.LINE, 1))
self.add_chart(chart)

# Plot data
self.plot('Risk Metrics', 'Portfolio Value', self.portfolio.total_portfolio_value)
```

## Demo Algorithm: ESFuturesRiskManagementDemo

### Location
`Algorithm.Python/ESFuturesRiskManagementDemo.py`

### Features Demonstrated

#### 1. **Risk Parameters**
- 2% risk per trade
- 1.5% fixed stop loss
- 3% take profit target (2:1 risk-reward)
- 10% maximum drawdown limit
- 2% trailing stop after profit

#### 2. **Position Management**
- **Dynamic Position Sizing** - Calculates contracts based on portfolio risk
- **Stop Loss Orders** - Automatic stops placed on entry
- **Take Profit Orders** - Target profits defined upfront
- **Trailing Stops** - Locks in profits as price moves favorably
- **Contract Rolling** - Handles futures contract expiration

#### 3. **Entry Signals**
- EMA crossover strategy (20/50 periods)
- Long when fast EMA > slow EMA
- Short when fast EMA < slow EMA

#### 4. **Risk Monitoring**
- Real-time drawdown calculation
- Automatic liquidation at max drawdown
- Trade statistics tracking
- Win/loss ratio monitoring

#### 5. **Charting (4 Custom Charts)**

**Portfolio Chart:**
- Portfolio value over time
- Daily P&L bars
- Drawdown percentage

**Trade Management Chart:**
- Entry prices (scatter)
- Stop loss levels (scatter)
- Take profit levels (scatter)
- Current price (line)

**Risk Metrics Chart:**
- Win rate percentage
- Risk/reward ratio
- Position size

**Indicators Chart:**
- Fast EMA (20 period)
- Slow EMA (50 period)
- ATR (14 period)

### Running the Demo

#### 1. Update Launcher Configuration

Edit `Launcher/config.json`:
```json
{
  "algorithm-type-name": "ESFuturesRiskManagementDemo",
  "algorithm-language": "Python",
  "algorithm-location": "../../../Algorithm.Python/ESFuturesRiskManagementDemo.py"
}
```

#### 2. Build and Run
```bash
cd /home/rochen/Downloads/pylean
source pylean/bin/activate
dotnet build
dotnet run --project Launcher
```

#### 3. View Results

Results will be saved to:
- `Launcher/bin/Debug/` directory
- Backtest report with charts
- Trade log with entry/exit details
- Performance statistics

### Expected Output

```
LONG ENTRY: 1 contracts @ 4235.50
  Stop Loss: 4172.04 | Take Profit: 4362.57
TRAILING STOP updated: 4193.61
TAKE PROFIT - WIN: $6353.50

============================================================
FINAL TRADE STATISTICS
============================================================
Total Trades: 15
Winning Trades: 9
Losing Trades: 6
Win Rate: 60.00%
Average Win: $4250.33
Average Loss: $2125.17
Risk/Reward Ratio: 2.00
Net P&L: $25516.50
Max Drawdown: 4.25%
Final Portfolio Value: $125516.50
============================================================
```

## Advanced Risk Management Techniques

### 1. **Kelly Criterion Position Sizing**
```python
# Kelly formula: f* = (bp - q) / b
win_rate = 0.6  # 60%
avg_win = 4000
avg_loss = 2000
risk_reward = avg_win / avg_loss

kelly_fraction = (win_rate * risk_reward - (1 - win_rate)) / risk_reward
position_size = portfolio_value * kelly_fraction * 0.5  # Use half Kelly
```

### 2. **Volatility-Based Position Sizing**
```python
# Scale position size inversely with volatility
atr = self.atr(symbol, 14)
normal_volatility = 50  # Baseline ATR
volatility_scalar = normal_volatility / atr.current.value
adjusted_position = base_position * volatility_scalar
```

### 3. **Time-Based Stops**
```python
# Exit if position not profitable after N bars
self.entry_time = self.time
max_hold_time = timedelta(days=5)

if self.time - self.entry_time > max_hold_time:
    self.liquidate(symbol)
```

### 4. **Correlation-Based Risk**
```python
# Reduce position if correlated assets already held
correlation_limit = 0.7
if self.get_correlation(symbol, existing_symbol) > correlation_limit:
    position_size *= 0.5  # Reduce by half
```

### 5. **Scaling In/Out**
```python
# Scale into position in thirds
entry_1 = self.market_order(symbol, quantity / 3)
# ... wait for confirmation ...
entry_2 = self.market_order(symbol, quantity / 3)
# ... wait for more confirmation ...
entry_3 = self.market_order(symbol, quantity / 3)
```

## Key Takeaways

✓ **Always use stop losses** - Protect capital on every trade
✓ **Define risk before entry** - Know your max loss upfront
✓ **Use trailing stops** - Lock in profits as they grow
✓ **Monitor drawdown** - Have circuit breakers for bad periods
✓ **Track statistics** - Learn from win/loss patterns
✓ **Size positions properly** - Risk management is position management
✓ **Visualize trades** - Charts help understand strategy behavior

## Additional Resources

- **Framework Algorithms**: `Algorithm.Python/*Framework*.py`
- **Risk Examples**: `Algorithm.Python/*Risk*.py`
- **Order Examples**: `Algorithm.Python/OrderTicketDemoAlgorithm.py`
- **Indicator Examples**: `Algorithm.Python/IndicatorSuiteAlgorithm.py`
- **Documentation**: [QuantConnect Documentation](https://www.quantconnect.com/docs/)
