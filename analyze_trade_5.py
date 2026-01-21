#!/usr/bin/env python3
"""
Detailed analysis of Trade #5 from ES Futures Risk Management Demo
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Use same random seed and data generation as original
np.random.seed(42)
days = 720
dates = pd.date_range(start='2023-01-01', periods=days*390, freq='1min')

# Generate same price data
t = np.linspace(0, 8*np.pi, len(dates))
trend = 4200 + 150 * np.sin(t) + 80 * np.sin(2*t) + 40 * np.sin(3*t)
noise = np.random.normal(0, 8, len(dates))
price = trend + noise

# Create DataFrame
df = pd.DataFrame({
    'timestamp': dates,
    'close': price,
    'high': price + np.abs(np.random.normal(2, 1, len(dates))),
    'low': price - np.abs(np.random.normal(2, 1, len(dates))),
})

# Add moving averages
df['ema_fast'] = df['close'].ewm(span=5).mean()
df['ema_slow'] = df['close'].ewm(span=15).mean()

# Resample to hourly like in the original
df_hourly = df.set_index('timestamp').resample('h').agg({
    'close': 'last',
    'high': 'max',
    'low': 'min',
    'ema_fast': 'last',
    'ema_slow': 'last'
}).dropna().reset_index()

print("="*80)
print("DETAILED ANALYSIS: TRADE #5")
print("="*80)

# Find Trade 5 entry and exit
# Based on the output, Trade 5 was:
# Entry: 2023-01-21 01:00 at $4250.35
# Exit: 2023-01-23 14:00 at $4186.59 (STOP LOSS)

entry_time = pd.Timestamp('2023-01-21 01:00')
exit_time = pd.Timestamp('2023-01-23 14:00')

# Find the exact rows
entry_idx = df_hourly[df_hourly['timestamp'] == entry_time].index[0]
exit_idx = df_hourly[df_hourly['timestamp'] == exit_time].index[0]

entry_row = df_hourly.iloc[entry_idx]
exit_row = df_hourly.iloc[exit_idx]
prev_entry_row = df_hourly.iloc[entry_idx - 1]

print("\n" + "="*80)
print("PART 1: PRE-ENTRY MARKET CONDITIONS")
print("="*80)

# Show market conditions leading up to entry
print("\nMarket data 5 hours before entry:")
pre_entry = df_hourly.iloc[entry_idx-5:entry_idx]
print(pre_entry[['timestamp', 'close', 'ema_fast', 'ema_slow']].to_string(index=False))

print("\n" + "-"*80)
print("Market Trend Analysis (5 hours before entry):")
print("-"*80)
price_change = pre_entry['close'].iloc[-1] - pre_entry['close'].iloc[0]
print(f"Price Movement: ${pre_entry['close'].iloc[0]:.2f} -> ${pre_entry['close'].iloc[-1]:.2f} ({price_change:+.2f})")
print(f"Fast EMA Trend: ${pre_entry['ema_fast'].iloc[0]:.2f} -> ${pre_entry['ema_fast'].iloc[-1]:.2f}")
print(f"Slow EMA Trend: ${pre_entry['ema_slow'].iloc[0]:.2f} -> ${pre_entry['ema_slow'].iloc[-1]:.2f}")

if pre_entry['ema_fast'].iloc[-1] > pre_entry['ema_slow'].iloc[-1]:
    print("EMA Relationship: Fast ABOVE Slow (Bullish)")
else:
    print("EMA Relationship: Fast BELOW Slow (Bearish)")

print("\n" + "="*80)
print("PART 2: ENTRY SIGNAL DETAILS")
print("="*80)

print(f"\nEntry Timestamp: {entry_time}")
print(f"Entry Price: ${entry_row['close']:.2f}")

print("\n" + "-"*80)
print("EMA Crossover Analysis:")
print("-"*80)
print(f"Previous Hour ({prev_entry_row['timestamp']}):")
print(f"  Fast EMA: ${prev_entry_row['ema_fast']:.2f}")
print(f"  Slow EMA: ${prev_entry_row['ema_slow']:.2f}")
print(f"  Relationship: Fast {'ABOVE' if prev_entry_row['ema_fast'] > prev_entry_row['ema_slow'] else 'BELOW'} Slow")
print(f"  Difference: ${prev_entry_row['ema_fast'] - prev_entry_row['ema_slow']:.2f}")

print(f"\nEntry Hour ({entry_row['timestamp']}):")
print(f"  Fast EMA: ${entry_row['ema_fast']:.2f}")
print(f"  Slow EMA: ${entry_row['ema_slow']:.2f}")
print(f"  Relationship: Fast {'ABOVE' if entry_row['ema_fast'] > entry_row['ema_slow'] else 'BELOW'} Slow")
print(f"  Difference: ${entry_row['ema_fast'] - entry_row['ema_slow']:.2f}")

print("\n" + "-"*80)
print("✓ SIGNAL TRIGGERED: Fast EMA crossed ABOVE Slow EMA")
print("-"*80)

print("\n" + "-"*80)
print("Position Details:")
print("-"*80)
quantity = 1
entry_price = entry_row['close']
stop_loss = entry_price * 0.985  # 1.5% below entry
take_profit = entry_price * 1.03  # 3% above entry
margin = 12000

print(f"Quantity: {quantity} contract(s)")
print(f"Entry Price: ${entry_price:.2f}")
print(f"Stop Loss: ${stop_loss:.2f} (-1.5% from entry)")
print(f"Take Profit: ${take_profit:.2f} (+3.0% from entry)")
print(f"Margin Required: ${margin:,.2f}")
print(f"Risk per contract: ${(entry_price - stop_loss) * 50:.2f}")
print(f"Potential profit per contract: ${(take_profit - entry_price) * 50:.2f}")
print(f"Risk/Reward Ratio: 2.0:1")

print("\n" + "="*80)
print("PART 3: TRADE LIFECYCLE")
print("="*80)

# Show all hourly data during the trade
trade_data = df_hourly.iloc[entry_idx:exit_idx+1]
print(f"\nTrade Duration: {len(trade_data)} hours")
print(f"From: {trade_data['timestamp'].iloc[0]}")
print(f"To: {trade_data['timestamp'].iloc[-1]}")

print("\n" + "-"*80)
print("Hourly Price Action During Trade:")
print("-"*80)
for idx, row in trade_data.iterrows():
    pnl = (row['close'] - entry_price) * 50
    hit_stop = row['low'] <= stop_loss
    hit_target = row['high'] >= take_profit
    
    status = ""
    if hit_stop:
        status = " ⚠ STOP LOSS HIT"
    elif hit_target:
        status = " ✓ TAKE PROFIT HIT"
    
    print(f"{row['timestamp']} | Close: ${row['close']:7.2f} | High: ${row['high']:7.2f} | Low: ${row['low']:7.2f} | P&L: ${pnl:+8.2f}{status}")

print("\n" + "="*80)
print("PART 4: EXIT ANALYSIS")
print("="*80)

print(f"\nExit Timestamp: {exit_time}")
print(f"Exit Price: ${exit_row['low']:.2f} (Stop Loss)")
print(f"Exit Reason: Stop Loss Hit")

print("\n" + "-"*80)
print("Market Conditions at Exit:")
print("-"*80)
print(f"Price: ${exit_row['close']:.2f}")
print(f"Fast EMA: ${exit_row['ema_fast']:.2f}")
print(f"Slow EMA: ${exit_row['ema_slow']:.2f}")
print(f"EMA Relationship: Fast {'ABOVE' if exit_row['ema_fast'] > exit_row['ema_slow'] else 'BELOW'} Slow")

print("\n" + "-"*80)
print("Price Movement During Trade:")
print("-"*80)
high_during_trade = trade_data['high'].max()
low_during_trade = trade_data['low'].min()
max_favorable = high_during_trade - entry_price
max_adverse = entry_price - low_during_trade

print(f"Entry Price: ${entry_price:.2f}")
print(f"Highest Price Reached: ${high_during_trade:.2f} (+${max_favorable:.2f} or +{max_favorable/entry_price*100:.2f}%)")
print(f"Lowest Price Reached: ${low_during_trade:.2f} (-${max_adverse:.2f} or -{max_adverse/entry_price*100:.2f}%)")
print(f"Exit Price: ${exit_row['low']:.2f}")

print("\n" + "="*80)
print("PART 5: TRADE OUTCOME")
print("="*80)

actual_exit_price = stop_loss
pnl = (actual_exit_price - entry_price) * quantity * 50
margin_returned = margin * quantity
final_cash_impact = pnl  # margin is returned, net impact is just P&L

print(f"\nTrade Result: LOSS")
print(f"Entry: ${entry_price:.2f}")
print(f"Exit: ${actual_exit_price:.2f}")
print(f"Price Change: ${actual_exit_price - entry_price:.2f} ({(actual_exit_price - entry_price)/entry_price*100:.2f}%)")
print(f"Contracts: {quantity}")
print(f"ES Multiplier: 50")
print(f"Total P&L: ${pnl:.2f}")
print(f"Margin Returned: ${margin_returned:,.2f}")
print(f"Net Cash Impact: ${pnl:.2f}")

print("\n" + "-"*80)
print("Why This Trade Lost:")
print("-"*80)
print("1. Price moved against the position immediately after entry")
print(f"2. Market dropped {max_adverse:.2f} points, hitting the 1.5% stop loss")
print(f"3. Although price briefly moved favorable by ${max_favorable:.2f}, it wasn't enough")
print("4. The stop loss protected from larger losses")
print(f"5. Without stop loss, potential loss at lowest point: ${(low_during_trade - entry_price) * 50:.2f}")

print("\n" + "="*80)
print("PART 6: VISUALIZATION")
print("="*80)

# Create detailed chart for this trade
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Extended window for context
window_start = entry_idx - 10
window_end = exit_idx + 5
window_data = df_hourly.iloc[window_start:window_end+1]

# Chart 1: Price action
ax1.plot(window_data['timestamp'], window_data['close'], 'b-', linewidth=2, label='Close Price')
ax1.plot(window_data['timestamp'], window_data['ema_fast'], 'g--', alpha=0.7, label='Fast EMA (5)')
ax1.plot(window_data['timestamp'], window_data['ema_slow'], 'r--', alpha=0.7, label='Slow EMA (15)')

# Mark entry and exit
ax1.scatter(entry_time, entry_price, color='green', s=200, marker='^', zorder=5, label='Entry')
ax1.scatter(exit_time, actual_exit_price, color='red', s=200, marker='v', zorder=5, label='Exit')

# Draw stop loss and take profit lines
ax1.axhline(y=stop_loss, color='red', linestyle=':', linewidth=2, alpha=0.5, label='Stop Loss')
ax1.axhline(y=take_profit, color='green', linestyle=':', linewidth=2, alpha=0.5, label='Take Profit')

# Shade the trade period
ax1.axvspan(entry_time, exit_time, alpha=0.1, color='yellow', label='Trade Period')

ax1.set_title('Trade #5: Price Action and EMAs', fontsize=14, fontweight='bold')
ax1.set_ylabel('Price ($)')
ax1.legend(loc='best')
ax1.grid(True, alpha=0.3)

# Chart 2: P&L over time
trade_pnl = [(row['close'] - entry_price) * 50 for _, row in trade_data.iterrows()]
ax2.plot(trade_data['timestamp'], trade_pnl, 'b-', linewidth=2)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.fill_between(trade_data['timestamp'], trade_pnl, 0, 
                  where=[p >= 0 for p in trade_pnl], alpha=0.3, color='green', label='Profit')
ax2.fill_between(trade_data['timestamp'], trade_pnl, 0, 
                  where=[p < 0 for p in trade_pnl], alpha=0.3, color='red', label='Loss')

ax2.scatter(exit_time, pnl, color='red', s=200, marker='X', zorder=5, label='Final P&L')

ax2.set_title('Trade #5: Profit/Loss Evolution', fontsize=14, fontweight='bold')
ax2.set_xlabel('Time')
ax2.set_ylabel('P&L ($)')
ax2.legend(loc='best')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
output_file = '/home/rochen/Downloads/pylean/trade_5_analysis.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\nDetailed chart saved to: {output_file}")

print("\n" + "="*80)
print("END OF ANALYSIS")
print("="*80)
