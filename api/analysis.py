import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
import io
import base64

def flatten(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def get_rsi(series, length=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=length-1, adjust=False).mean()
    ema_down = down.ewm(com=length-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def safe_slope(series, window=5):
    return series.rolling(window).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0]
        if len(x) == window and not np.isnan(x).any()
        else 0,
        raw=True
    )

def analyze_btc(kst):
    plt.switch_backend('Agg')
    try:
        now_str = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
        dxy = flatten(yf.download("DX-Y.NYB", period="1y", progress=False))
        tnx = flatten(yf.download("^TNX", period="1y", progress=False))
        spx = flatten(yf.download("^GSPC", period="1y", progress=False))
        btc = flatten(yf.download("BTC-USD", period="1y", progress=False))

        current_price = btc["Close"].iloc[-1]

        dxy["MA20"] = dxy["Close"].rolling(20).mean()
        dxy["MA60"] = dxy["Close"].rolling(60).mean()
        tnx["MA20"] = tnx["Close"].rolling(20).mean()
        spx["MA60"] = spx["Close"].rolling(60).mean()
        spx["VOL"] = spx["Close"].pct_change().rolling(10).std()

        btc["MA20"] = btc["Close"].rolling(20).mean()
        btc["MA20_Slope"] = safe_slope(btc["MA20"], 5)
        btc["VOL_MA20"] = btc["Volume"].rolling(20).mean()
        btc["VOL_RATIO"] = btc["Volume"] / btc["VOL_MA20"]
        btc["Internal_Score"] = (btc["VOL_RATIO"] > 1.3).astype(int)
        btc["RSI"] = get_rsi(btc["Close"], 14)

        results = []
        for i in range(60, len(btc)):
            try:
                date = btc.index[i]
                d_idx = dxy.index.get_indexer([date], method='pad')[0]
                t_idx = tnx.index.get_indexer([date], method='pad')[0]
                s_idx = spx.index.get_indexer([date], method='pad')[0]
                dxy_s = int(dxy["MA20"].iloc[d_idx] < dxy["MA60"].iloc[d_idx] and np.polyfit(range(10), dxy["MA60"].iloc[d_idx-9:d_idx+1], 1)[0] < 0)
                rate_s = int(tnx["MA20"].iloc[t_idx] < tnx["MA20"].iloc[t_idx-5])
                stock_s = int(spx["Close"].iloc[s_idx] > spx["MA60"].iloc[s_idx] and spx["VOL"].iloc[s_idx] < spx["VOL"].iloc[s_idx-5])
                results.append({"Date": date, "Score": dxy_s + rate_s + stock_s})
            except: continue
        df_res = pd.DataFrame(results).set_index("Date")

        merge_df = pd.merge(df_res, btc[["Close", "MA20", "MA20_Slope", "Volume", "VOL_MA20", "Internal_Score", "RSI"]], left_index=True, right_index=True)
        spx_aligned = spx["Close"].reindex(merge_df.index, method="nearest")
        merge_df["RS"] = merge_df["Close"] / spx_aligned
        merge_df["RS_MA20"] = merge_df["RS"].rolling(20).mean()
        merge_df["RS_Slope"] = safe_slope(merge_df["RS"], 5)
        merge_df["Internal_Strong"] = (merge_df["Internal_Score"].rolling(2).sum() >= 1).astype(int)
        merge_df["Final_Strong_Signal"] = ((merge_df["Score"] >= 2) & (merge_df["Internal_Strong"] == 1) & (merge_df["MA20_Slope"] > 0)).astype(int)
        merge_df["Sell_Signal"] = (merge_df["Score"] <= 1).astype(int)

        plot_df = merge_df.tail(20)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1.2, 1]})
        plt.style.use('dark_background')
        fig.patch.set_facecolor('#0f172a')
        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_facecolor('#0f172a')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#334155')

        ax1.plot(plot_df.index, plot_df["Close"], marker="o", linewidth=2, color='#38bdf8')
        ax1.plot(plot_df.index, plot_df["MA20"], "--", alpha=0.6, color='#94a3b8')
        ax1b = ax1.twinx()
        ax1b.plot(plot_df.index, plot_df["Score"], color="#f43f5e", linewidth=4, drawstyle="steps-mid", alpha=0.3)
        ax1b.set_ylim(0, 4)
        for idx, row in plot_df[plot_df["Final_Strong_Signal"] == 1].iterrows():
            ax1.scatter(idx, row["Close"] * 0.96, color="#f43f5e", s=100, marker="^")
        for idx, row in plot_df[plot_df["Sell_Signal"] == 1].iterrows():
            ax1.scatter(idx, row["Close"] * 1.04, color="#10b981", s=100, marker="v")

        vol_colors = ["#f43f5e" if v > m else "#475569" for v, m in zip(plot_df["Volume"], plot_df["VOL_MA20"])]
        ax2.bar(plot_df.index, plot_df["Volume"], color=vol_colors, alpha=0.6)
        ax2.plot(plot_df.index, plot_df["VOL_MA20"], ":", color="white", alpha=0.5)

        for i in range(len(plot_df)-1):
            c = "#10b981" if plot_df["RS_Slope"].iloc[i+1] > 0 else "#f43f5e"
            ax3.plot(plot_df.index[i:i+2], plot_df["RS"].iloc[i:i+2], color=c, linewidth=2)
        ax3.plot(plot_df.index, plot_df["RS_MA20"], "#f59e0b", linestyle="--")

        ax4.plot(plot_df.index, plot_df["RSI"], color="#a855f7")
        ax4.axhline(30, color="#f43f5e", ls="--", alpha=0.5)
        ax4.axhline(70, color="#10b981", ls="--", alpha=0.5)
        ax4.axhline(50, color="#38bdf8", ls=":", alpha=0.8)

        plt.suptitle(f"BTC-USD Analysis - {now_str}", color='white', fontsize=12)
        plt.xticks(rotation=30)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=False)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return {
            "name": "Bitcoin (BTC-USD)",
            "price": float(current_price),
            "score": int(merge_df["Score"].iloc[-1]),
            "chart": f"data:image/png;base64,{img_str}",
            "unit": "USD"
        }
    except Exception as e:
        return {"name": "BTC", "error": str(e)}

