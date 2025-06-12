import streamlit as st
import traceback
import os
import gdown
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import plotly.express as px
import pickle

# ─────────────────────────────────────────────────────
# 1) 페이지 설정 & 한글 폰트
# ─────────────────────────────────────────────────────
mpl.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'AppleGothic'
st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")

# ─────────────────────────────────────────────────────
# 2) Drive 파일 ID 매핑 (요약본 + 모델)
# ─────────────────────────────────────────────────────
FILE_IDS = {
    "user_metrics_top3.csv":        "15burF431bA9iR3FanRqYUx7w4-fbJ0Je",
    "top10_products_diamond.csv":   "1Fo5ow7APMBlaiV-CI-Qc7L4HW2s6sg2e",
    "diamond_2_3_lightfm_model.pkl": "1uOwXXvKPZQFcO-KSIdHgWDD58iqSIrBK"
}
DATA_DIR = "data_InstaCart"
os.makedirs(DATA_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────
# 3) 요약파일 & 모델 다운로드
# ─────────────────────────────────────────────────────
for fname, fid in FILE_IDS.items():
    out_path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(out_path):
        st.info(f"📥 {fname} 다운로드 중...")
        url = f"https://drive.google.com/uc?id={fid}"
        gdown.download(url, out_path, quiet=False, fuzzy=True)
        st.success(f"✅ {fname} 다운로드 완료")

# ─────────────────────────────────────────────────────
# 4) 데이터 & 모델 로드
# ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    metrics = pd.read_csv(f"{DATA_DIR}/user_metrics_top3.csv")
    top_prods = pd.read_csv(f"{DATA_DIR}/top10_products_diamond.csv")
    return metrics, top_prods

@st.cache_resource(show_spinner=False)
def load_model():
    with open(f"{DATA_DIR}/diamond_2_3_lightfm_model.pkl", 'rb') as f:
        model, user_id_map, product_id_map = pickle.load(f)
    return model, user_id_map, product_id_map

metrics_df, top_prods_df = load_data()
model, user_id_map, product_id_map = load_model()

# ─────────────────────────────────────────────────────
# 5) 추천 함수 준비
# ─────────────────────────────────────────────────────
inv_product_map = {v:k for k,v in product_id_map.items()}

@st.cache_data(show_spinner=False)
def cached_recommend_products(user_id, N=5):
    if user_id not in user_id_map:
        return []
    user_x = user_id_map[user_id]
    scores = model.predict(user_x, np.arange(len(product_id_map)))
    top_idxs = np.argsort(-scores)[:N]
    return [inv_product_map[i] for i in top_idxs]

# ─────────────────────────────────────────────────────
# 6) 탭 구성
# ─────────────────────────────────────────────────────
tabs = st.tabs([
    "🏠 개요",
    "📊 등급별 고객 분석",
    "🔎 1등급 고객 집중 분석",
    "💡 2~3등급 전환 전략",
    "🎯 맞춤형 추천 시스템"
])
tab_home, tab_dist, tab_diamond, tab_strategy, tab_reco = tabs

# ─── 홈 탭 ────────────────────────────────────────────
with tab_home:
    st.header("🚀 InstaCart VIP 대시보드")
    st.markdown("""
    요약된 VIP 상위(1~3등급) 고객의 주요 지표를 기반으로  
    1등급 집중 분석, 전환 전략, 추천 시스템을 제공합니다.
    """)
    total_users = len(metrics_df)
    pct_diamond = (metrics_df['vip_grade']=='1.Diamond').mean()*100
    avg_score = metrics_df['vip_score'].mean() if 'vip_score' in metrics_df else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("대상 고객 수", f"{total_users:,}명")
    c2.metric("1등급 비율", f"{pct_diamond:.1f}%")
    if not np.isnan(avg_score):
        c3.metric("평균 VIP Score", f"{avg_score:.2f}")

# ─── 등급별 분포 ───────────────────────────────────────
with tab_dist:
    st.header("📊 등급별 주요 지표 분포")
    # 박스플롯: total_orders, total_products, reorder_rate 등
    metrics = ['total_orders','total_products','reorder_rate','avg_cart_size','recency','unique_product_count']
    fig, axes = plt.subplots(2,3,figsize=(18,8))
    for i, m in enumerate(metrics):
        ax = axes[i//3, i%3]
        sns.boxplot(x='vip_grade', y=m, data=metrics_df, palette='Set2', ax=ax)
        ax.set_title(m+' 분포')
    fig.tight_layout()
    st.pyplot(fig)

# ─── 1등급 집중 분석 ────────────────────────────────────
with tab_diamond:
    st.header("🔎 1등급 고객 집중 분석")
    # Top10 상품
    st.subheader("🛒 Top 10 구매 상품")
    fig1 = px.bar(
        top_prods_df,
        x='count', y='product_name',
        orientation='h',
        labels={'count':'구매 횟수','product_name':'상품명'},
        title='1등급 고객 TOP 10 상품'
    )
    st.plotly_chart(fig1, use_container_width=True)

    # 재구매 주기 분포
    st.subheader("📈 평균 재구매 주기 분포")
    d = metrics_df.loc[metrics_df['vip_grade']=='1.Diamond','avg_reorder_interval']
    fig2 = px.histogram(d, nbins=30, labels={'value':'재구매 주기(일)'}, title="1등급 평균 재구매 주기")
    st.plotly_chart(fig2, use_container_width=True)

# ─── 전환 전략 ─────────────────────────────────────────
with tab_strategy:
    st.header("💡 2~3등급 → 1등급 전환 전략")
    strategies = [
        ("상품 다양성 확대", 'unique_product_count'),
        ("재방문 유도", 'reorder_rate'),
        ("휴면 방지", 'recency'),
        ("장바구니 크기 증가", 'avg_cart_size'),
    ]
    for title, metric in strategies:
        with st.expander(f"📌 {title}"):
            dfm = metrics_df.groupby('vip_grade')[metric].mean().reset_index()
            fig = px.bar(
                dfm, x=metric, y='vip_grade', orientation='h',
                labels={metric:title,'vip_grade':'등급'},
                title=f"{title} 비교"
            )
            st.plotly_chart(fig, use_container_width=True)

# ─── 추천 시스템 ───────────────────────────────────────
with tab_reco:
    st.header("🎯 맞춤형 추천 시스템")
    grade_opt = st.selectbox(
        "고객 등급 선택",
        ["1등급 (Diamond)", "2~3등급 (Platinum+Gold)"]
    )
    sel = ['1.Diamond'] if grade_opt.startswith('1') else ['2.Platinum','3.Gold']
    candidates = metrics_df[metrics_df['vip_grade'].isin(sel)]['user_id'].tolist()
    uid = st.selectbox("고객 선택", candidates)

    # 고객 지표
    info = metrics_df[metrics_df['user_id']==uid].iloc[0]
    st.subheader("📋 고객 지표")
    st.table(info[['total_orders','total_products','reorder_rate','avg_cart_size','recency']])

    # 추천
    if st.button("추천 받기"):
        recs = cached_recommend_products(uid)
        if recs:
            st.subheader("🛍️ 추천 상품")
            for pid in recs:
                st.write(f"- {pid}")
        else:
            st.info("추천할 상품이 없습니다.")

# ─────────────────────────────────────────────────────
# 예외 처리
# ─────────────────────────────────────────────────────
except Exception as e:
    st.error("⚠️ 앱 실행 중 예외가 발생했습니다!")
    st.error(f"{e}")
    st.text(traceback.format_exc())
    st.stop()
