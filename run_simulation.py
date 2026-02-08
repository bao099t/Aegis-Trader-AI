import sys
import os
import datetime
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.simulation.data_loader import DataLoader
from src.simulation.strategy import DailySurferStrategy

def main():
    print("=========================================")
    print("    PORTFOLIO SIMULATION (HYBRID ARSENAL TEST)    ")
    print("      Trend Hunter (>25) + Mean Reversion (<20)      ")
    print("           (2014 - 2026)                 ")
    print("=========================================")
    
    # 1. Configuration
    TICKERS = [
        'BTC-USD', 'ETH-USD', # Crypto
        'GC=F', 'CL=F',       # Commodities
        'NVDA', 'TSLA', 'AMZN', 'AAPL', 'MSFT', 'GOOGL' # Tech Stocks
    ]
    
    START_DATE = "2014-01-01"
    END_DATE = "2026-12-31" 
    INITIAL_CAPITAL = 10000.0
    POSITION_SIZE_PCT = 0.20 # Max 5 positions? Or dynamic?
    # User said: "Focus on Top 3". So maybe 33% capital each?
    # Let's be safer: Max 3 positions, 30% each. 10% cash Reserve.
    MAX_POSITIONS = 3
    ALLOCATION_PER_TRADE = 0.33 
    
    # 2. Initialize Components
    loader = DataLoader() 
    strategy = DailySurferStrategy()
    
    # 3. Load and Prepare Data
    data_map = {}
    print(f"Loading data for {len(TICKERS)} assets...")
    
    all_dates = set()
    
    for ticker in TICKERS:
        df = loader.fetch_data(ticker, START_DATE, END_DATE)
        if df is not None and not df.empty:
            # Flatten MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Normalize Columns
            cols = {c.lower(): c for c in df.columns}
            rename_map = {}
            if 'close' in cols: rename_map[cols['close']] = 'Close'
            if 'high' in cols: rename_map[cols['high']] = 'High'
            if 'low' in cols: rename_map[cols['low']] = 'Low'
            if 'open' in cols: rename_map[cols['open']] = 'Open'
            if 'volume' in cols: rename_map[cols['volume']] = 'Volume'
            df.rename(columns=rename_map, inplace=True)
            
            try:
                # Calculate Indicators (Turbo Mode Logic in strategy.prepare_data)
                df_prepared = strategy.prepare_data(df)
                data_map[ticker] = df_prepared
                all_dates.update(df_prepared.index)
            except Exception as e:
                print(f"ERROR processing {ticker}: {e}")
    
    # Sort dates
    timeline = sorted(list(all_dates))
    print(f"Timeline: {len(timeline)} trading days.")
    
    # 4. Simulation Loop
    capital = INITIAL_CAPITAL
    portfolio = {} # ticker -> { 'shares': float, 'entry_price': float }
    history = []
    trades = []
    
    # 4. Simulation Loop
    capital = INITIAL_CAPITAL
    portfolio = {} # ticker -> { 'shares': float, 'entry_price': float }
    history = []
    trades = []
    
    last_known_prices = {}
    
    for current_date in timeline:
        # A. Mark to Market (Update Portfolio Value)
        # current_prices = {} # OLD: Reset every day -> Caused 0 value on holidays
        
        # Update prices with today's data where available
        daily_candidates = []
        
        for ticker, df in data_map.items():
            if current_date in df.index:
                row = df.loc[current_date]
                price = row['Close']
                last_known_prices[ticker] = price # Update last known
            
            # Use last known price for valuation/logic
            # Note: Logic triggers should only happen on ACTIVE trading days for that asset
            if current_date in df.index and ticker in last_known_prices:
                 price = last_known_prices[ticker]
                 row = df.loc[current_date]
                 
                 # Logic Checks (Same as before)
                 sma200 = row.get('SMA_200', 0)
                 sma50 = row.get('SMA_50', 0)
                 sma20 = row.get('SMA_20', 0)
                 adx = row.get('ADX', 0)
                 rsi = row.get('RSI', 50)
                 
                 if pd.isna(sma50) or pd.isna(sma20) or pd.isna(sma200): continue
                 
                 is_exit = price < sma20
                 
                 # --- HYBRID ARSENAL (Phase 5) ---
                 # 1. MARKET REGIME CHECK
                 # ADX > 25: Trending (Use Trend Hunter)
                 # ADX < 20: Sideways (Use Mean Reversion)
                 
                 is_crypto = ticker in ['BTC-USD', 'ETH-USD']
                 
                 if adx > 25:
                     # --- TREND HUNTER MODE ---
                     if is_crypto:
                         # Turbo for Crypto (Catch the pump early)
                         is_uptrend = price > sma50
                     else:
                         # Balanced for Stocks (Safety first)
                         is_uptrend = price > sma50 and price > sma200
                         
                     is_strong = True
                     is_entry = is_uptrend and is_strong and rsi < 70
                     
                     # Trend Exit
                     is_exit = price < sma20
                     
                 elif adx < 20:
                     # --- MEAN REVERSION MODE 2.0 (Sniper + Bollinger) ---
                     # Buy Fear (Extreme Oversold), Sell Greed
                     
                     bb_lower = row.get('BB_Lower', 0)
                     bb_upper = row.get('BB_Upper', 999999)
                     
                     # Entry: RSI < 30 AND Price < Lower Band (Double confirmation)
                     # This filters out "mildly oversold" drifts.
                     is_entry = (rsi < 30) and (price < bb_lower)
                     
                     # Exit: RSI > 70 OR Price > Upper Band
                     is_exit = (rsi > 70) or (price > bb_upper)
                     
                 else:
                     # TRANSITION ZONE (20-25)
                     # Do nothing or Strict Trend
                     is_entry = False
                     is_exit = price < sma20 # Protective stop still active
                 
                 daily_candidates.append({
                     'ticker': ticker,
                     'adx': adx,
                     'price': price,
                     'is_entry': is_entry,
                     'is_exit': is_exit
                 })
                 
        # Calculate Equity using Last Known Prices
        portfolio_value = capital
        for t, p in portfolio.items():
            if t in last_known_prices:
                portfolio_value += p['shares'] * last_known_prices[t]
        
        # B. Execute Exits (Safety First)
        # Only execute if market was open today (cand exists)
        for cand in daily_candidates:
            ticker = cand['ticker']
            if ticker in portfolio and cand['is_exit']:
                # SELL
                shares = portfolio[ticker]['shares']
                proceeds = shares * cand['price']
                profit = proceeds - (shares * portfolio[ticker]['entry_price'])
                capital += proceeds
                
                trades.append({
                    'date': current_date,
                    'action': 'SELL',
                    'ticker': ticker,
                    'price': cand['price'],
                    'profit': profit
                })
                del portfolio[ticker]
                # print(f"{current_date.date()} [SELL] {ticker} Gain: {profit:.2f}")

        # C. Execute Entries (Ranked)
        # 1. Sort Candidates by ADX (Strongest First)
        daily_candidates.sort(key=lambda x: x['adx'], reverse=True)
        
        # 2. Identify Top 3
        top_3 = [c['ticker'] for c in daily_candidates[:3]]
        
        # 3. Buy if Eligible
        for cand in daily_candidates:
            ticker = cand['ticker']
            
            # Must be in Top 3 AND Signal is Entry
            if cand['is_entry'] and ticker in top_3:
                # Check if we have slots
                if len(portfolio) < MAX_POSITIONS and ticker not in portfolio:
                    # BUY
                    # Allocation Size
                    # Use last_known_prices for Portfolio Value
                    current_equity = capital + sum(p['shares']*last_known_prices[p_ticker] for p_ticker, p in portfolio.items() if p_ticker in last_known_prices)
                    max_invest = current_equity * ALLOCATION_PER_TRADE
                    invest_amount = min(capital, max_invest)
                    
                    if invest_amount > 100: # Min trade
                        shares = invest_amount / cand['price']
                        capital -= invest_amount
                        
                        portfolio[ticker] = {
                            'shares': shares,
                            'entry_price': cand['price']
                        }
                        trades.append({
                            'date': current_date,
                            'action': 'BUY',
                            'ticker': ticker,
                            'price': cand['price'],
                            'amount': invest_amount
                        })

        # D. Record History
        # (calculated above in loop step A, but let's recalc to be sure after trades)
        equity_end_of_day = capital
        for t, p in portfolio.items():
            if t in last_known_prices:
                equity_end_of_day += p['shares'] * last_known_prices[t]
        
        history.append({
            'date': current_date,
            'equity': equity_end_of_day
        })

    # 5. Final Detailed Report
    final_equity = history[-1]['equity']
    total_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Group Trades by Year
    trades_by_year = {}
    for t in trades:
        y = t['date'].year
        if y not in trades_by_year: trades_by_year[y] = []
        trades_by_year[y].append(t)
        
    # Yearly Stats
    yearly_stats = {}
    current_equity_cursor = INITIAL_CAPITAL
    
    # We need equity at start/end of each year
    # history is list of {date, equity}
    history_df = pd.DataFrame(history)
    history_df['year'] = history_df['date'].apply(lambda x: x.year)
    
    report_lines = []
    report_lines.append("# BÁO CÁO CHI TIẾT GIAO DỊCH (2014-2026)")
    report_lines.append(f"**Vốn Ban Đầu:** ${INITIAL_CAPITAL:,.2f}")
    report_lines.append(f"**Vốn Cuối Cùng:** ${final_equity:,.2f}")
    report_lines.append(f"**Tổng Lợi Nhuận:** {total_return:.2f}%")
    report_lines.append("---")
    
    for year in sorted(list(set(history_df['year']))):
        year_data = history_df[history_df['year'] == year]
        if year_data.empty: continue
        
        start_eq = year_data.iloc[0]['equity']
        end_eq = year_data.iloc[-1]['equity']
        profit = end_eq - start_eq
        ret_pct = (profit / start_eq) * 100
        
        # Max Drawdown this year
        eq_curve = year_data['equity'].values
        run_max = np.maximum.accumulate(eq_curve)
        dd = (eq_curve - run_max) / run_max * 100
        mdd = np.min(dd)
        
        # Trade Stats
        y_trades = trades_by_year.get(year, [])
        wins = [t for t in y_trades if t['action'] == 'SELL' and t['profit'] > 0]
        losses = [t for t in y_trades if t['action'] == 'SELL' and t['profit'] <= 0]
        count = len(wins) + len(losses)
        win_rate = (len(wins)/count*100) if count > 0 else 0
        
        report_lines.append(f"## NĂM {year}")
        report_lines.append(f"- **Lợi Nhuận:** ${profit:,.2f} ({ret_pct:+.2f}%)")
        report_lines.append(f"- **Vốn Cuối Năm:** ${end_eq:,.2f}")
        report_lines.append(f"- **Max Drawdown:** {mdd:.2f}%")
        report_lines.append(f"- **Số Lệnh:** {count} (Thắng: {len(wins)} | Thua: {len(losses)})")
        report_lines.append(f"- **Tỉ Lệ Thắng:** {win_rate:.2f}%")
        
        if count > 0:
            report_lines.append("\n| Ngày | Mã | Hành Động | Giá | PnL ($) |")
            report_lines.append("|---|---|---|---|---|")
            for t in y_trades:
                date_str = t['date'].strftime('%Y-%m-%d')
                pnl = f"${t['profit']:,.2f}" if 'profit' in t else "-"
                action = t['action']
                if action == 'SELL':
                    # Add icon
                    icon = "✅" if t['profit'] > 0 else "❌"
                    report_lines.append(f"| {date_str} | **{t['ticker']}** | {action} | ${t['price']:.2f} | {icon} {pnl} |")
                else:
                    report_lines.append(f"| {date_str} | {t['ticker']} | {action} | ${t['price']:.2f} | - |")
        else:
            report_lines.append("\n*(Không có giao dịch)*")
            
        report_lines.append("---\n")
        
    full_report = "\n".join(report_lines)
    
    print("Generating DETAILED_REPORT.md...")
    with open("DETAILED_REPORT.md", "w", encoding='utf-8') as f:
        f.write(full_report)
    print("Done.")

if __name__ == "__main__":
    main()
