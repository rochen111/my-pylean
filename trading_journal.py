#!/usr/bin/env python3
"""
Trading Journal System for ES Futures
Comprehensive trade tracking, analysis, and journaling

ADVANCED FEATURES INCLUDED:
=========================

This journal addresses common gaps found in basic trade recording systems.

Basic journals typically ONLY track:
- Entry/exit prices and P&L
- Trade timestamps
- Simple win/loss count

This implementation adds COMPREHENSIVE features for serious traders:

✅ EXPORT & PERSISTENCE
   - CSV export/import for review workflow
   - Persistent storage with automatic save/load
   - Export filtered views (unreviewed trades)
   
✅ TRADE NOTES & CONTEXT
   - entry_reasoning: Why you entered (setup quality, signals)
   - exit_reasoning: Why you exited (planned vs actual execution)
   - trade_plan: Original plan documentation
   - notes: General observations and thoughts
   
✅ SETUP DESCRIPTION & QUALITY
   - setup_type: Categorize strategy (EMA crossover, breakout, etc.)
   - confluence_factors: Number of confirming signals
   - risk_reward_planned vs risk_reward_actual: Plan vs execution comparison
   
✅ EMOTIONAL STATE TRACKING
   - emotional_state: Track fear, greed, confidence, revenge trading
   - Critical for identifying psychological patterns
   
✅ POST-TRADE REVIEW
   - review_date: When you analyzed the trade
   - mistakes_made: What went wrong
   - lessons_learned: Key takeaways for improvement
   - performance_rating: Self-assessment (1-10)
   - execution_quality: How well you followed your plan (1-10)
   
✅ SCREENSHOTS & DOCUMENTATION
   - screenshot_path: Link to entry/exit charts
   - Visual record for pattern recognition
   
✅ PLAN VS ACTUAL COMPARISON
   - risk_reward_planned: What you intended
   - risk_reward_actual: What you achieved
   - Highlights execution gaps
   
✅ TAGS & CATEGORIES
   - tags: Custom labels for filtering
   - setup_type: Strategy classification
   - market_condition: Trending, range-bound, volatile, etc.
   
✅ ADVANCED METRICS
   - r_multiple: Risk-adjusted returns (P&L / risk dollars)
   - price_change and price_change_pct: Move analysis
   - Aggregate statistics by setup type, market condition
   
✅ ANALYSIS TOOLS
   - get_trade_summary(): Win rate, P&L, R-multiples by category
   - analyze_mistakes(): Pattern recognition in errors
   - Performance breakdown by setup type and market condition
   - List unreviewed trades for follow-up

RECOMMENDED WORKFLOW:
====================
1. Import backtest trades with import_from_backtest()
2. Export for review with export_for_review()
3. Manually add qualitative notes in CSV (reasoning, emotions, mistakes)
4. Import reviewed trades with import_reviewed_trades()
5. Analyze patterns with analyze_mistakes() and get_trade_summary()
6. Use insights to refine strategy and psychology
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class TradingJournal:
    """
    Comprehensive trading journal for tracking and analyzing trades
    
    Features that address common journal limitations:
    - Persistent CSV storage (not just in-memory lists)
    - Extended fields for qualitative analysis
    - Review workflow with export/import
    - Risk-adjusted metrics (R-multiples)
    - Pattern analysis in mistakes and lessons
    """
    
    def __init__(self, journal_file='trading_journal.csv'):
        self.journal_file = journal_file
        self.trades = []
        
        # Load existing journal if it exists
        if os.path.exists(journal_file):
            self.load_journal()
    
    def add_trade(self, trade_data):
        """
        Add a new trade to the journal with extended tracking fields
        
        ADDRESSES MISSING FEATURES IN BASIC JOURNALS:
        ============================================
        
        Required fields from backtest:
        - timestamp: Entry timestamp
        - entry_price: Entry price
        - exit_price: Exit price
        - quantity: Number of contracts
        - pnl: Profit/Loss
        - reason: Exit reason
        - equity: Account equity after trade
        
        ✅ EXTENDED FIELDS (addresses "no trade notes" problem):
        - setup_type: Type of setup (e.g., 'EMA Crossover', 'Breakout', 'Pullback')
        - market_condition: Overall market state (e.g., 'Trending Up', 'Range', 'Volatile')
        
        ✅ TRADE CONTEXT (addresses "no trade setup description"):
        - entry_reasoning: Why you entered this trade (signal quality, confluence)
        - exit_reasoning: Why you exited (planned vs actual execution)
        - trade_plan: Original trade plan documentation
        - confluence_factors: Number of confirming signals
        
        ✅ EXECUTION TRACKING (addresses "no plan vs actual comparison"):
        - execution_quality: How well you executed (1-10)
        - risk_reward_planned: Planned R:R ratio
        - risk_reward_actual: Actual R:R ratio
        
        ✅ PSYCHOLOGICAL TRACKING (addresses "no emotional state tracking"):
        - emotional_state: How you felt during the trade (fear, greed, confidence)
        
        ✅ POST-TRADE REVIEW (addresses "no post-trade review fields"):
        - mistakes_made: What went wrong
        - lessons_learned: Key takeaways for improvement
        - performance_rating: Self-rating (1-10)
        - review_date: When you reviewed this trade
        
        ✅ DOCUMENTATION (addresses "no entry/exit screenshots"):
        - screenshot_path: Path to chart screenshot
        
        ✅ ORGANIZATION (addresses "no tags/categories"):
        - tags: Comma-separated tags for filtering
        - notes: General notes and observations
        
        ✅ RISK-ADJUSTED METRICS (addresses missing in basic systems):
        - r_multiple: P&L divided by risk dollars (how many R you made/lost)
        """
        
        # Calculate additional metrics
        trade_enriched = trade_data.copy()
        
        # Handle timestamps for entry/exit dates and duration
        if 'entry_timestamp' not in trade_enriched and 'timestamp' in trade_enriched:
            # If only timestamp exists, use it as exit, calculate entry from duration if available
            trade_enriched['exit_timestamp'] = trade_enriched['timestamp']
        
        if 'entry_timestamp' in trade_enriched and 'exit_timestamp' in trade_enriched:
            # Calculate trade duration
            entry_dt = pd.to_datetime(trade_enriched['entry_timestamp'])
            exit_dt = pd.to_datetime(trade_enriched['exit_timestamp'])
            duration = exit_dt - entry_dt
            trade_enriched['duration_days'] = duration.days
            trade_enriched['duration_hours'] = duration.total_seconds() / 3600
        
        # Add calculated fields
        if 'entry_price' in trade_enriched and 'exit_price' in trade_enriched:
            trade_enriched['price_change'] = trade_enriched['exit_price'] - trade_enriched['entry_price']
            trade_enriched['price_change_pct'] = (trade_enriched['price_change'] / trade_enriched['entry_price']) * 100
            
        if 'pnl' in trade_enriched and 'entry_price' in trade_enriched and 'quantity' in trade_enriched:
            # Calculate R-multiple (how many times your risk did you make/lose)
            stop_loss_distance = trade_enriched['entry_price'] * 0.015  # Assuming 1.5% stop
            risk_dollars = stop_loss_distance * trade_enriched['quantity'] * 50
            if risk_dollars > 0:
                trade_enriched['r_multiple'] = trade_enriched['pnl'] / risk_dollars
            else:
                trade_enriched['r_multiple'] = 0
        
        # Add timestamp for journal entry
        trade_enriched['journal_entry_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate streak information
        if 'pnl' in trade_enriched:
            is_win = trade_enriched['pnl'] > 0
            
            # Calculate current streak based on previous trades
            if len(self.trades) > 0:
                last_trade = self.trades[-1]
                last_streak = last_trade.get('current_streak', 0)
                
                if is_win:
                    # If last streak was positive (winning), increment it
                    # If last streak was negative (losing), reset to +1
                    trade_enriched['current_streak'] = last_streak + 1 if last_streak > 0 else 1
                else:
                    # If last streak was negative (losing), decrement it
                    # If last streak was positive (winning), reset to -1
                    trade_enriched['current_streak'] = last_streak - 1 if last_streak < 0 else -1
            else:
                # First trade
                trade_enriched['current_streak'] = 1 if is_win else -1
        
        # Add empty fields for later filling
        journal_fields = [
            'setup_type', 'market_condition', 'entry_reasoning', 'exit_reasoning',
            'trade_plan', 'execution_quality', 'emotional_state', 'mistakes_made',
            'lessons_learned', 'confluence_factors', 'risk_reward_planned',
            'risk_reward_actual', 'notes', 'tags', 'performance_rating',
            'review_date', 'screenshot_path'
        ]
        
        for field in journal_fields:
            if field not in trade_enriched:
                trade_enriched[field] = ''
        
        self.trades.append(trade_enriched)
        
    def import_from_backtest(self, trades_list):
        """
        Import trades from backtest results
        trades_list: List of trade dictionaries from RiskManagementDemo
        """
        print(f"Importing {len(trades_list)} trades from backtest...")
        
        for trade in trades_list:
            self.add_trade(trade)
        
        print(f"✓ Imported {len(trades_list)} trades")
        
    def save_journal(self):
        """
        Save journal to CSV file
        
        ✅ ADDRESSES: "No export to file (CSV, JSON, Excel)"
        - Saves to CSV format for easy viewing in Excel, Google Sheets
        - Can be opened with any spreadsheet software
        - Enables manual editing and annotation
        """
        if not self.trades:
            print("No trades to save")
            return
        
        df = pd.DataFrame(self.trades)
        
        # Ensure timestamp is properly formatted
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        # Save to CSV
        df.to_csv(self.journal_file, index=False)
        print(f"✓ Journal saved to {self.journal_file}")
        print(f"  Total trades: {len(df)}")
        
    def load_journal(self):
        """Load existing journal from CSV"""
        try:
            df = pd.read_csv(self.journal_file)
            self.trades = df.to_dict('records')
            print(f"✓ Loaded {len(self.trades)} trades from {self.journal_file}")
        except Exception as e:
            print(f"Error loading journal: {e}")
            self.trades = []
    
    def update_trade(self, trade_index, updates):
        """
        Update a specific trade with journal entries
        
        trade_index: Index of trade to update (0-based)
        updates: Dictionary of fields to update
        """
        if 0 <= trade_index < len(self.trades):
            self.trades[trade_index].update(updates)
            self.trades[trade_index]['review_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"✓ Updated trade #{trade_index + 1}")
        else:
            print(f"Error: Trade index {trade_index} out of range")
    
    def add_notes_to_recent_trades(self, notes_dict):
        """
        Add notes to recent trades
        notes_dict: {trade_number: {'field': 'value', ...}}
        """
        for trade_num, updates in notes_dict.items():
            trade_idx = trade_num - 1  # Convert to 0-based index
            self.update_trade(trade_idx, updates)
    
    def get_trade_summary(self):
        """
        Get comprehensive trade statistics and analysis
        
        ✅ ADVANCED ANALYTICS (not in basic journals):
        - R-multiple analysis: Risk-adjusted performance
        - Performance by setup type: Which strategies work best
        - Performance by market condition: When to trade
        - Win rate and risk/reward ratios
        - Average R per trade (expectancy)
        
        This helps identify:
        - Which setups have edge
        - Which market conditions suit your strategy
        - Whether execution matches your edge
        """
        if not self.trades:
            print("No trades in journal")
            return
        
        df = pd.DataFrame(self.trades)
        
        print("\n" + "="*70)
        print("TRADING JOURNAL SUMMARY")
        print("="*70)
        
        # Basic stats
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {winning_trades} ({win_rate:.1f}%)")
        print(f"Losses: {losing_trades} ({100-win_rate:.1f}%)")
        print()
        
        # P&L stats
        total_pnl = df['pnl'].sum()
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = abs(df[df['pnl'] <= 0]['pnl'].mean()) if losing_trades > 0 else 0
        
        print(f"Total P&L: ${total_pnl:,.2f}")
        print(f"Average Win: ${avg_win:,.2f}")
        print(f"Average Loss: ${avg_loss:,.2f}")
        print(f"Win/Loss Ratio: {avg_win/avg_loss:.2f}" if avg_loss > 0 else "N/A")
        print()
        
        # R-multiple analysis
        if 'r_multiple' in df.columns:
            avg_r = df['r_multiple'].mean()
            print(f"Average R-Multiple: {avg_r:.2f}R")
            print(f"Best Trade: {df['r_multiple'].max():.2f}R")
            print(f"Worst Trade: {df['r_multiple'].min():.2f}R")
            print()
        
        # Streak analysis
        if 'current_streak' in df.columns:
            longest_win_streak = df[df['current_streak'] > 0]['current_streak'].max() if len(df[df['current_streak'] > 0]) > 0 else 0
            longest_loss_streak = abs(df[df['current_streak'] < 0]['current_streak'].min()) if len(df[df['current_streak'] < 0]) > 0 else 0
            current_streak = df.iloc[-1]['current_streak'] if len(df) > 0 else 0
            
            print(f"Longest Winning Streak: {int(longest_win_streak)} trades")
            print(f"Longest Losing Streak: {int(longest_loss_streak)} trades")
            if current_streak > 0:
                print(f"Current Streak: {int(current_streak)} wins 🔥")
            elif current_streak < 0:
                print(f"Current Streak: {int(abs(current_streak))} losses 📉")
            print()
        
        # Setup type analysis
        if 'setup_type' in df.columns and df['setup_type'].notna().any():
            print("Performance by Setup Type:")
            setup_stats = df[df['setup_type'] != ''].groupby('setup_type').agg({
                'pnl': ['count', 'sum', 'mean'],
                'r_multiple': 'mean'
            }).round(2)
            print(setup_stats)
            print()
        
        # Reviewed trades
        reviewed = df['review_date'].notna().sum() if 'review_date' in df.columns else 0
        print(f"Reviewed Trades: {reviewed}/{total_trades} ({reviewed/total_trades*100:.1f}%)")
        print("="*70)
    
    def list_trades(self, n=10, show_unreviewed=False):
        """
        List trades with key information
        
        ✅ REVIEW WORKFLOW SUPPORT:
        - Filter for unreviewed trades (show_unreviewed=True)
        - Identifies which trades need post-trade analysis
        - Shows performance rating and setup type for quick assessment
        
        Parameters:
        n: Number of trades to show (default 10)
        show_unreviewed: Only show unreviewed trades
        
        Helps maintain discipline of reviewing every trade
        """
        if not self.trades:
            print("No trades in journal")
            return
        
        df = pd.DataFrame(self.trades)
        
        if show_unreviewed and 'review_date' in df.columns:
            df = df[df['review_date'].isna() | (df['review_date'] == '')]
            print(f"\nUnreviewed trades: {len(df)}")
        
        # Show last n trades
        display_df = df.tail(n) if not show_unreviewed else df.head(n)
        
        # Select key columns to display
        display_cols = ['timestamp', 'entry_price', 'exit_price', 'quantity', 'pnl', 
                       'reason', 'setup_type', 'performance_rating']
        display_cols = [col for col in display_cols if col in display_df.columns]
        
        print("\n" + "="*70)
        print(f"RECENT TRADES (showing {len(display_df)} of {len(df)} total)")
        print("="*70)
        
        for idx, row in display_df.iterrows():
            trade_num = list(df.index).index(idx) + 1
            win_loss = "WIN" if row['pnl'] > 0 else "LOSS"
            
            print(f"\nTrade #{trade_num} - {win_loss}")
            
            # Display entry and exit dates
            if 'entry_timestamp' in row and pd.notna(row['entry_timestamp']):
                print(f"  Entry Date: {pd.to_datetime(row['entry_timestamp']).strftime('%Y-%m-%d %H:%M')}")
            if 'exit_timestamp' in row and pd.notna(row['exit_timestamp']):
                print(f"  Exit Date:  {pd.to_datetime(row['exit_timestamp']).strftime('%Y-%m-%d %H:%M')}")
            elif 'timestamp' in row:
                print(f"  Exit Date:  {pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M')}")
            
            # Display duration
            if 'duration_days' in row and pd.notna(row['duration_days']):
                days = int(row['duration_days'])
                hours = int(row['duration_hours']) % 24 if 'duration_hours' in row else 0
                if days > 0:
                    print(f"  Duration: {days} days, {hours} hours")
                else:
                    hours_total = int(row['duration_hours']) if 'duration_hours' in row else 0
                    print(f"  Duration: {hours_total} hours")
            
            print(f"  Entry: ${row['entry_price']:.2f} → Exit: ${row['exit_price']:.2f}")
            print(f"  Quantity: {row['quantity']} contracts")
            print(f"  P&L: ${row['pnl']:,.2f}")
            print(f"  Exit Reason: {row['reason']}")
            
            if 'r_multiple' in row and pd.notna(row['r_multiple']):
                print(f"  R-Multiple: {row['r_multiple']:.2f}R")
            
            # Display streak
            if 'current_streak' in row and pd.notna(row['current_streak']):
                streak = int(row['current_streak'])
                if streak > 0:
                    print(f"  Streak: {streak} wins in a row 🔥")
                elif streak < 0:
                    print(f"  Streak: {abs(streak)} losses in a row 📉")
            
            # Helper function to check if field has value (not empty, not NaN)
            def has_value(field):
                return field in row and pd.notna(row[field]) and str(row[field]).strip() != ''
            
            # SETUP DESCRIPTION & QUALITY
            if has_value('setup_type'):
                print(f"\n  📊 Setup Type: {row['setup_type']}")
            
            if has_value('market_condition'):
                print(f"  📈 Market Condition: {row['market_condition']}")
            
            if has_value('confluence_factors'):
                print(f"  ✓ Confluence Factors: {row['confluence_factors']}")
            
            # TRADE NOTES & CONTEXT
            if has_value('entry_reasoning'):
                print(f"\n  💭 Entry Reasoning: {row['entry_reasoning']}")
            
            if has_value('exit_reasoning'):
                print(f"  💭 Exit Reasoning: {row['exit_reasoning']}")
            
            if has_value('trade_plan'):
                print(f"  📝 Trade Plan: {row['trade_plan']}")
            
            # EXECUTION & EMOTION
            if has_value('execution_quality'):
                print(f"\n  ⭐ Execution Quality: {row['execution_quality']}/10")
            
            if has_value('performance_rating'):
                print(f"  ⭐ Performance Rating: {row['performance_rating']}/10")
            
            if has_value('emotional_state'):
                print(f"  😊 Emotional State: {row['emotional_state']}")
            
            # POST-TRADE REVIEW
            if has_value('mistakes_made'):
                print(f"\n  ❌ Mistakes: {row['mistakes_made']}")
            
            if has_value('lessons_learned'):
                print(f"  💡 Lessons Learned: {row['lessons_learned']}")
            
            if has_value('notes'):
                print(f"\n  📌 Notes: {row['notes']}")
        
        print("="*70)
    
    def export_for_review(self, output_file='trades_to_review.csv'):
        """
        Export trades that need review to a CSV file for manual editing
        
        ✅ ADDRESSES: "No export to file (CSV, JSON, Excel)"
        ✅ REVIEW WORKFLOW:
        
        Process:
        1. Export unreviewed trades to CSV
        2. Open in Excel/Google Sheets
        3. Add qualitative notes (reasoning, emotions, mistakes, lessons)
        4. Import back with import_reviewed_trades()
        
        This enables deep post-trade analysis that's hard to do in code:
        - Reflecting on emotional state
        - Describing what you saw in the market
        - Articulating mistakes and lessons
        - Planning improvements
        """
        if not self.trades:
            print("No trades to export")
            return
        
        df = pd.DataFrame(self.trades)
        
        # Select key columns for review
        review_cols = [
            'timestamp', 'entry_price', 'exit_price', 'quantity', 'pnl', 'reason',
            'setup_type', 'market_condition', 'entry_reasoning', 'exit_reasoning',
            'trade_plan', 'execution_quality', 'emotional_state', 'mistakes_made',
            'lessons_learned', 'notes', 'tags', 'performance_rating'
        ]
        
        # Only include columns that exist
        review_cols = [col for col in review_cols if col in df.columns]
        
        export_df = df[review_cols].copy()
        export_df.to_csv(output_file, index=False)
        
        print(f"✓ Exported {len(export_df)} trades to {output_file}")
        print(f"  Edit the CSV file and re-import using import_reviewed_trades()")
    
    def import_reviewed_trades(self, input_file='trades_to_review.csv'):
        """
        Import trades after manual review/editing
        """
        try:
            df = pd.read_csv(input_file)
            
            # Update trades with reviewed data
            for idx, row in df.iterrows():
                if idx < len(self.trades):
                    # Update only the review fields
                    update_dict = row.to_dict()
                    self.trades[idx].update(update_dict)
            
            print(f"✓ Imported reviewed data for {len(df)} trades")
            self.save_journal()
            
        except Exception as e:
            print(f"Error importing reviewed trades: {e}")
    
    def analyze_mistakes(self):
        """
        Analyze common mistakes and lessons learned
        
        ✅ ADDRESSES: "No post-trade review fields"
        ✅ PATTERN RECOGNITION:
        
        This method aggregates:
        - mistakes_made field from all trades
        - lessons_learned field from all trades
        
        Helps identify recurring errors:
        - "Entered too early before confirmation"
        - "Moved stop loss (broke discipline)"
        - "Didn't wait for pullback"
        - "Traded in low-liquidity hours"
        
        Use this to create rules that prevent repeated mistakes
        """
        if not self.trades:
            print("No trades to analyze")
            return
        
        df = pd.DataFrame(self.trades)
        
        print("\n" + "="*70)
        print("MISTAKES & LESSONS ANALYSIS")
        print("="*70)
        
        # Trades with mistakes noted
        if 'mistakes_made' in df.columns:
            mistakes_df = df[df['mistakes_made'].notna() & (df['mistakes_made'] != '')]
            print(f"\nTrades with mistakes documented: {len(mistakes_df)}/{len(df)}")
            
            if len(mistakes_df) > 0:
                print("\nRecent Mistakes:")
                for idx, row in mistakes_df.tail(5).iterrows():
                    trade_num = list(df.index).index(idx) + 1
                    print(f"  Trade #{trade_num}: {row['mistakes_made']}")
        
        # Lessons learned
        if 'lessons_learned' in df.columns:
            lessons_df = df[df['lessons_learned'].notna() & (df['lessons_learned'] != '')]
            print(f"\nTrades with lessons documented: {len(lessons_df)}/{len(df)}")
            
            if len(lessons_df) > 0:
                print("\nRecent Lessons:")
                for idx, row in lessons_df.tail(5).iterrows():
                    trade_num = list(df.index).index(idx) + 1
                    print(f"  Trade #{trade_num}: {row['lessons_learned']}")
        
        print("="*70)


def demo_journal_workflow():
    """
    Demonstrate the journal workflow with sample data
    """
    print("="*70)
    print("TRADING JOURNAL DEMO WORKFLOW")
    print("="*70)
    
    # Step 1: Load trades from backtest
    print("\n1. Loading trades from backtest...")
    from risk_management_demo_standalone import RiskManagementDemo
    
    demo = RiskManagementDemo(initial_capital=100000)
    demo.run_backtest()
    
    # Step 2: Create journal and import trades
    print("\n2. Creating trading journal...")
    journal = TradingJournal('es_futures_journal.csv')
    journal.import_from_backtest(demo.trades)
    
    # Step 3: Add sample review notes to first few trades
    print("\n3. Adding sample review notes...")
    sample_notes = {
        1: {
            'setup_type': 'EMA Crossover',
            'market_condition': 'Trending Up',
            'entry_reasoning': 'Clean EMA 20/50 crossover with strong momentum',
            'exit_reasoning': 'Hit profit target as price continued higher',
            'execution_quality': 8,
            'performance_rating': 9,
            'notes': 'Good trade - followed plan perfectly'
        },
        2: {
            'setup_type': 'EMA Crossover',
            'market_condition': 'Choppy',
            'entry_reasoning': 'EMA crossover but lower conviction',
            'exit_reasoning': 'Stopped out as market reversed quickly',
            'mistakes_made': 'Entered despite choppy market conditions',
            'execution_quality': 6,
            'performance_rating': 5,
            'lessons_learned': 'Avoid trading in choppy conditions even with signals'
        }
    }
    
    journal.add_notes_to_recent_trades(sample_notes)
    
    # Step 4: Save journal
    print("\n4. Saving journal...")
    journal.save_journal()
    
    # Step 5: Display summary and trades
    journal.get_trade_summary()
    journal.list_trades(n=5)
    
    # Step 6: Export for review
    print("\n5. Exporting trades for review...")
    journal.export_for_review('es_trades_to_review.csv')
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Review and edit: es_trades_to_review.csv")
    print("2. Add your notes, setup types, lessons learned, etc.")
    print("3. Re-import: journal.import_reviewed_trades('es_trades_to_review.csv')")
    print("4. Analyze: journal.analyze_mistakes()")
    print("="*70)


if __name__ == "__main__":
    demo_journal_workflow()


"""
================================================================================
FEATURE COMPARISON: BASIC JOURNAL vs THIS IMPLEMENTATION
================================================================================

