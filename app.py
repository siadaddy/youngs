import streamlit as st
import traceback

# 전체 예외 잡아서 웹에 띄우기
try:
    import os
    import gdown
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    import matplotlib as mpl
    import plotly.express as px
    import pickle

    # 한글 깨짐 방지
    plt.rcParams['font.family'] = 'AppleGothic'
    mpl.rcParams['axes.unicode_minus'] = False

    # 페이지 설정
    st.set_page_config(page_title="InstaCart VIP 분석", layout="wide")

    # 구글 드라이브 파일 ID 매핑
    # (공유 폴더 안의 각 파일 ID를 직접 적어 주세요)
    FILE_IDS = {
        "vip_summary_v2.csv": "1PlOEkoWZjfkbEB7pIoOveIoRPCBHY26_",
        "products.csv":        "1w0FOTvUsW-2yfPnCqqWsbQUtOhQmXWN3",
        "orders.csv":          "h18q3WSsBvPMQLRyYCy868AfYY795P4Raw",
        "order_products__prior.csv": "1p87GV2QV9D99X2TtKM5J4kbs6phtfeNb",
        "diamond_2_3_lightfm_model.pkl": "1uOwXXvKPZQFcO-KSIdHgWDD58iqSIrBK"
    }

    DATA_DIR = "data_InstaCart"
    os.makedirs(DATA_DIR, exist_ok=True)

    # 개별 파일 다운로드
    for fname, fid in FILE_IDS.items():
        out_path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(out_path):
            st.info(f"📥 {fname} 다운로드 중...")
            url = f"https://drive.google.com/uc?id={fid}"
            gdown.download(url, out_path, quiet=False)
            st.success(f"✅ {fname} 다운로드 완료")

    # 데이터 로드
    @st.cache_data(show_spinner=False)
    def load_data():
        vip_df = pd.read_csv(f"{DATA_DIR}/vip_summary_v2.csv")
        products = pd.read_csv(f"{DATA_DIR}/products.csv")
        orders = pd.read_csv(f"{DATA_DIR}/orders.csv")
        order_products = pd.read_csv(f"{DATA_DIR}/order_products__prior.csv")
        return vip_df, products, orders, order_products

    @st.cache_resource(show_spinner=False)
    def load_model():
        with open(f"{DATA_DIR}/diamond_2_3_lightfm_model.pkl", "rb") as f:
            model, user_id_map, product_id_map = pickle.load(f)
        return model, user_id_map, product_id_map

    vip_df, products, orders, order_products = load_data()
    model, user_id_map, product_id_map = load_model()

    # VIP 등급 분류
    bins = [-0.1, 60, 70, 80, 90, 100]
    labels = ['5.Bronze','4.Silver','3.Gold','2.Platinum','1.Diamond']
    vip_df['vip_grade'] = pd.cut(vip_df['vip_score'], bins=bins, labels=labels)

    # 추천 인덱스 반전 맵
    inv_user_map = {v:k for k,v in user_id_map.items()}
    inv_product_map = {v:k for k,v in product_id_map.items()}

    @st.cache_data(show_spinner=False)
    def cached_recommend_products(user_id, N=5):
        if user_id not in user_id_map:
            return []
        user_x = user_id_map[user_id]
        scores = model.predict(user_x, np.arange(len(product_id_map)))
        top_items = np.argsort(-scores)[:N]
        return [inv_product_map[i] for i in top_items]

    # 전략 탭용 데이터 준비
    @st.cache_data(show_spinner=False)
    def prepare_strategy_data(vip_df, orders, order_products):
        op_u = order_products.merge(orders[['order_id','user_id']], on='order_id', how='left')
        diversity = op_u.groupby('user_id')['product_id'].nunique().rename('unique_product_count')
        vip = vip_df.set_index('user_id').join(diversity).reset_index()
        g1 = vip[vip['vip_grade']=='1.Diamond'].copy(); g1['group']='1등급'
        g23 = vip[vip['vip_grade'].isin(['2.Platinum','3.Gold'])].copy(); g23['group']='2~3등급'
        compare_df = pd.concat([g1,g23])
        du = vip[vip['vip_grade']=='1.Diamond']['user_id']
        dorders = orders[orders['user_id'].isin(du)].sort_values(['user_id','order_number'])
        dorders['days_since_prior_order'] = dorders['days_since_prior_order'].fillna(0)
        avg_int = dorders.groupby('user_id')['days_since_prior_order'].mean().reset_index().rename(columns={'days_since_prior_order':'avg_reorder_interval'})
        return compare_df, avg_int

    compare_df, avg_interval_df = prepare_strategy_data(vip_df, orders, order_products)

    # 탭 구성
    탭_개요, 탭_등급, 탭_1등급, 탭_전략, 탭_추천 = st.tabs([
        "🏠 개요", "📊 등급별 고객 분석", "🔎 1등급 고객 집중 분석", 
        "💡 2~3등급 전환 전략", "🎯 맞춤형 추천 시스템"
    ])

    # ── 탭_개요 ──
    with 탭_개요:
        st.header("InstaCart VIP 고객 분석 개요")
        st.markdown("""
        - 고객의 활동/재구매/최근성 등을 반영한 VIP 스코어 기반 등급 분류
        - 상위 고객군 분석과 등급별 행동 패턴 비교
        - 전환 전략 제안과 추천 시스템 탑재 예정
        """)
        grade_counts = vip_df['vip_grade'].value_counts(normalize=True).reindex(labels).fillna(0)
        grade_percents = (grade_counts*100).round(1)
        cols = st.columns(5)
        titles = ["1등급 (Diamond)","2등급 (Platinum)","3등급 (Gold)","4등급 (Silver)","5등급 (Bronze)"]
        for col, title, lab in zip(cols, titles, labels):
            col.metric(title, f"{grade_percents[lab]}%")
        st.markdown("---")
        tot_cols = st.columns(3)
        tot_cols[0].metric("전체 고객 수", f"{vip_df.shape[0]:,}명")
        tot_cols[1].metric("1등급 고객 비율", f"{grade_percents['1.Diamond']}%")
        tot_cols[2].metric("평균 VIP Score", f"{vip_df['vip_score'].mean():.2f}")

    # ── 탭_등급 ──
    with 탭_등급:
        st.header("📌 고객 등급 분포")
        counts = vip_df['vip_grade'].value_counts().reindex(labels)
        fig = px.bar(x=counts.index, y=counts.values, color=counts.index,
                     color_discrete_sequence=px.colors.sequential.Blues_r,
                     labels={'x':'VIP 등급','y':'고객 수'}, title='고객 등급 분포')
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("🔍 등급별 행동 비교 보기"):
            st.markdown("1등급 vs 2~3등급 주요 행동 지표 비교")
            metrics = ['total_orders','total_products','reorder_rate','avg_cart_size','recency','unique_product_count']
            fig2, axes = plt.subplots(2,3,figsize=(18,8))
            for i, m in enumerate(metrics):
                ax = axes[i//3,i%3]
                sns.boxplot(x='group',y=m,data=compare_df,palette='Set2',ax=ax)
                ax.set_title(f"{m} 비교")
            fig2.delaxes(axes[1][2])
            st.pyplot(fig2)
            st.markdown("#### 평균값 비교표")
            st.dataframe(compare_df.groupby('group')[metrics].mean().round(2))

    # ── 탭_1등급 ──
    with 탭_1등급:
        st.header("🔎 1등급 고객 집중 분석")
        op = order_products.merge(orders[['order_id','user_id','order_number','order_dow','order_hour_of_day']], on='order_id')
        top_u = vip_df[vip_df['vip_grade']=='1.Diamond']['user_id']
        top_o = op[op['user_id'].isin(top_u)].merge(products[['product_id','product_name']], on='product_id')
        with st.expander("🛒 상위 구매 상품 분석"):
            tp = top_o['product_name'].value_counts().head(10)
            fig3, ax3 = plt.subplots()
            sns.barplot(x=tp.values, y=tp.index, palette='viridis', ax=ax3)
            ax3.set(xlabel='구매 횟수', ylabel='상품명', title='1등급 고객 TOP 구매 상품')
            st.pyplot(fig3)
        with st.expander("📆 활동 요일/시간대 분석"):
            c1, c2 = st.columns(2)
            with c1:
                fig4, ax4 = plt.subplots()
                sns.countplot(x='order_dow', data=top_o, palette='Blues', ax=ax4)
                ax4.set_title('요일별 주문 분포 (0=일)')
                st.pyplot(fig4)
            with c2:
                fig5, ax5 = plt.subplots()
                sns.countplot(x='order_hour_of_day', data=top_o, palette='Greens', ax=ax5)
                ax5.set_title('시간대별 주문 분포')
                st.pyplot(fig5)
        with st.expander("📈 재구매 주기 분석"):
            fig6, ax6 = plt.subplots(figsize=(10,5))
            sns.histplot(avg_interval_df['avg_reorder_interval'], bins=30, kde=True, ax=ax6)
            ax6.set(xlabel='재구매 주기 (일)', ylabel='고객 수', title='평균 재구매 주기 분포')
            st.pyplot(fig6)
            st.markdown(f"**평균 재구매 주기:** {avg_interval_df['avg_reorder_interval'].mean():.2f}일")

    # ── 탭_전략 ──
    with 탭_전략:
        st.header("💡 2~3등급 → 1등급 전환 전략")
        strategies = [
            ("다양한 상품 경험 유도", 'unique_product_count'),
            ("재방문 유도", 'reorder_rate'),
            ("휴면 방지", 'recency'),
            ("장바구니 크기 증가", 'avg_cart_size')
        ]
        for title, metric in strategies:
            with st.expander(f"📌 {title}"):
                dfm = compare_df.groupby('group')[metric].mean().reset_index()
                fig, ax = plt.subplots()
                sns.barplot(x=metric, y='group', data=dfm, ax=ax)
                ax.set_title(title)
                st.pyplot(fig)

    # ── 탭_추천 ──
    with 탭_추천:
        st.header("🎯 맞춤형 추천 시스템")
        opt = st.selectbox("고객 등급 선택", ["1등급 (Diamond)", "2~3등급 (Platinum+Gold)"])
        sel = '1.Diamond' if opt.startswith('1') else ['2.Platinum','3.Gold']
        users = vip_df[vip_df['vip_grade'].isin(sel)]['user_id']
        uid = st.selectbox("고객 선택", users)
        user_info = vip_df[vip_df['user_id']==uid].iloc[0]
        hist = pd.DataFrame({"항목":["VIP 등급","총 주문 수","재구매율"],"값":[user_info['vip_grade'], user_info['total_orders'], user_info['reorder_rate']]})
        st.table(hist)
        if st.button("추천 받기"):
            recs = cached_recommend_products(uid)
            if recs:
                st.write("추천 상품:")
                for pid in recs:
                    name = products.loc[products['product_id']==pid,'product_name'].values[0]
                    st.write(f"- {name}")
            else:
                st.write("추천할 상품이 없습니다.")

    st.success("✅ 대시보드 로드 완료")

except Exception as e:
    st.error("⚠️ 앱 실행 중 예외가 발생했습니다!")
    st.error(f"Error: {e}")
    st.text(traceback.format_exc())
    st.stop()
