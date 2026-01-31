#!/usr/bin/env python3
"""
Analyze ES Futures Volatility by Year
Calculates daily move standard deviations and statistics by year
"""

import pandas as pd
import numpy as np

def calculate_yearly_volatility(df):
    """
    Calculate daily move standard deviations by year
    Starting from most recent year
    """
    print("\n" + "="*80)
    print("YEARLY PRICE RANGE ANALYSIS")
    print("="*80)
    
    # Create a copy and calculate daily changes
    df_analysis = df.copy()
    df_analysis['year'] = df_analysis['timestamp'].dt.year
    df_analysis['daily_change_points'] = df_analysis['close'].diff()
    df_analysis['daily_change_pct'] = df_analysis['close'].pct_change() * 100
    df_analysis['daily_range'] = df_analysis['high'] - df_analysis['low']
    
    # Group by year to get detailed stats including high/low dates
    yearly_details = {}
    for year in sorted(df_analysis['year'].unique(), reverse=True):
        year_data = df_analysis[df_analysis['year'] == year].copy()
        
        # Find high and low
        high_idx = year_data['high'].idxmax()
        low_idx = year_data['low'].idxmin()
        
        yearly_details[year] = {
            'open': year_data.iloc[0]['close'],
            'low': year_data.loc[low_idx, 'low'],
            'low_date': year_data.loc[low_idx, 'timestamp'],
            'high': year_data.loc[high_idx, 'high'],
            'high_date': year_data.loc[high_idx, 'timestamp'],
            'close': year_data.iloc[-1]['close'],
            'trading_days': len(year_data)
        }
    
    # PART 1: Price Range Analysis
    print("\nPart 1: PRICE EXTREMES BY YEAR")
    print(f"{'Year':<6}   {'Open':<10}   {'Low':<10}      {'Low Date':<12} {'High':<10}      {'High Date':<12} {'Close':<10}   {'Range(cls-opn)':<10}   {'YoY %':<10}")
    print("-" * 105)
    
    for year in sorted(yearly_details.keys(), reverse=True):
        details = yearly_details[year]
        yoy_change = ((details['close'] - details['open']) / details['open']) * 100
        close_open_range = details['close'] - details['open']
        
        print(f"{year:<6}   "
              f"{details['open']:>9,.0f}   "
              f"{details['low']:>9,.0f}      "
              f"{details['low_date'].strftime('%m-%d'):<12} "
              f"{details['high']:>9,.0f}      "
              f"{details['high_date'].strftime('%m-%d'):<12} "
              f"{details['close']:>9,.0f}   "
              f"{close_open_range:>+9,.0f}   "
              f"{yoy_change:>+8.1f}%")
    
    print("\nNOTE: Range = Close - Open (in points)")
    print("      YoY % = (Close - Open) / Open × 100")
    print("      Represents the percentage gain/loss from year start to year end")
    
    print("\n" + "="*80)
    
    # PART 2: Yearly Statistics
    print("\nPart 2: YEARLY STATISTICS")
    print("="*80)
    
    # Remove first row (NaN from diff)
    df_analysis = df_analysis.dropna()
    
    print(f"\n{'Year':<6} {'Days':<6} {'Up Days':<8} {'Down Days':<10} {'Hi-Lo':<12} {'Biggest Up':<18} {'Biggest Down':<19} {'Volatility':<12}")
    print("-" * 100)
    
    for year in sorted(df_analysis['year'].unique(), reverse=True):
        year_data = df_analysis[df_analysis['year'] == year].copy()
        
        trading_days = len(year_data)
        up_days = (year_data['daily_change_points'] > 0).sum()
        down_days = (year_data['daily_change_points'] < 0).sum()
        
        # Yearly high-low range
        high_low_range = year_data['high'].max() - year_data['low'].min()
        
        # Biggest single day moves with dates
        biggest_up_idx = year_data['daily_change_points'].idxmax()
        biggest_up = year_data.loc[biggest_up_idx, 'daily_change_points']
        biggest_up_date = year_data.loc[biggest_up_idx, 'timestamp'].strftime('%m-%d')
        
        biggest_down_idx = year_data['daily_change_points'].idxmin()
        biggest_down = year_data.loc[biggest_down_idx, 'daily_change_points']
        biggest_down_date = year_data.loc[biggest_down_idx, 'timestamp'].strftime('%m-%d')
        
        # Volatility (standard deviation)
        volatility = year_data['daily_change_points'].std()
        
        print(f"{year:<6} {trading_days:<6} "
              f"{up_days:<8} "
              f"{down_days:<10} "
              f"{high_low_range:>10,.0f} "
              f"{biggest_up:>+7.0f} {biggest_up_date:<6} "
              f"{biggest_down:>+8.0f} {biggest_down_date:<6} "
              f"{volatility:>10.0f}")
    
    print("\n" + "="*80)
    print("NOTES:")
    print("- Up/Down Days: Number of days price closed higher/lower than previous day")
    print("- High-Low: Total range from yearly low to yearly high (points)")
    print("- Biggest Up/Down: Largest single-day gain/loss (points)")
    print("- Volatility: Standard deviation of daily point changes")
    print("="*80 + "\n")
    
    # PART 3: Standard Deviation Ranges
    print("\nPart 3: EXPECTED DAILY MOVE RANGES (By Standard Deviation)")
    print("="*80)
    
    print(f"\n{'Year':<6}   {'1σ Range':<12}   {'Days':<8}   {'2σ Range':<12}   {'Days':<8}   {'3σ Range':<12}   {'Days':<8}")
    print("-" * 105)
    
    for year in sorted(df_analysis['year'].unique(), reverse=True):
        year_data = df_analysis[df_analysis['year'] == year].copy()
        volatility = year_data['daily_change_points'].std()
        
        # Calculate standard deviation ranges
        one_sigma = volatility
        two_sigma = volatility * 2
        three_sigma = volatility * 3
        
        # Count days falling within each range
        abs_changes = year_data['daily_change_points'].abs()
        days_1sigma = (abs_changes <= one_sigma).sum()
        days_2sigma = ((abs_changes > one_sigma) & (abs_changes <= two_sigma)).sum()
        days_3sigma = (abs_changes > two_sigma).sum()
        
        print(f"{year:<6}   "
              f"{one_sigma:>5.0f} pts      "
              f"{days_1sigma:<8}   "
              f"{two_sigma:>5.0f} pts      "
              f"{days_2sigma:<8}   "
              f"{three_sigma:>5.0f} pts      "
              f"{days_3sigma:<8}")
    
    print("\n" + "="*80)
    print("NOTES:")
    print("- 1σ (68%): 68% of daily moves fall within this range")
    print("- 2σ (95%): 95% of daily moves fall within this range")
    print("- 3σ (99.7%): 99.7% of daily moves fall within this range (extreme moves)")
    print("- Dollar values per 1 ES contract (multiplier = $50)")
    print("- Use these ranges to set stop losses and position sizes")
    print("="*80 + "\n")
    
    # PART 4: Extreme Moves Analysis (4σ and 5σ+)
    print("\nPart 4: EXTREME MOVES ANALYSIS (4σ and 5σ+ Days)")
    print("="*80)
    
    extreme_moves_list = []
    
    for year in sorted(df_analysis['year'].unique(), reverse=True):
        year_data = df_analysis[df_analysis['year'] == year].copy()
        volatility = year_data['daily_change_points'].std()
        
        abs_changes = year_data['daily_change_points'].abs()
        
        # Count extreme moves
        days_4sigma = ((abs_changes > volatility * 3) & (abs_changes <= volatility * 4)).sum()
        days_5sigma_plus = (abs_changes > volatility * 5).sum()
        
        # Get all moves beyond 3σ
        extreme_days = year_data[abs_changes > volatility * 3].copy()
        
        if len(extreme_days) > 0:
            print(f"\n{year}: {days_4sigma} days in 4σ range, {days_5sigma_plus} days beyond 5σ")
            print(f"{'Date':<12} {'Change':<12} {'Sigma Level':<12} {'Type':<10}")
            print("-" * 50)
            
            for idx, row in extreme_days.iterrows():
                change = row['daily_change_points']
                sigma_level = abs(change) / volatility
                move_type = "UP" if change > 0 else "DOWN"
                
                print(f"{row['timestamp'].strftime('%Y-%m-%d'):<12} {change:>+8.2f} pts  {sigma_level:>6.2f}σ       {move_type:<10}")
                
                # Store for CSV export
                extreme_moves_list.append({
                    'date': row['timestamp'].strftime('%Y-%m-%d'),
                    'year': year,
                    'change_points': change,
                    'sigma_level': sigma_level,
                    'direction': move_type,
                    'close': row['close']
                })
    
    # Export extreme moves to CSV
    if extreme_moves_list:
        extreme_df = pd.DataFrame(extreme_moves_list)
        extreme_df = extreme_df.sort_values('sigma_level', ascending=False)
        extreme_df.to_csv('/home/rochen/Downloads/pylean/es_extreme_moves.csv', index=False)
        print("\n" + "="*80)
        print(f"✓ Exported {len(extreme_moves_list)} extreme moves to: es_extreme_moves.csv")
        print("="*80 + "\n")
    
    print("\nNOTES:")
    print("- 4σ moves: Between 3σ and 4σ (very rare)")
    print("- 5σ+ moves: Beyond 5σ (extremely rare, black swan events)")
    print("- These are tail risk events that occur more often than normal distribution predicts")
    print("="*80 + "\n")

def main():
    """Run volatility analysis on existing ES futures data"""
    print("="*80)
    print("ES FUTURES VOLATILITY ANALYZER")
    print("="*80)
    
    # Load the ES futures data
    try:
        df = pd.read_csv('/home/rochen/Downloads/pylean/es_futures_actual_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        print(f"Loaded {len(df)} rows of ES futures data")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Calculate yearly volatility
        calculate_yearly_volatility(df)
        
    except FileNotFoundError:
        print("\nError: es_futures_actual_data.csv not found!")
        print("Please run get_es_futures_actual_data.py first to download the data.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
