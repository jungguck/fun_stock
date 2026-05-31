import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta

# 데이터 기간 설정 (백테스트용 2년치)
END   = datetime.today()
START = END - timedelta(days=365 * 2)

def fetch(ticker):
    df = yf.download(ticker, start=START, end=END, progress=False, auto_adjust=True)
    return df["Close"].squeeze()

print("데이터 다운로드 중...")
qqq  = fetch("QQQ")   # 나스닥 추종 ETF
tqqq = fetch("TQQQ")  # 3배 레버리지
vix  = fetch("^VIX")  # 공포지수

# ── 신호 계산 ──────────────────────────────────────────────────────────────
qqq_ma50  = qqq.rolling(50).mean()
qqq_ma200 = qqq.rolling(200).mean()

delta     = qqq.diff()
gain      = delta.clip(lower=0).rolling(14).mean()
loss      = (-delta.clip(upper=0)).rolling(14).mean()
rs        = gain / loss
rsi14     = 100 - (100 / (1 + rs))

def signal(qqq_p, ma50, ma200, rsi, vix_p):
    """
    매수 조건:
      1) QQQ > 50일 MA  (단기 상승 추세)
      2) QQQ > 200일 MA (장기 상승 추세)
      3) RSI < 70       (과매수 아님)
      4) VIX < 25       (공포 낮음)
    모두 만족 → BUY, 하나라도 아니면 WAIT
    """
    if (qqq_p > ma50) and (qqq_p > ma200) and (rsi < 70) and (vix_p < 25):
        return "BUY"
    elif (qqq_p < ma200) or (vix_p > 35):
        return "SELL"
    else:
        return "WAIT"

# ── 오늘 신호 ──────────────────────────────────────────────────────────────
today_data = {
    "date":       END.strftime("%Y-%m-%d"),
    "qqq_price":  round(float(qqq.iloc[-1]),  2),
    "tqqq_price": round(float(tqqq.iloc[-1]), 2),
    "vix":        round(float(vix.iloc[-1]),  2),
    "ma50":       round(float(qqq_ma50.iloc[-1]),  2),
    "ma200":      round(float(qqq_ma200.iloc[-1]), 2),
    "rsi14":      round(float(rsi14.iloc[-1]), 2),
    "signal":     signal(
                    qqq.iloc[-1], qqq_ma50.iloc[-1],
                    qqq_ma200.iloc[-1], rsi14.iloc[-1], vix.iloc[-1]
                  ),
}

# ── 과거 히스토리 (백테스트용) ─────────────────────────────────────────────
common_idx = qqq_ma200.dropna().index
history = []
for date in common_idx:
    sig = signal(
        qqq[date], qqq_ma50[date], qqq_ma200[date], rsi14[date], vix.reindex([date]).iloc[0]
    )
    history.append({
        "date":      str(date.date()),
        "qqq":       round(float(qqq[date]),      2),
        "tqqq":      round(float(tqqq.reindex([date]).iloc[0]), 2),
        "ma50":      round(float(qqq_ma50[date]),  2),
        "ma200":     round(float(qqq_ma200[date]), 2),
        "rsi":       round(float(rsi14[date]),     2),
        "vix":       round(float(vix.reindex([date]).iloc[0]), 2),
        "signal":    sig,
    })

# ── JSON 저장 ──────────────────────────────────────────────────────────────
output = {
    "updated_at": END.strftime("%Y-%m-%d %H:%M"),
    "today":      today_data,
    "history":    history[-60:],   # 최근 60일 (홈페이지 차트용)
}

with open("data.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n✅ 완료!")
print(f"   날짜     : {today_data['date']}")
print(f"   QQQ      : ${today_data['qqq_price']}")
print(f"   TQQQ     : ${today_data['tqqq_price']}")
print(f"   VIX      : {today_data['vix']}")
print(f"   MA50     : ${today_data['ma50']}")
print(f"   MA200    : ${today_data['ma200']}")
print(f"   RSI(14)  : {today_data['rsi14']}")
print(f"   ★ 신호  : {today_data['signal']}")
print(f"\n   data.json 저장됨 (히스토리 {len(history)}일치)")
