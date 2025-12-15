import streamlit as st
import pandas as pd
import os
import yfinance as yf
from screener import fetch_data, calculate_technicals, run_screener
from vision_analyst import generate_chart, analyze_chart
from sector_monitor import get_sector_performance

# Set page config
st.set_page_config(page_title="VCP Sniper Dashboard", layout="wide")

# Title and Description
st.title("🎯 VCP Sniper Dashboard")
st.markdown("Automated screening for Minervini/Qullamaggie setups.")

# Constants
DATA_FILE = "candidates.csv"
SECTOR_FILE = "sector_performance.csv"
BREADTH_FILE = "market_breadth.csv"

def make_clickable(df):
    if df is None or df.empty:
        return df
    df_display = df.copy()
    if 'Ticker' in df_display.columns:
        df_display['Ticker'] = df_display['Ticker'].apply(
            lambda x: f"https://finance.yahoo.com/quote/{x}"
        )
    return df_display

def color_variant(val):
    """
    Takes a scalar and returns a string with
    the css property `'color: red'` for negative
    strings, green for positive.
    """
    try:
        val = float(val)
        color = 'green' if val >= 0 else 'red'
    except:
        color = 'black'
    return f'color: {color}'

@st.cache_data
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return None

@st.cache_data
def load_sector_data():
    if os.path.exists(SECTOR_FILE):
        return pd.read_csv(SECTOR_FILE)
    return None

@st.cache_data
def load_breadth_data():
    if os.path.exists(BREADTH_FILE):
        return pd.read_csv(BREADTH_FILE)
    return None

# Sidebar - Cloud Controls
st.sidebar.header("☁️ Cloud Controls")
if st.sidebar.button("Run Cloud Screener (Slow)"):
    with st.spinner("Running Screener on 500+ stocks... This takes 2-3 minutes."):
        try:
            # Run Screener
            new_df = run_screener()
            if not new_df.empty:
                new_df.to_csv(DATA_FILE, index=False)
            
            # Run Sector Monitor
            new_sector = get_sector_performance()
            if not new_sector.empty:
                new_sector.to_csv(SECTOR_FILE, index=False)
                
            st.success("Screener Complete! Reloading...")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Screener Failed: {e}")

st.sidebar.divider()

# Load Data
df = load_data()
df_sector = load_sector_data()
df_breadth = load_breadth_data()

# Sidebar Filters
st.sidebar.header("🔍 Filters")

# Macro Indicators
st.sidebar.markdown("### 🌍 Macro Context")
try:
    macro_tickers = {'VIX': '^VIX', '10Y Yield': '^TNX', 'Bitcoin': 'BTC-USD'}
    cols = st.sidebar.columns(3)
    for i, (label, ticker) in enumerate(macro_tickers.items()):
        m_data = yf.Ticker(ticker).history(period='2d')
        if len(m_data) >= 1:
            current = m_data['Close'].iloc[-1]
            prev = m_data['Close'].iloc[-2] if len(m_data) > 1 else current
            delta = current - prev
            cols[i].metric(label, f"{current:.2f}", f"{delta:.2f}")
except Exception as e:
    st.sidebar.error(f"Macro data error: {e}")
st.sidebar.divider()

# Key Events
st.sidebar.markdown("### 📅 Key Events")

