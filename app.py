import datetime
import ssl
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import feedparser

# 1. 보안 및 기본 설정 ㅋㅋ
ssl._create_default_https_context = ssl._create_unverified_context
st.set_page_config(page_title="금융 데이터 분석 시스템", layout="wide")

# --- CSS: 다크모드 대응 및 레이아웃 스타일 ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] > div {
        color: var(--text-color) !important;
        font-size: 2.8rem !important;
        font-weight: 800 !important;
    }
    .news-container {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 12px;
        background-color: rgba(128, 128, 128, 0.05);
    }
    .news-title {
        font-weight: 600;
        text-decoration: none;
        color: #228be6 !important;
        font-size: 1.05rem;
    }
    .insight-box {
        background-color: rgba(34, 139, 230, 0.1);
        padding: 25px;
        border-radius: 20px;
        border-left: 8px solid #228be6;
        color: var(--text-color) !important;
        margin-bottom: 25px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 뉴스 및 데이터 수집 함수 ---
def get_stock_news(keyword):
    rss_url = f"https://news.google.com/rss/search?q={keyword}+주가&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]

@st.cache_data(ttl=86400)
def get_listing_data():
    df = fdr.StockListing('KRX')
    df['Display'] = df['Name'] + " (" + df['Code'] + ")"
    return df

df_listing = get_listing_data()

# --- 사이드바 ---
with st.sidebar:
    st.title("📊 분석 제어 센터")
    selected_display = st.selectbox(
        '종목 검색', 
        options=df_listing['Display'].unique(),
        index=None,
        placeholder="종목명을 입력하세요..."
    )
    today = datetime.datetime.now()
    date_range = st.date_input('분석 범위', [datetime.date(today.year, 1, 1), today])
    analyze_btn = st.button('데이터 모델 가동', use_container_width=True, type="primary")

# --- 메인 섹션 ---
if analyze_btn and selected_display:
    try:
        code = selected_display.split('(')[-1].replace(')', '')
        name = selected_display.split(' (')[0]
        price_df = fdr.DataReader(code, date_range[0], date_range[1])

        if not price_df.empty:
            curr_p = int(price_df['Close'].iloc[-1])
            prev_p = int(price_df['Close'].iloc[-2]) if len(price_df) > 1 else curr_p
            high_p = int(price_df['High'].max())
            low_p = int(price_df['Low'].min())
            
            st.markdown(f"## {name} <span style='font-size:1rem; color:#868e96;'>{code}</span>", unsafe_allow_html=True)
            
            # 1. 상단 지표 카드
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("현재가", f"{curr_p:,}원", f"{curr_p - prev_p:,}원")
            with m2: st.metric("기간 최고가", f"{high_p:,}원")
            with m3: st.metric("기간 최저가", f"{low_p:,}원")

            # 2. 통합 차트 (제목 및 축 라벨 추가)
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.1, 
                row_heights=[0.7, 0.3],
                subplot_titles=("📈 주가 추이 (Price Trend)", "📊 거래량 (Trading Volume)") # 각 그래프 제목 추가
            )

            # 상단: 주가
            fig.add_trace(go.Scatter(
                x=price_df.index, y=price_df['Close'], name='종가',
                line=dict(color='#228be6', width=3), fill='tozeroy', 
                fillcolor='rgba(34, 139, 230, 0.05)'
            ), row=1, col=1)

            # 하단: 거래량
            colors = ['#ff4b4b' if price_df['Close'].iloc[i] >= price_df['Close'].iloc[i-1] 
                      else '#007bff' for i in range(len(price_df))]
            
            fig.add_trace(go.Bar(
                x=price_df.index, y=price_df['Volume'], name='거래량',
                marker_color=colors, opacity=0.8
            ), row=2, col=1)

            # 최고/최저 어노테이션
            max_idx = price_df['High'].idxmax()
            min_idx = price_df['Low'].idxmin()
            fig.add_annotation(x=max_idx, y=high_p, text=f"최고 {high_p:,}", showarrow=True, 
                               arrowhead=1, arrowcolor="#ff4b4b", font=dict(color="#ff4b4b"), row=1, col=1)
            fig.add_annotation(x=min_idx, y=low_p, text=f"최저 {low_p:,}", showarrow=True, 
                               arrowhead=1, arrowcolor="#007bff", font=dict(color="#007bff"), row=1, col=1)

            # 레이아웃 및 축 설정
            fig.update_layout(
                template="none", height=700, margin=dict(l=0, r=0, t=50, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False, font=dict(color='#868e96')
            )
            
            # Y축 단위 및 위치 설정
            fig.update_yaxes(title_text="가격 (원)", row=1, col=1, side="right", gridcolor='rgba(128, 128, 128, 0.1)', tickformat=",")
            fig.update_yaxes(title_text="거래량 (주)", row=2, col=1, side="right", gridcolor='rgba(128, 128, 128, 0.1)', tickformat=",")
            
            # 서브플롯 제목 스타일 수정 (글자색 다크모드 대응)
            for i in fig['layout']['annotations']:
                i['font'] = dict(size=16, color='#228be6', weight='bold')

            st.plotly_chart(fig, use_container_width=True)

            # 3. 뉴스 및 인사이트 섹션
            st.markdown("---")
            col_news, col_insight = st.columns([1.5, 1])

            with col_news:
                st.markdown("### 📰 실시간 시장 뉴스")
                news_items = get_stock_news(name)
                if news_items:
                    for item in news_items:
                        st.markdown(f"""
                        <div class="news-container">
                            <a href="{item.link}" target="_blank" class="news-title">{item.title}</a>
                            <p style="font-size:0.85rem; color:#868e96; margin-top:8px;">{item.published}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("실시간 뉴스를 가져올 수 없습니다.")

            with col_insight:
                st.markdown("### 💡 금융 분석 인사이트")
                st.markdown(f"""
                <div class="insight-box">
                    <strong>데이터 분석 요약</strong><br><br>
                    • 현재가는 최고가 대비 <b>{(curr_p/high_p)*100:.1f}%</b> 수준입니다.<br><br>
                    • <b>거래량 분석:</b> 하단 차트의 색상은 전일 종가 대비 등락(상승:빨강, 하락:파랑)을 의미합니다.<br><br>
                    • <b>기술적 분석:</b> 주가와 거래량의 상관관계를 통해 매수/매도 에너지를 확인할 수 있습니다.
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### 📋 상세 데이터 리스트")
                st.dataframe(price_df.sort_index(ascending=False).head(100), use_container_width=True, height=280)

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
else:
    st.info("왼쪽 사이드바에서 종목을 검색하고 [데이터 모델 가동] 버튼을 클릭하세요.")