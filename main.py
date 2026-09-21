import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import subprocess
import math

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
    #df.loc[(df["sma_fast"] < df["sma_slow"]) , (df["RSI"] > rsi_sell), "signal"] = -1
    
    df.loc[(df["sma_fast"] > df["sma_slow"]), "signal"] = 1
    df.loc[(df["sma_fast"] < df["sma_slow"]), "signal"] = 0
   
    df["signal_change"] = df["signal"].diff().shift(1)
    
    df["stop_ma"] = df["Close"].rolling(150).mean()
    return df

# def compute_rsi(df, length=14):
#     delta = df['Close'].diff()
#     gain = delta.clip(lower=0)
#     loss = -delta.clip(upper=0)
#
#     avg_gain = gain.rolling(length).mean()
#     avg_loss = loss.rolling(length).mean()
#
#     rs = avg_gain / avg_loss
#     rsi = 100 - (100 / (1 + rs))
#     return rsi


def trade_loop(df, starting_capital=10000.0, position_size=1.0, transaction_fee=0.001):
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

                # simulated transaction fee
                transaction_cost = shares_held * price * transaction_fee
                
                cost = (shares_held * price) + transaction_cost
                cash -= cost
                open_trade = ("buy", date, price, shares_held, transaction_cost)

        elif open_trade is not None:
            

            stop_price = row.stop_ma
            if signal == -1 or price < stop_price:
                sell_price = price

                transaction_cost = shares_held * price * transaction_fee
                
                revenue = (shares_held * sell_price) - transaction_cost
                cash += revenue

                # profit and loss includes both buy and sell fees 
                pnl = revenue - (open_trade[2] * shares_held + open_trade[4])

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

def calculate_risk_metrics(capital_series):
    capital = list(capital_series)

    # calculate daily returns
    returns = []

    for i in range(1, len(capital)):
        daily_return = (capital[i] / capital[i-1])-1
        returns.append(daily_return)


    # calculate volatility
    mean_return = sum(returns)/len(returns)
    count = 0
    for r in returns:
        count += (r-mean_return) ** 2
        
    variance = count / len(returns)
    daily_volatility = math.sqrt(variance)

    # 252 is number of trading days
    annual_volatilty = daily_volatility * math.sqrt(252)

    # calculate drawdown

    maximum_drawdown = 0
    peak = capital[0]

    for value in capital:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak

        if drawdown < maximum_drawdown:
            maximum_drawdown = drawdown

    # calculate sharpe: return/standard deviation

    if daily_volatility != 0:
        annual_sharpe = (mean_return/daily_volatility) * math.sqrt(252)
    else:
        annual_sharpe = 0

    return(annual_volatilty, maximum_drawdown, annual_sharpe)

def plot_stocks(stock_data_list):
    for df, trades, label, color in stock_data_list:
        plt.figure(figsize=(10, 4))
        plt.plot(df.index, df["Close"], color=color, label=label)
        
        for buy_trade, sell_trade, pnl in trades:
            plt.scatter(buy_trade[1], buy_trade[2], color="green", marker="^") 
            plt.scatter(sell_trade[1], sell_trade[2], color="red", marker="v")
            
        plt.title(f"{label} Trades")
        plt.legend()
        
    plt.show()


def calculate_noalgorithm_trade(ticker, df_ticker, investment_per_ticker):
    start_price = df_ticker.iloc[0]["Close"]
    end_price = df_ticker.iloc[-1]["Close"]
    shares_held = investment_per_ticker // start_price
    total_gain = shares_held * (end_price - start_price)
    
    invested_amount = shares_held * start_price
    dividend_gain = invested_amount * average_dividend_yield * years_held
    
    remaining_money = investment_per_ticker - invested_amount
    buy_hold = (df_ticker["Close"] * shares_held) + remaining_money
    
    return total_gain, dividend_gain, buy_hold


def calculate_yearly_return(end_price, start_price, length):
    return(end_price/start_price)**(1/length)


investment = 50000

df_list = []
tickers = ["ABBN.SW", "ADM.L", "AV.L", "BATS.L"]

start_date = "2020-01-04"
end_date ="2026-04-04"

average_dividend_yield = 0.045  
years_held = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 365

trades_list = []
profit_list = []
capital_list = []
noalgorithm_list = []
dividend_list = []
buy_hold_list=[]

volatility_list = []
drawdown_list = []
sharpe_list = []


for i in range(len(tickers)):
    try: 
        df_ticker = load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date)
    except FileNotFoundError:
        subprocess.run(["python3", "data/download_data.py", tickers[i]])
        df_ticker = load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date)
    
    df_ticker = compute_signals(df_ticker, tickers[i])
    trade, profit, capital = trade_loop(df_ticker, investment/len(tickers))

    volatility, drawdown, sharpe = calculate_risk_metrics(capital)
    volatility_list.append(volatility)
    drawdown_list.append(drawdown)
    sharpe_list.append(sharpe)

    trades_list.append(trade)
    profit_list.append(profit)
    capital_list.append(capital)

    gain, divs, buy_hold = calculate_noalgorithm_trade(tickers[i], df_ticker, investment/len(tickers))    
    noalgorithm_list.append(gain)
    dividend_list.append(divs)
    buy_hold_list.append(buy_hold)

# align trading days based of date
portfolio_capital = pd.concat(capital_list, axis=1, sort=True).ffill().sum(axis=1) # ffill fills any missing data
buy_hold_capital = pd.concat(buy_hold_list, axis=1, sort=True).ffill().sum(axis=1) # sum to calculate total capital

portfolio_volatility, portfolio_drawdown, portfolio_sharpe = calculate_risk_metrics(portfolio_capital)
buy_hold_volatility, buy_hold_drawdown, buy_hold_sharpe = calculate_risk_metrics(buy_hold_capital)

for i in range(0, len(tickers)):
    print (f"{tickers[i]} Total profit: ${profit_list[i]:.2f}")

total_profit = portfolio_capital.iloc[-1] - investment
algorithm_return = (calculate_yearly_return(portfolio_capital.iloc[-1], investment, years_held)-1)*100

total_buy_hold = investment + sum(noalgorithm_list)
dividend_total = sum(dividend_list)
buy_hold_return = (calculate_yearly_return(total_buy_hold+dividend_total, investment, years_held)-1)*100

print(f"Algorithm Final Capital: ${portfolio_capital.iloc[-1]:.2f} (Return: {algorithm_return:.2f}%)")
print(f"Algorithm Risk Metrics: Sharpe: {portfolio_sharpe:.2f}, Volatility: {portfolio_volatility:.2%} , Max Drawdown: {portfolio_drawdown:.2%}")
print(f"Buy&Hold Final Capital: ${total_buy_hold+dividend_total:.2f} (Return: {buy_hold_return:.2f}% incl. divs)")
print(f"Buy&Hold Risk Metrics: Sharpe: {buy_hold_sharpe:.2f}, Volatility: {buy_hold_volatility:.2%} , Max Drawdown: {buy_hold_drawdown:.2%}")


stock_data_list = [
    (load_stock_data(f"data/{tickers[i]}_daily.csv", start_date, end_date), trades_list[i], tickers[i], "blue")  for i in range(len(tickers))
]

plot_stocks(stock_data_list)