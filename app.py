import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import duckdb
import matplotlib

# ✅ 페이지 설정
st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")

# ✅ 폰트 설정 (Mac용)
matplotlib.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

# ✅ 캐시 기반 데이터 로딩 함수
@st.cache_data(show_spinner="📦 데이터 로딩 중... 조금만 기다려주세요!")
def load_data():
    DB_PATH = "instacart_min_v1_1000.duckdb"  # ← 변경된 경량 버전 경로
    con = duckdb.connect(DB_PATH)

    queries = {
        "vip_df":        "SELECT * FROM customscore_min",
        "orders":        "SELECT * FROM orders_min",
        "order_products":"SELECT * FROM order_products_min",
        "products":      "SELECT * FROM products_min",
        "rec_df":        "SELECT * FROM user_recommendations_min",
        "departments":   "SELECT * FROM departments_min",
        "image_map":     "SELECT product_name, image_url FROM product_image_min"
    }

    result = {}
    for key, query in queries.items():
        result[key] = con.execute(query).df()

    con.close()

    # ✅ 이미지 딕셔너리 구성
    image_dict = dict(zip(result['image_map']['product_name'], result['image_map']['image_url']))
    result['image_dict'] = image_dict
    del result['image_map']

    return result

# ✅ 고객 주문 전처리 함수
@st.cache_data(show_spinner=False)
def preprocess_orders(order_products, orders, products, user_ids):
    order_user = orders[['order_id', 'user_id']]
    merged = order_products.merge(order_user, on='order_id', how='left')
    filtered = merged[merged['user_id'].isin(user_ids)]
    result = filtered.merge(products[['product_id', 'product_name']], on='product_id', how='left')
    return result

# ✅ 공통 인기 상품 함수
@st.cache_data(show_spinner=False)
def compute_top5_common_products(diamond_orders, pg_orders, n_diamond, n_pg):
    diamond_counts = diamond_orders.groupby('product_name').size().reset_index(name='diamond_count')
    pg_counts = pg_orders.groupby('product_name').size().reset_index(name='pg_count')
    common_counts = pd.merge(diamond_counts, pg_counts, on='product_name', how='inner')

    common_counts['total_count'] = common_counts['diamond_count'] + common_counts['pg_count']
    common_counts['diamond_avg'] = common_counts['diamond_count'] / n_diamond
    common_counts['pg_avg'] = common_counts['pg_count'] / n_pg

    top5_common = common_counts.sort_values(by='total_count', ascending=False).head(5)

    plot_df = pd.melt(
        top5_common[['product_name', 'diamond_avg', 'pg_avg']],
        id_vars='product_name',
        var_name='grade',
        value_name='avg_purchase_per_user'
    )
    plot_df['grade'] = plot_df['grade'].map({'diamond_avg': '1.Diamond', 'pg_avg': '2~3등급'})
    return plot_df

# ✅ 재구매율 함수
@st.cache_data(show_spinner=False)
def compute_reorder_ratio(diamond_orders, pg_orders):
    # 1등급 재구매율
    diamond_reorder = (
        diamond_orders['reordered']
        .value_counts(normalize=True)
        .to_frame(name='ratio')
        .reset_index()
    )
    diamond_reorder.columns = ['reordered_status', 'ratio']
    diamond_reorder['grade'] = '1.Diamond'

    # 2~3등급 재구매율
    pg_reorder = (
        pg_orders['reordered']
        .value_counts(normalize=True)
        .to_frame(name='ratio')
        .reset_index()
    )
    pg_reorder.columns = ['reordered_status', 'ratio']
    pg_reorder['grade'] = '2~3등급'

    # 병합
    reorder_df = pd.concat([diamond_reorder, pg_reorder], ignore_index=True)
    reorder_df['reordered_status'] = reorder_df['reordered_status'].map({1: '재구매', 0: '최초구매'})
    
    return reorder_df

# ✅ 재구매 Top 5 상품 함수
@st.cache_data(show_spinner=False)
def compute_top5_reorder_products(diamond_orders, pg_orders):
    # 1등급 재구매 Top 5
    d_top5 = (
        diamond_orders[diamond_orders['reordered'] == 1]
        .groupby('product_name').size()
        .sort_values(ascending=False)
        .head(5)
        .reset_index(name='diamond_reorder_count')
    )

    # 2~3등급 재구매 Top 5
    pg_top5 = (
        pg_orders[pg_orders['reordered'] == 1]
        .groupby('product_name').size()
        .sort_values(ascending=False)
        .head(5)
        .reset_index(name='pg_reorder_count')
    )

    # 병합
    reorder_top5 = pd.merge(d_top5, pg_top5, on='product_name', how='outer').fillna(0)

    # melt
    reorder_melted = pd.melt(
        reorder_top5,
        id_vars='product_name',
        var_name='grade',
        value_name='reorder_count'
    )
    reorder_melted['grade'] = reorder_melted['grade'].map({
        'diamond_reorder_count': '1.Diamond',
        'pg_reorder_count': '2~3등급'
    })

    return reorder_melted



# ✅ 데이터 로딩
data = load_data()

# ✅ 변수 할당
vip_df      = data['vip_df']
orders      = data['orders']
order_products = data['order_products']
products    = data['products']
rec_df      = data['rec_df']
departments = data['departments']
image_dict  = data['image_dict']




# ────────────────────────────────────────────────────────
# 📊 대시보드 제목
# ────────────────────────────────────────────────────────

st.title("InstaCart 분석 대시보드")


