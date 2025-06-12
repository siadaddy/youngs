import os
import gdown
import streamlit as st

# ============================
# Streamlit 페이지 설정 (가장 먼저 호출)
# ============================
st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")

# ============================
# 1) Google Drive 폴더 URL
# ============================
GDRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/11ZilE7WPPlFMslvnUy4tIFzoJgNTQtpN"

# ============================
# 2) 로컬 데이터 디렉토리 준비 및 다운로드
# ============================
DATA_DIR = "data_InstaCart"
os.makedirs(DATA_DIR, exist_ok=True)
if not os.listdir(DATA_DIR):
    st.info("📥 Google Drive에서 데이터 다운로드 중...")
    gdown.download_folder(
        url=GDRIVE_FOLDER_URL,
        output=DATA_DIR,
        quiet=False,
        use_cookies=False
    )
    st.success("✅ 데이터 다운로드 완료")

# ============================
# 라이브러리 임포트 (st.* 호출 이후)
# ============================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl
import plotly.express as px
import pickle

# Mac에서 한글 깨짐 방지
plt.rcParams['font.family'] = 'AppleGothic'
mpl.rcParams['axes.unicode_minus'] = False

# 대시보드 제목 및 설명
st.title("🚀 InstaCart VIP 고객 전환 전략 및 행동 분석 대시보드")
st.markdown("""
이 대시보드는 1등급 고객 행동 분석을 기반으로,  
2~3등급 고객을 1등급으로 전환하기 위한 전략과 맞춤 추천을 제공합니다.
""")

# 데이터 로드 (캐시)
@st.cache_data(show_spinner=False)
def load_data():
    vip_df = pd.read_csv(f"{DATA_DIR}/vip_summary_v2.csv")
    products = pd.read_csv(f"{DATA_DIR}/products.csv")
    orders = pd.read_csv(f"{DATA_DIR}/orders.csv")
    order_products = pd.read_csv(f"{DATA_DIR}/order_products__prior.csv")
    return vip_df, products, orders, order_products

# 모델 로드 (캐시 리소스)
@st.cache_resource(show_spinner=False)
def load_model():
    with open(f'{DATA_DIR}/diamond_2_3_lightfm_model.pkl', 'rb') as f:
        model, user_id_map, product_id_map = pickle.load(f)
    return model, user_id_map, product_id_map

vip_df, products, orders, order_products = load_data()
model, user_id_map, product_id_map = load_model()

# VIP 등급 분류
bins = [-0.1, 60, 70, 80, 90, 100]
labels = ['5.Bronze','4.Silver','3.Gold','2.Platinum','1.Diamond']
vip_df['vip_grade'] = pd.cut(vip_df['vip_score'], bins=bins, labels=labels)

# invert maps for 추천
inv_user_map = {v: k for k, v in user_id_map.items()}
inv_product_map = {v: k for k, v in product_id_map.items()}

# 추천 함수 캐시
@st.cache_data(show_spinner=False)
def cached_recommend_products(user_id, N=5):
    if user_id not in user_id_map:
        return []
    user_x = user_id_map[user_id]
    scores = model.predict(user_x, np.arange(len(product_id_map)))
    top_items = np.argsort(-scores)[:N]
    return [inv_product_map[i] for i in top_items]

# 준비 함수
@st.cache_data(show_spinner=False)
def prepare_strategy_data(vip_df, orders, order_products):
    op_u = order_products.merge(orders[['order_id','user_id']], on='order_id', how='left')
    diversity = op_u.groupby('user_id')['product_id'].nunique().rename('unique_product_count')
    vip = vip_df.set_index('user_id').join(diversity).reset_index()
    g1 = vip[vip['vip_grade']=='1.Diamond'].copy(); g1['group']='1등급'
    g23 = vip[vip['vip_grade'].isin(['2.Platinum','3.Gold'])].copy(); g23['group']='2~3등급'
    comp = pd.concat([g1,g23])
    # 재구매 주기
    d_users = vip[vip['vip_grade']=='1.Diamond']['user_id']
    d_orders = orders[orders['user_id'].isin(d_users)].sort_values(['user_id','order_number'])
    d_orders['days_since_prior_order'] = d_orders['days_since_prior_order'].fillna(0)
    avg_int = d_orders.groupby('user_id')['days_since_prior_order'].mean().reset_index().rename(columns={'days_since_prior_order':'avg_reorder_interval'})
    return comp, avg_int

