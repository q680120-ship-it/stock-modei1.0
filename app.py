import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股 200 狙擊 Pro", layout="wide")

# 2. 完整 200 檔清單 (分類編列，防止截斷)
G1 = ["2330.TW","2303.TW","2454.TW","3711.TW","2379.TW","3034.TW","2408.TW","3661.TW","3443.TW","6415.TW","2329.TW","2449.TW","6239.TW","3035.TW","3583.TW","6271.TW","8150.TW","3264.TWO","6182.TWO","6223.TWO","3587.TWO","8046.TW","3037.TW","2368.TW"]
G2 = ["2317.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW","2353.TW","2376.TW","6669.TW","2395.TW","3013.TW","3515.TW","2417.TW","3017.TW","3324.TW","2313.TW","2421.TW","2486.TW","6153.TW","3211.TWO","5483.TWO","8299.TWO"]
G3 = ["1513.TW","1519.TW","1503.TW","1504.TW","1514.TW","1605.TW","1608.TW","1609.TW","6806.TW","8996.TW","1517.TW","1560.TW","3708.TW","6443.TWO","6477.TW","1506.TW","1522.TW","9958.TW","1516.TW","1589.TW","1504.TW"]
G4 = ["2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2633.TW","2637.TW","2606.TW","2002.TW","2014.TW","2006.TW","2031.TW","2027.TW","1101.TW","110
