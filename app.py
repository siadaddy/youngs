import streamlit as st
import os
import duckdb
import gdown
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import pickle
import traceback

# Mac에서 한글 깨짐 방지 (필요시 제거)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── 1) Streamlit 페이지 설정 ─────────────────────────
st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")
DATA_DIR = Path("data_InstaCart")
os.makedirs(DATA_DIR, exist_ok=True)

# ── 2) DuckDB 파일 & 모델 다운로드 ─────────────────────────
FILE_IDS = {
    "instacart.duckdb":            "1BY8nUq5OfyrDnxyZRiuSACf3TDbrdx7m",
    "diamond_2_3_lightfm_model.pkl":"1uOwXXvKPZQFcO-KSIdHgWDD58iqSIrBK"
}
for fname, fid in FILE_IDS.items():
    out_path = DATA_DIR / fname
    if not out_path.exists():
        st.info(f"📥 {fname} 다운로드 중…")
        url = f"https://drive.google.com/uc?id={fid}"
        gdown.download(url, str(out_path), quiet=False)
        st.success(f"✅ {fname} 다운로드 완료")

# ── 3) DuckDB 커넥션 생성 ─────────────────────────
@st.cache_resource(show_spinner=False)
def get_duckdb_conn(db_path: str = str(DATA_DIR / "instacart.duckdb")):
    return duckdb.connect(db_path)

con = get_duckdb_conn()

# ── 4) 데이터 로드 (DuckDB 쿼리) ─────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    vip_df = con.execute("SELECT * FROM vip_summary_v2").df()
    products = con.execute("SELECT * FROM products").df()
    orders = con.execute("""
        SELECT order_id, user_id, order_number,
               days_since_prior_order, order_dow, order_hour_of_day
        FROM orders
    """).df()
    order_products = con.execute("""
        SELECT order_id, product_id
        FROM order_products__prior
    """).df()
    return vip_df, products, orders, order_products

vip_df, products, orders, order_products = load_data()

# ── 5) 모델 로드 ─────────────────────────
@st.cache_resource(show_spinner=False)
def load_model():
    pkl_path = DATA_DIR / "diamond_2_3_lightfm_model.pkl"
    with open(pkl_path, 'rb') as f:
        return pickle.load(f)

model, user_id_map, product_id_map = load_model()

# ── 6) VIP 등급 분류 및 맵 생성 ─────────────────────────
bins   = [-0.1, 60, 70, 80, 90, 100]
labels = ['5.Bronze','4.Silver','3.Gold','2.Platinum','1.Diamond']
vip_df['vip_grade'] = pd.cut(vip_df['vip_score'], bins=bins, labels=labels)

inv_user_map = {v: k for k, v in user_id_map.items()}
inv_product_map = {v: k for k, v in product_id_map.items()}

@st.cache_data(show_spinner=False)
def cached_recommend_products(user_id, N=5):
    if user_id not in user_id_map:
        return []
    user_x = user_id_map[user_id]
    scores = model.predict(user_x, np.arange(len(product_id_map)))
    top_idxs = np.argsort(-scores)[:N]
    return [inv_product_map[i] for i in top_idxs]

# ── 7) 전략 탭용 데이터 준비 ─────────────────────────
@st.cache_data(show_spinner=False)
def prepare_strategy_data(vip_df, orders, order_products):
    op_u = order_products.merge(
        orders[['order_id','user_id']], on='order_id', how='left'
    )
    diversity = op_u.groupby('user_id')['product_id']\
                    .nunique().rename('unique_product_count')
    vip = vip_df.set_index('user_id').join(diversity).reset_index()
    g1 = vip[vip['vip_grade']=='1.Diamond'].copy(); g1['group']='1등급'
    g23 = vip[vip['vip_grade'].isin(['2.Platinum','3.Gold'])].copy(); g23['group']='2~3등급'
    compare_df = pd.concat([g1, g23])

    du = vip[vip['vip_grade']=='1.Diamond']['user_id']
    dorders = orders[orders['user_id'].isin(du)].copy()
    dorders['days_since_prior_order'].fillna(0, inplace=True)
    avg_int = dorders.groupby('user_id')['days_since_prior_order']\
                     .mean().reset_index().rename(
                         columns={'days_since_prior_order':'avg_reorder_interval'}
                     )
    return compare_df, avg_int

compare_df, avg_interval_df = prepare_strategy_data(
    vip_df, orders, order_products
)

# ── 8) 탭 구성 및 시각화 ─────────────────────────
tabs = st.tabs([
    "🏠 개요","📊 등급별 분석","🔎 1등급 집중 분석",
    "💡 전환 전략","🎯 추천 시스템"
])
tab_home, tab_dist, tab_diamond, tab_strategy, tab_reco = tabs

