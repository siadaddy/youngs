import streamlit as st
import pandas as pd
import duckdb
import gdown
import os

@st.cache_data
def download_duckdb():
    file_id = "1BY8nUq5OfyrDnxyZRiuSACf3TDbrdx7m"
    url = f"https://drive.google.com/uc?id={file_id}"
    output_path = "data_cache/instacart.duckdb"
    
    os.makedirs("data_cache", exist_ok=True)
    if not os.path.exists(output_path):
        gdown.download(url, output_path, quiet=False)
    
    return output_path

# DuckDB 파일 다운로드 및 연결
DB_PATH = download_duckdb()
con = duckdb.connect(DB_PATH)

# 테이블 불러오기
vip_df         = con.execute("SELECT * FROM _customscore").df()
orders         = con.execute("SELECT * FROM orders").df()
order_products = con.execute("SELECT * FROM order_products__prior").df()
products       = con.execute("SELECT * FROM products").df()
rec_df         = con.execute("SELECT * FROM user_recommendations").df()
con.close()



tab1, tab2, tab3, tab4 = st.tabs([
    "💎 1등급 고객 분석",
    "📊 등급 비교",
    "📈 전환 전략",
    "🎯 고객 맞춤 추천"
])



# ────────────────────────────────────────────────────────
# 📌 탭 1: 1등급 고객 분석
# ────────────────────────────────────────────────────────
with tab1:
    st.markdown("## 💎 1등급 고객 행동 분석")

    st.info("""
    **InstaCart 고객 데이터** 중 **1등급(Diamond)** 고객들의  
    행동 패턴 및 스코어링 구조를 분석하여  
    하위 등급 고객의 전환 전략 수립에 활용합니다.
    """)

    # 스코어링 설명
    st.markdown("### 📊 VIP Score 산정 기준")
    st.table(pd.DataFrame({
        "항목": ["총 주문 수", "총 상품 수", "재구매율", "최신성(recency)"],
        "설명": ["고객의 전체 주문 횟수", "고객이 구매한 상품 수", "Reordered 비율", "최근 주문일 기준 경과 일수 (적을수록 높음)"],
        "가중치": ["30%", "20%", "25%", "25%"]
    }))

    # KPI 요약
    st.markdown("### 📌 전체 고객군 요약 KPI")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("전체 고객 수", f"{len(vip_df):,}")
    with col2:
        diamond_avg = vip_df[vip_df['vip_grade'] == '1.Diamond']['vip_score'].mean()
        st.metric("1등급 평균 점수", f"{diamond_avg:.1f}")
    with col3:
        st.metric("전체 평균 점수", f"{vip_df['vip_score'].mean():.1f}")

    # 등급 분포 시각화
    st.markdown("### 🧱 고객 등급 분포")
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    sns.countplot(
        x='vip_grade',
        data=vip_df,
        order=['5.Bronze','4.Silver','3.Gold','2.Platinum','1.Diamond'],
        palette='Blues',
        ax=ax1
    )
    ax1.set_title("고객 등급 분포")
    st.pyplot(fig1)

    # 히트맵 (요일 vs 시간)
    st.markdown("### 🕒 1등급 고객의 활동 요일/시간대")
    diamond_users = vip_df[vip_df['vip_grade'] == '1.Diamond']['user_id']
    diamond_orders = orders[orders['user_id'].isin(diamond_users)]
    heatmap_data = pd.crosstab(
        diamond_orders['order_dow'],
        diamond_orders['order_hour_of_day']
    )
    fig2, ax2 = plt.subplots(figsize=(12, 4))
    sns.heatmap(heatmap_data, cmap='Blues', ax=ax2)
    ax2.set_title("1등급 고객 주문 시간 히트맵")
    st.pyplot(fig2)

    # Top10 상품
    st.markdown("### 🛍️ 1등급 고객 Top 10 구매 상품")
    top_orders = order_products[order_products['order_id'].isin(diamond_orders['order_id'])]
    top_items = top_orders['product_id'].value_counts().head(10).reset_index()
    top_items.columns = ['product_id', 'count']
    top_items = top_items.merge(products, on='product_id', how='left')
    st.dataframe(top_items[['product_name', 'count']], use_container_width=True)


# ────────────────────────────────────────────────────────
# 🧱 탭 2: 등급 비교 (레이아웃만)
# ────────────────────────────────────────────────────────
with tab2:
    st.markdown("## 📊 2~3등급 vs 1등급 비교")

    st.info("""
    2~3등급 고객이 1등급으로 전환되기 위해  
    어떤 요소를 개선해야 하는지 비교 시각화를 통해 확인합니다.
    """)

    st.markdown("▶️ 향후 포함할 분석 예시:")
    st.markdown("- 총 주문 수, 재구매율 등 지표 분포 비교")
    st.markdown("- 평균 장바구니 크기 및 최신성 차이 시각화")
    st.markdown("- 1등급 고객 특징 기반 피쳐 중요도 분석")


# ────────────────────────────────────────────────────────
# 🎯 탭 3: 전환 전략 (레이아웃만)
# ────────────────────────────────────────────────────────
with tab3:
    st.markdown("## 📈 2~3등급 고객의 1등급 전환 전략")

    st.info("""
    행동 패턴, 상품 선호도, 재구매 성향 등을 기반으로  
    개별 고객에 맞는 **1등급 전환 유도 전략**을 제시합니다.
    """)

    st.markdown("▶️ 향후 포함할 전략 예시:")
    st.markdown("- 유사한 1등급 고객 군집과의 비교")
    st.markdown("- 관심 상품군 기반 맞춤 캠페인 제안")
    st.markdown("- 고객별 행동 개선 시나리오 예측")


# ────────────────────────────────────────────────────────
# 🎯 탭 4: 고객 맞춤 추천
# ────────────────────────────────────────────────────────

with tab4:
    st.markdown("## 🎯 고객 맞춤 추천")
    st.markdown("2~3등급 고객의 추천 상품 Top 5를 확인하고, 1등급 전환 전략을 유도해보세요.")

    # 고객 선택 드롭다운 (화면 내 위치)
    user_list = rec_df['user_id'].tolist()
    selected_user = st.selectbox("👤 고객 선택 (2~3등급)", user_list)

    # 선택한 고객의 추천 상품 표시
    selected_row = rec_df[rec_df['user_id'] == selected_user]
    if not selected_row.empty:
        recommended_products = selected_row.iloc[0, 1:].tolist()

        st.markdown(f"### 🛍️ 추천 상품 목록 (User ID: `{selected_user}`)")
        for i, product_name in enumerate(recommended_products, 1):
            st.markdown(f"- **{i}. {product_name}**")
    else:
        st.warning("해당 고객에 대한 추천 결과가 없습니다.")



    