# Momentum Leaders Earnings
with st.sidebar.expander("Momentum Leaders 🚀", expanded=True):
    mom_tickers = ['PLTR', 'APP', 'RDDT', 'MSTR', 'COIN', 'NVDA', 'TSLA']
    
    # Fetch data for all at once for speed
    try:
        # Fetch 5d to ensure we have at least 2 days of data
        mom_data = yf.download(mom_tickers, period="5d", progress=False)
        
        # Handle MultiIndex if necessary
        if isinstance(mom_data.columns, pd.MultiIndex):
            closes = mom_data['Close']
            vols = mom_data['Volume']
        else:
            # Fallback if structure is different
            closes = mom_data['Close']
            vols = mom_data['Volume']
        
        # Ensure we have enough data
        if len(closes) >= 2:
            for t in mom_tickers:
                try:
                    # Get latest close and prev close
                    if t in closes.columns:
                        # Drop NaNs for this specific ticker to find last valid prices
                        t_close = closes[t].dropna()
                        t_vol = vols[t].dropna()
                        
                        if len(t_close) >= 2:
                            current = t_close.iloc[-1]
                            prev = t_close.iloc[-2]
                            pct_chg = ((current - prev) / prev) * 100
                            
                            vol = t_vol.iloc[-1]
                            # Format volume (M or K)
                            if vol > 1_000_000:
                                vol_str = f"{vol/1_000_000:.1f}M"
                            else:
                                vol_str = f"{vol/1_000:.0f}K"
                                
                            # Color code
                            color = "green" if pct_chg >= 0 else "red"
                            st.markdown(f"**{t}**: :{color}[{pct_chg:+.2f}%] (Vol: {vol_str})")
                        else:
                            st.write(f"**{t}**: Insufficient Data")
                    else:
                        st.write(f"**{t}**: N/A")
                except Exception as e:
                    st.write(f"**{t}**: -")
        else:
            st.error("Not enough market data returned.")
    except Exception as e:
        st.error(f"Failed to load momentum data: {e}")

with st.sidebar.expander("Economic Events (Est.)", expanded=False):
    st.write("• **FOMC Meeting**: Dec 17-18")
    st.write("• **CPI Release**: Dec 10")
    st.write("• **NFP Report**: Dec 05")
st.sidebar.divider()

# Market Health (Sidebar)
if df_breadth is not None and not df_breadth.empty:
    st.sidebar.markdown("### 🏥 Market Health")
    b_50 = df_breadth['Pct_Above_SMA50'].iloc[0]
    b_200 = df_breadth['Pct_Above_SMA200'].iloc[0]
    
    col_b1, col_b2 = st.sidebar.columns(2)
    col_b1.metric("> SMA50", f"{b_50:.1f}%")
    col_b2.metric("> SMA200", f"{b_200:.1f}%")
    
    if b_50 > 50 and b_200 > 50:
        st.sidebar.success("Market is Healthy 🟢")
    elif b_50 < 30:
        st.sidebar.error("Market is Weak 🔴")
    else:
        st.sidebar.warning("Market is Mixed 🟡")
    st.sidebar.divider()

# Refresh Button
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Check if data loaded
if df is None:
    st.info("👋 Welcome! Please click **'Run Cloud Screener'** in the sidebar to generate data.")
