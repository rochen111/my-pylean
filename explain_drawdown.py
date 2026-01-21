#!/usr/bin/env python3
"""
Explain the difference between Max Drawdown and Total Return
"""

print("="*80)
print("UNDERSTANDING MAX DRAWDOWN vs TOTAL RETURN")
print("="*80)

print("\nKey Concepts:")
print("-"*80)
print("1. MAX DRAWDOWN = Measured from PEAK equity (highest point reached)")
print("2. TOTAL RETURN = Measured from INITIAL capital (starting point)")
print("")
print("These are DIFFERENT because the peak can be ABOVE the initial capital!")
print("-"*80)

# Recreate the equity progression from the trade output
initial_capital = 100000

trades = [
    ("2023-01-10 19:00", 710.71, "WIN"),
    ("2023-01-12 10:00", -3274.40, "LOSS"),
    ("2023-01-15 10:00", -3236.56, "LOSS"),
    ("2023-01-20 23:00", -3213.59, "LOSS"),
    ("2023-01-23 14:00", -3187.76, "LOSS"),
    ("2023-01-26 03:00", -3174.58, "LOSS"),
    ("2023-01-29 18:00", -3143.32, "LOSS"),
    ("2023-02-04 12:00", -3118.70, "LOSS"),
    ("2023-02-06 16:00", -3094.36, "LOSS"),
    ("2023-02-07 22:00", -3074.30, "LOSS"),
    ("2023-02-09 13:00", -3041.47, "LOSS"),
    ("2023-02-11 11:00", -3016.05, "LOSS"),
    ("2023-02-16 20:00", 6000.34, "WIN"),
    ("2023-02-19 01:00", 6181.89, "WIN"),
    ("2023-02-21 14:00", 6359.76, "WIN"),
    ("2023-02-28 06:00", 47.70, "WIN"),
    ("2023-03-02 11:00", -3272.52, "LOSS"),
    ("2023-03-04 12:00", -3242.15, "LOSS"),
    ("2023-03-07 00:00", -3222.61, "LOSS"),
    ("2023-03-13 03:00", -3197.87, "LOSS"),
    ("2023-03-15 14:00", -3172.52, "LOSS"),
    ("2023-03-19 06:00", -3145.31, "LOSS"),
    ("2023-03-25 10:00", -3119.97, "LOSS"),
    ("2023-07-14 23:00", 3903.60, "WIN"),  # Final exit
]

print("\n" + "="*80)
print("EQUITY PROGRESSION ANALYSIS")
print("="*80)

equity = initial_capital
peak_equity = initial_capital
max_drawdown_pct = 0

print(f"\n{'Trade':<6} {'Date':<20} {'P&L':<12} {'Equity':<15} {'Peak':<15} {'Drawdown %':<12} {'Status':<10}")
print("-"*100)

for i, (date, pnl, result) in enumerate(trades, 1):
    equity += pnl
    
    # Update peak
    if equity > peak_equity:
        peak_equity = equity
    
    # Calculate drawdown from peak
    current_drawdown = (peak_equity - equity) / peak_equity * 100
    
    # Track max drawdown
    if current_drawdown > max_drawdown_pct:
        max_drawdown_pct = current_drawdown
    
    # Check if max drawdown threshold hit
    status = ""
    if current_drawdown >= 50.0 and i < len(trades):  # 50% threshold
        status = "⚠ STOP!"
    elif result == "WIN":
        status = "✓ WIN"
    else:
        status = "✗ LOSS"
    
    print(f"{i:<6} {date:<20} ${pnl:>10.2f} ${equity:>13.2f} ${peak_equity:>13.2f} {current_drawdown:>10.2f}% {status:<10}")
    
    # Show when 50% drawdown is hit
    if current_drawdown >= 50.0 and i == 23:
        print("\n" + "="*100)
        print(">>> MAX DRAWDOWN OF 50% REACHED - TRADING STOPS HERE <<<")
        print("="*100)
        print(f"\nAt this point:")
        print(f"  Peak Equity:     ${peak_equity:,.2f}")
        print(f"  Current Equity:  ${equity:,.2f}")
        print(f"  Drawdown:        ${peak_equity - equity:,.2f} ({current_drawdown:.2f}% from peak)")
        print(f"  Initial Capital: ${initial_capital:,.2f}")
        print(f"  Total Return:    ${equity - initial_capital:,.2f} ({(equity - initial_capital)/initial_capital*100:.2f}% from initial)")
        print("="*100 + "\n")

print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

final_equity = equity
total_return = (final_equity - initial_capital) / initial_capital * 100

print(f"\nInitial Capital:       ${initial_capital:,.2f}")
print(f"Peak Equity Reached:   ${peak_equity:,.2f}  (+${peak_equity - initial_capital:,.2f} or +{(peak_equity - initial_capital)/initial_capital*100:.2f}%)")
print(f"Final Equity:          ${final_equity:,.2f}")
print(f"")
print(f"Total Return:          {total_return:.2f}%  (from initial ${initial_capital:,.2f})")
print(f"Max Drawdown:          {max_drawdown_pct:.2f}%  (from peak ${peak_equity:,.2f})")

print("\n" + "="*80)
print("WHY THE DIFFERENCE?")
print("="*80)
print(f"""
The algorithm stops when drawdown from PEAK reaches 50%, not from initial capital.

Here's what happened:

1. Started with:           ${initial_capital:,.2f}
2. Won some trades and reached PEAK of: ${peak_equity:,.2f}
3. Then losses brought equity down to:  ${final_equity:,.2f}
4. Drawdown from peak = (${peak_equity:,.2f} - ${final_equity:,.2f}) / ${peak_equity:,.2f} = {max_drawdown_pct:.2f}%
5. This exceeded the 50% threshold, so trading stopped

BUT the total return from initial capital is:
   (${final_equity:,.2f} - ${initial_capital:,.2f}) / ${initial_capital:,.2f} = {total_return:.2f}%

The LEAN algorithm uses 10% max drawdown, which would stop much earlier!
""")

print("="*80)
print("COMPARISON OF 10% vs 50% MAX DRAWDOWN")
print("="*80)

# Find where 10% drawdown would have been hit
equity = initial_capital
peak_equity = initial_capital

print("\nWith 10% Max Drawdown threshold:")
print("-"*80)

for i, (date, pnl, result) in enumerate(trades, 1):
    equity += pnl
    
    if equity > peak_equity:
        peak_equity = equity
    
    current_drawdown = (peak_equity - equity) / peak_equity * 100
    
    if current_drawdown >= 10.0:
        print(f"Trade #{i} on {date}")
        print(f"  Peak: ${peak_equity:,.2f}")
        print(f"  Current: ${equity:,.2f}")
        print(f"  Drawdown: {current_drawdown:.2f}%")
        print(f"  >>> 10% DRAWDOWN EXCEEDED - Would stop here!")
        print(f"  >>> Final loss would be: ${equity - initial_capital:,.2f} ({(equity - initial_capital)/initial_capital*100:.2f}%)")
        break

print("\n" + "="*80)
