import sys
import os
import datetime
import pandas as pd
import numpy as np

# Add src to path for standalone imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.simulation.data_loader import DataLoader
from src.simulation.strategy import DailySurferStrategy
from src.intelligence.predictor import PricePredictor
from src.intelligence.asset_selector import AssetSelector

def main():
    print("=========================================")
    print("    AEGIS TURBO SIMULATION (12-YEAR)    ")
    print("      Dynamic Alpha Discovery (DAD)     ")
    print("           (2014 - 2026)                 ")
    print("=========================================")
    
    # 1. Configuration
    USE_AI = True
    predictor = PricePredictor(mode="hybrid")
    
    # DAD Broad Universe (Phase 9)
    BROAD_UNIVERSE = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'LINK-USD',
        'NVDA', 'TSLA', 'AMZN', 'AAPL', 'MSFT', 'AMD', 'MSTR', 'GOOGL', 'META',
        'GC=F', 'CL=F'
    ]
    
    DATA_START_DATE = "2013-01-01" 
    START_DATE = "2014-01-01"
    END_DATE = "2026-12-31" 
    INITIAL_CAPITAL = 10000.0
    MAX_POSITIONS = 5
    ALLOCATION_PER_TRADE = 0.20 
    
    # 2. Initialize Components
    loader = DataLoader() 
    strategy = DailySurferStrategy()
    selector = AssetSelector(broad_universe=BROAD_UNIVERSE)
    
    # 3. Load and Prepare Data
    data_map = {}
    print(f"Loading data for {len(BROAD_UNIVERSE)} assets...")
    all_dates = set()
    
    for ticker in BROAD_UNIVERSE:
        df = loader.fetch_data(ticker, DATA_START_DATE, END_DATE)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            cols = {c.lower(): c for c in df.columns}
            rename_map = {}
            if 'close' in cols: rename_map[cols['close']] = 'Close'
            if 'high' in cols: rename_map[cols['high']] = 'High'
            if 'low' in cols: rename_map[cols['low']] = 'Low'
            if 'open' in cols: rename_map[cols['open']] = 'Open'
            if 'volume' in cols: rename_map[cols['volume']] = 'Volume'
            df.rename(columns=rename_map, inplace=True)
            
            try:
                df_prepared = strategy.prepare_data(df)
                data_map[ticker] = df_prepared
                all_dates.update(df_prepared.index)
            except Exception as e:
                print(f"ERROR processing {ticker}: {e}")
    
    timeline = sorted([d for d in all_dates if d >= pd.to_datetime(START_DATE)])
    print(f"Timeline: {len(timeline)} trading days.")
    
    # 4. Simulation Loop
    capital = INITIAL_CAPITAL
    portfolio = {} # ticker -> { 'shares': float, 'entry_price': float, 'high_water': float }
    history = []
    trades = []
    last_known_prices = {}
    reentry_guard = {} # ticker -> last_exit_date
    
    trading_day_count = 0
    active_tickers = BROAD_UNIVERSE[:5] # Initial guess
    
    for current_date in timeline:
        daily_candidates = []
        trading_day_count += 1
        
        # Phase 9: Dynamic Re-balancing every 30 days for Agile Alpha
        if trading_day_count % 30 == 0:
            active_tickers = selector.get_top_alpha(data_map, current_date, top_n=5)
            # print(f"[{current_date.date()}] DAD Re-balanced. Active Alpha: {active_tickers}")
            
        for ticker, df in data_map.items():
            if current_date in df.index:
                row = df.loc[current_date]
                price = row['Close']
                last_known_prices[ticker] = price
                
                # Update High Water Mark for Trailing Stop
                if ticker in portfolio:
                    portfolio[ticker]['high_water'] = max(portfolio[ticker]['high_water'], price)
            
            # Skip non-active assets unless we already have a position (to handle exits)
            if ticker not in active_tickers and ticker not in portfolio:
                continue

            if current_date in df.index and ticker in last_known_prices:
                price = last_known_prices[ticker]
                row = df.loc[current_date]
                
                sma200 = row.get('SMA_200', 0)
                sma50 = row.get('SMA_50', 0)
                sma20 = row.get('SMA_20', 0)
                atr = row.get('ATR', price * 0.05)
                adx = row.get('ADX', 0)
                rsi = row.get('RSI', 50)
                
                if pd.isna(sma50) or pd.isna(sma20) or pd.isna(sma200): continue
                
                # --- EXIT LOGIC (Balanced Turbo Trail) ---
                is_exit = False
                if ticker in portfolio:
                    high_water = portfolio[ticker]['high_water']
                    # 3.5x ATR for Balanced Hyper-Growth
                    if price < (high_water - 3.5 * atr):
                        is_exit = True
                    # Fast MA safety exit
                    elif price < sma20 and (price/portfolio[ticker]['entry_price'] - 1) < -0.05:
                        is_exit = True

                # --- ENTRY LOGIC (Agile Entry) ---
                is_entry = False
                if ticker not in portfolio:
                    # Re-entry Guard (3 day cooldown)
                    if ticker in reentry_guard:
                        days_since_exit = (current_date - reentry_guard[ticker]).days
                        if days_since_exit < 3:
                            continue

                    # Trend Barrier
                    if adx > 20: 
                        is_entry = (price > sma50) and rsi < 75
                    elif adx < 15:
                        # Defensive Mean Reversion
                        is_entry = (rsi < 25) and (price < row.get('BB_Lower', 0))

                # --- WIS 2.0 (Turbo Scaling) ---
                hybrid_signal = None
                ai_score = 0
                if USE_AI and is_entry:
                    current_df_slice = df.loc[:current_date]
                    hybrid_signal, _ = predictor.predict_from_df(current_df_slice)
                    
                    if isinstance(hybrid_signal, dict):
                        neural_dir = hybrid_signal['neural_dir']
                        rf_prob = hybrid_signal['rf_prob']
                        
                        if neural_dir == "DOWN":
                            is_entry = False
                        else:
                            ai_score = rf_prob + (0.5 if neural_dir == "UP" else 0)
                    else:
                        is_entry = False

                daily_candidates.append({
                    'ticker': ticker,
                    'ai_score': ai_score,
                    'price': price,
                    'is_entry': is_entry,
                    'is_exit': is_exit,
                    'hybrid_signal': hybrid_signal
                })
        
        # Mark to Market & Update High Water
        portfolio_value = capital
        for t, p in portfolio.items():
            if t in last_known_prices:
                price = last_known_prices[t]
                portfolio_value += p['shares'] * price
                portfolio[t]['high_water'] = max(portfolio[t]['high_water'], price)
        
        # Execute Exits
        for cand in daily_candidates:
            ticker = cand['ticker']
            if ticker in portfolio and cand['is_exit']:
                shares = portfolio[ticker]['shares']
                proceeds = shares * cand['price']
                profit = proceeds - (shares * portfolio[ticker]['entry_price'])
                capital += proceeds
                trades.append({
                    'date': current_date, 'action': 'SELL',
                    'ticker': ticker, 'price': cand['price'], 'profit': profit
                })
                del portfolio[ticker]
                reentry_guard[ticker] = current_date
        # Execute Entries
        daily_candidates.sort(key=lambda x: x['ai_score'], reverse=True)
        top_N = [c['ticker'] for c in daily_candidates[:MAX_POSITIONS]]
        
        for cand in daily_candidates:
            ticker = cand['ticker']
            if cand['is_entry'] and ticker in top_N:
                if len(portfolio) < MAX_POSITIONS and ticker not in portfolio:
                    # Dynamic Allocation (WIS 2.0 Turbo)
                    current_equity = capital + sum(p['shares']*last_known_prices[pt] for pt, p in portfolio.items() if pt in last_known_prices)
                    
                    # DEFAULT: 30%
                    scaling = 1.0
                    
                    if isinstance(cand['hybrid_signal'], dict):
                        h = cand['hybrid_signal']
                        # TURBO MODE: 1.5x (45% capital)
                        if h['neural_dir'] == "UP" and h['rf_prob'] > 0.75:
                            scaling = 1.5
                        # LEAN MODE: 0.5x (15% capital)
                        elif h['neural_dir'] == "NEUTRAL":
                            scaling = 0.5
                    
                    max_invest = current_equity * ALLOCATION_PER_TRADE * scaling
                    invest_amount = min(capital, max_invest)
                    
                    if invest_amount > 100:
                        shares = invest_amount / cand['price']
                        capital -= invest_amount
                        portfolio[ticker] = {
                            'shares': shares, 
                            'entry_price': cand['price'],
                            'high_water': cand['price']
                        }
                        trades.append({
                            'date': current_date, 'action': 'BUY',
                            'ticker': ticker, 'price': cand['price'], 'amount': invest_amount
                        })

        # Record History
        equity_eod = capital + sum(p['shares']*last_known_prices[pt] for pt, p in portfolio.items() if pt in last_known_prices)
        history.append({'date': current_date, 'equity': equity_eod})

    # Final Report Generation
    final_equity = history[-1]['equity']
    total_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    history_df = pd.DataFrame(history)
    history_df['year'] = history_df['date'].apply(lambda x: x.year)
    
    trades_by_year = {}
    for t in trades:
        y = t['date'].year
        if y not in trades_by_year: trades_by_year[y] = []
        trades_by_year[y].append(t)
        
    report_lines = [
        "# BÁO CÁO CHI TIẾT GIAO DỊCH AEGIS TURBO (MAX PROFIT)",
        f"**Vốn Ban Đầu:** ${INITIAL_CAPITAL:,.2f}",
        f"**Vốn Cuối Cùng:** ${final_equity:,.2f}",
        f"**Tổng Lợi Nhuận:** {total_return:.2f}%",
        "---"
    ]
    
    for year in sorted(list(set(history_df['year']))):
        year_data = history_df[history_df['year'] == year]
        if year_data.empty: continue
        start_eq = year_data.iloc[0]['equity']
        end_eq = year_data.iloc[-1]['equity']
        profit = end_eq - start_eq
        ret_pct = (profit / start_eq) * 100
        
        eq_curve = year_data['equity'].values
        mdd = np.min((eq_curve - np.maximum.accumulate(eq_curve)) / np.maximum.accumulate(eq_curve) * 100)
        
        y_trades = trades_by_year.get(year, [])
        wins = [t for t in y_trades if t['action'] == 'SELL' and t['profit'] > 0]
        losses = [t for t in y_trades if t['action'] == 'SELL' and t['profit'] <= 0]
        count = len(wins) + len(losses)
        win_rate = (len(wins)/count*100) if count > 0 else 0
        
        report_lines.append(f"## NĂM {year}")
        report_lines.append(f"- **Lợi Nhuận:** ${profit:,.2f} ({ret_pct:+.2f}%) | **Vốn:** ${end_eq:,.2f}")
        report_lines.append(f"- **Drawdown:** {mdd:.2f}% | **Lệnh:** {count} (Thắng: {len(wins)} | Thua: {len(losses)}) | **WinRate:** {win_rate:.2f}%")
        
        if count > 0:
            report_lines.append("\n| Ngày | Mã | Hành Động | Giá | PnL ($) |")
            report_lines.append("|---|---|---|---|---|")
            for t in y_trades:
                date_str = t['date'].strftime('%Y-%m-%d')
                pnl = f"${t['profit']:,.2f}" if 'profit' in t else "-"
                action = t['action']
                icon = "✅" if ('profit' in t and t['profit'] > 0) else ("❌" if 'profit' in t else "")
                report_lines.append(f"| {date_str} | **{t['ticker']}** | {action} | ${t['price']:.2f} | {icon} {pnl} |")
        report_lines.append("---\n")
        
    print("Generating DETAILED_REPORT.md...")
    with open("DETAILED_REPORT.md", "w", encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    print("Done.")

if __name__ == "__main__":
    main()