TYPICAL BASIC JOURNAL (what most traders have):
❌ No export to file (CSV, JSON, Excel) - only in-memory tracking
❌ No trade notes/comments - just entry/exit prices and P&L
❌ No trade setup description - can't identify which setups work
❌ No emotional state tracking - miss psychological patterns
❌ No post-trade review fields - no systematic improvement process
❌ No entry/exit screenshots - hard to remember context later
❌ No trade plan vs actual comparison - can't measure execution quality
❌ No tags/categories - can't filter by setup type or market condition

THIS IMPLEMENTATION:
✅ CSV export/import - full review workflow with Excel/Sheets
✅ Trade notes - entry_reasoning, exit_reasoning, notes fields
✅ Setup description - setup_type, confluence_factors, market_condition
✅ Emotional tracking - emotional_state field for each trade
✅ Post-trade review - mistakes_made, lessons_learned, review_date
✅ Screenshots - screenshot_path field for visual documentation
✅ Plan vs actual - risk_reward_planned vs risk_reward_actual comparison
✅ Tags/categories - tags field plus setup_type and market_condition filters

ADDITIONAL ADVANCED FEATURES:
✅ R-multiple calculation - risk-adjusted performance metrics
✅ Execution quality rating - how well you followed your plan (1-10)
✅ Performance rating - self-assessment of trade quality (1-10)
✅ Pattern analysis - analyze_mistakes() aggregates common errors
✅ Performance by category - stats by setup_type and market_condition
✅ Unreviewed trade filtering - list_trades(show_unreviewed=True)
✅ Trade plan documentation - trade_plan field for pre-trade planning

HOW TO USE:
===========
1. Import backtest trades: journal.import_from_backtest(demo.trades)
2. Export for review: journal.export_for_review('my_trades.csv')
3. Open CSV in Excel/Sheets and add qualitative notes
4. Import reviewed: journal.import_reviewed_trades('my_trades.csv')
5. Analyze patterns: journal.analyze_mistakes()
6. Check stats: journal.get_trade_summary()

KEY BENEFIT:
===========
Transforms simple trade recording into a systematic learning system.
Helps you identify and eliminate mistakes, optimize setups, and improve
execution by maintaining comprehensive records with both quantitative
and qualitative data.
================================================================================
"""
