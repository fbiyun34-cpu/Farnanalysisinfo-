import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. 환경 설정 및 비밀키 관리 (Secret Management)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Farminfo Analytics",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 비밀키 로드 함수 (Local vs Cloud Hybrid)
def get_naver_api_secrets():
    """
    Naver API 키를 로드합니다.
    1순위: Streamlit Cloud Secrets (st.secrets)
    2순위: 로컬 .env 파일
    """
    # 1. Streamlit Cloud Secrets 확인
    if "naver_api" in st.secrets:
        return st.secrets["naver_api"]["client_id"], st.secrets["naver_api"]["client_secret"]
    
    # 2. 로컬 .env 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # .env 후보 경로
    env_candidates = [
        os.path.join(project_root, ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    
    for env_path in env_candidates:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break
            
    c_id = os.getenv('NAVER_CLIENT_ID')
    c_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if c_id and c_secret:
        return c_id, c_secret
    
    return None, None

client_id, client_secret = get_naver_api_secrets()

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 (Data Loading)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    """데이터를 로드하고 캐싱합니다."""
    # 파일 경로 (절대 경로 또는 상대 경로)
    # ---------------------------
    # [Path Debugging Strategy]
    # ---------------------------
    # Streamlit Cloud와 로컬 환경의 경로 차이를 해결하기 위한 후보군 탐색
    current_dir = os.path.dirname(os.path.abspath(__file__)) # .../output
    project_root = os.path.dirname(current_dir)             # .../farminfo
    
    candidate_paths = [
        # 1. 스크립트 기준 상대 경로 (로컬/Cloud 일반적)
        os.path.join(project_root, "input", "preprocessed_data.csv"),
        # 2. 현재 작업 디렉토리(CWD) 기준 입수 (Streamlit Cloud Root 실행 시)
        os.path.join(os.getcwd(), "input", "preprocessed_data.csv"),
        # 3. Mount 경로 하드코딩 (최후의 수단, 리포지토리명에 따라 다를 수 있음)
        "/mount/src/farminfo/input/preprocessed_data.csv", 
        "input/preprocessed_data.csv"
    ]
    
    filepath = None
    for path in candidate_paths:
        if os.path.exists(path):
            filepath = path
            break
            
    if filepath is None:
        st.error("🚨 데이터 파일을 찾을 수 없습니다.")
        st.write("### Debug Info")
        st.write(f"- Current Working Dir: `{os.getcwd()}`")
        st.write(f"- Script Loc: `{current_dir}`")
        st.write("#### Checked Paths:")
        for p in candidate_paths:
            st.write(f"- `{p}`")
            
        # 디렉토리 구조 힌트 제공
        st.write("#### Directory Structure (Root):")
        try:
            st.write(os.listdir(os.getcwd()))
            if os.path.exists("input"):
                 st.write(f"input dir contents: {os.listdir('input')}")
        except Exception as e:
            st.write(f"Error listing dir: {e}")
            
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    
    # 날짜 변환
    if '주문일' in df.columns:
        df['주문일'] = pd.to_datetime(df['주문일'])
        df['주문월'] = df['주문일'].dt.to_period('M').astype(str)
        df['주문시간'] = df['주문일'].dt.hour
        df['요일'] = df['주문일'].dt.day_name()
    
    # 숫자형 컬럼 변환 (콤마 제거)
    numeric_cols = ['결제금액', '판매단가', '공급단가', '주문취소 금액', '실결제 금액', '주문수량']
    for col in numeric_cols:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    # 마진 계산
    if '판매단가' in df.columns and '공급단가' in df.columns:
        df['마진'] = (df['판매단가'] - df['공급단가']) * df.get('주문수량', 1)
        
    return df

raw_df = load_data()

if raw_df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. 사이드바 및 프롬프트 (Sidebar & Prompt UI)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🎛️ 컨트롤 패널")
    
    # 기간 설정
    min_date = raw_df['주문일'].min().date()
    max_date = raw_df['주문일'].max().date()
    
    date_range = st.date_input(
        "기간 선택",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # 빠른 필터
    st.divider()
    all_channels = raw_df['주문경로'].unique().tolist()
    selected_channels = st.multiselect("주문 경로 필터", all_channels, default=all_channels)
    
    if '이벤트 여부' in raw_df.columns:
        show_event_only = st.checkbox("이벤트 주문만 보기")
    else:
        show_event_only = False
        
    st.info(f"Updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    
    # API 상태 표시 (보안상 키 자체는 노출 X)
    if client_id:
        st.success("Naver API Key Loaded ✅")
    else:
        st.warning("Naver API Key Not Found ⚠️")

# 메인 프롬프트 영역
st.markdown("## 🍊 Farminfo Prompt Analytics")
prompt = st.text_input(
    "분석하고 싶은 키워드를 입력하세요 (예: 서울, 감귤, 선물, 카카오톡)", 
    placeholder="키워드를 입력하면 관련 데이터만 필터링하여 깊이 있게 분석합니다.",
    help="상품명, 옵션, 주소, 주문경로 등에서 키워드를 검색합니다."
)

# -----------------------------------------------------------------------------
# 4. 데이터 필터링 로직 (Filtering Logic)
# -----------------------------------------------------------------------------
df_filtered = raw_df.copy()

# 1. 기간 필터
if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[
        (df_filtered['주문일'].dt.date >= start_date) & 
        (df_filtered['주문일'].dt.date <= end_date)
    ]

# 2. 채널 필터
if selected_channels:
    df_filtered = df_filtered[df_filtered['주문경로'].isin(selected_channels)]

# 3. 이벤트 필터
if show_event_only and '이벤트 여부' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['이벤트 여부'] == 'Y']

# 4. 프롬프트(검색어) 필터 - 핵심 로직
if prompt:
    with st.spinner(f"'{prompt}' 관련 데이터 분석 중..."):
        # 검색 대상 컬럼
        search_cols = ['상품명', '옵션코드', '주소', '주문경로', '목적', '고객선택옵션']
        valid_cols = [c for c in search_cols if c in df_filtered.columns]
        
        # 키워드 포함 여부 마스크 생성 (OR 조건)
        mask = pd.Series(False, index=df_filtered.index)
        for col in valid_cols:
            mask |= df_filtered[col].astype(str).str.contains(prompt, case=False)
        
        df_filtered = df_filtered[mask]
        
        if df_filtered.empty:
            st.warning(f"'{prompt}'에 대한 검색 결과가 없습니다.")
            st.stop()
        else:
            st.success(f"'{prompt}' 키워드로 {len(df_filtered):,}건의 데이터를 찾았습니다.")

# -----------------------------------------------------------------------------
# 5. KPI 메트릭 (Metrics) [Table Like 1]
# -----------------------------------------------------------------------------
total_sales = df_filtered['실결제 금액'].sum()
total_orders = len(df_filtered)
avg_order_value = total_sales / total_orders if total_orders > 0 else 0
avg_margin = df_filtered['마진'].mean() if '마진' in df_filtered.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 매출액", f"{total_sales:,.0f}원")
col2.metric("총 주문수", f"{total_orders:,}건")
col3.metric("평균 객단가 (AOV)", f"{avg_order_value:,.0f}원")
col4.metric("평균 마진", f"{avg_margin:,.0f}원")

st.divider()

# -----------------------------------------------------------------------------
# 6. 메인 탭 구성 (Main Tabs)
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 분석", "🔍 심층 EDA (Deep Dive)", "👥 고객 데이터", "📈 셀러 분석"])

with tab1:
    col_chart1, col_chart2 = st.columns(2)
    
    # [Graph 1] 일별 매출 추이
    with col_chart1:
        st.subheader("📆 일별 매출 추이")
        daily_sales = df_filtered.groupby(df_filtered['주문일'].dt.date)['실결제 금액'].sum().reset_index()
        fig_daily = px.line(daily_sales, x='주문일', y='실결제 금액', markers=True, template="plotly_white")
        fig_daily.update_layout(hovermode="x unified")
        st.plotly_chart(fig_daily, use_container_width=True)

    # [Graph 2] 상품별 판매 비중 (Sunburst)
    with col_chart2:
        st.subheader("🍊 상품 및 옵션 비중")
        if '무게 구분' in df_filtered.columns:
            path_cols = ['상품명', '무게 구분']
        else:
            path_cols = ['상품명']
            
        fig_sun = px.sunburst(
            df_filtered, 
            path=path_cols, 
            values='실결제 금액',
            color='실결제 금액',
            color_continuous_scale='OrRd'
        )
        st.plotly_chart(fig_sun, use_container_width=True)

    # [Table 2] 상품별 판매 랭킹
    st.subheader("🏆 상품별 판매 성과")
    prod_rank = df_filtered.groupby('상품명').agg(
        총주문수=('주문수량', 'sum'),
        총매출=('실결제 금액', 'sum')
    ).reset_index().sort_values('총매출', ascending=False)
    prod_rank['매출비중'] = (prod_rank['총매출'] / total_sales * 100).map('{:.1f}%'.format)
    st.dataframe(prod_rank, use_container_width=True)


with tab2:
    # [Graph 3] 채널별 성과 비교
    st.subheader("📢 채널별 성과")
    channel_perf = df_filtered.groupby('주문경로')[['실결제 금액', '마진']].sum().reset_index()
    fig_channel = px.bar(
        channel_perf, x='주문경로', y='실결제 금액', 
        color='마진', title="주문경로별 매출 (색상: 마진)",
        text_auto='.2s'
    )
    st.plotly_chart(fig_channel, use_container_width=True)

    col_deep1, col_deep2 = st.columns(2)
    
    # [Graph 4] 주문수량 vs 매출 산점도
    with col_deep1:
        st.subheader("📈 주문 패턴 (Scatter)")
        fig_scatter = px.scatter(
            df_filtered, x='주문수량', y='실결제 금액', 
            color='주문경로', hover_data=['상품명'],
            title="주문수량 vs 결제금액 상관관계"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # [Graph 5] 지역별 매출 (Bar Chart)
    with col_deep2:
        st.subheader("📊 지역별 매출 규모 (Bar)")
        if '광역지역' in df_filtered.columns:
            region_stats = df_filtered.groupby('광역지역')['실결제 금액'].sum().reset_index().sort_values('실결제 금액', ascending=True)
            
            fig_bar_region = px.bar(
                region_stats, 
                x='실결제 금액', 
                y='광역지역', 
                orientation='h',
                text_auto='.2s',
                title="지역별 매출액"
            )
            fig_bar_region.update_traces(marker_color='#FF8C00') # 감귤색 포인트
            fig_bar_region.update_layout(xaxis_title="매출액", yaxis_title="지역")
            st.plotly_chart(fig_bar_region, use_container_width=True)
            
    # [Table 3] 지역별 통계
    st.subheader("📍 지역별 상세 통계")
    if '광역지역' in df_filtered.columns:
        region_df = df_filtered.groupby('광역지역').agg(
            주문건수=('UID', 'count'),
            총매출=('실결제 금액', 'sum')
        ).sort_values('총매출', ascending=False)
        st.dataframe(region_df, use_container_width=True)

with tab3:
    col_cust1, col_cust2 = st.columns([1, 2])
    
    # [Table 4] VIP 고객 리스트
    with col_cust1:
        st.subheader("👑 VIP 고객 리스트")
        if 'UID' in df_filtered.columns:
            vip_df = df_filtered.groupby('UID').agg(
                구매횟수=('주문번호', 'count'),
                총결제금액=('실결제 금액', 'sum')
            ).sort_values('구매횟수', ascending=False).head(20)
            st.dataframe(vip_df, use_container_width=True)
            
    # [Table 5] 원본 데이터 브라우저
    with col_cust2:
        st.subheader("📄 상세 데이터 조회")
        st.dataframe(df_filtered, use_container_width=True)

with tab4:
    st.header("📈 셀러 분석 (Seller Analysis)")
    
    if '셀러명' not in df_filtered.columns:
         st.warning("데이터에 '셀러명' 컬럼이 없어 분석할 수 없습니다.")
    else:
        # 1. 셀러 요약 지표
        total_sellers = df_filtered['셀러명'].nunique()
        
        # 월별 활동 셀러 계산
        df_monthly = df_filtered.copy()
        df_monthly['주문월'] = df_monthly['주문일'].dt.to_period('M')
        
        monthly_seller_counts = df_monthly.groupby('주문월')['셀러명'].nunique()
        current_active = monthly_seller_counts.iloc[-1] if not monthly_seller_counts.empty else 0
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("총 활동 셀러수 (기간내)", f"{total_sellers}명")
        col_s2.metric("현재 월 활동 셀러", f"{current_active}명")
        
        st.divider()
        
        # 2. 유입/이탈 분석 (Churn Analysis)
        st.subheader("🔄 월별 셀러 유입/이탈 현황")
        
        # 전체 기간 데이터가 필요함 (필터링되지 않은 원본 raw_df 사용 권장하지만, 현재 필터 내 분석이면 df_filtered)
        # 유입/이탈은 '전체 기간' 관점이 중요하므로 raw_df를 사용하는 것이 맞을 수 있음.
        # 하지만 사용자가 기간을 선택했으므로, 선택된 기간 내에서의 변동만 보여주는 것이 일관적일 수 있음.
        # 여기서는 df_filtered를 기준으로 하되, 첫 주문일을 계산.
        
        # 각 셀러의 첫 주문일
        first_order_date = df_filtered.groupby('셀러명')['주문일'].min().reset_index()
        first_order_date['가입월'] = first_order_date['주문일'].dt.to_period('M')
        
        # 각 월별 신규 셀러수
        new_sellers = first_order_date.groupby('가입월')['셀러명'].count().reset_index()
        new_sellers.columns = ['월', '신규 유입']
        new_sellers['월'] = new_sellers['월'].astype(str)
        
        # 이탈 (Churn) - 전월에는 있었으나 이번달에는 없는 경우
        # 월별 활동 리스트
        periods = sorted(df_monthly['주문월'].unique())
        churn_data = []
        
        if len(periods) > 1:
            for i in range(1, len(periods)):
                prev_month = periods[i-1]
                curr_month = periods[i]
                
                prev_sellers = set(df_monthly[df_monthly['주문월'] == prev_month]['셀러명'])
                curr_sellers = set(df_monthly[df_monthly['주문월'] == curr_month]['셀러명'])
                
                churned = len(prev_sellers - curr_sellers)
                churn_data.append({'월': str(curr_month), '이탈': churned * -1}) # 음수로 표현
                
        churn_df = pd.DataFrame(churn_data)
        
        # 병합
        if not new_sellers.empty:
            analysis_df = new_sellers
            if not churn_df.empty:
                analysis_df = pd.merge(analysis_df, churn_df, on='월', how='outer').fillna(0)
        else:
             analysis_df = churn_df

        if not analysis_df.empty:
            analysis_df = analysis_df.sort_values('월')
            
            fig_churn = go.Figure()
            fig_churn.add_trace(go.Bar(x=analysis_df['월'], y=analysis_df['신규 유입'], name='신규 유입', marker_color='green'))
            fig_churn.add_trace(go.Bar(x=analysis_df['월'], y=analysis_df['이탈'], name='이탈', marker_color='red'))
            
            fig_churn.update_layout(title="월별 셀러 유입(+) vs 이탈(-)", barmode='relative')
            st.plotly_chart(fig_churn, use_container_width=True)
            
        # 3. 셀러별 매출 변동 (Revenue Trend)
        st.subheader("📊 셀러별 매출 추이")
        
        # 상위 5명 셀러 기본 선택
        top_sellers = df_filtered.groupby('셀러명')['실결제 금액'].sum().nlargest(5).index.tolist()
        
        selected_sellers_trend = st.multiselect(
            "매출 추이를 확인할 셀러 선택", 
            df_filtered['셀러명'].unique(),
            default=top_sellers
        )
        
        if selected_sellers_trend:
            trend_df = df_filtered[df_filtered['셀러명'].isin(selected_sellers_trend)]
            # 월별 or 주별 매출
            trend_pivot = trend_df.groupby([trend_df['주문일'].dt.to_period('W').astype(str), '셀러명'])['실결제 금액'].sum().reset_index()
            trend_pivot.columns = ['기간(주)', '셀러명', '매출액']
            
            fig_trend = px.line(trend_pivot, x='기간(주)', y='매출액', color='셀러명', markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
