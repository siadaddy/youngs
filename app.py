import streamlit as st
import traceback
import os
import gdown
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl
import plotly.express as px
import pickle

try:


    # Streamlit 페이지 설정
    st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")

    # 1) 구글 드라이브 파일 ID 매핑
    FILE_IDS = {
        "vip_summary_v2.csv":           "1PlOEkoWZjfkbEB7pIoOveIoRPCBHY26_",
        "products.csv":                 "1w0FOTvUsW-2yfPnCqqWsbQUtOhQmXWN3",
        "orders.csv":                   "18q3WSsBvPMQLRyYCy868AfYY795P4Raw",
        "order_products__prior.csv":    "1p87GV2QV9D99X2TtKM5J4kbs6phtfeNb",
        "diamond_2_3_lightfm_model.pkl": "1uOwXXvKPZQFcO-KSIdHgWDD58iqSIrBK"
    }
    DATA_DIR = "data_InstaCart"
    os.makedirs(DATA_DIR, exist_ok=True)

    # 2) 개별 파일 다운로드
    for fname, fid in FILE_IDS.items():
        out_path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(out_path):
            st.info(f"📥 {fname} 다운로드 중...")
            url = f"https://drive.google.com/uc?id={fid}"
            gdown.download(url, out_path, quiet=False)
            st.success(f"✅ {fname} 다운로드 완료")

    # 3) 데이터 및 모델 로드 함수 (샘플 로드 적용)
    @st.cache_data(show_spinner=False)
    def load_data():
        vip_df = pd.read_csv(f"{DATA_DIR}/vip_summary_v2.csv")
        products = pd.read_csv(f"{DATA_DIR}/products.csv")
        orders = pd.read_csv(
            f"{DATA_DIR}/orders.csv",
            nrows=sample_rows,
            usecols=[
                'order_id','user_id','order_number',
                'days_since_prior_order','order_dow','order_hour_of_day'
            ]
        )
        order_products = pd.read_csv(
            f"{DATA_DIR}/order_products__prior.csv",
            nrows=sample_rows,
            usecols=['order_id','product_id']
        )
        return vip_df, products, orders, order_products

    # ★ LightFM 모델 로딩 주석 처리 ★
    # @st.cache_resource(show_spinner=False)
    # def load_model():
    #     with open(f"{DATA_DIR}/diamond_2_3_lightfm_model.pkl", 'rb') as f:
    #         model, user_id_map, product_id_map = pickle.load(f)
    #     return model, user_id_map, product_id_map

    vip_df, products, orders, order_products = load_data()
    # model, user_id_map, product_id_map = load_model()

    # 4) VIP 등급 분류
    bins = [-0.1, 60, 70, 80, 90, 100]
    labels = ['5.Bronze','4.Silver','3.Gold','2.Platinum','1.Diamond']
    vip_df['vip_grade'] = pd.cut(vip_df['vip_score'], bins=bins, labels=labels)

    # ★ 추천 함수 주석 처리 ★
    # inv_user_map = {v:k for k,v in user_id_map.items()}
    # inv_product_map = {v:k for k,v in product_id_map.items()}
    #
    # @st.cache_data(show_spinner=False)
    # def cached_recommend_products(user_id, N=5):
    #     if user_id not in user_id_map:
    #         return []
    #     user_x = user_id_map[user_id]
    #     scores = model.predict(user_x, np.arange(len(product_id_map)))
    #     top_items = np.argsort(-scores)[:N]
    #     return [inv_product_map[i] for i in top_items]

    # 5) 전략 탭용 데이터 준비
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
        compare_df = pd.concat([g1,g23])

        du = vip[vip['vip_grade']=='1.Diamond']['user_id']
        dorders = orders[orders['user_id'].isin(du)]\
                       .sort_values(['user_id','order_number'])
        dorders['days_since_prior_order'] = dorders['days_since_prior_order'].fillna(0)
        avg_int = dorders.groupby('user_id')['days_since_prior_order']\
                         .mean().reset_index()\
                         .rename(columns={'days_since_prior_order':'avg_reorder_interval'})
        return compare_df, avg_int

    compare_df, avg_interval_df = prepare_strategy_data(
        vip_df, orders, order_products
    )

    # 6) 탭 구성 및 시각화
    tabs = st.tabs([
        "🏠 개요","📊 등급별 고객 분석","🔎 1등급 고객 집중 분석",
        "💡 2~3등급 전환 전략","🎯 맞춤형 추천 시스템"
    ])
    tab_home, tab_dist, tab_diamond, tab_strategy, tab_reco = tabs

    # ── 홈 탭 ─────────────────────────
    with tab_home:
        st.header("🚀 InstaCart VIP 고객 분석 개요")
        grade_counts = vip_df['vip_grade'].value_counts(normalize=True).reindex(labels).fillna(0)
        grade_percents = (grade_counts*100).round(1)
        cols = st.columns(5)
        titles = ["1등급 (Diamond)","2등급 (Platinum)","3등급 (Gold)","4등급 (Silver)","5등급 (Bronze)"]
        for col, title, lab in zip(cols, titles, labels):
            col.metric(title, f"{grade_percents[lab]}%")
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("전체 고객 수", f"{vip_df.shape[0]:,}명")
        c2.metric("1등급 고객 비율", f"{grade_percents['1.Diamond']}%")
        c3.metric("평균 VIP Score", f"{vip_df['vip_score'].mean():.2f}")

    # ── 등급별 분포 탭 ─────────────────────────
    with tab_dist:
        st.header("📊 고객 등급 분포")
        counts = vip_df['vip_grade'].value_counts().reindex(labels)
        fig = px.bar(x=counts.index, y=counts.values, color=counts.index,
                     color_discrete_sequence=px.colors.sequential.Blues_r,
                     labels={'x':'VIP 등급','y':'고객 수'},
                     title='고객 등급 분포')
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("🔍 등급별 행동 비교"):
            st.markdown("1등급 vs 2~3등급 주요 행동 지표 비교")
            metrics = ['total_orders','total_products','reorder_rate','avg_cart_size','recency','unique_product_count']
            fig2, axes = plt.subplots(2,3,figsize=(18,8))
            for i, m in enumerate(metrics):
                ax = axes[i//3, i%3]
                sns.boxplot(x='group', y=m, data=compare_df, palette='Set2', ax=ax)
                ax.set_title(f"{m} 비교")
            fig2.delaxes(axes[1][2])
            st.pyplot(fig2)
            st.markdown("#### 평균값")
            st.dataframe(compare_df.groupby('group')[metrics].mean().round(2))

    # ── 1등급 집중 분석 탭 ─────────────────────────
    with tab_diamond:
        st.header("🔎 1등급 고객 집중 분석")
        op = order_products.merge(
            orders[['order_id','user_id','order_number','order_dow','order_hour_of_day']],
            on='order_id', how='left'
        ).merge(products[['product_id','product_name']], on='product_id', how='left')
        with st.expander("🛒 상위 구매 상품"):
            tp = op[op['user_id'].isin(vip_df[vip_df['vip_grade']=='1.Diamond']['user_id'])]
            tp_counts = tp['product_name'].value_counts().head(10)
            fig3, ax3 = plt.subplots()
            sns.barplot(x=tp_counts.values, y=tp_counts.index, palette='viridis', ax=ax3)
            ax3.set_title("TOP 10 상품")
            st.pyplot(fig3)
        with st.expander("📆 요일·시간대"):
            c1, c2 = st.columns(2)
            with c1:
                fig4, ax4 = plt.subplots()
                sns.countplot(x='order_dow', data=op, palette='Blues', ax=ax4)
                ax4.set_title("요일별 주문")
                st.pyplot(fig4)
            with c2:
                fig5, ax5 = plt.subplots()
                sns.countplot(x='order_hour_of_day', data=op, palette='Greens', ax=ax5)
                ax5.set_title("시간대별 주문")
                st.pyplot(fig5)
        with st.expander("📈 재구매 주기"):
            fig6, ax6 = plt.subplots(figsize=(10,5))
            sns.histplot(avg_interval_df['avg_reorder_interval'], bins=30, kde=True, ax=ax6)
            ax6.set_title("평균 재구매 주기 분포")
            st.pyplot(fig6)
            st.markdown(f"**평균:** {avg_interval_df['avg_reorder_interval'].mean():.2f}일")

    # ── 전환 전략 탭 ─────────────────────────
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
                dfm = compare_df.groupby('group')[metric].mean().reset_index()
                fig, ax = plt.subplots()
                sns.barplot(x=metric, y='group', data=dfm, ax=ax)
                ax.set_title(f"{title} 비교")
                st.pyplot(fig)

    # ── 추천 시스템 탭 ─────────────────────────
    with tab_reco:
        st.header("🎯 추천 시스템 (준비 중)")
        grade_opt = st.selectbox("고객 등급 선택", ["1등급 (Diamond)", "2~3등급 (Platinum+Gold)"])
        sel = ['1.Diamond'] if grade_opt.startswith('1') else ['2.Platinum','3.Gold']
        candidates = vip_df[vip_df['vip_grade'].isin(sel)]['user_id'].tolist()
        uid = st.selectbox("고객 선택", candidates)
        user_info = vip_df[vip_df['user_id']==uid].iloc[0]
        st.table({
            "항목": ["총 주문 수","총 구매 상품 수","재구매율","평균 장바구니 크기","최근성"],
            "값": [
                int(user_info['total_orders']),
                int(user_info['total_products']),
                round(user_info['reorder_rate'],3),
                round(user_info['avg_cart_size'],2),
                round(user_info['recency'],1)
            ]
        })
        if st.button("추천 받기"):
            st.info("현재 추천 기능은 준비 중입니다.")

    st.success("✅ 대시보드 로드 완료")

except Exception as e:
    st.error("⚠️ 앱 실행 중 예외가 발생했습니다!")
    st.error(f"Error: {e}")
    st.text(traceback.format_exc())
    st.stop()
