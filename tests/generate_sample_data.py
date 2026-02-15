
import yfinance as yf
import pandas as pd

def generate_sample_data():
    tickers = ["2330.TW", "0050.TW"]
    data = []
    for ticker in tickers:
        df = yf.download(ticker, period="1mo")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        df["Ticker"] = ticker
        data.append(df)
    
    final_df = pd.concat(data)
    final_df.to_csv("tests/data.csv", index=False)
    print("Sample data saved to tests/data.csv")

if __name__ == "__main__":
    generate_sample_data()
