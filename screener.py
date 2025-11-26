import yfinance as yf
import pandas as pd
import numpy as np
import requests
from io import StringIO

def get_sp500_tickers():
    """Fetches S&P 500 tickers and sectors from Wikipedia."""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        
        # Find the table with 'Symbol' and 'GICS Sector'
        df = None
        for t in tables:
            if 'Symbol' in t.columns and 'GICS Sector' in t.columns:
                df = t
                break
        
        if df is None:
            print("Could not find S&P 500 table with 'Symbol' column.")
            # Fallback
            return pd.DataFrame({'Symbol': ['NVDA', 'TSLA', 'AAPL'], 'Sector': ['Technology', 'Consumer Discretionary', 'Technology']})
            
        # Rename columns
        df = df[['Symbol', 'GICS Sector']].rename(columns={'GICS Sector': 'Sector'})
        return df
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")
        return pd.DataFrame({'Symbol': ['NVDA', 'TSLA', 'AAPL'], 'Sector': ['Technology', 'Consumer Discretionary', 'Technology']})

def fetch_data(ticker):
    """Fetches 2 years of daily data for a ticker."""
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df.empty:
            return None
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
             df.columns = df.columns.get_level_values(0)
             
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def calculate_technicals(df):
    """Calculates SMAs, RSI, and RS."""
    if len(df) < 200:
        return None
    
    # Ensure unique columns
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Check if Close is unique
    if isinstance(df['Close'], pd.DataFrame):
        df['Close'] = df['Close'].iloc[:, 0]
    
    # SMAs
    try:
        df['SMA_50'] = df['Close'].rolling(window=50, min_periods=50).mean()
        df['SMA_150'] = df['Close'].rolling(window=150, min_periods=150).mean()
        df['SMA_200'] = df['Close'].rolling(window=200, min_periods=200).mean()
    except Exception as e:
        print(f"Error calculating SMAs: {e}")
        return None
    
    # 52-week High/Low (252 trading days)
    df['52_Week_High'] = df['Close'].rolling(window=252, min_periods=200).max()
    df['52_Week_Low'] = df['Close'].rolling(window=252, min_periods=200).min()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Relative Strength (Simple ROC)
    df['RS_1D'] = df['Close'].pct_change(periods=1) * 100
    df['RS_1W'] = df['Close'].pct_change(periods=5) * 100
    df['RS_1M'] = df['Close'].pct_change(periods=21) * 100
    df['RS_3M'] = df['Close'].pct_change(periods=63) * 100
    df['RS_1Y'] = df['Close'].pct_change(periods=252) * 100
    
    # Volume and RVOL
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
    # Handle division by zero
    df['RVOL'] = np.where(df['Vol_SMA_20'] > 0, df['Volume'] / df['Vol_SMA_20'], 0)
    
    return df

def check_minervini_trend(df):
    """Checks Minervini's Trend Template criteria (Lite Version)."""
    current = df.iloc[-1]
    
    # 1. Price > SMA200
    c1 = current['Close'] > current['SMA_200']
    
    # 2. Price > SMA50
    c2 = current['Close'] > current['SMA_50']
    
    # 3. Price within 35% of 52-week high
    c4 = current['Close'] >= (0.65 * current['52_Week_High'])
    
    # 4. SMA50 > SMA200
    c5 = current['SMA_50'] > current['SMA_200']
    
    return c1 and c2 and c4

def check_qullamaggie_momentum(df):
    """Checks Qullamaggie's momentum criteria."""
    current = df.iloc[-1]
    
    # 1. RSI > 50
    c1 = current['RSI'] > 50
    
    # 2. 1-month change > 0%
    c2 = current['RS_1M'] > 0
    
    return c1 and c2

def check_minervini_downtrend(df):
    """Checks for Stage 4 Downtrend (Short Setup)."""
    current = df.iloc[-1]
    
    # 1. Price < SMA200
    c1 = current['Close'] < current['SMA_200']
    
    # 2. Price < SMA50
    c2 = current['Close'] < current['SMA_50']
    
    # 3. SMA50 < SMA200
    c3 = current['SMA_50'] < current['SMA_200']
    
    # 4. Price within 25% of 52-week Low
    c4 = current['Close'] <= (1.25 * current['52_Week_Low'])
    
    return c1 and c2 and c3 and c4

