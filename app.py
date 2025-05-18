
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import requests
import io
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CONFIG ---
st.set_page_config(
    layout="wide",  # ✅ Use wide layout for full-width plots
    page_title="Stock Returns Viewer",
    page_icon="📈"
)
st.title("📈 Stock Returns from Buy Date")

# --- VISIT COUNTER ---
# COUNTER_URL = "https://api.npoint.io/3d12053ea7002f9f1482"  # json endpoint 
# COUNTER_URL = "https://api.npoint.io/c9fb396401861929d8e7" # json endpoint

COUNTER_URL = st.secrets["COUNTER_URL"]

# """
# def get_and_increment_visits():
#     try:
#         response = requests.get(COUNTER_URL)
#         data = response.json()
#         visits = data.get("visits", 0) + 1
#         requests.post(COUNTER_URL, json={"visits": visits})
#         return visits
#     except Exception:
#         return None
# """

def get_and_update_counters(update_upload=False):
    try:
        response = requests.get(COUNTER_URL)
        data = response.json()

        visits = data.get("visits", 0) + 1
        uploads = data.get("uploads", 0)

        if update_upload:
            uploads += 1

        # Update both, even if only one changed
        requests.post(COUNTER_URL, json={"visits": visits, "uploads": uploads})

        return visits
    except Exception:
        return None


# visits = get_and_increment_visits()
visits = get_and_update_counters()  # Only update visit counter here

if visits is not None:
    st.markdown(f"🧮 **Total visits so far:** {visits}")
    st.sidebar.markdown(f"👀 Total Visits: **{visits}**")
else:
    st.warning("⚠️ Visit counter unavailable")

# --- INSTRUCTIONS ---
with st.expander("📋 Instructions"):
    st.markdown("""
    This app visualizes your stock returns from the buy date onward using your tradebook.

    #### ✅ Required CSV format:
    - Must be a Zerodha-style tradebook (`tradebook-EQ.csv`)
    - Required columns:
      - `symbol` – e.g., `RELIANCE`
      - `trade_date` – format: `YYYY-MM-DD`
      - `quantity`
      - `trade_type` – must include `'buy'`

    #### 🔁 What it does:
    - Fetches stock prices from Yahoo Finance
    - Calculates returns from your earliest buy date
    - Plots each stock's performance
    - Lists unavailable stocks separately

    #### ⚠️ Notes:
    - Internet is required (for fetching live price data)
    - Only **NSE stocks** (e.g., `RELIANCE.NS`) are supported
    - If data is missing on your buy date, that stock is skipped
    - It calculates the return from close price of the buy date

    #### 💡 Tip:
    - You can export your tradebook from Zerodha Console → Reports → Tradebook → Export to CSV
    """)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📁 Upload your tradebook CSV", type="csv")

if uploaded_file is not None:
    try:
        tradebook = pd.read_csv(uploaded_file)
        buys = tradebook[tradebook['trade_type'].str.lower() == 'buy'].copy()
        buys['trade_date'] = pd.to_datetime(buys['trade_date'])

        buys_date_sum = buys.groupby(['symbol', 'trade_date'])['quantity'].sum().reset_index()
        buys_earliest_date = buys_date_sum.groupby(['symbol']).agg({'trade_date': 'min'}).reset_index()
        buys_earliest_date['trade_date'] = buys_earliest_date['trade_date'].dt.date

        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, row_width=[1],
                            subplot_titles=['Returns from Buy Date'], vertical_spacing=0.01)

        unavailable_symbols = []

        for _, row in buys_earliest_date.iterrows():
            symbol = row['symbol']
            buy_date = row['trade_date']
            stock_name = symbol + '.NS'

            try:
                data = yf.download(stock_name, progress=False)
                data.index = pd.to_datetime(data.index).date

                buy_price = data[data.index == buy_date]['Close'].values
                if len(buy_price) == 0:
                    unavailable_symbols.append(symbol)
                    continue

                buy_price = buy_price[0]
                data = data[data.index >= buy_date]
                data['returns'] = (data['Close'] - buy_price) * 100 / buy_price

                fig.add_trace(
                    go.Scatter(x=data.index, y=data['returns'], name=f"{symbol} Returns"),
                    row=1, col=1
                )

                fig.add_vline(
                    x=buy_date, line_width=0.8, line_color="green",
                    annotation_text=f"{symbol} Buy", row=1, col=1
                )

            except Exception:
                unavailable_symbols.append(symbol)
                continue

        fig.update_layout(
            height=800,  # ✅ No width specified — allows container to manage it
            title_text="Stock Returns from Buy Date",
            yaxis_title="Returns (%)",  # Y-axis is Returns in percentage
            showlegend=True
        )
        
        get_and_update_counters(update_upload=True) #increment upload counter

        st.plotly_chart(fig, use_container_width=True)

        # --- DOWNLOAD BUTTON ---
        img_buffer = io.BytesIO()
        pio.write_image(fig, img_buffer, format='png', width=1400, height=800)
        img_buffer.seek(0)

        st.download_button(
            label="💾 Download Plot as PNG",
            data=img_buffer,
            file_name="stock_returns.png",
            mime="image/png"
        )

        # Display unavailable symbols
        if unavailable_symbols:
            st.markdown("---")
            st.markdown("### ⚠️ Data could not be fetched for:")
            st.markdown(", ".join(unavailable_symbols))

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

else:
    st.info("Please upload a Zerodha-style tradebook CSV file to begin.")