def analyze_stock(ticker, name, baseline_ticker, kst):
    plt.switch_backend('Agg')
    try:
        now_str = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
        stock = flatten(yf.download(ticker, period="1y", progress=False))
        baseline = flatten(yf.download(baseline_ticker, period="1y", progress=False))
        dxy = flatten(yf.download("DX-Y.NYB", period="1y", progress=False))
        us10y = flatten(yf.download("^TNX", period="1y", progress=False))

        current_price = stock["Close"].iloc[-1]

        stock["MA20"] = stock["Close"].rolling(20).mean()
        stock["MA60"] = stock["Close"].rolling(60).mean()
        stock["MA20_Slope"] = safe_slope(stock["MA20"], 5)
        stock["VOL_MA20"] = stock["Volume"].rolling(20).mean()
        stock["VOL_RATIO"] = stock["Volume"] / stock["VOL_MA20"]
        stock["Internal_Score"] = (stock["VOL_RATIO"] > 1.3).astype(int)
        stock["RSI"] = get_rsi(stock["Close"], 14)

        baseline["MA60"] = baseline["Close"].rolling(60).mean()

        results = []
        for i in range(60, len(stock)):
            try:
                date = stock.index[i]
                d_idx = dxy.index.get_indexer([date], method='pad')[0]
                u_idx = us10y.index.get_indexer([date], method='pad')[0]
                b_idx = baseline.index.get_indexer([date], method='pad')[0]
                
                dxy_s = int(dxy["Close"].iloc[d_idx] < dxy["Close"].iloc[d_idx-5])
                rate_s = int(us10y["Close"].iloc[u_idx] < us10y["Close"].iloc[u_idx-5])
                base_s = int(baseline["Close"].iloc[b_idx] > baseline["MA60"].iloc[b_idx])
                results.append({"Date": date, "Score": dxy_s + rate_s + base_s})
            except: continue
        df_res = pd.DataFrame(results).set_index("Date")

        merge_df = pd.merge(df_res, stock[["Close", "MA20", "MA60", "MA20_Slope", "Volume", "VOL_MA20", "Internal_Score", "RSI"]], left_index=True, right_index=True)
        base_aligned = baseline["Close"].reindex(merge_df.index, method="ffill")
        merge_df["RS"] = merge_df["Close"] / base_aligned
        merge_df["RS_MA20"] = merge_df["RS"].rolling(20).mean()
        merge_df["RS_Slope"] = safe_slope(merge_df["RS"], 5)
        merge_df["Internal_Strong"] = (merge_df["Internal_Score"].rolling(2).sum() >= 1).astype(int)
        merge_df["Final_Buy"] = ((merge_df["Score"] >= 2) & (merge_df["MA20_Slope"] > 0) & (merge_df["Internal_Strong"] == 1)).astype(int)
        merge_df["Sell"] = ((merge_df["Score"] <= 1) & (merge_df["MA20_Slope"] < 0)).astype(int)

        plot_df = merge_df.tail(20)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1.2, 1]})
        plt.style.use('dark_background')
        fig.patch.set_facecolor('#0f172a')
        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_facecolor('#0f172a')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#334155')

        ax1.plot(plot_df.index, plot_df["Close"], marker="o", linewidth=2, color='#38bdf8')
        ax1.plot(plot_df.index, plot_df["MA20"], "--", alpha=0.6, color='#94a3b8')
        ax1b = ax1.twinx()
        ax1b.plot(plot_df.index, plot_df["Score"], color="#f43f5e", linewidth=4, drawstyle="steps-mid", alpha=0.3)
        ax1b.set_ylim(0, 3.5)
        for idx, row in plot_df[plot_df["Final_Buy"] == 1].iterrows():
            ax1.scatter(idx, row["Close"] * 0.96, color="#f43f5e", s=100, marker="^")
        for idx, row in plot_df[plot_df["Sell"] == 1].iterrows():
            ax1.scatter(idx, row["Close"] * 1.04, color="#10b981", s=100, marker="v")

        vol_colors = ["#f43f5e" if v > m else "#475569" for v, m in zip(plot_df["Volume"], plot_df["VOL_MA20"])]
        ax2.bar(plot_df.index, plot_df["Volume"], color=vol_colors, alpha=0.6)
        ax2.plot(plot_df.index, plot_df["VOL_MA20"], ":", color="white", alpha=0.5)

        for i in range(len(plot_df)-1):
            c = "#10b981" if plot_df["RS_Slope"].iloc[i+1] > 0 else "#f43f5e"
            ax3.plot(plot_df.index[i:i+2], plot_df["RS"].iloc[i:i+2], color=c, linewidth=2)
        ax3.plot(plot_df.index, plot_df["RS_MA20"], "#f59e0b", linestyle="--")

        ax4.plot(plot_df.index, plot_df["RSI"], color="#a855f7")
        ax4.axhline(30, color="#f43f5e", ls="--", alpha=0.5)
        ax4.axhline(70, color="#10b981", ls="--", alpha=0.5)
        ax4.axhline(50, color="#38bdf8", ls=":", alpha=0.8)

        plt.suptitle(f"{name} ({ticker}) Analysis - {now_str}", color='white', fontsize=12)
        plt.xticks(rotation=30)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=False)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return {
            "name": f"{name} ({ticker})",
            "price": float(current_price),
            "score": int(merge_df["Score"].iloc[-1]),
            "chart": f"data:image/png;base64,{img_str}",
            "unit": "KRW"
        }
    except Exception as e:
        return {"name": ticker, "error": str(e)}

def run_analysis():
    kst = timezone(timedelta(hours=9))
    results = []
    
    # 1. BTC Analysis
    results.append(analyze_btc(kst))
    
    # 2. LG Electronics Analysis
    results.append(analyze_stock("066570.KS", "LG전자", "^KS11", kst))
    
    # 3. Samsung Electronics Analysis (User mentioned SM_Check but the file content says Samsung)
    # The file SM_Check.py has "▶ 삼성전자 매크로 통합 분석 시작" and ticker "005930.KS"
    results.append(analyze_stock("005930.KS", "삼성전자", "^KS11", kst))
    
    return {
        "status": "success",
        "time": datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S'),
        "results": results
    }
