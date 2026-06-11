import yfinance as yf
import matplotlib.pyplot as plt
import sys

tickers = sys.argv[1:]
print(tickers)

for i in tickers:
    try:
        df = yf.download(i, period="2y")
        df.columns = df.columns.droplevel(1) 
        df.to_csv(f"data/{i}_daily.csv")
    except:
        print("dont add: ", i)