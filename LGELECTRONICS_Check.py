import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys

# ===============================
# 0. 공통 함수
# ===============================
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

print("▶ LG전자 매크로 통합 분석 시작")

# ===============================
# 1. 데이터 다운로드
# ===============================
try:
    lg = flatten(yf.download("066570.KS", period="1y", progress=False))
    kospi = flatten(yf.download("^KS11", period="1y", progress=False))
    dxy = flatten(yf.download("DX-Y.NYB", period="1y", progress=False))
    us10y = flatten(yf.download("^TNX", period="1y", progress=False))
except Exception as e:
    print("데이터 다운로드 실패:", e)
    sys.exit()

if lg.empty or kospi.empty or dxy.empty or us10y.empty:
    print("필수 데이터 누락 → 종료")
    sys.exit()

current_price = lg["Close"].iloc[-1]
print(f"현재 LG전자 가격: {current_price:,.0f} 원")

# ===============================
# 2. LG전자 지표 계산
# ===============================
lg["MA20"] = lg["Close"].rolling(20).mean()
lg["MA60"] = lg["Close"].rolling(60).mean()
lg["MA20_Slope"] = safe_slope(lg["MA20"], 5)

lg["VOL_MA20"] = lg["Volume"].rolling(20).mean()
lg["VOL_RATIO"] = lg["Volume"] / lg["VOL_MA20"]
lg["Internal_Score"] = (lg["VOL_RATIO"] > 1.3).astype(int)

lg["RSI"] = get_rsi(lg["Close"], 14)

# ===============================
# 3. 매크로 점수 계산 (3점 체계)
# ===============================
results = []

kospi["MA60"] = kospi["Close"].rolling(60).mean()

for i in range(60, len(lg)):

    date = lg.index[i]

    d_idx = dxy.index.get_indexer([date], method='pad')[0]
    u_idx = us10y.index.get_indexer([date], method='pad')[0]
    k_idx = kospi.index.get_indexer([date], method='pad')[0]

    if d_idx < 5 or u_idx < 5:
        continue

    # 달러 약세
    dxy_score = int(dxy["Close"].iloc[d_idx] < dxy["Close"].iloc[d_idx-5])

    # 미국 금리 하락
    us_rate_score = int(us10y["Close"].iloc[u_idx] < us10y["Close"].iloc[u_idx-5])

    # 코스피 상승 추세
    kospi_score = int(
        kospi["Close"].iloc[k_idx] > kospi["MA60"].iloc[k_idx]
    )

    total_score = dxy_score + us_rate_score + kospi_score

    results.append({"Date": date, "Macro_Score": total_score})

if len(results) == 0:
    print("매크로 점수 생성 실패 → 종료")
    sys.exit()

df_macro = pd.DataFrame(results).set_index("Date")

# ===============================
# 4. 병합
# ===============================
merge_df = pd.merge(
    df_macro,
    lg[["Close","MA20","MA60","MA20_Slope",
        "Volume","VOL_MA20","Internal_Score","RSI"]],
    left_index=True,
    right_index=True
)

# RS 계산 (LG전자 vs 코스피)
kospi_aligned = kospi["Close"].reindex(merge_df.index, method="ffill")
merge_df["RS"] = merge_df["Close"] / kospi_aligned
merge_df["RS_MA20"] = merge_df["RS"].rolling(20).mean()
merge_df["RS_Slope"] = safe_slope(merge_df["RS"], 5)

# ===============================
# 5. 시그널 생성
# ===============================
merge_df["Internal_Strong"] = (
    merge_df["Internal_Score"].rolling(2).sum() >= 1
).astype(int)

merge_df["Final_Buy"] = (
    (merge_df["Macro_Score"] >= 2) &
    (merge_df["MA20_Slope"] > 0) &
    (merge_df["Internal_Strong"] == 1)
).astype(int)

merge_df["Sell"] = (
    (merge_df["Macro_Score"] <= 1) &
    (merge_df["MA20_Slope"] < 0)
).astype(int)

plot_df = merge_df.tail(60)

# ===============================
# 6. 시각화
# ===============================
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

fig, (ax1, ax2, ax3, ax4) = plt.subplots(
    4, 1, figsize=(10,8),
    sharex=True,
    gridspec_kw={"height_ratios":[3,1,1.2,1]}
)

# 가격
ax1.plot(plot_df.index, plot_df["Close"], label="LG전자")
ax1.plot(plot_df.index, plot_df["MA20"], "--", label="MA20")
ax1.plot(plot_df.index, plot_df["MA60"], ":", label="MA60")

for idx, row in plot_df[plot_df["Final_Buy"]==1].iterrows():
    ax1.scatter(idx, row["Close"]*0.97, marker="^", s=120)
    ax1.text(idx, row["Close"]*0.94, "매수", ha="center", fontsize=8)

for idx, row in plot_df[plot_df["Sell"]==1].iterrows():
    ax1.scatter(idx, row["Close"]*1.03, marker="v", s=120)
    ax1.text(idx, row["Close"]*1.06, "매도", ha="center", fontsize=8)

ax1.legend()

# 거래량
ax2.bar(plot_df.index, plot_df["Volume"], alpha=0.4)
ax2.plot(plot_df.index, plot_df["VOL_MA20"], linestyle="--")
ax2.set_title("거래량")

# RS
ax3.plot(plot_df.index, plot_df["RS"])
ax3.plot(plot_df.index, plot_df["RS_MA20"], linestyle="--")
ax3.set_title("Relative Strength vs 코스피")

# RSI
ax4.plot(plot_df.index, plot_df["RSI"])
ax4.axhline(30, linestyle="--")
ax4.axhline(70, linestyle="--")
ax4.axhline(50, linestyle=":")
ax4.set_title("RSI")

plt.xticks(rotation=30)
plt.tight_layout()
plt.show()

print("▶ 분석 완료")