# ────────────────────────────────────────────────────────
# 📊 탭 구성 및 한글 매핑
# ────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "🎁 개인 맞춤 추천 시스템",
    "🔎 고객 선정 및 등급 소개",
    "📈 전체 고객 분석",
    "🧑‍🤝‍🧑 고객 행동 분석(1등급 vs 2~3등급)"
])


# 항목 스코어 → 한글 매핑 (전역)
score_label_map = {
    'total_orders_score': '총 주문 수',
    'total_products_score': '총 상품 수',
    'reorder_rate_score': '재구매율',
    'recency_score': '최신성'
}




# ────────────────────────────────────────────────────────
# 🎯 탭 1: 고객 맞춤 추천
# ────────────────────────────────────────────────────────

with tab1:
    st.markdown("## 🎯 개인 맞춤 추천 시스템")
    st.markdown("""
    <div style='background-color:#f9f9f9; border-left: 6px solid #3f51b5; padding: 16px 20px; border-radius: 10px; margin-bottom: 20px; font-size:16px; line-height:1.6'>
        <strong>🧐 추천 시스템 안내</strong><br><br>
        선택한 <strong style="color:#3f51b5;">2~3등급 고객</strong>의 <strong>구매 이력</strong>을 확인하고,<br>
        <strong style="color:#2e7d32;">1등급 고객군과의 행동 차이</strong>를 비교해보세요. <br><br>
        👉 고객의 성향에 맞춘 <strong style="color:#ef6c00;">상품 추천</strong>을 통해 <strong>1등급 전환 전략</strong>을 제시할 수 있습니다!
    </div>
    """, unsafe_allow_html=True)

    # 고객 선택
    user_list = rec_df['user_id'].tolist()
    selected_user = st.selectbox("👤 고객 선택 (2~3등급)", user_list)

    # avg_cart_size 없으면 계산해서 추가
    if 'avg_cart_size' not in vip_df.columns:
        vip_df['avg_cart_size'] = vip_df['total_products'] / vip_df['total_orders']

    # 선택 고객 정보
    selected_info = vip_df[vip_df['user_id'] == selected_user]
    if not selected_info.empty:
        user_score = selected_info['vip_score'].values[0]
        user_reorder = selected_info['reorder_rate'].values[0]
        user_total_orders = selected_info['total_orders'].values[0]
        user_total_products = selected_info['total_products'].values[0]
        user_avg_cart_size = selected_info['avg_cart_size'].values[0]

        # 1등급 평균 계산
        diamond_df = vip_df[vip_df['vip_grade'] == '1.Diamond']
        avg_score = diamond_df['vip_score'].mean()
        avg_reorder = diamond_df['reorder_rate'].mean()
        avg_orders = diamond_df['total_orders'].mean()
        avg_products = diamond_df['total_products'].mean()
        avg_cart_size = diamond_df['avg_cart_size'].mean()

        metrics = [
            ("VIP 점수", user_score, avg_score),
            ("평균 재구매율", user_reorder * 100, avg_reorder * 100),  # ✅ 퍼센트 변환
            ("평균 주문 수", user_total_orders, avg_orders),
            ("평균 상품 수", user_total_products, avg_products),
            ("평균 장바구니 크기", user_avg_cart_size, avg_cart_size)
        ]


        st.markdown("### 선택 고객 vs 1등급 평균 비교")
        for label, user_val, avg_val in metrics:
            col1, col2, col3 = st.columns(3)
            diff = user_val - avg_val
            diff_color = '#2e7d32' if diff >= 0 else '#c62828'
            diff_str = f"{diff:+.1f}" if '재구매율' not in label else f"{diff:+.1f}%"
            v1_formatted = f"{avg_val:.1f}" if '재구매율' not in label else f"{avg_val:.1f}%"
            user_formatted = f"{user_val:.1f}" if '재구매율' not in label else f"{user_val:.1f}%"

            st.markdown(f"<span style='font-size:14px; font-weight:600;'>📌 {label}</span>", unsafe_allow_html=True)  # ✅ 항목 이름 표시 (글씨 크기 조정)

            with col1:
                st.markdown(f"""
                <div style="background-color:#f0f4f8;padding:16px;border-radius:12px;text-align:center">
                    <div style="font-size:14px;font-weight:600;margin-bottom:4px;">1등급 평균</div>
                    <div style="font-size:18px;font-weight:bold;color:#2e7d32;">{v1_formatted}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style="background-color:#fff8e1;padding:16px;border-radius:12px;text-align:center">
                    <div style="font-size:14px;font-weight:600;margin-bottom:4px;">선택 고객</div>
                    <div style="font-size:18px;font-weight:bold;color:#ef6c00;">{user_formatted}</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div style="background-color:#fafafa;padding:16px;border-radius:12px;text-align:center">
                    <div style="font-size:14px;font-weight:600;margin-bottom:4px;">차이</div>
                    <div style="font-size:18px;font-weight:bold;color:{diff_color};">{diff_str}</div>
                </div>
                """, unsafe_allow_html=True)



    # 주문 정보 필터링
    user_orders = orders[orders['user_id'] == selected_user]['order_id']
    user_order_products = order_products[order_products['order_id'].isin(user_orders)]

    # Top 5 구매 상품 집계
    top_purchased = (
        user_order_products['product_id']
        .value_counts()
        .head(5)
        .reset_index()
    )
    top_purchased.columns = ['product_id', 'count']

    # 상품명 병합
    top_purchased = top_purchased.merge(products[['product_id', 'product_name']], on='product_id', how='left')

    # 🎯 실제 구매 Top 5 상품
    st.markdown("### 🛒 실제 구매 Top 5 상품")
    cols = st.columns(5)
    for i, row in enumerate(top_purchased.itertuples(), 1):
        product_name = row.product_name
        count = row.count
        image_url = image_dict.get(product_name)
        short_name = product_name if len(product_name) <= 25 else product_name[:22] + "..."

        with cols[i - 1]:
            if image_url:
                st.image(image_url, width=100)
            else:
                st.markdown("🖼️ (이미지 없음)", unsafe_allow_html=True)
            st.markdown(
                f"<div style='text-align:center; font-size:13px'><b>{short_name}</b><br><span style='font-size:11px;'>구매 {count}회</span></div>",
                unsafe_allow_html=True
            )

    # 구분선
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr style="border: 1px solid #e0e0e0; margin-top: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("### 📊 구매 데이터 요약 시각화")

    # ✅ Top 5 바차트 & 파이차트
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ Top 5 상품 구매 횟수")
        fig_bar = px.bar(
            top_purchased.sort_values(by='count'),
            x='count',
            y='product_name',
            orientation='h',
            text='count',
            labels={'product_name': '상품명', 'count': '구매 수'}
        )
        fig_bar.update_traces(
            marker_color='#7e57c2',
            textposition='outside',
            hovertemplate='%{y}<br>구매 수: %{x}회'
        )
        fig_bar.update_layout(
            title_text=None,
            plot_bgcolor='#f9f9f9',
            paper_bgcolor='#f9f9f9',
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis=dict(categoryorder='total ascending'),
            xaxis_title=None,
            yaxis_title=None
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("#### ✅ 카테고리별 구매 비율")

        merged = user_order_products.merge(products[['product_id', 'department_id']], on='product_id', how='left')
        merged = merged.merge(departments[['department_id', 'department']], on='department_id', how='left')
        dept_counts = merged['department'].value_counts().head(5)

        labels = [
            f"{dept} ({p:.1f}%)" for dept, p in zip(
                dept_counts.index,
                100 * dept_counts.values / dept_counts.values.sum()
            )
        ]

        fig_pie, ax = plt.subplots(figsize=(4.5, 4.5))
        colors = ['#d1c4e9', '#b39ddb', '#9575cd', '#7e57c2', '#5e35b1']
        explode = [0.05] * len(dept_counts)
        wedges, texts, autotexts = ax.pie(
            dept_counts.values,
            labels=labels,
            startangle=140,
            colors=colors,
            explode=explode,
            autopct='%1.1f%%',
            pctdistance=0.8,
            textprops={'fontsize': 10}
        )

        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_color('black')

        ax.set_facecolor('#f9f9f9')
        fig_pie.patch.set_facecolor('#f9f9f9')
        ax.axis('equal')

        st.pyplot(fig_pie)

    st.markdown("---")

    # ✅ LightFM 기반 추천 알고리즘 설명 추가
    st.markdown("""
    <div style='
        background-color: #e8f0fe;
        padding: 18px 20px;
        border-left: 5px solid #1a73e8;
        border-radius: 8px;
        margin-bottom: 16px;
        font-size: 15px;
        line-height: 1.6;
    '>
    <b>📌 추천 방식 안내</b><br><br>
    본 추천은 <b style='color:#1a73e8;'>LightFM</b>이라는 머신러닝 기반의 추천 알고리즘으로 생성되었습니다. <br>
    고객님의 <b>구매 이력</b>과 <b>유사 고객의 행동 패턴</b>을 함께 학습하여, 개인화된 상품을 제안합니다. <br><br>
    <small style='color:#555;'>👉 LightFM은 협업 필터링(Collaborative Filtering)과 콘텐츠 기반 필터링(Content-Based)을 결합하여,<br>
    상품 간 유사성뿐 아니라 사용자 간의 취향도 함께 고려합니다.</small>
    </div>
    """, unsafe_allow_html=True)


    # 🎁 추천 상품 카드
    if st.button("✨ 추천 상품 보기"):
        selected_row = rec_df[rec_df['user_id'] == selected_user]
        if not selected_row.empty:
            recommended_products = selected_row.iloc[0, 1:].tolist()
            purchased_names = top_purchased['product_name'].tolist()
            overlap = set(purchased_names) & set(recommended_products)
            diff = set(recommended_products) - set(purchased_names)
            core_purchased = purchased_names[:3]

            st.markdown(
                f"### 🎁 추천 상품 목록 (User ID: <span style='color:green;'>{selected_user}</span>)",
                unsafe_allow_html=True
            )
            rec_cols = st.columns(5)
            for i, product_name in enumerate(recommended_products):
                image_url = image_dict.get(product_name)
                short_name = product_name if len(product_name) <= 25 else product_name[:22] + "..."

                with rec_cols[i % 5]:
                    if image_url:
                        st.image(image_url, width=100)
                    else:
                        st.markdown("🖼️ (이미지 없음)")
                    st.markdown(
                        f"<div style='text-align:center; font-size:13px'><b>{short_name}</b></div>",
                        unsafe_allow_html=True
                    )

            # 🤖 추천 사유
            st.markdown("### 🤖 추천 사유")

            if overlap:
                st.markdown(
                    f"""
                    <div style='
                        background-color: #f5f5f5;
                        padding: 18px 20px;
                        border-left: 5px solid #7e57c2;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        font-size: 15px;
                        line-height: 1.7;
                    '>
                    <b>🔎 고객 행동 인사이트</b><br><br>
                    이 고객님은 <b style='color:#5e35b1'>{', '.join(core_purchased)}</b> 등을 자주 구매하는 경향이 있습니다.<br>
                    이러한 성향을 가진 고객들은 <b style='color:#00897b'>{', '.join(diff)}</b> 같은 상품도 함께 선택하는 경우가 많아 추천드립니다.<br><br>
                    <span style='color:#666;'>개인의 취향을 고려한 맞춤형 제안으로,<br>보다 만족스러운 쇼핑 경험을 기대할 수 있습니다 😊</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style='
                        background-color: #f5f5f5;
                        padding: 18px 20px;
                        border-left: 5px solid #7e57c2;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        font-size: 15px;
                        line-height: 1.7;
                    '>
                    <b>🔎 고객 행동 인사이트</b><br><br>
                    이 고객님은 주로 <b style='color:#5e35b1'>{', '.join(core_purchased)}</b> 제품을 구매하셨습니다.<br>
                    비슷한 소비 패턴을 가진 다른 고객들은 <b style='color:#00897b'>{', '.join(diff)}</b>도 함께 많이 구매하고 있어 추천드립니다.<br><br>
                    <span style='color:#666;'>나와 유사한 고객의 선택을 참고해보는 건 언제나 좋은 선택이 될 수 있어요 😉</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )




# ────────────────────────────────────────────────────────
# 📌 탭 2: 소개, 스코어링 기준 + 등급 분포 등
# ────────────────────────────────────────────────────────

with tab2:
    st.markdown("## 📊 고객 선정 및 등급 소개")

    # 1. 스코어링 기준 표
    st.markdown("### 📈 고객 스코어링 기준 및 가중치")
    st.markdown("""
    고객의 구매 행동을 네 가지 핵심 지표로 수치화하고,  
    각 항목에 가중치를 부여해 최종 VIP 점수를 산출합니다.
    """)

    with st.container():
        st.table(pd.DataFrame({
            "항목": ["총 주문 수", "총 상품 수", "재구매율", "최신성(recency)"],
            "가중치": ["30%", "20%", "25%", "25%"],
            "설명": [
                "전체 주문 횟수 (높을수록 우수)",
                "구매한 전체 상품 개수",
                "Reordered 상품 비율",
                "최근 주문일 기준 경과일수"
            ]
        }))

    # 1-1. 항목별 해석 - 카드 스타일 블록
    st.markdown("#### 📌 항목별 해석")

    with st.container():
        st.markdown("""
        <div style="background-color:#f9f9f9;padding:15px;border-radius:10px;line-height:1.7">
        🛒 <b>총 주문 수 (30%)</b>  
        반복 구매 여부는 장기 고객 관계를 반영하므로 가장 높은 비중을 부여했습니다.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color:#f9f9f9;padding:15px;border-radius:10px;line-height:1.7">
        📦 <b>총 상품 수 (20%)</b>  
        다양한 상품을 구매한 고객은 니즈 확장성과 교차 판매 가능성이 높습니다.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color:#f9f9f9;padding:15px;border-radius:10px;line-height:1.7">
        🔁 <b>재구매율 (25%)</b>  
        동일 상품 반복 구매는 제품 충성도와 소비 습관의 일관성을 보여줍니다.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color:#f9f9f9;padding:15px;border-radius:10px;line-height:1.7">
        ⏱️ <b>최신성 (25%)</b>  
        최근까지도 활발히 구매한 고객은 리텐션 우선 관리 대상입니다.
        </div>
        """, unsafe_allow_html=True)

    # 2. VIP 등급 기준 - 강조 블럭
    st.markdown("### 🏅 VIP 등급 산정 기준")

    st.markdown("""
    <div style="background-color:#e6f0fa;padding:15px;border-radius:10px;line-height:1.8">
    VIP 점수 기반으로 전체 고객을 다음과 같이 분류합니다:<br><br>
    💎 <b>1.Diamond</b> : 상위 5%<br>
    🥈 <b>2.Platinum</b> : 상위 5~20%<br>
    🥉 <b>3.Gold</b> : 상위 20~50%<br>
    🔘 <b>4.Silver</b> : 하위 50~80%<br>
    ⚪ <b>5.Bronze</b> : 하위 80% 이하
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    등급 구간은 상대적 위치를 기준으로 하며,  
    마케팅 타겟팅과 전환 전략 설계에 활용됩니다.
    """)



# ────────────────────────────────────────────────────────
# 📊 탭 3: 전체 고객 분석 (KPI 요약 + 등급)
# ────────────────────────────────────────────────────────
with tab3:
    # 3. KPI 요약
    st.markdown("### 📌 전체 고객군 요약 KPI")

    # 계산
    total_users = len(vip_df)
    diamond_avg = vip_df[vip_df['vip_grade'] == '1.Diamond']['vip_score'].mean()
    total_avg = vip_df['vip_score'].mean()

    # 3-1. 예쁜 KPI 카드
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="background-color:#f0f4f8;padding:18px;border-radius:12px;text-align:center">
            <div style="font-size:22px;">👥</div>
            <div style="font-size:16px;font-weight:600;margin-top:6px;">전체 고객 수</div>
            <div style="font-size:20px;font-weight:bold;color:#2c3e50;margin-top:4px;">
                {:,}명
            </div>
        </div>
        """.format(total_users), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background-color:#eafaf1;padding:18px;border-radius:12px;text-align:center">
            <div style="font-size:22px;">💎</div>
            <div style="font-size:16px;font-weight:600;margin-top:6px;">1등급 평균 점수</div>
            <div style="font-size:20px;font-weight:bold;color:#2e7d32;margin-top:4px;">
                {:.1f}
            </div>
        </div>
        """.format(diamond_avg), unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background-color:#eef6fb;padding:18px;border-radius:12px;text-align:center">
            <div style="font-size:22px;">📊</div>
            <div style="font-size:16px;font-weight:600;margin-top:6px;">전체 평균 점수</div>
            <div style="font-size:20px;font-weight:bold;color:#1565c0;margin-top:4px;">
                {:.1f}
            </div>
        </div>
        """.format(total_avg), unsafe_allow_html=True)

    # 3-2. 등급별 평균 점수 막대그래프
    # 칸 공백을 주는 용도로는 st.markdown("")(빈 줄)도 쓸 수 있지만,
    # 더 명확하게 여백을 주고 싶다면 st.write("") 또는 st.markdown("&nbsp;", unsafe_allow_html=True)도 사용합니다.
    # 시각적으로 더 큰 여백이 필요하면 아래처럼 스타일을 줄 수도 있습니다.
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr style="border: 1px solid #e0e0e0; margin-top: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("### 📊 등급별 평균 VIP 점수")

    grade_order = ['1.Diamond', '2.Platinum', '3.Gold', '4.Silver', '5.Bronze']
    grade_labels = {
        '1.Diamond': '💎 Diamond',
        '2.Platinum': '🥈 Platinum',
        '3.Gold': '🥉 Gold',
        '4.Silver': '🔘 Silver',
        '5.Bronze': '⚪ Bronze'
    }
    grade_colors = ['#0B6E4F', '#3587A4', '#FFB400', '#C0C0C0', '#CD7F32']

    # 평균 점수 계산
    grade_avg = (
        vip_df.groupby('vip_grade')['vip_score']
        .mean()
        .reindex(grade_order)
        .reset_index()
    )
    grade_avg['vip_grade'] = grade_avg['vip_grade'].map(grade_labels)

    # Plotly bar chart
    fig = px.bar(
        grade_avg,
        x='vip_grade',
        y='vip_score',
        text='vip_score',
        color='vip_grade',
        color_discrete_sequence=grade_colors,
        title='등급별 평균 VIP 점수'
    )
    fig.update_traces(
        texttemplate='%{text:.1f}',
        textposition='auto',
        textfont_size=18  # 폰트 크기 키움
    )
    fig.update_layout(
        xaxis_title="VIP 등급",
        yaxis_title="평균 점수",
        showlegend=False,
        plot_bgcolor="#fafafa",
        font=dict(size=16),  # 전체 폰트 크기 키움
        xaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
        yaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
        title_font_size=20
    )
    st.plotly_chart(fig, use_container_width=True)


    # 📊 3-3 ~ 3-4: 등급별 요약 테이블 + 레이더 차트 병렬 배치
    col1, col2 = st.columns(2)
    # Streamlit의 st.columns([1.0, 2.0])에서 숫자는 "비율"만 의미하고, 두 컬럼 사이의 "간격"은 자동으로 최소한만 들어갑니다.
    # 컬럼 사이에 명시적으로 간격(여백)을 주고 싶다면, 빈 컬럼을 추가하세요.
    # 예시: [1.0, 0.2, 2.0]로 하면 col1 | (여백) | col2 구조가 됩니다.

    col1, spacer, col2 = st.columns([1.0, 0.2, 2.0])

    with col1:
        st.markdown("#### 📋 등급별 고객 수 & 평균 점수 요약")

        grade_summary = (
            vip_df.groupby('vip_grade')
            .agg(
                고객수=('user_id', 'count'),
                평균점수=('vip_score', 'mean')
            )
            .reindex(grade_order)
            .reset_index()
        )

        grade_summary['vip_grade'] = grade_summary['vip_grade'].map(grade_labels)
        total_users = grade_summary['고객수'].sum()

        grade_summary['고객수'] = grade_summary['고객수'].apply(
            lambda x: f"{x:,}명 ({x / total_users * 100:.1f}%)"
        )
        grade_summary['평균점수'] = grade_summary['평균점수'].round(1)

        st.dataframe(grade_summary, use_container_width=True)

    with col2:
        st.markdown("#### 🕸️ 등급별 항목별 스코어 비교 (Radar Chart)")

        radar_data = vip_df.groupby('vip_grade')[
            ['total_orders_score', 'total_products_score', 'reorder_rate_score', 'recency_score']
        ].mean().reindex(grade_order)

        radar_data['label'] = radar_data.index.map({
            '1.Diamond': '💎 Diamond',
            '2.Platinum': '🥈 Platinum',
            '3.Gold': '🥉 Gold',
            '4.Silver': '🔘 Silver',
            '5.Bronze': '⚪ Bronze'
        })

        radar_melted = pd.melt(
            radar_data.reset_index(drop=True),
            id_vars='label',
            var_name='항목',
            value_name='점수'
        )

        radar_melted["항목"] = radar_melted["항목"].map(score_label_map)


        fig_radar = px.line_polar(
            radar_melted,
            r='점수',
            theta='항목',
            color='label',
            line_close=True,
            color_discrete_sequence=grade_colors,
            title='등급별 항목별 평균 점수 (Radar Chart)',
            template='plotly_white'
        )
        fig_radar.update_traces(fill='toself', line=dict(width=2))
        fig_radar.update_layout(legend_title_text="VIP 등급")
        st.plotly_chart(fig_radar, use_container_width=True)


    # ───────────────────────────────────────────
    # 📊 시각화 - VIP 점수 분포 + 상관관계
    # ───────────────────────────────────────────
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr style="border: 1px solid #e0e0e0; margin-top: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("### 📊 고객 점수 및 상관관계 시각화")
    col4, col5 = st.columns(2)

    with col4:
        st.markdown("#### 📈 VIP 점수 분포 (등급별)")
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        sns.histplot(
            data=vip_df,
            x='vip_score',
            hue='vip_grade',
            palette={
                '1.Diamond': '#0B6E4F',
                '2.Platinum': '#3587A4',
                '3.Gold': '#FFB400',
                '4.Silver': '#C0C0C0',
                '5.Bronze': '#CD7F32'
            },
            bins=30,
            kde=True,
            multiple='stack',  # 또는 'layer' (겹침)
            ax=ax2
        )
        ax2.set_title("VIP Score 분포 (등급별)")
        ax2.set_xlabel("VIP Score")
        ax2.set_ylabel("고객 수")
        ax2.legend(title='등급')
        st.pyplot(fig2)


    with col5:
        st.markdown("#### 🔍 항목 간 상관관계")

        score_cols = [
            'total_orders_score', 'total_products_score',
            'reorder_rate_score', 'recency_score'
        ]

        fig3, ax3 = plt.subplots(figsize=(5, 3))
        corr = vip_df[score_cols].corr()

        # ✅ 한글 라벨로 변경
        corr.index = corr.index.map(score_label_map)
        corr.columns = corr.columns.map(score_label_map)

        sns.heatmap(corr, annot=True, cmap='YlGnBu', fmt=".2f", ax=ax3)
        ax3.set_title("VIP 항목 간 상관관계")
        st.pyplot(fig3)


    # ───────────────────────────────────────────
    # 📊 시각화 - 항목별 분포 + 1등급 재구매율 비교
    # ───────────────────────────────────────────
    st.markdown("### 📦 항목별 점수 및 등급별 비교")
    col6, col7 = st.columns(2)

    with col6:
        st.markdown("#### 🎯 항목별 스코어 분포")

        # melt + 한글 라벨 매핑
        df_melted = vip_df[score_cols].melt(var_name="지표", value_name="점수")
        df_melted["지표"] = df_melted["지표"].map(score_label_map)

        # boxplot 시각화
        fig4, ax4 = plt.subplots(figsize=(5, 3))
        sns.boxplot(data=df_melted, x="지표", y="점수", palette="pastel", ax=ax4)
        ax4.set_title("항목별 스코어 분포")
        ax4.set_xlabel("")
        st.pyplot(fig4)


    with col7:
        st.markdown("#### 💎 재구매율: 1등급 vs 전체")
        fig5, ax5 = plt.subplots(figsize=(5, 3))
        sns.kdeplot(vip_df['reorder_rate'], label='전체 고객', linewidth=2, color='gray')
        sns.kdeplot(
            vip_df[vip_df['vip_grade'] == '1.Diamond']['reorder_rate'],
            label='1등급 고객',
            linewidth=2,
            linestyle="--",
            color='blue'
        )
        ax5.set_title("재구매율 분포 비교")
        ax5.set_xlabel("재구매율")
        ax5.legend()
        st.pyplot(fig5)





# ────────────────────────────────────────────────────────
# 🎯 탭 4: 행동분석(1등급 vs 2~3등급
# ────────────────────────────────────────────────────────
with tab4:
    # 등급별 데이터 분리
    diamond_df = vip_df[vip_df['vip_grade'] == '1.Diamond']
    tier23_df = vip_df[vip_df['vip_grade'].isin(['2.Platinum', '3.Gold'])]

    # KPI 계산
    metrics = {
        "1등급 고객 수": [len(diamond_df), len(tier23_df)],
        "평균 VIP 점수": [diamond_df['vip_score'].mean(), tier23_df['vip_score'].mean()],
        "평균 재구매율": [diamond_df['reorder_rate'].mean(), tier23_df['reorder_rate'].mean()],
        "평균 주문 수": [diamond_df['total_orders'].mean(), tier23_df['total_orders'].mean()],
        "평균 상품 수": [diamond_df['total_products'].mean(), tier23_df['total_products'].mean()],
        "평균 장바구니 크기": [
            (diamond_df['total_products'] / diamond_df['total_orders']).mean(),
            (tier23_df['total_products'] / tier23_df['total_orders']).mean()
        ]
    }

    # 카드 스타일
    card_styles = {
        "1등급 고객 수":        ("👤", "#f0f4f8", "#2c3e50"),
        "평균 VIP 점수":        ("📊", "#eafaf1", "#2e7d32"),
        "평균 재구매율":        ("🔁", "#fff3e0", "#ef6c00"),
        "평균 주문 수":         ("📦", "#fce4ec", "#c2185b"),
        "평균 상품 수":         ("🛍️", "#ede7f6", "#5e35b1"),
        "평균 장바구니 크기":   ("🧺", "#e0f7fa", "#00838f"),
    }

    # 항목 → 앵커 ID 매핑
    anchor_map = {
        "평균 주문 수": "order_detail",
        "평균 재구매율": "reorder_detail",
        "평균 상품 수": "product_detail"
    }

    st.markdown('<div id="top_kpi"></div>', unsafe_allow_html=True)
    st.markdown("### 💎 1등급 vs 🥈 2~3등급 핵심 지표 비교")
    st.markdown("<div style='text-align:right; font-size:14px; font-weight:600;'>(계산 : 2~3등급 - 1등급)</div>", unsafe_allow_html=True)

    for label, (v1, v2) in metrics.items():
        col1, col2, col3 = st.columns(3)
        icon, bg, color = card_styles[label]

        def format_value(val, label):
            if '율' in label:
                return f"{val:.1%}"
            elif '평균' in label or '크기' in label:
                return f"{val:.2f}"
            else:
                return f"{int(val):,}"

        def get_diff_display(v1, v2, label):
            diff = v2 - v1
            if '율' in label:
                diff_str = f"{diff:+.1%}"
            elif '평균' in label or '크기' in label:
                diff_str = f"{diff:+.2f}"
            else:
                diff_str = f"{diff:+,.0f}"
            diff_color = "#2e7d32" if diff > 0 else "#d32f2f"
            return diff_str, diff_color

        v1_formatted = format_value(v1, label)
        v2_formatted = format_value(v2, label)
        diff_str, diff_color = get_diff_display(v1, v2, label)

        # 항목 라벨 및 링크
        label_line = f"<span style='font-size:14px; font-weight:600;'>📌 {label}</span>"
        if label in anchor_map:
            label_line += f" <a href='#{anchor_map[label]}' style='font-size:12px; margin-left:8px;'>🔎 상세 분석 보기</a>"
        st.markdown(label_line, unsafe_allow_html=True)

        with col1:
            st.markdown(f"""
            <div style="background-color:{bg};padding:16px;border-radius:12px;text-align:center">
                <div style="font-size:22px;">{icon}</div>
                <div style="font-size:14px;font-weight:600;margin-top:4px;">1등급</div>
                <div style="font-size:18px;font-weight:bold;color:{color};margin-top:4px;">
                    {v1_formatted}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background-color:{bg};padding:16px;border-radius:12px;text-align:center">
                <div style="font-size:22px;">{icon}</div>
                <div style="font-size:14px;font-weight:600;margin-top:4px;">2~3등급</div>
                <div style="font-size:18px;font-weight:bold;color:{color};margin-top:4px;">
                    {v2_formatted}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="background-color:#fafafa;padding:16px;border-radius:12px;text-align:center">
                <div style="font-size:22px;">➖</div>
                <div style="font-size:14px;font-weight:600;margin-top:4px;">차이</div>
                <div style="font-size:18px;font-weight:bold;color:{diff_color};margin-top:4px;">
                    {diff_str}
                </div>
            </div>
            """, unsafe_allow_html=True)



    # 등급별 필터링
    diamond_df = vip_df[vip_df['vip_grade'] == '1.Diamond']
    tier23_df = vip_df[vip_df['vip_grade'].isin(['2.Platinum', '3.Gold'])]

    diamond_users = diamond_df['user_id']
    pg_users = tier23_df['user_id']
    n_diamond = len(diamond_users)
    n_pg = len(pg_users)

    # ✅ 캐시 기반 전처리 함수 사용
    diamond_orders = preprocess_orders(order_products, orders, products, diamond_users)
    pg_orders = preprocess_orders(order_products, orders, products, pg_users)


    # 📦 평균 주문 수 → 공통 인기 상품 분석
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr style="border: 1px solid #e0e0e0; margin-top: 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("## 🔎 상세 분석")
    st.markdown("""
    <div style="background-color:#f9f9f9; border-left: 6px solid #0B6E4F; padding: 16px 18px; border-radius: 10px; margin-bottom: 18px; font-size:17px;">
        <b>📦 분석 개요</b><br>
        고객 등급별 행동을 비교해 <span style="color:#0B6E4F;font-weight:600;">상위 상품군 선호도</span>,<br>
        <span style="color:#3587A4;font-weight:600;">재구매 패턴</span>, <span style="color:#5e35b1;font-weight:600;">구매 상품 다양성</span> 측면에서 차이를 분석합니다.<br><br>
        🔎 아래의 각 항목을 클릭해 등급별 행동 차이와 <strong>1등급 전환 전략</strong>을 확인해보세요.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div id="order_detail"></div>', unsafe_allow_html=True)
    with st.expander("📦 평균 주문 수 상세 분석 (공통 인기 상품 비교)"):
        plot_df = compute_top5_common_products(diamond_orders, pg_orders, n_diamond, n_pg)

        fig1 = px.bar(
            plot_df,
            x='avg_purchase_per_user',
            y='product_name',
            color='grade',
            orientation='h',
            barmode='group',
            title="공통 상품 Top 5 비교 (고객 1인당 평균 구매 수 기준)",
            labels={"avg_purchase_per_user": "고객 1인당 평균 구매 수"}
        )
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'})

        st.plotly_chart(fig1, use_container_width=True)


        # 시각화된 인사이트 해설
        st.markdown("""
        <div style='padding: 15px; background-color: #fef8e7; border-left: 6px solid #ff9800; border-radius: 5px;'>
        <h4>🔍 <strong>인사이트 요약</strong></h4>
        <ul>
            <li>1등급 고객은 특정 상품에 대한 <strong>구매 집중도</strong>가 매우 높음</li>
            <li>2~3등급 고객도 동일한 상품을 구매하지만, <strong>1인당 평균 구매량이 낮음</strong></li>
        </ul>

        <h4>🎯 <strong>전환 전략 제안</strong></h4>
        <ul>
            <li>🛍️ <strong>1등급의 인기 상품을 중심으로 세트 구성 & 할인 프로모션 기획</strong></li>
            <li>🔁 <strong>공통 상품 Top 5에 대해 “다시 구매” 캠페인</strong> (리마인드 알림)</li>
            <li>📢 <strong>상품별 구매빈도 기반 추천 모델로 개인화 마케팅 적용</strong></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:right; margin-top: 12px;'>
        <a href="#top_kpi" style='font-size:13px; color:#1565c0;'>🔝 돌아가기</a>
    </div>
    """, unsafe_allow_html=True)




    # 🔁 재구매율 → 재구매율 비율 + top5 상품
    st.markdown('<div id="reorder_detail"></div>', unsafe_allow_html=True)
    with st.expander("🔁 평균 재구매율 상세 분석 (재구매 행동 분석)"):
        reorder_df = compute_reorder_ratio(diamond_orders, pg_orders)

        fig2 = px.bar(
            reorder_df,
            x='reordered_status',
            y='ratio',
            color='grade',
            barmode='group',
            title='재구매 vs 최초구매 비율 비교',
            labels={'ratio': '비율', 'reordered_status': '구매 유형'}
        )
        fig2.update_layout(yaxis_tickformat='.0%')
        st.plotly_chart(fig2, use_container_width=True)


        # 재구매 상품 Top5 비교
        reorder_melted = compute_top5_reorder_products(diamond_orders, pg_orders)

        fig3 = px.bar(
            reorder_melted,
            x='reorder_count',
            y='product_name',
            color='grade',
            orientation='h',
            barmode='group',
            title="재구매 Top 5 상품 비교 (횟수 기준)"
        )
        st.plotly_chart(fig3, use_container_width=True)


        # 🔍 인사이트 카드 (HTML + Markdown)
        st.markdown("""
        <div style='padding: 15px; background-color: #fef8e7; border-left: 6px solid #ff9800; border-radius: 5px;'>
        <h4>🔍 <strong>인사이트 요약</strong></h4>
        <ul>
            <li>1등급 고객은 전체 구매 중 <strong>재구매 비중이 77%</strong>로 매우 높음</li>
            <li>반면 2~3등급 고객은 <strong>최초구매 비중이 높고 재구매 전환율이 낮음</strong></li>
            <li>재구매 Top 5 상품은 양 고객군 모두 유사하지만, <strong>2~3등급 고객의 반복 구매가 장기적 충성으로 연결되지 않음</strong></li>
        </ul>

        <h4>🎯 <strong>전환 전략 제안</strong></h4>
        <ul>
            <li>🧾 <strong>첫 구매 후 7일 내 재구매 시 할인 쿠폰 지급</strong></li>
            <li>🔔 <strong>Push 알림 / 이메일 리마인드 마케팅</strong> (예: 'Banana 다시 필요하신가요?')</li>
            <li>🧺 <strong>재구매 상위 품목 기반 번들 패키지 or 정기배송 상품 구성</strong></li>
            <li>🏷️ <strong>3회 구매 시 1회 무료 이벤트</strong> 등 충성도 유도 인센티브</li>
            <li>📊 <strong>1등급 고객의 구매 시간·패턴 기반 맞춤 프로모션 타겟팅</strong></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:right; margin-top: 12px;'>
        <a href="#top_kpi" style='font-size:13px; color:#1565c0;'>🔝 돌아가기</a>
    </div>
    """, unsafe_allow_html=True)




    st.markdown('<div id="product_detail"></div>', unsafe_allow_html=True)
    with st.expander("🛍 평균 상품 수 상세 분석 (고객별 상품 다양성 분포)"):

        # 스타일 설정
        sns.set(style="whitegrid")
        plt.rcParams["font.family"] = "AppleGothic"  # Mac용 (Windows는 'Malgun Gothic')
        plt.rcParams['axes.unicode_minus'] = False

        # 좌우 레이아웃 분할
        col1, col2 = st.columns([1.2, 1.0])

        with col1:
            fig, ax = plt.subplots(figsize=(10, 5))

            # KDE Plot
            sns.kdeplot(
                data=diamond_df,
                x='total_products',
                fill=True,
                label='1등급',
                color="#1565c0",
                linewidth=2
            )
            sns.kdeplot(
                data=tier23_df,
                x='total_products',
                fill=True,
                label='2~3등급',
                color="#90caf9",
                linewidth=2
            )

            # 제목/축/범례 스타일
            ax.set_title("📈 고객별 총 구매 상품 수 분포", fontsize=14, weight='bold')
            ax.set_xlabel("총 구매 상품 수", fontsize=12)
            ax.set_ylabel("밀도", fontsize=12)
            ax.legend(title="고객 등급", title_fontsize=12, fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.5)

            st.pyplot(fig)

        with col2:
            # 🔍 인사이트 카드
            st.markdown("""
            <div style='padding: 15px; background-color: #fef8e7; border-left: 6px solid #ff9800; border-radius: 5px;'>
            <h4>🔍 <strong>인사이트 요약</strong></h4>
            <ul>
                <li>1등급 고객은 <strong>더 다양한 상품군을 구매</strong>하며 상품 탐색 범위가 넓음</li>
                <li>반면 2~3등급 고객은 <strong>구매 상품 수가 적고 반복성이 낮음</strong></li>
                <li>다양한 상품을 구매한 고객일수록 <strong>충성도와 LTV가 높을 가능성</strong>이 큼</li>
            </ul>

            <h4>🎯 <strong>전환 전략 제안</strong></h4>
            <ul>
                <li>🧃 <strong>5개 이상 다른 상품 구매 시 할인 쿠폰 제공</strong> (상품 다양성 미션)</li>
                <li>🎁 <strong>다양성 높은 1등급 고객 기반 번들 추천</strong> (타 고객의 인기 조합)</li>
                <li>📦 <strong>신규 카테고리 체험 쿠폰</strong> (예: 유제품, 음료군 첫 구매 할인)</li>
                <li>📮 <strong>개인화 추천 기반 큐레이션</strong>으로 고객 취향 확장 유도</li>
                <li>📊 <strong>"다양한 상품 추천" 섹션</strong>을 통해 탐색 유도 및 장바구니 유입 확대</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:right; margin-top: 12px;'>
        <a href="#top_kpi" style='font-size:13px; color:#1565c0;'>🔝 돌아가기</a>
    </div>
    """, unsafe_allow_html=True)