with tab_home:
    st.header("🚀 InstaCart VIP 고객 분석 개요")
    grade_perc = (vip_df['vip_grade'].value_counts(normalize=True)
                  .reindex(labels).fillna(0)*100).round(1)
    cols = st.columns(5)
    titles = ["1.Diamond","2.Platinum","3.Gold","4.Silver","5.Bronze"]
    for col, title, lab in zip(cols, titles, labels):
        col.metric(f"{title}", f"{grade_perc[lab]}%")
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("전체 고객 수", f"{vip_df.shape[0]:,}명")
    c2.metric("1등급 비율", f"{grade_perc['1.Diamond']}%")
    c3.metric("평균 VIP Score", f"{vip_df['vip_score'].mean():.2f}")

with tab_dist:
    st.header("📊 고객 등급 분포")
    counts = vip_df['vip_grade'].value_counts().reindex(labels).fillna(0)
    fig = px.bar(
        x=counts.index, y=counts.values, color=counts.index,
        labels={'x':'VIP 등급','y':'고객 수'},
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 행동 지표 비교"):
        metrics = ['total_orders','total_products','reorder_rate',
                   'avg_cart_size','recency','unique_product_count']
        fig2, axes = plt.subplots(2,3,figsize=(18,8))
        for i, m in enumerate(metrics):
            ax = axes[i//3, i%3]
            sns.boxplot(x='group', y=m, data=compare_df, palette='Set2', ax=ax)
            ax.set_title(m)
        fig2.delaxes(axes[1][2])
        st.pyplot(fig2)
        st.dataframe(compare_df.groupby('group')[metrics].mean().round(2))

with tab_diamond:
    st.header("🔎 1등급 고객 집중 분석")
    top_u = vip_df[vip_df['vip_grade']=='1.Diamond']['user_id']
    op = order_products.merge(
        orders[['order_id','user_id','order_dow','order_hour_of_day']],
        on='order_id', how='left'
    ).merge(products[['product_id','product_name']], on='product_id', how='left')
    tp = op[op['user_id'].isin(top_u)]
    with st.expander("🛒 TOP 상품"):
        tp_counts = tp['product_name'].value_counts().head(10)
        fig3, ax3 = plt.subplots()
        sns.barplot(x=tp_counts.values, y=tp_counts.index, ax=ax3)
        st.pyplot(fig3)
    with st.expander("📈 재구매 주기"):
        fig6, ax6 = plt.subplots(figsize=(10,5))
        sns.histplot(avg_interval_df['avg_reorder_interval'], bins=30, kde=True, ax=ax6)
        st.pyplot(fig6)
        st.markdown(f"**평균 재구매 주기:** {avg_interval_df['avg_reorder_interval'].mean():.2f}일")

with tab_strategy:
    st.header("💡 2~3등급 → 1등급 전환 전략")
    strategies = [
        ("상품 다양성", 'unique_product_count'),
        ("재구매율", 'reorder_rate'),
        ("최근성", 'recency'),
        ("장바구니 크기", 'avg_cart_size'),
    ]
    for title, metric in strategies:
        with st.expander(title):
            dfm = compare_df.groupby('group')[metric].mean().reset_index()
            fig, ax = plt.subplots()
            sns.barplot(x=metric, y='group', data=dfm, ax=ax)
            st.pyplot(fig)

with tab_reco:
    st.header("🎯 맞춤형 추천 시스템")
    grade_opt = st.selectbox("등급 선택", ["1.Diamond","2~3등급"])
    sel = ['1.Diamond'] if grade_opt=="1.Diamond" else ['2.Platinum','3.Gold']
    users = vip_df[vip_df['vip_grade'].isin(sel)]['user_id'].tolist()
    uid = st.selectbox("고객 선택", users)
    st.table(pd.DataFrame({
        "항목":["총 주문","상품 수","재구매율","장바구니 크기","최근성"],
        "값":[
            int(vip_df.loc[vip_df.user_id==uid,'total_orders']),
            int(vip_df.loc[vip_df.user_id==uid,'total_products']),
            round(vip_df.loc[vip_df.user_id==uid,'reorder_rate'].values[0],3),
            round(vip_df.loc[vip_df.user_id==uid,'avg_cart_size'].values[0],2),
            round(vip_df.loc[vip_df.user_id==uid,'recency'].values[0],1),
        ]
    }))
    if st.button("추천 받기"):
        recs = cached_recommend_products(uid, N=5)
        if recs:
            st.write("추천 상품:")
            for pid in recs:
                st.write(f"- {products.loc[products.product_id==pid,'product_name'].values[0]}")
        else:
            st.write("추천 불가")

st.success("✅ DuckDB 기반 대시보드 로드 완료")