else:
    # Price Filter
    min_price_data, max_price_data = int(df['Price'].min()), int(df['Price'].max())
    
    price_input_mode = st.sidebar.radio("Price Input Mode", ["Slider", "Manual"], horizontal=True)
    
    if price_input_mode == "Slider":
        price_range = st.sidebar.slider("Price Range ($)", min_price_data, max_price_data, (min_price_data, max_price_data))
    else:
        col_p1, col_p2 = st.sidebar.columns(2)
        with col_p1:
            min_price_input = st.number_input("Min Price", min_value=0, max_value=10000, value=min_price_data)
        with col_p2:
            max_price_input = st.number_input("Max Price", min_value=0, max_value=10000, value=max_price_data)
        price_range = (min_price_input, max_price_input)
    
    # Sector Filter
    if 'Sector' in df.columns:
        all_sectors = sorted(df['Sector'].dropna().unique().tolist())
        selected_sectors = st.sidebar.multiselect("Filter by Sector", all_sectors, default=all_sectors)
    else:
        selected_sectors = []
        st.sidebar.warning("Sector data not available.")

    # Time Frame Filter
    time_frame = st.sidebar.selectbox(
        "Select Time Frame",
        ("Day", "Week", "Month", "3 Months", "Year"),
        index=3
    )
    
    # Map Time Frame to Column
    time_frame_map = {
        "Day": "RS_1D",
        "Week": "RS_1W",
        "Month": "RS_1M",
        "3 Months": "RS_3M",
        "Year": "RS_1Y"
    }
    selected_metric = time_frame_map[time_frame]

    # Apply Filters
    filtered_df = df[
        (df['Price'] >= price_range[0]) & 
        (df['Price'] <= price_range[1])
    ]
    
    if selected_sectors:
        filtered_df = filtered_df[filtered_df['Sector'].isin(selected_sectors)]

    # Metrics
    total_candidates = len(filtered_df)
    longs = filtered_df[filtered_df['Side'] == 'LONG']
    shorts = filtered_df[filtered_df['Side'] == 'SHORT']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Candidates", total_candidates)
    col2.metric("Long Setups 🚀", len(longs))
    col3.metric("Short Setups 📉", len(shorts))

    # --- NEW: Sniper's Cockpit (Trade Light, Focus, Catalysts) ---
    st.markdown("### 🎛️ Sniper's Cockpit")
    
    col_cockpit1, col_cockpit2, col_cockpit3 = st.columns(3)

    # 1. Trade Light (Market Internals)
    with col_cockpit1:
        st.markdown("#### 🚦 Trade Light")
        light_color = "red"
        status_msg = "Defensive (Cash is King)"
        
        # Logic: Green if Breadth > 50 AND VIX < 20 (if VIX exists)
        # Simplify: Green > 50% Breadth, Yellow > 30%, Red < 30%
        b_50 = 0
        if df_breadth is not None and not df_breadth.empty:
            b_50 = df_breadth['Pct_Above_SMA50'].iloc[0]
            
        vix_val = 99
        if 'vix' in sentiment_context:
             try:
                 vix_val = float(sentiment_context['vix'])
             except:
                 pass
        
        if b_50 > 50 and vix_val < 25:
            light_color = "green"
            status_msg = "Aggressive (Green Light) 🟢"
        elif b_50 < 30 or vix_val > 30:
            light_color = "red"
            status_msg = "Defensive (Red Light) 🔴"
        else:
            light_color = "orange"
            status_msg = "Caution (Yellow Light) 🟡"
            
        st.info(f"**Status:** {status_msg}")
        if df_breadth is not None:
             st.caption(f"Stocks > SMA50: {b_50:.1f}% | VIX: {vix_val:.2f}")

    # 2. Daily Focus (Top 3)
    with col_cockpit2:
        st.markdown("#### 🎯 Daily Focus")
        if not longs.empty:
            # Rank by a composite score: RS_3M + RVOL (simple proxy)
            # Or just use the sorted 'longs' from filtered results
            top_3 = longs.sort_values(by=selected_metric, ascending=False).head(3)
            
            for i, (idx, row) in enumerate(top_3.iterrows()):
                t = row['Ticker']
                p = row['Price']
                rs = row[selected_metric]
                # Create a mini link
                link = f"https://finance.yahoo.com/quote/{t}"
                st.markdown(f"**{i+1}. [{t}]({link})** (${p:.2f})")
                st.caption(f"RS: {rs:.1f}% | RVOL: {row['RVOL']:.1f}x")
        else:
            st.write("No candidates for focus list.")

    # 3. Catalyst Watch (Earnings)
    with col_cockpit3:
        st.markdown("#### 📅 Catalyst Watch")
        # Check top 5 candidates for earnings
        if not longs.empty:
            top_candidates = longs.head(5) # Limit to top 5 to be fast
            found_catalyst = False
            
            # We need to fetch this live as it's not in CSV deeply
            # Use specific container to avoid re-running widely
            catalyst_container = st.empty()
            
            if st.button("Scan Top 5 for Earnings"):
                events = []
                with st.spinner("Scanning calendars..."):
                    for _, row in top_candidates.iterrows():
                        t = row['Ticker']
                        try:
                            tk = yf.Ticker(t)
                            cal = tk.calendar
                            # Different yfinance versions return different formats (dict or df)
                            # Try to handle generic
                            if cal is not None:
                                # If dataframe
                                if isinstance(cal, pd.DataFrame) and not cal.empty:
                                   # Usually contains 'Earnings Date' or 0
                                   if 0 in cal.columns: # Often date is in first column
                                       next_date = cal.iloc[0][0]
                                   elif 'Earnings Date' in cal.columns:
                                       next_date = cal['Earnings Date'].iloc[0]
                                   else:
                                       next_date = None
                                       
                                   if next_date:
                                       # Check if within 7 days
                                       nd = pd.to_datetime(next_date).tz_localize(None)
                                       today = pd.Timestamp.now().normalize()
                                       days_diff = (nd - today).days
                                       
                                       if 0 <= days_diff <= 14:
                                           events.append(f"**{t}**: {nd.strftime('%b %d')} ({days_diff} days)")
                        except Exception:
                            pass
                
                if events:
                    for e in events:
                        st.write(e)
                else:
                    st.write("No earnings in next 14 days for top 5.")
            else:
                st.write("(Click to scan top 5)")
        else:
            st.write("No candidates.")

    st.divider()

    # Institutional Radar (Whale Tracker)
    st.markdown("### 🐋 Institutional Radar (High RVOL)")
    # Filter for RVOL > 2.0 (2x average volume)
    whales = filtered_df[filtered_df['RVOL'] > 2.0].sort_values(by='RVOL', ascending=False)
    
    if not whales.empty:
        st.success(f"Detected {len(whales)} stocks with >2x Volume (Institutional Footprints)")
        st.dataframe(
            make_clickable(whales[['Ticker', 'Price', 'RVOL', 'Side', 'Sector']]),
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker", display_text="https://finance\\.yahoo\\.com/quote/(.*)"
                ),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "RVOL": st.column_config.NumberColumn("RVOL", format="%.2fx"),
            },
            use_container_width=True,
            height=200,
            hide_index=True
        )
    else:
        st.info("No unusual institutional volume detected (>2x RVOL) in current candidates.")
    
    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Long Candidates", "📉 Short Candidates", "📊 Sector Monitor", "📈 Chart Viewer"])

    with tab1:
        st.subheader("Long Setups (Trend Template + Momentum)")
        if not longs.empty:
            # Sort by selected metric
            longs = longs.sort_values(by=selected_metric, ascending=False)
            
            st.dataframe(
                make_clickable(longs[['Ticker', 'Price', 'RVOL', 'RSI', selected_metric, 'Sector', 'Earnings']]),
                column_config={
                    "Ticker": st.column_config.LinkColumn(
                        "Ticker", display_text="https://finance\\.yahoo\\.com/quote/(.*)"
                    ),
                    "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                    "RVOL": st.column_config.NumberColumn("RVOL", format="%.2f"),
                    "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                    selected_metric: st.column_config.NumberColumn(selected_metric, format="%.2f%%"),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No Long candidates found.")

    with tab2:
        st.subheader("Short Setups (Downtrend + Weakness)")
        if not shorts.empty:
            shorts = shorts.sort_values(by=selected_metric, ascending=True) # Sort by weakest
            st.dataframe(
                make_clickable(shorts[['Ticker', 'Price', 'RVOL', 'RSI', selected_metric, 'Sector', 'Earnings']]),
                column_config={
                    "Ticker": st.column_config.LinkColumn(
                        "Ticker", display_text="https://finance\\.yahoo\\.com/quote/(.*)"
                    ),
                    "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                    "RVOL": st.column_config.NumberColumn("RVOL", format="%.2f"),
                    "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                    selected_metric: st.column_config.NumberColumn(selected_metric, format="%.2f%%"),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No Short candidates found.")

    with tab3:
        st.subheader("Sector Performance")
        if df_sector is not None:
            # Sort by selected metric
            metric_col = f"{time_frame_map[time_frame].replace('RS_', '')} %"
            # Handle mapping mismatch (RS_1D -> 1D %)
            metric_col = metric_col.replace("1D %", "1D %").replace("1W %", "1W %").replace("1M %", "1M %").replace("3M %", "3M %").replace("1Y %", "1Y %")
            
            if metric_col in df_sector.columns:
                df_sector = df_sector.sort_values(by=metric_col, ascending=False)
                
            # Apply styling
            st.dataframe(
                df_sector.style.format({
                    "1D %": "{:.2f}%",
                    "1W %": "{:.2f}%",
                    "1M %": "{:.2f}%",
                    "3M %": "{:.2f}%",
                    "1Y %": "{:.2f}%"
                }).background_gradient(cmap='RdYlGn', subset=["1D %", "1W %", "1M %", "3M %", "1Y %"]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Sector data not available.")

    with tab4:
        st.subheader("AI Chart Analysis")
        ticker_input = st.text_input("Enter Ticker for VCP Analysis:", value="PLTR").upper()
        
        if st.button("Analyze Chart"):
            if ticker_input:
                with st.spinner(f"Fetching data and analyzing {ticker_input}..."):
                    # 1. Fetch Data
                    data = fetch_data(ticker_input)
                    if data is not None:
                        data = calculate_technicals(data)
                        
                        # 2. Earnings Check
                        try:
                            t_obj = yf.Ticker(ticker_input)
                            cal = t_obj.calendar
                            if cal is not None and not cal.empty:
                                next_earn = cal.iloc[0][0]
                                earn_str = pd.to_datetime(next_earn).strftime('%Y-%m-%d')
                                st.info(f"📅 Next Earnings: {earn_str}")
                        except:
                            pass

                        # 3. Generate Chart
                        chart_path = generate_chart(ticker_input, data)
                        st.image(chart_path, caption=f"{ticker_input} Daily Chart")
                        
                        # 4. Analyze with Gemini
                        analysis = analyze_chart(ticker_input, chart_path)
                        
                        if "error" in analysis:
                            st.error(f"Analysis Failed: {analysis['error']}")
                        else:
                            # Display Results
                            score = analysis.get('score', 0)
                            verdict = analysis.get('verdict', 'N/A')
                            reasoning = analysis.get('reasoning', 'No reasoning provided.')
                            
                            col_a, col_b = st.columns(2)
                            col_a.metric("VCP Score", f"{score}/100")
                            col_b.metric("Verdict", verdict)
                            
                            st.write(f"**Reasoning:** {reasoning}")
                            
                            if 'pivot_price' in analysis:
                                st.write(f"**Pivot:** ${analysis['pivot_price']}")
                            if 'stop_loss' in analysis:
                                st.write(f"**Stop Loss:** ${analysis['stop_loss']}")
                    else:
                        st.error(f"Could not fetch data for {ticker_input}")

    # Watchlist & Export
    st.divider()
    st.subheader("📋 Watchlist & Export")
    
    # Export CSV
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Filtered Candidates (CSV)",
        csv,
        "vcp_candidates.csv",
        "text/csv",
        key='download-csv'
    )
    
    # TradingView List
    tv_list = ",".join(filtered_df['Ticker'].tolist())
    st.text_area("Copy for TradingView Import:", tv_list, height=100)

    # Position Size Calculator
    st.divider()
    st.subheader("🧮 Position Size Calculator")
    
    col_calc1, col_calc2, col_calc3, col_calc4 = st.columns(4)
    account_size = col_calc1.number_input("Account Size ($)", value=10000, step=1000)
    risk_pct = col_calc2.number_input("Risk % per Trade", value=1.0, step=0.1)
    entry_price = col_calc3.number_input("Entry Price ($)", value=100.0, step=1.0)
    stop_loss = col_calc4.number_input("Stop Loss ($)", value=95.0, step=1.0)
    
    if entry_price > stop_loss:
        risk_per_share = entry_price - stop_loss
        risk_amount = account_size * (risk_pct / 100)
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        
        st.success(f"**Buy {shares} shares**")
        st.write(f"Position Value: ${position_value:,.2f}")
        st.write(f"Risk Amount: ${risk_amount:.2f}")
    else:
        st.warning("Stop Loss must be below Entry Price for Longs.")
