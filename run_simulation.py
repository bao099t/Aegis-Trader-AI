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
    print("    AEGIS ZENITH LONG-SHORT (12-YEAR)    ")
    print("      Dynamic Alpha Discovery (DAD)     ")
    print("            (2014 - 2026)                ")
    print("=========================================")
    
    # Configuration
    USE_AI = True
    predictor = PricePredictor(mode="hybrid")
    
    BROAD_UNIVERSE = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'LINK-USD',
        'NVDA', 'TSLA', 'AMZN', 'AAPL', 'MSFT', 'AMD', 'MSTR', 'GOOGL', 'META',
        'GC=F', 'CL=F'
    ]
    
    DATA_START_DATE = "2013-01-01" 
    START_DATE = "2014-01-01"
    END_DATE = "2026-12-31" 
    INITIAL_CAPITAL = 10000.0
    MAX_POSITIONS = 4 
    ALLOCATION_PER_TRADE = 0.30 
    
    # Phase 48: Ultimate Reality Audit (Double Friction)
    APPLY_REALITY_COSTS = True # Toggle for Truth Mode
    COMMISSION_RATE = 0.002    # 0.2% per trade (Double Fee)
    SLIPPAGE_RATE = 0.002      # 0.2% slippage (Double Penalty)
    
    # Phase 51: Leverage Stress Test
    LEVERAGE = 1.5             # 1.5x (Zenith Turbo Mode)
    
    # Initialize
    loader = DataLoader() 
    strategy = DailySurferStrategy()
    selector = AssetSelector(broad_universe=BROAD_UNIVERSE)
    
    data_map = {}
    print(f"Loading data for {len(BROAD_UNIVERSE)} assets...")
    for ticker in BROAD_UNIVERSE:
        df = loader.fetch_data(ticker, DATA_START_DATE, END_DATE)
        if df is not None and not df.empty:
            df = strategy.prepare_data(df)
            data_map[ticker] = df
            
    capital = INITIAL_CAPITAL
    portfolio = {}
    trades = []
    history = []
    reentry_guard = {}
    
    active_tickers = selector.get_top_alpha(data_map, pd.to_datetime(START_DATE), top_n=5)
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq='B')
    trading_day_count = 0
    
    for current_date in dates:
        trading_day_count += 1
        if trading_day_count % 30 == 0:
            active_tickers = selector.get_top_alpha(data_map, current_date, top_n=5)

        daily_candidates = []
        last_known_prices = {}
        
        # Calculate Equity & Mark-to-Market
        current_equity = capital
        for t, p in portfolio.items():
            df_t = data_map.get(t)
            if df_t is not None and current_date in df_t.index:
                price_t = df_t.loc[current_date]['Close']
                last_known_prices[t] = price_t
                if p['side'] == 'LONG':
                    current_equity += p['shares'] * price_t
                    portfolio[t]['high_water'] = max(p['high_water'], price_t)
                else: # SHORT
                    # Value = Entry Capital + (Entry Price - Current Price) * shares
                    current_equity += p['shares'] * (2 * p['entry_price'] - price_t)
                    portfolio[t]['low_water'] = min(p.get('low_water', price_t), price_t)
            else:
                # Use last known equity value for that position
                if p['side'] == 'LONG': current_equity += p['shares'] * p['high_water']
                else: current_equity += p['shares'] * (2 * p['entry_price'] - p.get('low_water', p['entry_price']))

        # Scan for Signals
        for ticker in BROAD_UNIVERSE:
            if ticker not in data_map: continue
            df_i = data_map[ticker]
            if ticker not in active_tickers and ticker not in portfolio: continue
            
            if current_date in df_i.index:
                row = df_i.loc[current_date]
                price = row['Close']
                last_known_prices[ticker] = price
                
                # Indicators
                sma50 = row.get('SMA_50')
                sma200 = row.get('SMA_200')
                sma20 = row.get('SMA_20')
                atr = row.get('ATR', price * 0.05)
                adx = row.get('ADX', 0)
                rsi = row.get('RSI', 50)
                
                if pd.isna(sma50) or pd.isna(sma20) or pd.isna(sma200): continue
                
                # EXIT / COVER Logic (Phase 43.6: Squeeze Protection)
                is_exit = False
                if ticker in portfolio:
                    pos = portfolio[ticker]
                    if pos['side'] == 'LONG':
                        hw = pos['high_water']
                        if price < (hw - 3.2 * atr): is_exit = True
                        elif price < sma20 and (price/pos['entry_price'] - 1) < -0.04: is_exit = True
                    else: # SHORT
                        lw = pos['low_water']
                        # Tighter exit for shorts (2.0x ATR) to avoid parabolic squeezes
                        if price > (lw + 2.0 * atr): is_exit = True
                        elif price > sma20: is_exit = True
                
                # ENTRY / SHORT Logic (Phase 43.6: Precision Filtering)
                is_entry = False
                is_short_entry = False
                if ticker not in portfolio:
                    if ticker in reentry_guard:
                        if (current_date - reentry_guard[ticker]).days < 3: continue
                    
                    if adx > 18:
                        if price > sma50: 
                            is_entry = rsi < 78
                        elif price < sma50: # Phase 43.6: Vulture Shorting (Below SMA50)
                            # Avoid shorting oversold (RSI < 30) - wait for bounce or consolidation
                            is_short_entry = rsi > 45 and adx > 20
                    elif adx < 12:
                        is_entry = (rsi < 28) and (price < row.get('BB_Lower', price))

                # AI Integration (Phase 43.6: Guided Shorts)
                ai_score = 0
                hybrid_signal = None
                if USE_AI and (is_entry or is_short_entry):
                    current_df_slice = df_i.loc[:current_date]
                    hybrid_signal, _ = predictor.predict_from_df(current_df_slice)
                    if isinstance(hybrid_signal, dict):
                        n_dir = hybrid_signal['neural_dir']
                        rf_p = hybrid_signal['rf_prob']
                        
                        if is_entry:
                            if n_dir == "DOWN": is_entry = False
                            else: ai_score = rf_p + (1.0 if n_dir == "UP" else 0)
                        
                        if is_short_entry:
                            # Guided Shorts: Neural MUST be DOWN, RF > 0.70
                            if n_dir != "DOWN" or rf_p < 0.70: 
                                is_short_entry = False
                            else: 
                                ai_score = rf_p * 0.95 # High priority for precision shorts
                    else:
                        is_entry = False
                        is_short_entry = False

                daily_candidates.append({
                    'ticker': ticker, 'is_entry': is_entry, 'is_short_entry': is_short_entry,
                    'is_exit': is_exit, 'price': price, 'ai_score': ai_score,
                    'priority': 1 if is_entry else 2, 'hybrid_signal': hybrid_signal
                })

        # Execute Exits
        for cand in daily_candidates:
            ticker = cand['ticker']
            if ticker in portfolio and cand['is_exit']:
                pos = portfolio[ticker]
                shares = pos['shares']
                side = pos['side']
                
                exit_price = cand['price']
                if APPLY_REALITY_COSTS:
                    # Penalty: Sell lower for longs, buy higher for shorts
                    exit_price *= (1 - SLIPPAGE_RATE) if side == 'LONG' else (1 + SLIPPAGE_RATE)
                
                if side == 'LONG':
                    proceeds = shares * exit_price
                    profit_raw = proceeds - pos['cost_basis']
                else: # SHORT
                    # Profit = (Entry - Exit) * shares
                    profit_actual = shares * (pos['entry_price'] - exit_price)
                    proceeds = (shares * pos['entry_price']) + profit_actual
                    profit_raw = proceeds - pos['cost_basis']

                fee = (proceeds * COMMISSION_RATE) if APPLY_REALITY_COSTS else 0
                net_proceeds = proceeds - fee
                net_profit = net_proceeds - pos['cost_basis']
                
                capital += net_proceeds
                trades.append({
                    'date': current_date, 'action': 'SELL' if side == 'LONG' else 'COVER',
                    'ticker': ticker, 'price': exit_price, 'profit': net_profit, 'fee': fee, 'side': side
                })
                del portfolio[ticker]
                reentry_guard[ticker] = current_date

        # Execute Entries
        daily_candidates.sort(key=lambda x: (x['priority'], -x['ai_score']))
        top_N = [c['ticker'] for c in daily_candidates if c['is_entry'] or c['is_short_entry']][:MAX_POSITIONS]
        
        for cand in daily_candidates:
            ticker = cand['ticker']
            if (cand['is_entry'] or cand['is_short_entry']) and ticker in top_N:
                if len(portfolio) < MAX_POSITIONS:
                    side = 'LONG' if cand['is_entry'] else 'SHORT'
                    
                    # Phase 51: Leverage Logic (Margin)
                    # Base allocation based on EQUITY, not Cash
                    target_size = current_equity * ALLOCATION_PER_TRADE * LEVERAGE
                    
                    # Check Global Leverage Limit (Safety)
                    # approximate current exposure
                    current_exposure = sum([p['shares'] * last_known_prices.get(t, p['entry_price']) for t, p in portfolio.items()])
                    max_total_exposure = current_equity * LEVERAGE * 0.95 # Buffer
                    
                    remaining_exposure_capacity = max(0, max_total_exposure - current_exposure)
                    invest_amount = min(target_size, remaining_exposure_capacity)
                    
                    if isinstance(cand['hybrid_signal'], dict):
                        h = cand['hybrid_signal']
                        if side == 'LONG' and h['neural_dir'] == "UP" and h['rf_prob'] > 0.70: invest_amount *= 1.2 # Turbo Boost
                    
                    # With leverage, Capital (Cash) can go negative (Margin Debt)
                    # So we allow invest_amount to exceed capital
                    
                    if invest_amount > 100:
                        entry_price = cand['price']
                        if APPLY_REALITY_COSTS:
                            # Penalty: Buy higher for longs, sell lower for shorts
                            entry_price *= (1 + SLIPPAGE_RATE) if side == 'LONG' else (1 - SLIPPAGE_RATE)
                        
                        shares = invest_amount / entry_price
                        fee = (invest_amount * COMMISSION_RATE) if APPLY_REALITY_COSTS else 0
                        capital -= (invest_amount + fee)
                        
                        portfolio[ticker] = {
                            'shares': shares, 'entry_price': entry_price, 
                            'cost_basis': invest_amount + fee, 'high_water': entry_price, 
                            'low_water': entry_price, 'side': side
                        }
                        trades.append({
                            'date': current_date, 'action': 'BUY' if side == 'LONG' else 'SHORT',
                            'ticker': ticker, 'price': entry_price, 'amount': invest_amount, 'fee': fee, 'side': side
                        })

        history.append({'date': current_date, 'equity': current_equity})

    # Final Report Engine (Restored Comprehensive Reporting)
    final_equity = history[-1]['equity']
    total_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Calculate Yearly Statistics
    history_df = pd.DataFrame(history)
    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df.set_index('date', inplace=True)
    
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df['date'] = pd.to_datetime(trades_df['date'])
    
    report = []
    report.append("# BÁO CÁO CHI TIẾT GIAO DỊCH AEGIS ZENITH (LONG-SHORT REALITY)")
    report.append(f"**Vốn Ban Đầu:** ${INITIAL_CAPITAL:,.2f}")
    report.append(f"**Vốn Cuối Cùng:** ${final_equity:,.2f}")
    report.append(f"**Tổng ROI:** {total_return:,.2f}% (Đã khấu trừ Phí & Trượt giá)")
    report.append("---\n")
    
    years = history_df.index.year.unique()
    for year in years:
        year_history = history_df[history_df.index.year == year]
        start_val = year_history['equity'].iloc[0]
        end_val = year_history['equity'].iloc[-1]
        year_pnl = end_val - start_val
        year_pct = (year_pnl / start_val) * 100
        
        # Yearly Drawdown
        rolling_max = year_history['equity'].cummax()
        drawdown = (year_history['equity'] - rolling_max) / rolling_max * 100
        max_dd = drawdown.min()
        
        # Yearly Trades
        year_trades = trades_df[trades_df['date'].dt.year == year] if not trades_df.empty else pd.DataFrame()
        # Count Closed Trades (SELL or COVER)
        closed_trades = year_trades[year_trades['action'].isin(['SELL', 'COVER'])]
        total_closed = len(closed_trades)
        winners = len(closed_trades[closed_trades['profit'] > 0])
        win_rate = (winners / total_closed * 100) if total_closed > 0 else 0
        
        report.append(f"## NĂM {year}")
        report.append(f"- **Lợi Nhuận:** ${year_pnl:,.2f} ({year_pct:.2f}%) | **Vốn:** ${end_val:,.2f}")
        report.append(f"- **Drawdown:** {max_dd:.2f}% | **Lệnh:** {total_closed} (Thắng: {winners}) | **WinRate:** {win_rate:.2f}%")
        report.append("\n| Ngày | Mã | Lệnh | Side | Giá | Phí | PnL |")
        report.append("| --- | --- | --- | --- | --- | --- | --- |")
        
        for _, t in year_trades.tail(20).iterrows(): # Show last 20 trades per year for brevity
            pnl_val = t.get('profit', 0)
            pnl_sym = "✅" if pnl_val > 0 else ("❌" if pnl_val < 0 else "-")
            pnl_str = f"{pnl_sym} ${pnl_val:,.2f}" if t['action'] in ['SELL', 'COVER'] else "-"
            
            fee_str = f"${t.get('fee', 0):.2f}"
            price_str = f"${t['price']:.2f}"
            
            report.append(f"| {t['date'].date()} | **{t['ticker']}** | {t['action']} | {t['side']} | {price_str} | {fee_str} | {pnl_str} |")
        report.append("\n")

    with open("DETAILED_REPORT.md", "w", encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"\nTerminal Equity: ${final_equity:,.2f}")
    print(f"Terminal ROI: {total_return:.2f}%")

if __name__ == "__main__":
    main()