compare_df, avg_interval_df = prepare_strategy_data(vip_df, orders, order_products)

# 탭 구성
tabs = st.tabs(["🏠 개요","📊 등급별 고객 분석","🔎 1등급 고객 집중 분석","💡 2~3등급 전환 전략","🎯 맞춤형 추천 시스템"])


with 탭_개요:
    st.header("InstaCart VIP 고객 분석 개요")
    st.markdown("""
    - 고객의 활동/재구매/최근성 등을 반영한 VIP 스코어 기반 등급 분류
    - 상위 고객군 분석과 등급별 행동 패턴 비교
    - 전환 전략 제안과 추천 시스템 탑재 예정
    """)

    grade_counts = vip_df['vip_grade'].value_counts(normalize=True).reindex(labels).fillna(0)
    grade_percents = (grade_counts * 100).round(1)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("1등급 (Diamond)", f"{grade_percents['1.Diamond']}%")
    col2.metric("2등급 (Platinum)", f"{grade_percents['2.Platinum']}%")
    col3.metric("3등급 (Gold)", f"{grade_percents['3.Gold']}%")
    col4.metric("4등급 (Silver)", f"{grade_percents['4.Silver']}%")
    col5.metric("5등급 (Bronze)", f"{grade_percents['5.Bronze']}%")

    st.markdown("---")

    col_total1, col_total2, col_total3 = st.columns(3)
    col_total1.metric("전체 고객 수", f"{vip_df.shape[0]:,}명")
    col_total2.metric("1등급 고객 비율", f"{grade_percents['1.Diamond']}%")
    col_total3.metric("평균 VIP Score", f"{vip_df['vip_score'].mean():.2f}")