def check_momentum_short(df):
    """Checks for negative momentum."""
    current = df.iloc[-1]
    
    # 1. RSI < 50
    c1 = current['RSI'] < 50
    
    # 2. 1-month change < 0%
    c2 = current['RS_1M'] < 0
    
    return c1 and c2

def run_screener():
    print("Fetching tickers...")
    sp500_df = get_sp500_tickers()
    tickers = sp500_df['Symbol'].tolist()
    
    print(f"Screening {len(tickers)} tickers...")
    
    candidates = []
    breadth_stats = {'Above_SMA50': 0, 'Above_SMA200': 0, 'Total': 0}
    
    def process_ticker(ticker):
        df = fetch_data(ticker)
        if df is None:
            return None, False, False
        
        df = calculate_technicals(df)
        if df is None:
            return None, False, False
            
        # Breadth Check
        current = df.iloc[-1]
        above_50 = current['Close'] > current['SMA_50'] if not pd.isna(current['SMA_50']) else False
        above_200 = current['Close'] > current['SMA_200'] if not pd.isna(current['SMA_200']) else False
            
        # Calculate common metrics
        rs_1d = df['RS_1D'].iloc[-1]
        rs_1w = df['RS_1W'].iloc[-1]
        rs_1m = df['RS_1M'].iloc[-1]
        rs_3m = df['RS_3M'].iloc[-1]
        rs_1y = df['RS_1Y'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        price = df['Close'].iloc[-1]
        high_52 = df['52_Week_High'].iloc[-1]
        rvol = df['RVOL'].iloc[-1]
        
        # Try to get earnings date (slow, maybe skip for now or do lightweight)
        # For now, placeholder or basic check if we had data
        earnings_date = "N/A" 
        
        candidate_data = None
        
        # Check LONG
        if check_minervini_trend(df):
            if check_qullamaggie_momentum(df):
                candidate_data = {
                    'Ticker': ticker,
                    'Side': 'LONG',
                    'Price': price,
                    'RVOL': rvol,
                    'RSI': rsi,
                    'RS_1D': rs_1d,
                    'RS_1W': rs_1w,
                    'RS_1M': rs_1m,
                    'RS_3M': rs_3m,
                    'RS_1Y': rs_1y,
                    '52W_High': high_52,
                    'Earnings': earnings_date
                }
        
        # Check SHORT
        elif check_minervini_downtrend(df):
            if check_momentum_short(df):
                candidate_data = {
                    'Ticker': ticker,
                    'Side': 'SHORT',
                    'Price': price,
                    'RVOL': rvol,
                    'RSI': rsi,
                    'RS_1D': rs_1d,
                    'RS_1W': rs_1w,
                    'RS_1M': rs_1m,
                    'RS_3M': rs_3m,
                    'RS_1Y': rs_1y,
                    '52W_High': high_52,
                    'Earnings': earnings_date
                }
                
        return candidate_data, above_50, above_200

    # Sequential execution
    results = []
    for ticker in tickers:
        res, abv50, abv200 = process_ticker(ticker)
        breadth_stats['Total'] += 1
        if abv50: breadth_stats['Above_SMA50'] += 1
        if abv200: breadth_stats['Above_SMA200'] += 1
        
        if res:
            results.append(res)
            
    # Save Breadth Stats
    breadth_df = pd.DataFrame([breadth_stats])
    breadth_df['Pct_Above_SMA50'] = (breadth_df['Above_SMA50'] / breadth_df['Total']) * 100
    breadth_df['Pct_Above_SMA200'] = (breadth_df['Above_SMA200'] / breadth_df['Total']) * 100
    breadth_df.to_csv("market_breadth.csv", index=False)
    
    for r in results:
        if r:
            candidates.append(r)
            
    # Convert to DataFrame
    results_df = pd.DataFrame(candidates)
    
    if results_df.empty:
        print("No candidates found.")
        return pd.DataFrame()
        
    # Merge Sector Data
    results_df = results_df.merge(sp500_df, left_on='Ticker', right_on='Symbol', how='left')
    if 'Symbol' in results_df.columns:
        results_df = results_df.drop(columns=['Symbol'])
        
    # Rank by 3-Month Relative Strength
    results_df = results_df.sort_values(by='RS_3M', ascending=False)
    
    return results_df

if __name__ == "__main__":
    df = run_screener()
    if not df.empty:
        print("\nTop Candidates:")
        print(df.head(20))
        df.to_csv("candidates.csv", index=False)
    else:
        print("No stocks passed the screener.")
