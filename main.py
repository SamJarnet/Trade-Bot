import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import subprocess


plt.style.use('_mpl-gallery')

def load_stock_data(filename, start="2020-01-01", end="2025-12-31"):
    df = pd.read_csv(filename, index_col="Date", parse_dates=True)
    return df[start:end]

def compute_signals(df, name, sma_fast_len=20, sma_slow_len=50, rsi_len=14,
                    rsi_buy=20, rsi_sell=80):
    df = df.copy()
    
    df["sma_fast"] = df["Close"].rolling(sma_fast_len).mean()
    df["sma_slow"] = df["Close"].rolling(sma_slow_len).mean()
    
    # df["RSI"] = compute_rsi(df, rsi_len)
    
    df["signal"] = 0 
    
    #df.loc[(df["sma_fast"] > df["sma_slow"]) & (df["RSI"] < rsi_buy), "signal"] = 1
    #df.loc[(df["sma_fast"] < df["sma_slow"]) | (df["RSI"] > rsi_sell), "signal"] = -1
    
    df.loc[(df["sma_fast"] > df["sma_slow"]), "signal"] = 1
    df.loc[(df["sma_fast"] < df["sma_slow"]), "signal"] = 0
   
    df["signal_change"] = df["signal"].diff()
    
    df["stop_ma"] = df["Close"].rolling(150).mean()
    return df

# def compute_rsi(df, length=14):
#     delta = df['Close'].diff()
#     gain = delta.clip(lower=0)
#     loss = -delta.clip(upper=0)

#     avg_gain = gain.rolling(length).mean()
#     avg_loss = loss.rolling(length).mean()

#     rs = avg_gain / avg_loss
#     rsi = 100 - (100 / (1 + rs))
#     return rsi

def trade_loop(df, starting_capital=10000.0, position_size=1.0):
    cash = starting_capital
    shares_held = 0
    trades = []
    capital_tracker = []  
    open_trade = None
        

    for row in df.itertuples():
        signal = row.signal_change
        price = row.Close
        date = row.Index

        if signal == 1 and open_trade is None:
            investment_amount = cash * position_size
            shares_held = investment_amount // price 
            if shares_held > 0:
                cost = shares_held * price
                cash -= cost
                open_trade = ("buy", date, price, shares_held)

        elif open_trade is not None:
            

            stop_price = row.stop_ma
            if signal == -1 or price < stop_price:
                sell_price = price
                revenue = shares_held * sell_price
                cash += revenue
                
                pnl = (sell_price - open_trade[2]) * shares_held
                sell_trade = ("sell", date, sell_price)
                trades.append((open_trade, sell_trade, pnl))
                
                open_trade = None
                shares_held = 0

        current_valuation = cash + (shares_held * price)
        capital_tracker.append(current_valuation)


    padding_needed = len(df) - len(capital_tracker)
    if padding_needed > 0:
        capital_tracker = [starting_capital] * padding_needed + capital_tracker

    final_profit = capital_tracker[-1] - starting_capital
    return trades, final_profit, pd.Series(capital_tracker, index=df.index)




def plot_stocks(stock_data_list):
    num_stocks = len(stock_data_list)
    fig, axes = plt.subplots(num_stocks, 1, figsize=(12, 4 * num_stocks), sharex=True)
    
    if num_stocks == 1:
        axes = [axes]

    for ax, (df, trades, label, color) in zip(axes, stock_data_list):
        ax.plot(df.index, df["Close"], color=color, label=f"{label} Price", alpha=0.7)

        if trades:
            buy_dates = [t[0][1] for t in trades]
            buy_prices = [t[0][2] for t in trades]
            sell_dates = [t[1][1] for t in trades]
            sell_prices = [t[1][2] for t in trades]

            ax.scatter(buy_dates, buy_prices, marker="^", color="green", s=80, label="Buy", zorder=5)
            ax.scatter(sell_dates, sell_prices, marker="v", color="red", s=80, label="Sell", zorder=5)

        ax.set_ylabel(f"{label} Price")
        ax.legend(loc="upper left")
        ax.grid(True, linestyle='--', alpha=0.6)

    axes[-1].set_xlabel("Date")
    plt.tight_layout()
    plt.show()


def combine_portfolio_capital(capital_series_list):
    combined_index = capital_series_list[0].index
    portfolio_capital = pd.Series(0, index=combined_index)

    for cap in capital_series_list:
        cap_aligned = cap.reindex(combined_index, method='ffill')
        portfolio_capital += cap_aligned

    return portfolio_capital


def calculate_noalgorithm_trade(ticker):
    df = pd.read_csv(f"data/{ticker}_daily.csv", parse_dates=["Date"])
    df = df.sort_values("Date")
    start_price = df.iloc[0]["Close"]
    end_price = df.iloc[-1]["Close"]
    shares_held = (investment / len(tickers)) // start_price
    total_gain = shares_held * (end_price - start_price)
    
    invested_amount = shares_held * start_price
    dividend_gain = invested_amount * average_dividend_yield * years_held
    
    return total_gain, dividend_gain

def calculate_yearly_return(end_price, start_price, length):
    return(end_price/start_price)**(1/length)
    

investment = 50000

df_list = []
tickers = [
     "ABBN.SW", "ADM.L", "AV.L", "BATS.L"
]

start_date = "2020-01-04"
end_date ="2026-04-04"

average_dividend_yield = 0.045  
years_held = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 365

trades_list = []
profit_list = []
capital_list = []
noalgorithm_list = []
dividend_list = []

for i in range(len(tickers)):
    try: 
        df_ticker = load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date)
    except FileNotFoundError:
        subprocess.run(["python3", "data/download_data.py", tickers[i]])
        df_ticker = load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date)
    
    df_ticker = compute_signals(df_ticker, tickers[i])
    trade, profit, capital = trade_loop(df_ticker, investment/len(tickers))
    trades_list.append(trade)
    profit_list.append(profit)
    capital_list.append(capital)
    x, y = calculate_noalgorithm_trade(tickers[i])
    noalgorithm_list.append(x)
    dividend_list.append(y)


portfolio_capital = combine_portfolio_capital(capital_list)

for i in range(0, len(tickers)):
    print (f"{tickers[i]} Total profit: ${profit_list[i]:.2f}")

economy_average = (1.1**(int(end_date[0:4]) - int(start_date[0:4]))) * investment



print("-" * 30)
real_profit = portfolio_capital.iloc[-1] - investment
print(f"Total Portfolio Profit: ${real_profit:.2f}")
print(f"Final Capital: ${portfolio_capital.iloc[-1]:.2f}")
print("Economy average: $", economy_average)
dividend_total = sum(dividend_list)

print(f"Average return of: {(calculate_yearly_return(dividend_total +portfolio_capital.iloc[-1], investment, 5.5)-1)*100:.2f}%")
total_buy_and_hold = investment + sum(noalgorithm_list)
print(f"If you didn't use the algorithm and just held it : ${total_buy_and_hold:.2f} + dividens: {dividend_total}")
print(f"Average return of just holding it including dividends: "
      f"{(calculate_yearly_return(total_buy_and_hold+dividend_total, investment, years_held)-1)*100:.2f}%")

color_palette = ["blue", "purple", "orange", "red", "green", "cyan", "magenta", "brown"]


stock_data_list = [
    (load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date), trades_list[i], tickers[i], random.choice(color_palette))  for i in range(len(tickers))
]


plot_stocks(stock_data_list)


