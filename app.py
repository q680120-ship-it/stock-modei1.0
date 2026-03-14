import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面基礎配置
st.set_page_config(page_title="台股 200 狙擊 Pro", layout="wide")

# 2. 分類清單
SEMI = ["2330.TW","2303.TW","2454.TW","3711.TW","2379.TW","3034.TW","2408.TW","3661.TW","3443.TW","6415.TW","2329.TW","2449.TW","6239.TW","3035.TW","3583.TW","6271.TW","8150.TW","3264.TWO","6182.TWO","6223.TWO","3587.TWO"]
AI_SERVER = ["2317.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW","2353.TW","2376.TW","6669.TW","2395.TW","3013.TW","3515.TW","2417.TW","6235.TW"]
COMPONENTS = ["3017.TW","3324.TW","3037.TW","8046.TW","2368.TW","2313.TW","2354.TW","2451.TW","2351.TW","3044.TW","2421.TW","6213.TW","6274.TWO","8039.TW","3376.TW","2486.TW","6153.TW","5483.TWO","8299.TWO","3105.TWO","6488.TWO"]
POWER_ENERGY = ["1513.TW","1519.TW","1503.TW","1504.TW","1514.TW","1605.TW","1608.TW","1609.TW","6806.TW","8996.TW","1517.TW","1560.TW","3708.TW","6443.TWO","6477.TW","1506.TW","1522.TW","9958.TW"]
SHIPPING_STEEL = ["2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2002.TW","1101.TW","1102.TW","2633.TW","2014.TW","2637.TW","2006.TW","2031.TW","2027.TW"]
FINANCE = ["2881.TW","2882.TW","2886.TW","2891.TW","2884.TW","2885.TW","2883.TW","2892.TW","2880.TW","2890.TW","2801.TW","2834.TW","5880.TW","5871.TW","2812.TW","6005.TW","2855.TW","2887.TW","2888.TW","2889.TW"]
OTHERS = ["1301.TW","1303.TW","1326.TW","6505.TW","1402.TW","2105.TW","1216.TW","1722.TW","1717.TW","1476.TW","1477.TW","2204.TW","2201.TW","1795.TW","2707.TW","9921.TW","9945.TW","8454.TW","8069.TWO","3293.TWO","3529.TWO","3131.TWO","3680.TWO"]

TW_200_LIST = list(set(SEMI + AI_SERVER + COMPONENTS + POWER_ENERGY + SHIPPING_STEEL + FINANCE + OTHERS))

# 3. 繪圖核心
def draw_chart(df, name):
    d = df.tail(60)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="K線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['Trailing_Stop'], name="停利價", line=dict(color='orange', width=2, dash='dash')), row=1, col=1)
    clrs = ['red' if c >= o else 'green' for o, c in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(x=d.index, y=d['Volume'], name="成交量", marker_color=clrs, opacity=0.8), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=30, b=20))
    return fig

# 4. 分析邏輯
@st.cache_data(ttl=3600)
def analyze(sid, vr, tp):
    try:
        t = yf.Ticker(sid)
        df = t.history(period="2y")
        if df.empty or len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        n = t.info.get('longName', sid).split('Co')[0].split('Inc')[0].strip()
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close
