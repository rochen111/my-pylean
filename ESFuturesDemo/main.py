# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from AlgorithmImports import *

class ESFuturesRiskManagementDemo(QCAlgorithm):
    """
    Demonstrates risk and trade management features using ES (S&P 500 E-mini) futures.
    
    Features demonstrated:
    1. Position sizing based on portfolio risk
    2. Stop loss orders (fixed and trailing)
    3. Take profit targets
    4. Risk-reward ratio management
    5. Maximum drawdown monitoring
    6. Performance charting and plotting
    7. Trade statistics tracking
    """

    def initialize(self):
        # Set backtest period
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2023, 6, 30)
        self.set_cash(100000)
        
        # Risk management parameters
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.stop_loss_percent = 0.015  # 1.5% stop loss
        self.take_profit_percent = 0.03  # 3% take profit (2:1 risk-reward)
        self.max_drawdown_percent = 0.10  # 10% max drawdown
        self.trailing_stop_percent = 0.02  # 2% trailing stop after profit
        
        # Add ES futures
        self.es_future = self.add_future(Futures.Indices.SP_500_E_MINI, Resolution.MINUTE)
        self.es_future.set_filter(timedelta(0), timedelta(90))  # Front month
        
        # Technical indicators for entry signals
        self.ema_fast = None
        self.ema_slow = None
        self.atr = None
        
        # Track active position
        self.active_contract = None
        self.entry_price = 0
        self.stop_loss_ticket = None
        self.take_profit_ticket = None
        self.position_side = 0  # 1 for long, -1 for short, 0 for flat
        self.highest_profit = 0
        
        # Track statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0
        self.max_drawdown = 0
        self.peak_portfolio_value = self.portfolio.total_portfolio_value
        
        # Setup charting
        self.setup_charts()
        
        # Warm up indicators
        self.set_warm_up(50, Resolution.DAILY)

    def setup_charts(self):
        """Setup custom charts for visualization"""
        
        # Portfolio value chart
        portfolio_chart = Chart('Portfolio')
        portfolio_chart.add_series(Series('Value', SeriesType.LINE, 0))
        portfolio_chart.add_series(Series('Daily PnL', SeriesType.BAR, 1))
        portfolio_chart.add_series(Series('Drawdown %', SeriesType.LINE, 2))
        self.add_chart(portfolio_chart)
        
        # Trade management chart
        trade_chart = Chart('Trade Management')
        trade_chart.add_series(Series('Entry Price', SeriesType.SCATTER, 0))
        trade_chart.add_series(Series('Stop Loss', SeriesType.SCATTER, 0))
        trade_chart.add_series(Series('Take Profit', SeriesType.SCATTER, 0))
        trade_chart.add_series(Series('Current Price', SeriesType.LINE, 0))
        self.add_chart(trade_chart)
        
        # Risk metrics chart
        risk_chart = Chart('Risk Metrics')
        risk_chart.add_series(Series('Win Rate %', SeriesType.LINE, 0))
        risk_chart.add_series(Series('Risk Reward Ratio', SeriesType.LINE, 1))
        risk_chart.add_series(Series('Position Size', SeriesType.BAR, 2))
        self.add_chart(risk_chart)
        
        # Indicator chart
        indicator_chart = Chart('Indicators')
        indicator_chart.add_series(Series('EMA Fast', SeriesType.LINE, 0))
        indicator_chart.add_series(Series('EMA Slow', SeriesType.LINE, 0))
        indicator_chart.add_series(Series('ATR', SeriesType.LINE, 1))
        self.add_chart(indicator_chart)

    def on_data(self, data):
        """Handle incoming data and manage trades"""
        
        if self.is_warming_up:
            return
        
        # Check for max drawdown breach
        if self.check_max_drawdown():
            self.liquidate()
            self.quit("Maximum drawdown exceeded")
            return
        
        # Update charts with current data
        self.update_portfolio_charts()
        
        # Process futures chain
        for chain in data.future_chains.values():
            # Get front month contract
            contracts = [x for x in chain if x.expiry > self.time + timedelta(30)]
            if not contracts:
                continue
            
            front_contract = sorted(contracts, key=lambda x: x.expiry)[0]
            
            # Initialize indicators for this contract if needed
            if self.ema_fast is None or self.active_contract != front_contract.symbol:
                self.initialize_indicators(front_contract.symbol)
            
            # Check if we need to roll contract
            if self.active_contract and self.active_contract != front_contract.symbol:
                self.roll_contract(front_contract.symbol)
            
            self.active_contract = front_contract.symbol
            current_price = front_contract.last_price
            
            # Update indicator charts
            if self.ema_fast.is_ready and self.ema_slow.is_ready and self.atr.is_ready:
                self.plot('Indicators', 'EMA Fast', self.ema_fast.current.value)
                self.plot('Indicators', 'EMA Slow', self.ema_slow.current.value)
                self.plot('Indicators', 'ATR', self.atr.current.value)
            
            # Trade logic
            if self.position_side == 0:
                # Look for entry signal
                self.check_entry_signals(front_contract)
            else:
                # Manage existing position
                self.manage_position(front_contract)
                self.update_trade_charts(current_price)

    def initialize_indicators(self, symbol):
        """Initialize technical indicators for a contract"""
        self.ema_fast = self.ema(symbol, 20, Resolution.MINUTE)
        self.ema_slow = self.ema(symbol, 50, Resolution.MINUTE)
        self.atr = self.atr(symbol, 14, Resolution.MINUTE)
        
        # Warm up new indicators
        history = self.history[TradeBar](symbol, 60, Resolution.MINUTE)
        if not history.empty:
            for bar in history:
                self.ema_fast.update(bar.end_time, bar.close)
                self.ema_slow.update(bar.end_time, bar.close)
                self.atr.update(bar)

    def check_entry_signals(self, contract):
        """Check for trade entry signals"""
        
        if not self.ema_fast.is_ready or not self.ema_slow.is_ready or not self.atr.is_ready:
            return
        
        current_price = contract.last_price
        
        # Simple EMA crossover strategy
        # Long signal: fast EMA crosses above slow EMA
        if self.ema_fast.current.value > self.ema_slow.current.value and \
           self.ema_fast.previous.value <= self.ema_slow.previous.value:
            self.enter_long_position(contract)
        
        # Short signal: fast EMA crosses below slow EMA
        elif self.ema_fast.current.value < self.ema_slow.current.value and \
             self.ema_fast.previous.value >= self.ema_slow.previous.value:
            self.enter_short_position(contract)

    def enter_long_position(self, contract):
        """Enter a long position with risk management"""
        
        current_price = contract.last_price
        
        # Calculate position size based on risk
        position_size = self.calculate_position_size(current_price, long=True)
        
        if position_size == 0:
            return
        
        # Enter position
        self.market_order(contract.symbol, position_size)
        self.entry_price = current_price
        self.position_side = 1
        self.highest_profit = 0
        
        # Set stop loss
        stop_price = current_price * (1 - self.stop_loss_percent)
        self.stop_loss_ticket = self.stop_market_order(contract.symbol, -position_size, stop_price)
        
        # Set take profit
        take_profit_price = current_price * (1 + self.take_profit_percent)
        self.take_profit_ticket = self.limit_order(contract.symbol, -position_size, take_profit_price)
        
        self.log(f"LONG ENTRY: {position_size} contracts @ {current_price:.2f}")
        self.log(f"  Stop Loss: {stop_price:.2f} | Take Profit: {take_profit_price:.2f}")
        
        # Plot entry
        self.plot('Trade Management', 'Entry Price', current_price)
        self.plot('Trade Management', 'Stop Loss', stop_price)
        self.plot('Trade Management', 'Take Profit', take_profit_price)
        self.plot('Risk Metrics', 'Position Size', position_size)

    def enter_short_position(self, contract):
        """Enter a short position with risk management"""
        
        current_price = contract.last_price
        
        # Calculate position size based on risk
        position_size = self.calculate_position_size(current_price, long=False)
        
        if position_size == 0:
            return
        
        # Enter position
        self.market_order(contract.symbol, -position_size)
        self.entry_price = current_price
        self.position_side = -1
        self.highest_profit = 0
        
        # Set stop loss
        stop_price = current_price * (1 + self.stop_loss_percent)
        self.stop_loss_ticket = self.stop_market_order(contract.symbol, position_size, stop_price)
        
        # Set take profit
        take_profit_price = current_price * (1 - self.take_profit_percent)
        self.take_profit_ticket = self.limit_order(contract.symbol, position_size, take_profit_price)
        
        self.log(f"SHORT ENTRY: {position_size} contracts @ {current_price:.2f}")
        self.log(f"  Stop Loss: {stop_price:.2f} | Take Profit: {take_profit_price:.2f}")
        
        # Plot entry
        self.plot('Trade Management', 'Entry Price', current_price)
        self.plot('Trade Management', 'Stop Loss', stop_price)
        self.plot('Trade Management', 'Take Profit', take_profit_price)
        self.plot('Risk Metrics', 'Position Size', position_size)

    def manage_position(self, contract):
        """Manage existing position with trailing stop"""
        
        if not self.active_contract or self.position_side == 0:
            return
        
        current_price = contract.last_price
        
        # Calculate current profit/loss
        if self.position_side == 1:  # Long
            profit_percent = (current_price - self.entry_price) / self.entry_price
        else:  # Short
            profit_percent = (self.entry_price - current_price) / self.entry_price
        
        # Update highest profit for trailing stop
        if profit_percent > self.highest_profit:
            self.highest_profit = profit_percent
            
            # Activate trailing stop if in profit
            if profit_percent > self.stop_loss_percent:
                self.update_trailing_stop(contract, current_price)

    def update_trailing_stop(self, contract, current_price):
        """Update trailing stop loss"""
        
        if not self.stop_loss_ticket or self.stop_loss_ticket.status == OrderStatus.FILLED:
            return
        
        position_size = abs(self.portfolio[contract.symbol].quantity)
        
        if self.position_side == 1:  # Long position
            new_stop = current_price * (1 - self.trailing_stop_percent)
            current_stop = self.stop_loss_ticket.get_field(OrderField.STOP_PRICE)
            
            # Only move stop up
            if new_stop > current_stop:
                update_fields = UpdateOrderFields()
                update_fields.stop_price = new_stop
                self.stop_loss_ticket.update(update_fields)
                self.log(f"TRAILING STOP updated: {new_stop:.2f}")
                self.plot('Trade Management', 'Stop Loss', new_stop)
        
        else:  # Short position
            new_stop = current_price * (1 + self.trailing_stop_percent)
            current_stop = self.stop_loss_ticket.get_field(OrderField.STOP_PRICE)
            
            # Only move stop down
            if new_stop < current_stop:
                update_fields = UpdateOrderFields()
                update_fields.stop_price = new_stop
                self.stop_loss_ticket.update(update_fields)
                self.log(f"TRAILING STOP updated: {new_stop:.2f}")
                self.plot('Trade Management', 'Stop Loss', new_stop)

    def calculate_position_size(self, price, long=True):
        """Calculate position size based on risk per trade"""
        
        # Risk amount in dollars
        risk_amount = self.portfolio.total_portfolio_value * self.risk_per_trade
        
        # Dollar risk per contract
        if long:
            stop_price = price * (1 - self.stop_loss_percent)
        else:
            stop_price = price * (1 + self.stop_loss_percent)
        
        risk_per_contract = abs(price - stop_price) * 50  # ES multiplier is 50
        
        # Position size
        position_size = int(risk_amount / risk_per_contract)
        
        # Limit to 1 contract for demo (can be adjusted)
        return min(position_size, 1)

    def roll_contract(self, new_contract):
        """Roll position to new contract"""
        
        if self.active_contract and self.position_side != 0:
            old_position = self.portfolio[self.active_contract].quantity
            
            # Close old position
            self.liquidate(self.active_contract)
            
            # Open new position
            self.market_order(new_contract, old_position)
            
            self.log(f"ROLLED contract from {self.active_contract} to {new_contract}")

    def on_order_event(self, order_event):
        """Handle order events and track statistics"""
        
        if order_event.status != OrderStatus.FILLED:
            return
        
        order = self.transactions.get_order_by_id(order_event.order_id)
        
        # Check if this is a stop loss or take profit
        if "Stop" in order.tag or order.type == OrderType.STOP_MARKET:
            self.handle_position_exit(order_event, is_stop=True)
        elif order.type == OrderType.LIMIT:
            self.handle_position_exit(order_event, is_stop=False)

    def handle_position_exit(self, order_event, is_stop):
        """Handle position exit and update statistics"""
        
        if self.position_side == 0:
            return
        
        # Calculate trade profit/loss
        exit_price = order_event.fill_price
        quantity = abs(order_event.fill_quantity)
        
        if self.position_side == 1:  # Long
            pnl = (exit_price - self.entry_price) * quantity * 50
        else:  # Short
            pnl = (self.entry_price - exit_price) * quantity * 50
        
        # Update statistics
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
            self.total_profit += pnl
            result = "WIN"
        else:
            self.losing_trades += 1
            self.total_loss += abs(pnl)
            result = "LOSS"
        
        exit_type = "STOP LOSS" if is_stop else "TAKE PROFIT"
        self.log(f"{exit_type} - {result}: ${pnl:.2f}")
        
        # Reset position tracking
        self.position_side = 0
        self.entry_price = 0
        self.highest_profit = 0
        self.stop_loss_ticket = None
        self.take_profit_ticket = None
        
        # Update risk metrics
        self.update_risk_metrics()

    def update_risk_metrics(self):
        """Update and plot risk metrics"""
        
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            
            avg_win = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0
            avg_loss = self.total_loss / self.losing_trades if self.losing_trades > 0 else 1
            risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
            
            self.plot('Risk Metrics', 'Win Rate %', win_rate)
            self.plot('Risk Metrics', 'Risk Reward Ratio', risk_reward)

    def check_max_drawdown(self):
        """Check if max drawdown is exceeded"""
        
        current_value = self.portfolio.total_portfolio_value
        
        if current_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_value
        
        drawdown_percent = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value
        
        if drawdown_percent > self.max_drawdown:
            self.max_drawdown = drawdown_percent
        
        return drawdown_percent >= self.max_drawdown_percent

    def update_portfolio_charts(self):
        """Update portfolio performance charts"""
        
        current_value = self.portfolio.total_portfolio_value
        self.plot('Portfolio', 'Value', current_value)
        
        # Calculate daily PnL
        if hasattr(self, 'previous_value'):
            daily_pnl = current_value - self.previous_value
            self.plot('Portfolio', 'Daily PnL', daily_pnl)
        
        self.previous_value = current_value
        
        # Plot drawdown
        drawdown_percent = ((self.peak_portfolio_value - current_value) / self.peak_portfolio_value) * 100
        self.plot('Portfolio', 'Drawdown %', -drawdown_percent)

    def update_trade_charts(self, current_price):
        """Update trade management charts"""
        
        self.plot('Trade Management', 'Current Price', current_price)

    def on_end_of_algorithm(self):
        """Print final statistics"""
        
        self.log("="*60)
        self.log("FINAL TRADE STATISTICS")
        self.log("="*60)
        self.log(f"Total Trades: {self.total_trades}")
        self.log(f"Winning Trades: {self.winning_trades}")
        self.log(f"Losing Trades: {self.losing_trades}")
        
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            self.log(f"Win Rate: {win_rate:.2f}%")
        
        if self.winning_trades > 0 and self.losing_trades > 0:
            avg_win = self.total_profit / self.winning_trades
            avg_loss = self.total_loss / self.losing_trades
            risk_reward = avg_win / avg_loss
            self.log(f"Average Win: ${avg_win:.2f}")
            self.log(f"Average Loss: ${avg_loss:.2f}")
            self.log(f"Risk/Reward Ratio: {risk_reward:.2f}")
        
        net_pnl = self.total_profit - self.total_loss
        self.log(f"Net P&L: ${net_pnl:.2f}")
        self.log(f"Max Drawdown: {self.max_drawdown*100:.2f}%")
        self.log(f"Final Portfolio Value: ${self.portfolio.total_portfolio_value:.2f}")
        self.log("="*60)
