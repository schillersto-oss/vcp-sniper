import yfinance as yf
import pandas as pd

def get_sector_performance():
    # SPDR Sector ETFs
    sectors = {
        'XLC': 'Communication Services',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLE': 'Energy',
        'XLF': 'Financials',
        'XLV': 'Health Care',
        'XLI': 'Industrials',
        'XLB': 'Materials',
        'XLRE': 'Real Estate',
        'XLK': 'Technology',
        'XLU': 'Utilities',
        'SPY': 'S&P 500'
    }
    
    print("Fetching Sector Data...")
    data = []
    
    for ticker, name in sectors.items():
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if df.empty:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            close = df['Close']
            
            # Calculate Performance
            perf_1d = close.pct_change(1).iloc[-1] * 100
            perf_1w = close.pct_change(5).iloc[-1] * 100
            perf_1m = close.pct_change(21).iloc[-1] * 100
            perf_3m = close.pct_change(63).iloc[-1] * 100
            perf_1y = close.pct_change(252).iloc[-1] * 100
            
            data.append({
                'Ticker': ticker,
                'Sector': name,
                '1D %': perf_1d,
                '1W %': perf_1w,
                '1M %': perf_1m,
                '3M %': perf_3m,
                '1Y %': perf_1y
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            
    df_perf = pd.DataFrame(data)
    df_perf = df_perf.sort_values(by='1M %', ascending=False)
    return df_perf

if __name__ == "__main__":
    df = get_sector_performance()
    print(df)
    df.to_csv("sector_performance.csv", index=False)
