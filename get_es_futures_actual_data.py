#!/usr/bin/env python3
"""
Download and plot ES Futures daily data from Investing.com
Displays the last 365 days of real historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import requests
from bs4 import BeautifulSoup
import time

def load_es_futures_data():
    """
    Download ES futures daily data from multiple sources
    Priority: FRED -> Stooq -> Manual CSV -> Sample data
    """
    print("Attempting to download S&P 500 Futures data...")
    
    # Try 1: FRED (Federal Reserve Economic Data)
    try:
        print("\n1. Trying FRED (Federal Reserve)...")
        import urllib.request
        import ssl
        from io import StringIO
        import base64
        
        # FRED series for S&P 500 index (close proxy for futures)
        # SP500 is the S&P 500 Index daily close
        series_id = "SP500"
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        
        # Setup proxy with authentication
        proxy_user = 'rochen'
        proxy_pass = 'Myheaven>9?L8x-10'
        proxy_url = f'http://{proxy_user}:{proxy_pass}@proxy.westernasset.com:8080'
        
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })
        
        auth_str = f'{proxy_user}:{proxy_pass}'.encode('utf-8')
        base64_auth = base64.b64encode(auth_str).decode('ascii')
        
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
        
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Proxy-Authorization': f'Basic {base64_auth}'
        })
        
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            data = response.read().decode('utf-8')
        
        df = pd.read_csv(StringIO(data))
        print(f"FRED columns: {df.columns.tolist()}")
        
        # FRED format: observation_date, SP500 (or DATE, SP500)
        if 'observation_date' in df.columns:
            df = df.rename(columns={'observation_date': 'timestamp', 'SP500': 'close'})
        elif 'DATE' in df.columns:
            df = df.rename(columns={'DATE': 'timestamp', 'SP500': 'close'})
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Remove rows with missing data (marked as '.')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna()
        
        # Create OHLC from close (approximate)
        df['open'] = df['close']
        df['high'] = df['close'] * 1.005  # Approximate daily high
        df['low'] = df['close'] * 0.995   # Approximate daily low
        df['volume'] = 0  # FRED doesn't provide volume
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        if len(df) > 100:  # Sanity check
            print(f"✓ Success! Downloaded {len(df)} rows from FRED")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print("Note: Using S&P 500 Index as proxy (OHLC approximated from close)")
            return df
        
    except Exception as e:
        print(f"✗ FRED failed: {e}")
    
    # Try 2: Stooq.com - simplest, no auth required
    try:
        print("\n2. Trying Stooq.com...")
        import urllib.request
        import ssl
        from io import StringIO
        
        # Stooq URL for ES futures
        url = "https://stooq.com/q/d/l/?s=es.f&i=d"
        
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            data = response.read().decode('utf-8')
        
        df = pd.read_csv(StringIO(data))
        
        # Stooq format: Date, Open, High, Low, Close, Volume
        df = df.rename(columns={
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.dropna()
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        if len(df) > 100:  # Sanity check
            print(f"✓ Success! Downloaded {len(df)} rows from Stooq")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            return df
        
    except Exception as e:
        print(f"✗ Stooq failed: {e}")
    
    # Try 3: Load from manually downloaded CSV files
    csv_files = [
        '/home/rochen/Downloads/pylean/sp500_futures_historical.csv',
        '/home/rochen/Downloads/pylean/es_futures_data.csv',
        '/home/rochen/Downloads/sp500_futures_historical.csv',
        '/home/rochen/Downloads/ES=F.csv'
    ]
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"\n2. Found CSV file: {csv_file}")
            try:
                df = pd.read_csv(csv_file)
                print(f"Columns: {df.columns.tolist()}")
                
                # Try to identify columns
                column_mapping = {}
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'date' in col_lower or 'time' in col_lower:
                        column_mapping[col] = 'timestamp'
                    elif 'open' in col_lower:
                        column_mapping[col] = 'open'
                    elif 'high' in col_lower:
                        column_mapping[col] = 'high'
                    elif 'low' in col_lower:
                        column_mapping[col] = 'low'
                    elif 'close' in col_lower or 'price' in col_lower:
                        column_mapping[col] = 'close'
                    elif 'vol' in col_lower:
                        column_mapping[col] = 'volume'
                
                df = df.rename(columns=column_mapping)
                
                if 'timestamp' in df.columns and 'close' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    df['close'] = pd.to_numeric(df['close'], errors='coerce')
                    df = df.dropna(subset=['timestamp', 'close'])
                    
                    # Handle volume if present
                    if 'volume' in df.columns:
                        def parse_volume(vol_str):
                            if pd.isna(vol_str) or vol_str == '-':
                                return 0
                            vol_str = str(vol_str).replace(',', '')
                            if 'K' in vol_str:
                                return float(vol_str.replace('K', '')) * 1000
                            elif 'M' in vol_str:
                                return float(vol_str.replace('M', '')) * 1000000
                            elif 'B' in vol_str:
                                return float(vol_str.replace('B', '')) * 1000000000
                            try:
                                return float(vol_str)
                            except:
                                return 0
                        df['volume'] = df['volume'].apply(parse_volume)
                    else:
                        df['volume'] = 0
                    
                    # Fill missing OHLC with close price if needed
                    for col in ['open', 'high', 'low']:
                        if col not in df.columns:
                            df[col] = df['close']
                        else:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Create approximate OHLC if only close is available
                    if df['open'].isna().all():
                        df['open'] = df['close']
                        df['high'] = df['close'] * 1.005
                        df['low'] = df['close'] * 0.995
                    
                    df = df.dropna(subset=['timestamp', 'close'])
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    print(f"✓ Success! Loaded {len(df)} rows from CSV")
                    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                    return df
                    
            except Exception as e:
                print(f"✗ Failed to load {csv_file}: {e}")
                continue
    
    # If all attempts failed, raise error
    print("\n✗ All download attempts failed!")
    print("\nTo get REAL data, download manually:")
    print("1. Visit: https://fred.stlouisfed.org/series/SP500")
    print("2. Or: https://stooq.com/q/d/?s=es.f")
    print("3. Or: https://finance.yahoo.com/quote/ES%3DF/history/")
    print("4. Download CSV and save as: /home/rochen/Downloads/pylean/sp500_futures_historical.csv")
    print("5. Run this script again")
    print("="*80 + "\n")
    
    raise Exception("Failed to download data from any source. Please download manually.")

def calculate_technical_indicators(df):
    """Add technical indicators to the dataframe"""
    print("Calculating technical indicators...")
    
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
    
    # ATR (Average True Range) - 10 day
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr_10'] = df['true_range'].rolling(window=10).mean()
    
    # Clean up temporary columns
    df = df.drop(['prev_close', 'tr1', 'tr2', 'tr3', 'true_range'], axis=1)
    
    return df

def identify_peaks_and_bottoms(df, distance=10, prominence=None):
    """Identify peaks and bottoms in the price data"""
    from scipy.signal import find_peaks
    
    # Find peaks (local maxima)
    if prominence is None:
        # Use more sensitive prominence: 0.2x standard deviation instead of 0.5x
        prominence = df['close'].std() * 0.2
    
    peaks, peak_properties = find_peaks(df['close'].values, distance=distance, prominence=prominence)
    bottoms, bottom_properties = find_peaks(-df['close'].values, distance=distance, prominence=prominence)
    
    # Create columns to mark peaks and bottoms
    df['is_peak'] = False
    df['is_bottom'] = False
    df.loc[peaks, 'is_peak'] = True
    df.loc[bottoms, 'is_bottom'] = True
    
    print(f"\nIdentified {len(peaks)} peaks and {len(bottoms)} bottoms")
    print(f"Parameters: distance={distance} days, prominence=${prominence:.2f}")
    
    return df, peaks, bottoms

def plot_last_3_months(df):
    """Plot all available data"""
    
    # Use all data
    df_recent = df.copy()
    
    if len(df_recent) == 0:
        print("No data available!")
        return
    
    # Identify peaks and bottoms with more sensitive parameters
    # Reduce distance to capture more peaks, reduce prominence for smaller swings
    df_recent, peaks, bottoms = identify_peaks_and_bottoms(df_recent, distance=10, prominence=None)
    
    print(f"\n{'='*80}")
    print(f"S&P 500 FUTURES DATA ANALYSIS (INVESTING.COM)")
    print(f"{'='*80}")
    print(f"Total data points: {len(df):,}")
    print(f"Full date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"\nAll Data:")
    print(f"Data points: {len(df_recent):,}")
    print(f"Date range: {df_recent['timestamp'].min()} to {df_recent['timestamp'].max()}")
    print(f"\nPrice Statistics (All Data):")
    print(f"Opening Price: ${df_recent['close'].iloc[0]:,.2f}")
    print(f"Closing Price: ${df_recent['close'].iloc[-1]:,.2f}")
    change = df_recent['close'].iloc[-1] - df_recent['close'].iloc[0]
    change_pct = (df_recent['close'].iloc[-1] / df_recent['close'].iloc[0] - 1) * 100
    print(f"Change: ${change:,.2f} ({change_pct:+.2f}%)")
    print(f"High: ${df_recent['high'].max():,.2f}")
    print(f"Low: ${df_recent['low'].min():,.2f}")
    print(f"Average: ${df_recent['close'].mean():,.2f}")
    print(f"Std Dev: ${df_recent['close'].std():.2f}")
    print(f"Average Volume: {df_recent['volume'].mean():,.0f}")
    print(f"{'='*80}\n")
    
    # Create chart with 2 subplots: price and ATR
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.1)
    ax = fig.add_subplot(gs[0])
    
    # Plot OHLC bars
    for i in range(len(df_recent)):
        date = df_recent['timestamp'].iloc[i]
        open_price = df_recent['open'].iloc[i]
        high = df_recent['high'].iloc[i]
        low = df_recent['low'].iloc[i]
        close = df_recent['close'].iloc[i]
        
        # Color: green if close >= open, red otherwise
        color = 'green' if close >= open_price else 'red'
        
        # Draw high-low line
        ax.plot([date, date], [low, high], color=color, linewidth=0.5, alpha=0.8)
        
        # Draw open-close bar
        bar_width = timedelta(days=0.6)
        ax.plot([date - bar_width/2, date + bar_width/2], [open_price, open_price], 
                color=color, linewidth=1, alpha=0.8)
        ax.plot([date - bar_width/2, date + bar_width/2], [close, close], 
                color=color, linewidth=1, alpha=0.8)
    
    # Plot moving averages
    ax.plot(df_recent['timestamp'], df_recent['ema_20'], 'g--', linewidth=1.5, label='EMA 20', alpha=0.7)
    ax.plot(df_recent['timestamp'], df_recent['ema_50'], 'r--', linewidth=1.5, label='EMA 50', alpha=0.7)
    ax.plot(df_recent['timestamp'], df_recent['sma_200'], 'purple', linewidth=1.5, label='SMA 200', alpha=0.6)
    
    # Bollinger Bands
    ax.fill_between(df_recent['timestamp'], df_recent['bb_upper'], df_recent['bb_lower'], 
                      alpha=0.1, color='gray', label='Bollinger Bands')
    ax.plot(df_recent['timestamp'], df_recent['bb_upper'], 'gray', linewidth=0.5, alpha=0.5)
    ax.plot(df_recent['timestamp'], df_recent['bb_lower'], 'gray', linewidth=0.5, alpha=0.5)
    
    # Mark peaks and bottoms
    peak_data = df_recent[df_recent['is_peak']]
    bottom_data = df_recent[df_recent['is_bottom']]
    
    ax.scatter(peak_data['timestamp'], peak_data['high'] * 1.01, 
               color='red', marker='v', s=100, label='Peaks', zorder=5, alpha=0.8)
    ax.scatter(bottom_data['timestamp'], bottom_data['low'] * 0.99, 
               color='green', marker='^', s=100, label='Bottoms', zorder=5, alpha=0.8)
    
    ax.set_title(f'S&P 500 Futures - All Data ({df_recent["timestamp"].min().year}-{df_recent["timestamp"].max().year})', fontsize=16, fontweight='bold')
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    # Collect all peak and bottom dates for x-axis ticks
    peak_bottom_dates = pd.concat([peak_data['timestamp'], bottom_data['timestamp']]).sort_values()
    
    # Hide x-axis labels on top chart
    ax.set_xticks(peak_bottom_dates)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.tick_params(labelbottom=False)
    
    # Plot 2: ATR (Average True Range)
    ax2 = fig.add_subplot(gs[1], sharex=ax)
    ax2.plot(df_recent['timestamp'], df_recent['atr_10'], 'purple', linewidth=1.5, label='ATR(10)')
    ax2.fill_between(df_recent['timestamp'], df_recent['atr_10'], alpha=0.3, color='purple')
    ax2.set_ylabel('ATR (10-day)', fontsize=12)
    ax2.set_xlabel('Peak/Bottom Dates', fontsize=12)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Show peak/bottom dates on bottom subplot x-axis
    ax2.set_xticks(peak_bottom_dates)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.tick_params(axis='x', rotation=90, labelsize=7)
    
    plt.tight_layout()
    
    # Save plot
    output_file = '/home/rochen/Downloads/pylean/es_futures_actual_3months.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_file}")
    
    # Show plot
    try:
        plt.show()
    except:
        print("(Chart display not available in this environment)")

def export_to_csv(df, filename='/home/rochen/Downloads/pylean/es_futures_actual_data.csv'):
    """Export data to CSV file"""
    df.to_csv(filename, index=False)
    print(f"\nData exported to: {filename}")
    print(f"Total rows: {len(df):,}")

def main():
    """Main execution function"""
    print("="*80)
    print("S&P 500 FUTURES DATA DOWNLOADER (Investing.com)")
    print("="*80)
    
    # Download ES futures data from Investing.com
    df = load_es_futures_data()
    
    if df is None or len(df) == 0:
        print("\nError: No data downloaded. Please check:")
        print("1. Internet connection is available")
        print("2. Investing.com website is accessible")
        print("3. BeautifulSoup4 is installed (pip install beautifulsoup4)")
        return
    
    # Calculate technical indicators
    print("\nCalculating technical indicators...")
    df = calculate_technical_indicators(df)
    
    # Plot all data
    print("\nCreating visualization for all available data...")
    plot_last_3_months(df)
    
    # Export full dataset
    print("\nExporting full dataset...")
    export_to_csv(df)
    
    # Show sample data
    print("\n" + "="*80)
    print("Sample data (first 5 rows):")
    print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].head())
    print("\nSample data (last 5 rows):")
    print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
    print("="*80)

if __name__ == "__main__":
    main()
