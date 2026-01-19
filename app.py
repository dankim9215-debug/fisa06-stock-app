import datetime
import ssl
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import feedparser

# 1. 보안 및 기본 설정
ssl._create_default_https_context = ssl._create_unverified_context
st.set_page_config(page_title="PRO 금융 분석 시스템", layout="wide")

# --- CSS: 커스텀 네온 스타일링 ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] > div {
        color: #00d4ff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }
    .news-container {
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0, 212, 255, 0.2);
        margin-bottom: 15px;
        background: rgba(255, 255, 255, 0.03);
        transition: all 0.3s ease;
    }
    .news-container:hover {
        border-color: #00d4ff;
        background: rgba(0, 212, 255, 0.05);
        transform: translateY(-2px);
    }
    .insight-box {
        background: linear-gradient(135deg, rgba(34, 139, 230, 0.15) 0%, rgba(0, 212, 255, 0.05) 100%);
        padding: 25px;
        border-radius: 20px;
        border: 1px solid #228be6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 계산 함수 (지표 추가) ---
def add_indicators(df):
    # 볼린저 밴드
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['std'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['std'] * 2)
    df['Lower'] = df['MA20'] - (df['std'] * 2)
    # RSI (상대강도지수)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_stock_news(keyword):
    rss_url = f"https://news.google.com/rss/search?q={keyword}+주가&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]

@st.cache_data(ttl=86400)
def get_listing_data():
    df = fdr.StockListing('KRX')
    df['Display'] = df['Name'] + " (" + df['Code'] + ")"
    return df

# --- 사이드바 ---
df_listing = get_listing_data()
with st.sidebar:
    st.markdown("## 🚀 분석 컨트롤러")
    selected_display = st.selectbox('종목 선택', options=df_listing['Display'].unique(), index=None)
    today = datetime.datetime.now()
    date_range = st.date_input('기간 설정', [datetime.date(today.year-1, today.month, today.day), today])
    analyze_btn = st.button('실시간 데이터 렌더링', use_container_width=True, type="primary")

# --- 메인 대시보드 ---
if analyze_btn and selected_display:
    try:
        code = selected_display.split('(')[-1].replace(')', '')
        name = selected_display.split(' (')[0]
        df = fdr.DataReader(code, date_range[0], date_range[1])
        df = add_indicators(df)

        if not df.empty:
            st.markdown(f"# {name} <small style='color:#868e96;'>{code}</small>", unsafe_allow_html=True)
            
            # 1. 지표 카드
            curr_p = int(df['Close'].iloc[-1])
            prev_p = int(df['Close'].iloc[-2])
            diff = curr_p - prev_p
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("현재가", f"{curr_p:,}원", f"{diff:,}원")
            m2.metric("24h 최고", f"{int(df['High'].max()):,}원")
            m3.metric("24h 최저", f"{int(df['Low'].min()):,}원")
            m4.metric("RSI 지표", f"{df['RSI'].iloc[-1]:.1f}", "과매수" if df['RSI'].iloc[-1] > 70 else "과매도" if df['RSI'].iloc[-1] < 30 else "중립")

            # 2. 메인 프로페셔널 차트 (Plotly)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, 
                               row_heights=[0.6, 0.2, 0.2],
                               subplot_titles=("Candlestick & Bollinger Bands", "Volume", "RSI Oscillator"))

            # 캔들스틱 차트
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                                         name='주가', increasing_line_color='#ff4b4b', decreasing_line_color='#007bff'), row=1, col=1)
            
            # 볼린저 밴드 (영역 채우기)
            fig.add_trace(go.Scatter(x=df.index, y=df['Upper'], line=dict(color='rgba(255,255,255,0.2)', width=1), name='Upper Band'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Lower'], line=dict(color='rgba(255,255,255,0.2)', width=1), fill='tonexty', fillcolor='rgba(0,212,255,0.05)', name='Lower Band'), row=1, col=1)

            # 거래량
            colors = ['#ff4b4b' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#007bff' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#00d4ff', width=2), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            # 레이아웃 업데이트
            fig.update_layout(height=900, template="plotly_dark", 
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis_rangeslider_visible=False, showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)

            # 3. 하단 섹션
            c1, c2 = st.columns([1, 1.2])
            with c1:
                st.markdown("### 💡 AI 분석 엔진 인사이트")
                st.markdown(f"""
                <div class="insight-box">
                    <h4 style='color:#00d4ff;'>기술적 상태 요약</h4>
                    • <b>추세:</b> 현재 주가는 볼린저 밴드 {'상단' if curr_p > df['MA20'].iloc[-1] else '하단'} 부근에서 움직이고 있습니다.<br>
                    • <b>강도:</b> RSI가 {df['RSI'].iloc[-1]:.1f}로 {'매수세가 강한' if df['RSI'].iloc[-1] > 60 else '매도세가 우세한' if df['RSI'].iloc[-1] < 40 else '안정적인'} 흐름입니다.<br>
                    • <b>전략:</b> 이동평균선(MA20) 돌파 여부를 주시하세요.
                </div>
                """, unsafe_allow_html=True)

            with c2:
                st.markdown("### 📰 주요 뉴스 헤드라인")
                for item in get_stock_news(name):
                    st.markdown(f"""<div class="news-container"><a href="{item.link}" class="news-title" target="_blank">{item.title}</a></div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"분석 중 오류 발생: {e}")