import os
import pandas as pd
import mplfinance as mpf
import google.generativeai as genai
from config import GEMINI_API_KEY, CHARTS_DIR
import json
import time
import PIL.Image
from screener import fetch_data, calculate_technicals

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an expert technical analyst specializing in Mark Minervini's Volatility Contraction Pattern (VCP). 
Input: I will provide a chart image and momentum stats. 
Task: Grade the setup from 0-100 based on "Tightness" and "Volume." 

Strict Criteria:
1. Trend: Price must be above the rising 20-day and 50-day SMA.
2. VCP Contraction: Look for 2-4 contractions, where each pullback is smaller than the last (e.g., -15%, then -8%, then -3%).
3. Volume Dry-Up: Volume in the final tight area must be below the 50-day average.

Output: JSON only. 
{ 
  "score": 85, 
  "verdict": "BUY_WATCH", 
  "pivot_price": 145.20, 
  "stop_loss": 139.50,
  "reasoning": "Brief explanation of the grade."
}
"""

def generate_chart(ticker, df):
    """Generates a 6-month candlestick chart with SMAs and Volume."""
    # Filter last 6 months (approx 126 trading days)
    df_chart = df.tail(126).copy()
    
    # Ensure output directory exists
    os.makedirs(CHARTS_DIR, exist_ok=True)
    
    # Create output path
    filepath = os.path.join(CHARTS_DIR, f"{ticker}.png")
    
    # Custom Style
    mc = mpf.make_marketcolors(up='g', down='r', inherit=True)
    s = mpf.make_mpf_style(marketcolors=mc)
    
    # Add SMAs
    apds = [
        mpf.make_addplot(df_chart['SMA_50'], color='blue', width=1.5),
        mpf.make_addplot(df_chart['SMA_200'], color='black', width=1.5)
    ]
    
    mpf.plot(
        df_chart,
        type='candle',
        style=s,
        volume=True,
        addplot=apds,
        title=f"{ticker} - VCP Analysis",
        savefig=filepath
    )
    return filepath

def analyze_chart(ticker, image_path):
    """Sends chart to Gemini for VCP analysis."""
    print(f"DEBUG: Analyzing {ticker}...")
    print(f"DEBUG: API Key present: {bool(GEMINI_API_KEY)}")
    
    if not GEMINI_API_KEY:
        print("Skipping analysis: No GEMINI_API_KEY found.")
        return {"error": "No API Key"}
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    img = PIL.Image.open(image_path)
    
    try:
        response = model.generate_content([SYSTEM_PROMPT, img])
        text = response.text
        
        # Clean markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        return json.loads(text)
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return {"error": f"Exception: {str(e)}"}

def generate_market_sentiment(context):
    """Generates a 3-line market sentiment summary using Gemini."""
    if not GEMINI_API_KEY:
        return ["Error: No API Key"]
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a cynical, expert hedge fund trader (like from 'The Big Short').
    Analyze this market data and give me 3 short, punchy bullet points on the current market sentiment.
    
    Data:
    - VIX: {context.get('vix', 'N/A')}
    - Market Breadth (>SMA50): {context.get('breadth_50', 'N/A')}%
    - Market Breadth (>SMA200): {context.get('breadth_200', 'N/A')}%
    - Momentum Leaders Avg Change: {context.get('mom_change', 'N/A')}%
    - Top Sector: {context.get('top_sector', 'N/A')}
    
    Format:
    - Just 3 short lines.
    - No intro/outro.
    - Be direct, use trader slang (e.g., "Risk On", "Frothy", "Oversold").
    - Example:
    "AI Bubble is expanding."
    "VIX asleep, complacency high."
    "Tech leading, breadth weak."
    """
    
    try:
        response = model.generate_content(prompt)
        lines = [line.strip().strip('- ') for line in response.text.strip().split('\\n') if line.strip()]
        return lines[:3]
    except Exception as e:
        return [f"Error generating sentiment: {str(e)}"]

def run_vision_check(candidates_file="candidates.csv"):
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return
    
    # Filter for LONG candidates only for VCP check
    longs = df[df['Side'] == 'LONG']
    
    if longs.empty:
        print("No Long candidates to analyze.")
        return

    # Take top 5 Longs for demo/rate limiting
    top_longs = longs.head(5)
    
    results = []
    
    print(f"Starting Vision Check on {len(top_longs)} candidates...")
    
    for _, row in top_longs.iterrows():
        ticker = row['Ticker']
        print(f"Processing {ticker}...")
        
        # Fetch Data (need fresh data for chart)
        data = fetch_data(ticker)
        if data is None:
            continue
        data = calculate_technicals(data)
        
        # Generate Chart
        chart_path = generate_chart(ticker, data)
        print(f"  Chart saved to {chart_path}")
        
        # Analyze
        analysis = analyze_chart(ticker, chart_path)
        if analysis and "error" not in analysis:
            print(f"  Gemini Verdict: {analysis.get('score')} - {analysis.get('verdict')}")
            analysis['Ticker'] = ticker
            results.append(analysis)
        elif analysis and "error" in analysis:
             print("  Analysis skipped (No API Key).")
             break
            
        time.sleep(2) # Rate limiting
        
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv("vision_results.csv", index=False)
        return results_df
    return pd.DataFrame()

if __name__ == "__main__":
    res = run_vision_check()
    if not res.empty:
        print("\nVision Analysis Results:")
        print(res)
