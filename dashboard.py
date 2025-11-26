import streamlit as st
import pandas as pd
import os
import yfinance as yf
from screener import fetch_data, calculate_technicals
from screener import fetch_data, calculate_technicals
from vision_analyst import generate_chart, analyze_chart, generate_market_sentiment

# Set page config
st.set_page_config(page_title="VCP Sniper Dashboard", layout="wide")

# Title and Description
st.title("🎯 VCP Sniper Dashboard")
st.markdown("Automated screening for Minervini/Qullamaggie setups.")

# Load Data
DATA_FILE = "candidates.csv"
DATA_FILE = "candidates.csv"
SECTOR_FILE = "sector_performance.csv"
BREADTH_FILE = "market_breadth.csv"

@st.cache_data
def load_data():
    candidates = None
    sectors = None
    
    if os.path.exists(DATA_FILE):
        candidates = pd.read_csv(DATA_FILE)
        
    if os.path.exists(SECTOR_FILE):
        sectors = pd.read_csv(SECTOR_FILE)
        
    breadth = None
    if os.path.exists(BREADTH_FILE):
        breadth = pd.read_csv(BREADTH_FILE)
        
    return candidates, sectors, breadth

df, df_sectors, df_breadth = load_data()

if df is None:
    st.error(f"Data file `{DATA_FILE}` not found. Please run `screener.py` first.")
