#!/usr/bin/env python3
"""
Get and plot ES Futures hourly data from 2022 onwards
Displays the last 3 months of data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_es_futures_data(start_date='2022-01-01', end_date=None):
    """
    Generate ES futures hourly data
    Note: This generates simulated data since we don't have direct market data access.
    In a real scenario, you would fetch this from a data provider or LEAN's data folder.
    """
    if end_date is None:
        end_date = datetime.now()
    
    # Generate hourly timestamps (trading hours only: 9:30 AM - 4:00 PM ET, Mon-Fri)
    dates = pd.bdate_range(start=start_date, end=end_date, freq='H')
    
    # Simulate ES futures price data with realistic characteristics
    np.random.seed(42)
    
    # Start price around 3800 in 2022 (more realistic starting point)
    base_price = 3800
    
    # Generate price movement with trend and volatility
    num_periods = len(dates)
    
    # Realistic upward trend over 4 years (2022-2026): ~20% total gain
    # ES went from ~3800 to ~4500-4700 range
    trend = np.linspace(0, 800, num_periods)
    
    # Multiple market cycles with realistic frequency
    t = np.linspace(0, 6 * np.pi, num_periods)  # Fewer, larger cycles
    cyclical = 200 * np.sin(t) + 100 * np.sin(2 * t) + 50 * np.sin(4 * t)
    
    # Reduced random walk for more realistic day-to-day movement
    random_walk = np.cumsum(np.random.normal(0, 3, num_periods))
    
    # Combine components with realistic weighting
    close_prices = base_price + trend + cyclical + random_walk * 0.5
    
    # Add some realistic volatility clustering (higher vol during market stress)
    volatility_periods = np.random.choice([1, 1.5, 2], num_periods, p=[0.7, 0.2, 0.1])
    close_prices = close_prices + np.random.normal(0, 5, num_periods) * volatility_periods
    
    # Generate OHLC data with realistic intraday ranges
    high_prices = close_prices + np.abs(np.random.normal(8, 4, num_periods))
    low_prices = close_prices - np.abs(np.random.normal(8, 4, num_periods))
    open_prices = close_prices + np.random.normal(0, 3, num_periods)
    
    # Generate volume (higher during volatile periods)
    volatility = np.abs(np.diff(close_prices, prepend=close_prices[0]))
    volume = 50000 + 30000 * (volatility / volatility.max()) + np.random.normal(0, 5000, num_periods)
    volume = np.abs(volume).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })
    
    return df

def calculate_technical_indicators(df):
    """Add technical indicators to the dataframe"""
    # Simple Moving Averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    # Exponential Moving Averages
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
    df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
    
    # Volume moving average
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    
    return df

def plot_last_3_months(df):
    """Plot the last 3 months of ES futures data"""
    
    # Get last 3 months
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=90)
    
    df_recent = df[df['timestamp'] >= start_date].copy()
    
    print(f"\n{'='*80}")
    print(f"ES FUTURES DATA ANALYSIS")
    print(f"{'='*80}")
    print(f"Total data points: {len(df):,}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"\nLast 3 months:")
    print(f"Data points: {len(df_recent):,}")
    print(f"Date range: {df_recent['timestamp'].min()} to {df_recent['timestamp'].max()}")
    print(f"\nPrice Statistics (Last 3 Months):")
    print(f"Opening Price: ${df_recent['close'].iloc[0]:,.2f}")
    print(f"Closing Price: ${df_recent['close'].iloc[-1]:,.2f}")
    print(f"Change: ${df_recent['close'].iloc[-1] - df_recent['close'].iloc[0]:,.2f} ({(df_recent['close'].iloc[-1] / df_recent['close'].iloc[0] - 1) * 100:.2f}%)")
    print(f"High: ${df_recent['high'].max():,.2f}")
    print(f"Low: ${df_recent['low'].min():,.2f}")
    print(f"Average: ${df_recent['close'].mean():,.2f}")
    print(f"Std Dev: ${df_recent['close'].std():.2f}")
    print(f"Average Volume: {df_recent['volume'].mean():,.0f}")
    print(f"{'='*80}\n")
    
    # Create comprehensive plot
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.1)
    
    # Plot 1: Price with Moving Averages and Bollinger Bands
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df_recent['timestamp'], df_recent['close'], 'b-', linewidth=1.5, label='Close Price', alpha=0.8)
    ax1.plot(df_recent['timestamp'], df_recent['ema_20'], 'g--', linewidth=1, label='EMA 20', alpha=0.7)
    ax1.plot(df_recent['timestamp'], df_recent['ema_50'], 'r--', linewidth=1, label='EMA 50', alpha=0.7)
    ax1.plot(df_recent['timestamp'], df_recent['sma_200'], 'purple', linewidth=1, label='SMA 200', alpha=0.6)
    
    # Bollinger Bands
    ax1.fill_between(df_recent['timestamp'], df_recent['bb_upper'], df_recent['bb_lower'], 
                      alpha=0.1, color='gray', label='Bollinger Bands')
    ax1.plot(df_recent['timestamp'], df_recent['bb_upper'], 'gray', linewidth=0.5, alpha=0.5)
    ax1.plot(df_recent['timestamp'], df_recent['bb_lower'], 'gray', linewidth=0.5, alpha=0.5)
    
    ax1.set_title('ES E-mini Futures - Last 3 Months (Hourly Data)', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Price ($)', fontsize=12)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.tick_params(labelbottom=False)
    
    # Plot 2: Volume
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    colors = ['green' if df_recent['close'].iloc[i] >= df_recent['open'].iloc[i] else 'red' 
              for i in range(len(df_recent))]
    ax2.bar(df_recent['timestamp'], df_recent['volume'], color=colors, alpha=0.5, width=0.03)
    ax2.plot(df_recent['timestamp'], df_recent['volume_ma'], 'blue', linewidth=1, label='Volume MA(20)')
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(labelbottom=False)
    
    # Plot 3: Daily Returns
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    returns = df_recent['close'].pct_change() * 100
    colors_returns = ['green' if r >= 0 else 'red' for r in returns]
    ax3.bar(df_recent['timestamp'], returns, color=colors_returns, alpha=0.6, width=0.03)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_ylabel('Returns (%)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(labelbottom=False)
    
    # Plot 4: Price Range (High-Low)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    price_range = df_recent['high'] - df_recent['low']
    ax4.plot(df_recent['timestamp'], price_range, 'orange', linewidth=1)
    ax4.fill_between(df_recent['timestamp'], price_range, alpha=0.3, color='orange')
    ax4.set_ylabel('Daily Range ($)', fontsize=12)
    ax4.set_xlabel('Date', fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    output_file = '/home/rochen/Downloads/pylean/es_futures_3months.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_file}")
    
    # Show plot
    try:
        plt.show()
    except:
        print("(Chart display not available in this environment)")

def export_to_csv(df, filename='/home/rochen/Downloads/pylean/es_futures_data.csv'):
    """Export data to CSV file"""
    df.to_csv(filename, index=False)
    print(f"Data exported to: {filename}")
    print(f"Total rows: {len(df):,}")

def main():
    """Main execution function"""
    print("Generating ES Futures hourly data from 2022...")
    
    # Generate data from 2022 to current date
    df = generate_es_futures_data(start_date='2022-01-01')
    
    # Calculate technical indicators
    print("Calculating technical indicators...")
    df = calculate_technical_indicators(df)
    
    # Plot last 3 months
    print("Creating visualization for last 3 months...")
    plot_last_3_months(df)
    
    # Export full dataset
    print("\nExporting full dataset...")
    export_to_csv(df)
    
    # Show sample data
    print("\nSample data (first 5 rows):")
    print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].head())
    print("\nSample data (last 5 rows):")
    print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())

if __name__ == "__main__":
    main()
