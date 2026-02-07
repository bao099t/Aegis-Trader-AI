import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, strategy, initial_capital=10000, fee_pct=0.001, slippage_pct=0.0005):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.equity = initial_capital
        # Holdings: {ticker: {'qty': 0, 'cost_basis': 0}}
        # qty > 0: Long, qty < 0: Short
        self.holdings = {} 
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.trades = []
        self.daily_returns = []

    def execute_trade(self, ticker, signal, price, date):
        """
        Executes a trade based on signal.
        Signal: "BUY" or "SHORT" (Entry), "SELL" or "COVER" (Exit/Reversal)
        """
        # Determine Current Position
        current_qty = self.holdings.get(ticker, {}).get('qty', 0)
        
        # 1. CLOSE EXISTING POSITIONS if Signal opposes direction
        if current_qty > 0 and signal in ["SHORT", "SELL"]:
            # Sell to Close Long
            self._close_position(ticker, price, date, "SELL")
            current_qty = 0 # Now flat
            
        elif current_qty < 0 and signal in ["BUY", "COVER"]:
            # Buy to Cover Short
            self._close_position(ticker, price, date, "COVER")
            current_qty = 0 # Now flat

        # 2. OPEN NEW POSITIONS if Signal is Entry and we are Flat
        # (For simplicity/surfing, we flip. If we just closed, we can open new in same tick or next? 
        # Let's assume we can flip in same tick for "Surfing" efficiency).
        
        if current_qty == 0:
            if signal == "BUY":
                self._open_position(ticker, price, date, "LONG")
            elif signal == "SHORT":
                self._open_position(ticker, price, date, "SHORT")

    def _open_position(self, ticker, price, date, direction):
        # Calculate Position Size (20% of current equity)
        target_size = self.equity * 0.20 
        qty = target_size / price
        
        # Adjust for slippage
        exec_price = price * (1 + self.slippage_pct) if direction == "LONG" else price * (1 - self.slippage_pct)
        
        cost = qty * exec_price
        fee = cost * self.fee_pct
        
        # Margin Check (Simplistic: Can we afford the margin requirement? Assume 1:1 for now)
        if self.cash >= cost + fee:
            self.cash -= fee # Fee is paid immediately
            
            if direction == "LONG":
                self.cash -= cost # Pay for shares
                self.holdings[ticker] = {'qty': qty, 'entry_price': exec_price}
                action = "BUY"
            else:
                # SHORT: We get cash from selling borrowed shares, but it's held as collateral. 
                # Simplification: Cash stays same (minus fee), but we track liability. 
                # actually in cash account you put up margin. 
                # Let's say we reserve 'cost' amount of cash as margin.
                self.cash -= cost # Reserve margin
                self.holdings[ticker] = {'qty': -qty, 'entry_price': exec_price}
                action = "SHORT"
                
            self.trades.append({
                'date': date, 'ticker': ticker, 'action': action, 
                'price': exec_price, 'qty': qty, 'fee': fee, 'pnl': 0
            })

    def _close_position(self, ticker, price, date, action):
        holding = self.holdings[ticker]
        qty = abs(holding['qty']) # Absolute quantity to close
        entry_price = holding['entry_price']
        
        # Adjust for slippage
        # SELL (to close Long): Bid price (lower)
        # COVER (to close Short): Ask price (higher)
        exec_price = price * (1 - self.slippage_pct) if action == "SELL" else price * (1 + self.slippage_pct)
        
        proceeds = qty * exec_price
        fee = proceeds * self.fee_pct
        
        pnl = 0
        if action == "SELL": # Closing Long
            # Cash in: Proceeds needed to be returned to cash pool
            # We spent 'entry_price * qty' earlier. Now we get 'proceeds'.
            # But wait, in _open, we deducted cost.
            # So now we add proceeds.
            self.cash += (proceeds - fee)
            pnl = (exec_price - entry_price) * qty - fee
            
        elif action == "COVER": # Closing Short
            # We reserved 'entry_price * qty' as margin.
            # We need to buy back at 'exec_price'.
            # Unreserve margin:
            margin_reserved = entry_price * qty
            cost_to_cover = proceeds # qty * exec_price
            
            # Cash update: We get back margin, pay cover cost, pay fee.
            # self.cash already has margin deducted.
            # So we add margin back, then subtract cover cost.
            self.cash += (margin_reserved - cost_to_cover - fee)
            
            pnl = (entry_price - exec_price) * qty - fee # Short PnL: (Entry - Exit) * Qty
            
        self.holdings[ticker] = {'qty': 0, 'entry_price': 0}
        
        self.trades.append({
            'date': date, 'ticker': ticker, 'action': action, 
            'price': exec_price, 'qty': qty, 'fee': fee, 
            'pnl': pnl
        })

    def run(self, data_map):
        """
        Main loop.
        """
        all_dates = sorted(list(set().union(*[df.index for df in data_map.values()])))
        
        if not all_dates:
             print("No data to simulate.")
             return

        print(f"  [Backtest] Running simulation from {all_dates[0].date()} to {all_dates[-1].date()}...")
        
        for current_date in all_dates:
            # Update Equity Mark-to-Market
            current_equity = self.cash
            
            for ticker, holding in self.holdings.items():
                qty = holding.get('qty', 0)
                if qty != 0:
                     if ticker in data_map and current_date in data_map[ticker].index:
                         current_price = data_map[ticker].loc[current_date]['Close']
                         
                         if qty > 0: # Long
                             # Equity = Cash + Value of Shares
                             # But 'Cash' in my logic already had Cost deducted. 
                             # So Equity = Cash + (Qty * CurrentPrice)
                             current_equity += qty * current_price
                             
                         else: # Short
                             # Equity = Cash + (MarginReserved + UnrealizedPnL)
                             # Wait, Cash has margin deducted.
                             # So actually: Equity = Cash + MarginReserved - (Qty * CurrentPrice) ? 
                             # Let's simplify: 
                             # Entry: Cash = 10k. Short $2k. Cash -> 8k. 
                             # Price stays same: Equity = 8k + 2k (Liability covered) = 10k.
                             # Price drops to $1k: Equity = 8k + (2k - 1k) = 9k? NO, profit.
                             # If price drops, I buy back cheaper. 
                             # Equity = Cash + (EntryVal - CurrentVal) + Margin?
                             # Equity = Cash + Margin + (EntryPrice * Qty - CurrentPrice * Qty)
                             # Let's rely on PnL logic:
                             # Equity = Cash + Margin + UnrealizedPnL
                             # UnrealizedPnL = (Entry - Current) * AbsQty
                             # Equity = Cash + Margin + (Entry - Current) * AbsQty
                             
                             abs_qty = abs(qty)
                             entry_price = holding['entry_price']
                             margin = abs_qty * entry_price # This is what we deducted from cash
                             
                             # We add back margin to see "Potentially available", then subtract current buyback cost
                             current_equity += margin # Add back what we reserved
                             current_equity -= (abs_qty * current_price) # Subtract what we owe to cover
                             
            self.equity = current_equity
            self.daily_returns.append({'date': current_date, 'equity': self.equity})
            
            # Trading Logic
            for ticker, df in data_map.items():
                if current_date in df.index:
                    row = df.loc[current_date]
                    signal = self.strategy.generate_signal(row)
                    price = row['Close']
                    
                    # DEBUG
                    if signal != "HOLD":
                        print(f"DEBUG: {current_date.date()} {ticker} Signal: {signal}")
                    
                    if signal != "HOLD":
                        self.execute_trade(ticker, signal, price, current_date)

    def generate_report(self):
        """
        Generates performance report.
        """
        if not self.trades:
            return "No trades executed."
            
        df_trades = pd.DataFrame(self.trades)
        
        # Calculate Stats on CLOSED trades
        completed_trades = df_trades[df_trades['action'].isin(['SELL', 'COVER'])]
        
        if completed_trades.empty:
             return f"Executed {len(df_trades)} trades (All entries, no exits)."
             
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        losing_trades = completed_trades[completed_trades['pnl'] <= 0]
        
        win_rate = (len(winning_trades) / len(completed_trades)) * 100
        roi = ((self.equity - self.initial_capital) / self.initial_capital) * 100
        
        # Sharpe
        equity_curve = pd.DataFrame(self.daily_returns)
        if not equity_curve.empty:
            equity_curve['returns'] = equity_curve['equity'].pct_change()
            sharpe = (equity_curve['returns'].mean() / equity_curve['returns'].std()) * np.sqrt(252) if equity_curve['returns'].std() != 0 else 0
        else:
            sharpe = 0
            
        report = f"""
=============================================
BACKTEST REPORT (2014-2026) - LONG/SHORT
=============================================
Initial Capital: ${self.initial_capital:,.2f}
Final Equity:    ${self.equity:,.2f}
Total Return:    {roi:.2f}%
---------------------------------------------
Total Trades:    {len(completed_trades)}
Win Rate:        {win_rate:.2f}%
Sharpe Ratio:    {sharpe:.2f}
---------------------------------------------
Best Trade:      ${completed_trades['pnl'].max():,.2f}
Worst Trade:     ${completed_trades['pnl'].min():,.2f}
=============================================
"""
        return report