else:
    # Sidebar Filters
    st.sidebar.header("Filters")
    
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

    # Market Sentiment (AI)
    st.markdown("### 🧠 Market Sentiment (AI)")
    
    # Gather Context
    sentiment_context = {}
    
    # 1. VIX
    try:
        vix_data = yf.Ticker("^VIX").history(period="1d")
        if not vix_data.empty:
            sentiment_context['vix'] = f"{vix_data['Close'].iloc[-1]:.2f}"
    except:
        pass
        
    # 2. Breadth
    if df_breadth is not None and not df_breadth.empty:
        sentiment_context['breadth_50'] = f"{df_breadth['Pct_Above_SMA50'].iloc[0]:.1f}"
        sentiment_context['breadth_200'] = f"{df_breadth['Pct_Above_SMA200'].iloc[0]:.1f}"
        
    # 3. Momentum Leaders
    # (Re-using the logic from sidebar if possible, or just re-fetch quickly)
    try:
        mom_tickers_sent = ['PLTR', 'NVDA', 'TSLA', 'APP']
        mom_data_sent = yf.download(mom_tickers_sent, period="2d", progress=False)
        if not mom_data_sent.empty:
             # Calculate simple avg change of these leaders
             closes_s = mom_data_sent['Close']
             if len(closes_s) >= 2:
                 changes = []
                 for t in mom_tickers_sent:
                     if t in closes_s.columns:
                         c = closes_s[t].dropna()
                         if len(c) >= 2:
                             chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100
                             changes.append(chg)
                 if changes:
                     avg_mom = sum(changes) / len(changes)
                     sentiment_context['mom_change'] = f"{avg_mom:+.2f}"
    except:
        pass

    # Generate Sentiment (Cached if possible, but for now direct call)
    if "sentiment_lines" not in st.session_state:
        with st.spinner("AI analyzing market sentiment..."):
            st.session_state.sentiment_lines = generate_market_sentiment(sentiment_context)
            st.session_state.sentiment_time = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            
    # Display
    if "sentiment_time" in st.session_state:
        st.caption(f"Updated: {st.session_state.sentiment_time}")
        
    if st.session_state.sentiment_lines:
         for line in st.session_state.sentiment_lines:
             st.markdown(f"**> {line}**")
             
    if st.button("Refresh Sentiment"):
        if "sentiment_lines" in st.session_state:
            del st.session_state.sentiment_lines
        if "sentiment_time" in st.session_state:
            del st.session_state.sentiment_time
        st.rerun()
        
    st.divider()

    # Institutional Radar (Whale Tracker)
    st.markdown("### 🐋 Institutional Radar (High RVOL)")
    # Filter for RVOL > 2.0 (2x average volume)
    whales = filtered_df[filtered_df['RVOL'] > 2.0].sort_values(by='RVOL', ascending=False)
    
    if not whales.empty:
        st.success(f"Detected {len(whales)} stocks with >2x Volume (Institutional Footprints)")
        st.dataframe(
            whales[['Ticker', 'Price', 'RVOL', 'Side', 'Sector']].style.format({
                "Price": "${:.2f}",
                "RVOL": "{:.2f}x"
            }),
            use_container_width=True,
            height=200
        )
    else:
        st.info("No unusual institutional volume detected (>2x RVOL) in current candidates.")
    
    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Long Candidates", "📉 Short Candidates", "📊 Sector Monitor", "📈 Chart Viewer"])

    with tab1:
        st.subheader("Strongest Momentum (Stage 2 Uptrend)")
        if not longs.empty:
            longs_sorted = longs.sort_values(by=selected_metric, ascending=False)
            st.dataframe(
                longs_sorted.style.format({
                    "Price": "${:.2f}",
                    "RVOL": "{:.2f}x",
                    "RSI": "{:.1f}",
                    "RS_1D": "{:+.1f}%",
                    "RS_1W": "{:+.1f}%",
                    "RS_1M": "{:+.1f}%",
                    "RS_3M": "{:+.1f}%",
                    "RS_1Y": "{:+.1f}%",
                    "52W_High": "${:.2f}"
                }),
                use_container_width=True,
                height=600
            )
        else:
            st.info("No Long candidates found matching filters.")

    with tab2:
        st.subheader("Weakest Momentum (Stage 4 Downtrend)")
        if not shorts.empty:
            shorts_sorted = shorts.sort_values(by=selected_metric, ascending=True)
            st.dataframe(
                shorts_sorted.style.format({
                    "Price": "${:.2f}",
                    "RVOL": "{:.2f}x",
                    "RSI": "{:.1f}",
                    "RS_1D": "{:+.1f}%",
                    "RS_1W": "{:+.1f}%",
                    "RS_1M": "{:+.1f}%",
                    "RS_3M": "{:+.1f}%",
                    "RS_1Y": "{:+.1f}%",
                    "52W_High": "${:.2f}"
                }),
                use_container_width=True,
                height=600
            )
        else:
            st.info("No Short candidates found matching filters.")
            
    with tab3:
        st.subheader("Sector Performance")
        if df_sectors is not None:
            # Heatmap style coloring
            st.dataframe(
                df_sectors.style.format({
                    "1D %": "{:+.2f}%",
                    "1W %": "{:+.2f}%",
                    "1M %": "{:+.2f}%",
                    "3M %": "{:+.2f}%",
                    "1Y %": "{:+.2f}%"
                }).background_gradient(cmap='RdYlGn', subset=['1D %', '1W %', '1M %', '3M %', '1Y %']),
                use_container_width=True,
                height=600
            )
        else:
            st.warning("Sector performance data not found. Run `sector_monitor.py`.")

    with tab4:
        st.subheader("VCP Chart Analysis")
        
        # On-Demand Analysis
        st.markdown("### Analyze Any Ticker")
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            ticker_input = st.text_input("Enter Ticker Symbol (e.g., NVDA)", "").upper()
        with col_btn:
            analyze_btn = st.button("Generate Analysis")
            
        if analyze_btn and ticker_input:
            with st.spinner(f"Fetching data and analyzing {ticker_input}..."):
                # 1. Fetch Data
                df_ticker = fetch_data(ticker_input)
                if df_ticker is not None and not df_ticker.empty:
                    df_ticker = calculate_technicals(df_ticker)
                    
                    # Fetch Earnings Date
                    try:
                        ticker_obj = yf.Ticker(ticker_input)
                        cal = ticker_obj.calendar
                        if cal is not None and not cal.empty:
                            next_earnings = cal.iloc[0][0]
                            # Format if it's a date object
                            st.info(f"📅 Next Earnings Date: {next_earnings}")
                        else:
                            st.info("📅 Earnings Date: Not found")
                    except Exception as e:
                        print(f"Earnings fetch error: {e}")
                    
                    # 2. Generate Chart
                    chart_path = generate_chart(ticker_input, df_ticker)
                    st.image(chart_path, caption=f"{ticker_input} Daily Chart", use_container_width=True)
                    
                    # 3. Analyze with Gemini
                    analysis = analyze_chart(ticker_input, chart_path)
                    
                    if analysis:
                        if "error" in analysis:
                            st.warning(f"Analysis skipped: {analysis['error']}")
                        else:
                            st.success(f"Gemini Verdict: {analysis.get('score')}/100 - {analysis.get('verdict')}")
                            st.json(analysis)
                    else:
                        st.error("Failed to generate analysis.")
                        
                else:
                    st.error(f"Could not fetch data for {ticker_input}")

        st.divider()
        st.markdown("### Saved Charts")
        
        # Get list of generated charts
        CHARTS_DIR = "charts"
        if os.path.exists(CHARTS_DIR):
            chart_files = [f for f in os.listdir(CHARTS_DIR) if f.endswith(".png")]
            
            if chart_files:
                # Selector
                selected_chart = st.selectbox("Select Saved Chart", chart_files)
                
                if selected_chart:
                    st.image(os.path.join(CHARTS_DIR, selected_chart), caption=selected_chart, use_container_width=True)
            else:
                st.info("No saved charts found.")
        else:
            st.warning("Charts directory not found.")

    # Watchlist & Export
    st.divider()
    st.subheader("📋 Watchlist & Export")
    
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Candidates (CSV)",
            data=csv,
            file_name='vcp_candidates.csv',
            mime='text/csv',
        )
        
        # TradingView List
        tv_list = ",".join(filtered_df['Ticker'].tolist())
        st.text_area("Copy for TradingView (Comma Separated)", tv_list)

    # Position Size Calculator
    st.divider()
    st.subheader("🛑 Position Size Calculator")
    
    with st.expander("Open Calculator"):
        col_calc1, col_calc2, col_calc3 = st.columns(3)
        account_size = col_calc1.number_input("Account Size ($)", value=10000, step=1000)
        risk_pct = col_calc2.number_input("Risk per Trade (%)", value=1.0, step=0.1)
        entry_price = col_calc3.number_input("Entry Price ($)", value=100.0, step=1.0)
        
        stop_loss = st.number_input("Stop Loss Price ($)", value=95.0, step=1.0)
        
        if entry_price > stop_loss:
            risk_amount = account_size * (risk_pct / 100)
            risk_per_share = entry_price - stop_loss
            shares = int(risk_amount / risk_per_share)
            position_value = shares * entry_price
            
            st.markdown(f"""
            ### Results:
            *   **Shares to Buy:** `{shares}`
            *   **Position Value:** `${position_value:,.2f}`
            *   **Risk Amount:** `${risk_amount:,.2f}`
            """)
        else:
            st.error("Stop Loss must be lower than Entry Price for Longs.")