with 탭_등급:
    st.header("📌 고객 등급 분포")
    grade_counts = vip_df['vip_grade'].value_counts().reindex(labels)
    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        color=grade_counts.index,
        color_discrete_sequence=px.colors.sequential.Blues_r,
        labels={'x': 'VIP 등급', 'y': '고객 수'},
        title='고객 등급 분포'
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 등급별 행동 비교 보기"):
        st.markdown("1등급과 2~3등급 고객의 행동 지표를 비교합니다. 큰 격차를 보이는 항목은 전환 전략 수립에 중요한 포인트가 됩니다.")
        cols = ['total_orders', 'total_products', 'reorder_rate', 'avg_cart_size', 'recency', 'unique_product_count']
        fig2, axes = plt.subplots(2, 3, figsize=(18, 8))
        for i, col in enumerate(cols):
            ax = axes[i//3, i%3]
            sns.boxplot(x='group', y=col, data=compare_df, palette='Set2', ax=ax)
            ax.set_title(f"{col} 비교")
        fig2.delaxes(axes[1][2])
        st.pyplot(fig2)

        st.markdown("#### 📋 평균값 비교표")
        group_means = compare_df.groupby('group')[cols].mean().round(2)
        st.dataframe(group_means)

with 탭_1등급:
    st.header("🔎 1등급 고객 집중 분석")
    order_products = order_products.merge(
        orders[['order_id', 'user_id', 'order_number', 'order_dow', 'order_hour_of_day']],
        on='order_id', how='left'
    )
    top_users = vip_df[vip_df['vip_grade'] == '1.Diamond']
    top_orders = order_products[order_products['user_id'].isin(top_users['user_id'])]
    top_orders = top_orders.merge(products[['product_id', 'product_name']], on='product_id', how='left')

    with st.expander("🛒 상위 구매 상품 분석"):
        top_products = top_orders['product_name'].value_counts().head(10)
        fig3, ax3 = plt.subplots()
        sns.barplot(x=top_products.values, y=top_products.index, palette='viridis', ax=ax3)
        ax3.set_title("1등급 고객 TOP 구매 상품")
        ax3.set_xlabel("구매 횟수")
        ax3.set_ylabel("상품명")
        st.pyplot(fig3)
        st.markdown("\n\n1등급 고객은 특정 인기 상품에 대한 충성도가 높고 반복 구매가 집중되는 경향이 있습니다. 추천 기반 마케팅이 효과적입니다.")

    with st.expander("📆 활동 요일/시간대 분석"):
        col1, col2 = st.columns(2)
        with col1:
            fig4, ax4 = plt.subplots()
            sns.countplot(x='order_dow', data=top_orders, palette='Blues', ax=ax4)
            ax4.set_title("요일별 주문 분포 (0=일)")
            st.pyplot(fig4)
        with col2:
            fig5, ax5 = plt.subplots()
            sns.countplot(x='order_hour_of_day', data=top_orders, palette='Greens', ax=ax5)
            ax5.set_title("시간대별 주문 분포")
            st.pyplot(fig5)
        st.markdown("\n\n1등급 고객은 주로 특정 요일과 시간대에 활동이 집중되어 있어, **타이밍 기반의 마케팅 자동화**가 효과적일 수 있습니다.")

    with st.expander("📈 재구매 주기 분석"):
        fig6, ax6 = plt.subplots(figsize=(10, 5))
        sns.histplot(avg_interval_df['avg_reorder_interval'], bins=30, kde=True, color='steelblue', ax=ax6)
        ax6.set_title("1등급 고객 평균 재구매 주기 분포")
        ax6.set_xlabel("평균 재구매 주기 (일)")
        ax6.set_ylabel("고객 수")
        st.pyplot(fig6)

        st.markdown(f"\n📊 **1등급 고객 평균 재구매 주기:** `{avg_interval_df['avg_reorder_interval'].mean():.2f}` 일")
        st.markdown("""
        **해석**: 대부분의 1등급 고객은 **5~15일 사이**에 재구매를 수행하고 있어,
        이 타이밍에 맞춘 **리마인드 마케팅** 또는 **정기배송 유도** 전략이 효과적입니다.
        """)

with 탭_전략:
    st.header("💡 2~3등급 → 1등급 전환 전략 상세 분석")
    st.markdown("1등급 고객과 2~3등급 고객 행동 차이에 기반한 전략별 인사이트입니다.\n")

    with st.expander("1️⃣ 다양한 상품 경험 유도"):
        st.markdown("""
        - 1등급 고객은 더 다양한 상품을 구매합니다.
        - 2~3등급 고객에게 신상품 체험 쿠폰, 번들 추천 등으로 경험 폭 확대 필요.
        """)
        fig = px.bar(compare_df.groupby('group')['unique_product_count'].mean().reset_index(),
                     x='unique_product_count', y='group', orientation='h', color='group',
                     labels={'unique_product_count':'고유 상품 수', 'group':'고객 그룹'},
                     title='고객 그룹별 상품 다양성 비교')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("2️⃣ 재방문 유도 전략"):
        st.markdown("""
        - 1등급 고객의 재구매율이 높음.
        - 리마인드 알림과 할인 쿠폰으로 2~3등급 고객 재방문 촉진 권장.
        """)
        fig = px.bar(compare_df.groupby('group')['reorder_rate'].mean().reset_index(),
                     x='reorder_rate', y='group', orientation='h', color='group',
                     labels={'reorder_rate':'재구매율', 'group':'고객 그룹'},
                     title='고객 그룹별 재구매율 비교')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("3️⃣ 휴면 방지"):
        st.markdown("""
        - 2~3등급 고객의 방문 주기가 길어 휴면 위험 존재.
        - 인기 상품 추천 및 장바구니 리마인드 알림 강화 필요.
        """)
        fig = px.bar(compare_df.groupby('group')['recency'].mean().reset_index(),
                     x='recency', y='group', orientation='h', color='group',
                     labels={'recency':'최근 방문 주기(일)', 'group':'고객 그룹'},
                     title='고객 그룹별 최근 방문 주기 비교')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("4️⃣ 장바구니 크기 증가"):
        st.markdown("""
        - 1등급 고객의 평균 장바구니 크기가 더 큼.
        - 일정 금액 이상 구매 시 사은품 제공 등 프로모션 제안.
        """)
        fig = px.bar(compare_df.groupby('group')['avg_cart_size'].mean().reset_index(),
                     x='avg_cart_size', y='group', orientation='h', color='group',
                     labels={'avg_cart_size':'평균 장바구니 크기', 'group':'고객 그룹'},
                     title='고객 그룹별 평균 장바구니 크기 비교')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("5️⃣ 재구매 유도"):
        st.markdown("""
        - 1등급과 2~3등급 고객의 재구매 주기 분포 비교  
        - 1등급 고객은 더 짧고 일정한 재구매 주기를 보입니다.  
        - 이를 활용한 타이밍 맞춤 마케팅이 중요합니다.
        """)

        # 1등급 고객 재구매 주기
        diamond_users = vip_df[vip_df['vip_grade'] == '1.Diamond']['user_id']
        diamond_orders = orders[orders['user_id'].isin(diamond_users)].copy()
        diamond_orders['days_since_prior_order'] = diamond_orders['days_since_prior_order'].fillna(0)
        diamond_avg_interval = diamond_orders.groupby('user_id')['days_since_prior_order'].mean().rename('avg_reorder_interval')

        # 2~3등급 고객 재구매 주기
        mid_users = vip_df[vip_df['vip_grade'].isin(['2.Platinum', '3.Gold'])]['user_id']
        mid_orders = orders[orders['user_id'].isin(mid_users)].copy()
        mid_orders['days_since_prior_order'] = mid_orders['days_since_prior_order'].fillna(0)
        mid_avg_interval = mid_orders.groupby('user_id')['days_since_prior_order'].mean().rename('avg_reorder_interval')

        fig, ax = plt.subplots(figsize=(10, 5))
        sns.kdeplot(diamond_avg_interval, label='1등급 (Diamond)', fill=True, ax=ax)
        sns.kdeplot(mid_avg_interval, label='2~3등급 (Platinum+Gold)', fill=True, ax=ax)
        ax.set_title("재구매 주기 분포 비교 (평균 재구매 주기)")
        ax.set_xlabel("재구매 주기 (일)")
        ax.set_ylabel("밀도")
        ax.legend()

        st.pyplot(fig)

        # 통계값 표시
        st.markdown(f"**1등급 평균 재구매 주기:** {diamond_avg_interval.mean():.2f}일")
        st.markdown(f"**2~3등급 평균 재구매 주기:** {mid_avg_interval.mean():.2f}일")
        st.markdown(f"**1등급 중앙값 재구매 주기:** {diamond_avg_interval.median():.2f}일")
        st.markdown(f"**2~3등급 중앙값 재구매 주기:** {mid_avg_interval.median():.2f}일")







with 탭_추천:
    st.header("🎯 맞춤형 추천 시스템")

    grade_option = st.selectbox(
        "고객 등급을 선택하세요",
        options=[
            "1등급 (Diamond)",
            "2~3등급 (Platinum + Gold)"
        ],
        help="1등급은 최상위 고객, 2~3등급은 중상위 고객군을 묶어서 봅니다."
    )

    if grade_option == "1등급 (Diamond)":
        selected_grade = '1.Diamond'
    else:
        selected_grade = ['2.Platinum', '3.Gold']

    if isinstance(selected_grade, list):
        candidate_users = vip_df[vip_df['vip_grade'].isin(selected_grade)]['user_id'].tolist()
    else:
        candidate_users = vip_df[vip_df['vip_grade'] == selected_grade]['user_id'].tolist()

    user_choice = st.selectbox("고객을 선택하세요", candidate_users)

    user_data = vip_df[vip_df['user_id'] == user_choice].iloc[0]

    # 고객 히스토리 표
    history_df = pd.DataFrame({
        "항목": ["고객 ID", "VIP 등급", "총 주문 수", "총 구매 상품 수", "최근 주문 주기 (일)", "재구매율"],
        "값": [
            user_choice,
            user_data['vip_grade'],
            int(user_data['total_orders']),
            int(user_data['total_products']),
            round(user_data['recency'], 1),
            round(user_data['reorder_rate'], 3)
        ]
    })
    st.subheader("📋 고객 히스토리")
    st.table(history_df)

    # 구매 상위 5개 상품 시각화
    user_orders = order_products[order_products['user_id'] == user_choice]
    user_orders = user_orders.merge(products[['product_id', 'product_name']], on='product_id', how='left')
    top_products = user_orders['product_name'].value_counts().head(5).reset_index()
    top_products.columns = ['상품명', '구매 횟수']

    st.subheader("🛒 고객의 Top 5 구매 상품")

    fig = px.bar(
        top_products,
        x='구매 횟수',
        y='상품명',
        orientation='h',
        color='구매 횟수',
        color_continuous_scale='Blues',
        height=350
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("추천 받기"):
        with st.spinner("추천 상품을 계산 중입니다..."):
            recommended_ids = cached_recommend_products(user_choice, N=5)
            if recommended_ids:
                recommended_products = products[products['product_id'].isin(recommended_ids)][['product_name']]
                st.markdown(f"**고객 {user_choice}님에게 추천되는 상품 리스트:**")
                for pname in recommended_products['product_name']:
                    st.write(f"- {pname}")
            else:
                st.write("추천 가능한 상품이 없습니다.")

st.success("✅ 대시보드 로드 완료")
