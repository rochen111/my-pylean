#!/usr/bin/env python3
"""
Standalone Risk Management Demo - ES Futures Trading
Demonstrates risk and trade management without requiring Lean engine.
Uses simulated data and order execution.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

class RiskManagementDemo:
    """
    Demonstrates risk and trade management features for ES futures trading
    """
    
    def __init__(self, initial_capital=100000):
        # Account settings
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0
        self.entry_price = 0
        
        # Risk management parameters
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.stop_loss_percent = 0.015  # 1.5% stop loss
        self.take_profit_percent = 0.90  # 100% take profit (2:1 risk-reward)
        self.max_drawdown_percent = 0.50  # 50% max drawdown (higher to allow more trades)
        self.trailing_stop_percent = 0.02  # 2% trailing stop
        
        # Position tracking
        self.stop_loss_price = 0
        self.take_profit_price = 0
        self.highest_profit_price = 0
        
        # Statistics
        self.trades = []
        self.equity_curve = []
        self.peak_equity = initial_capital
        self.max_drawdown = 0
        
    def load_real_es_data(self):
        """Load real ES futures data from CSV"""
        try:
            # Load the actual ES futures data
            df = pd.read_csv('/home/rochen/Downloads/pylean/es_futures_actual_data.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Select required columns
            df = df[['timestamp', 'close', 'high', 'low', 'ema_20', 'ema_50']].copy()
            df = df.rename(columns={'ema_20': 'ema_fast', 'ema_50': 'ema_slow'})
            
            # Remove any NaN values
            df = df.dropna()
            
            print(f"Loaded {len(df)} days of real ES futures data")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            print(f"Error loading real data: {e}")
            print("Falling back to simulated data...")
            return self.generate_sample_data()
    
    def generate_sample_data(self, days=180):
        """Generate sample ES futures price data"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=days*390, freq='1min')  # 390 minutes per trading day
        
        # Simulate price with stronger trend and better signals
        t = np.linspace(0, 8*np.pi, len(dates))  # More cycles for more crossovers
        trend = 4200 + 150 * np.sin(t) + 80 * np.sin(2*t) + 40 * np.sin(3*t)  # Multiple cycles
        noise = np.random.normal(0, 8, len(dates))  # Reduced noise for cleaner signals
        
        price = trend + noise
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'close': price,
            'high': price + np.abs(np.random.normal(2, 1, len(dates))),
            'low': price - np.abs(np.random.normal(2, 1, len(dates))),
        })
        
        # Add moving averages for signals
        df['ema_fast'] = df['close'].ewm(span=5).mean()  # Very fast EMA for more frequent signals
        df['ema_slow'] = df['close'].ewm(span=15).mean()  # Short slow EMA for more crossovers
        
        return df
    
    def calculate_position_size(self, price):
        """Calculate position size based on risk per trade"""
        current_equity = self.cash + (self.position * (price - self.entry_price) * 50 if self.position else 0)
        risk_amount = current_equity * self.risk_per_trade
        
        # Dollar risk per contract (ES multiplier is 50)
        stop_distance = price * self.stop_loss_percent
        risk_per_contract = stop_distance * 50
        
        # Position size (minimum 1, maximum 3 for demo)
        position_size = max(1, int(risk_amount / risk_per_contract))
        return min(position_size, 3)
    
    def enter_long(self, price, timestamp):
        """Enter a long position"""
        quantity = self.calculate_position_size(price)
        
        if quantity == 0:
            return False
        
        # Calculate costs (use margin, not full contract value)
        # ES futures use margin, typically around $12,000 per contract
        margin_required = 12000 * quantity
        
        if margin_required > self.cash:
            return False
        
        self.position = quantity
        self.entry_price = price
        self.cash -= margin_required  # Deduct margin, not full contract value
        
        # Set stop loss and take profit
        self.stop_loss_price = price * (1 - self.stop_loss_percent)
        self.take_profit_price = price * (1 + self.take_profit_percent)
        self.highest_profit_price = price
        
        print(f"\n[{timestamp.strftime('%Y-%m-%d %H:%M')}] LONG ENTRY")
        print(f"  Quantity: {quantity} contracts @ ${price:.2f}")
        print(f"  Stop Loss: ${self.stop_loss_price:.2f}")
        print(f"  Take Profit: ${self.take_profit_price:.2f}")
        print(f"  Cash: ${self.cash:.2f}")
        
        return True
    
    def exit_position(self, price, timestamp, reason):
        """Exit current position"""
        if self.position == 0:
            return
        
        # Calculate P&L
        pnl = (price - self.entry_price) * self.position * 50
        
        # Return margin and add/subtract P&L
        margin_returned = 12000 * self.position
        self.cash += margin_returned + pnl
        
        # Record trade
        trade = {
            'timestamp': timestamp,
            'entry_price': self.entry_price,
            'exit_price': price,
            'quantity': self.position,
            'pnl': pnl,
            'reason': reason,
            'equity': self.cash
        }
        self.trades.append(trade)
        
        result = "WIN" if pnl > 0 else "LOSS"
        print(f"\n[{timestamp.strftime('%Y-%m-%d %H:%M')}] EXIT - {reason}")
        print(f"  {result}: ${pnl:.2f}")
        print(f"  Exit Price: ${price:.2f}")
        print(f"  Equity: ${self.cash:.2f}")
        
        # Reset position
        self.position = 0
        self.entry_price = 0
        self.stop_loss_price = 0
        self.take_profit_price = 0
    
    def update_trailing_stop(self, current_price):
        """Update trailing stop loss"""
        if self.position == 0:
            return
        
        # Track highest price for trailing stop
        if current_price > self.highest_profit_price:
            self.highest_profit_price = current_price
            
            # Calculate profit percentage
            profit_percent = (current_price - self.entry_price) / self.entry_price
            
            # Activate trailing stop if in profit
            if profit_percent > self.stop_loss_percent:
                new_stop = current_price * (1 - self.trailing_stop_percent)
                
                # Only move stop up
                if new_stop > self.stop_loss_price:
                    self.stop_loss_price = new_stop
    
    def check_exits(self, row):
        """Check if stop loss hit"""
        if self.position == 0:
            return False
        
        # Check stop loss
        if row['low'] <= self.stop_loss_price:
            self.exit_position(self.stop_loss_price, row['timestamp'], 'STOP LOSS')
            return True
        
        # No take profit - let winners run with trailing stop only
        
        return False
    
    def check_drawdown(self):
        """Check if max drawdown exceeded"""
        if self.cash > self.peak_equity:
            self.peak_equity = self.cash
        
        current_drawdown = (self.peak_equity - self.cash) / self.peak_equity
        
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        return current_drawdown >= self.max_drawdown_percent
    
    def run_backtest(self):
        """Run the backtest simulation"""
        print("="*70)
        print("ES FUTURES RISK MANAGEMENT DEMO - BACKTEST")
        print("="*70)
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Risk Per Trade: {self.risk_per_trade*100}%")
        print(f"Stop Loss: {self.stop_loss_percent*100}%")
        print(f"Take Profit: {self.take_profit_percent*100}%")
        print(f"Max Drawdown: {self.max_drawdown_percent*100}%")
        print("="*70)
        
        # Load real ES futures data
        df = self.load_real_es_data()
        
        # Use daily data (already daily in the CSV)
        df_daily = df.copy()
        
        # Run through data
        trades_checked = 0
        for idx, row in df_daily.iterrows():
            # Record equity
            current_equity = self.cash + (self.position * row['close'] * 50 if self.position else 0)
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'equity': current_equity
            })
            
            # Check for max drawdown
            if self.check_drawdown():
                print("\n" + "="*70)
                print("MAX DRAWDOWN EXCEEDED - STOPPING")
                print("="*70)
                break
            
            # If in position, check exits and trailing stop
            if self.position != 0:
                if self.check_exits(row):
                    continue
                self.update_trailing_stop(row['close'])
            else:
                # Look for entry signals (EMA crossover)
                if idx > 50:  # Need enough data for EMA to stabilize
                    prev_row = df_daily.iloc[idx - 1]
                    
                    # Check if EMAs exist and are valid
                    if (pd.notna(row['ema_fast']) and pd.notna(row['ema_slow']) and
                        pd.notna(prev_row['ema_fast']) and pd.notna(prev_row['ema_slow'])):
                        
                        # Long signal: fast EMA crosses above slow EMA
                        if (row['ema_fast'] > row['ema_slow'] and 
                            prev_row['ema_fast'] <= prev_row['ema_slow']):
                            self.enter_long(row['close'], row['timestamp'])
        
        # Print final statistics
        self.print_statistics()
        
        # Generate plots
        self.plot_results(df_daily)
    
    def print_statistics(self):
        """Print final backtest statistics"""
        print("\n" + "="*70)
        print("FINAL STATISTICS")
        print("="*70)
        
        if not self.trades:
            print("No trades executed")
            return
        
        trades_df = pd.DataFrame(self.trades)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] <= 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].mean()) if losing_trades > 0 else 0
        
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        final_equity = self.cash
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {winning_trades}")
        print(f"Losing Trades: {losing_trades}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"")
        print(f"Average Win: ${avg_win:.2f}")
        print(f"Average Loss: ${avg_loss:.2f}")
        print(f"Risk/Reward Ratio: {risk_reward_ratio:.2f}")
        print(f"")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Equity: ${final_equity:,.2f}")
        print(f"Total P&L: ${total_pnl:,.2f}")
        print(f"Total Return: {total_return:.2f}%")
        print(f"Max Drawdown: {self.max_drawdown*100:.2f}%")
        print("="*70)
    
    def plot_results(self, df):
        """Generate result plots"""
        if not self.trades:
            print("\nNo trades to plot")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        
        # Plot 1: Equity Curve
        equity_df = pd.DataFrame(self.equity_curve)
        axes[0].plot(equity_df['timestamp'], equity_df['equity'], label='Equity', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
        axes[0].set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('Equity ($)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Price with Entry/Exit points
        axes[1].plot(df['timestamp'], df['close'], label='ES Price', alpha=0.7)
        axes[1].plot(df['timestamp'], df['ema_fast'], label='EMA Fast (20)', alpha=0.5)
        axes[1].plot(df['timestamp'], df['ema_slow'], label='EMA Slow (50)', alpha=0.5)
        
        trades_df = pd.DataFrame(self.trades)
        for _, trade in trades_df.iterrows():
            if trade['pnl'] > 0:
                color = 'green'
                marker = '^'
            else:
                color = 'red'
                marker = 'v'
            axes[1].scatter(trade['timestamp'], trade['exit_price'], color=color, marker=marker, s=100, zorder=5)
        
        axes[1].set_title('ES Futures Price with Trades', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('Price ($)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot 3: Trade P&L
        axes[2].bar(range(len(trades_df)), trades_df['pnl'], 
                    color=['green' if x > 0 else 'red' for x in trades_df['pnl']])
        axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[2].set_title('Trade Profit/Loss', fontsize=14, fontweight='bold')
        axes[2].set_xlabel('Trade Number')
        axes[2].set_ylabel('P&L ($)')
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        output_file = '/home/rochen/Downloads/pylean/risk_management_results.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\nResults chart saved to: {output_file}")
        
        try:
            plt.show()
        except:
            print("(Chart display not available in this environment)")

def main():
    """Run the risk management demo"""
    demo = RiskManagementDemo(initial_capital=100000)
    demo.run_backtest()

if __name__ == "__main__":
    main()
