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
from lightfm import LightFM

# (Optional) Mac 한글 깨짐 방지
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
        gdown.download(f"https://drive.google.com/uc?id={fid}",
                       str(out_path), quiet=False)
        st.success(f"✅ {fname} 다운로드 완료")

# ── 3) DuckDB 커넥션 생성 ─────────────────────────
@st.cache_resource(show_spinner=False)
def get_duckdb_conn(db_path: str = str(DATA_DIR / "instacart.duckdb")):
    return duckdb.connect(db_path)

con = get_duckdb_conn()

# ── 4) 데이터 & VIP summary 동적 생성 ─────────────────────────
@st.cache_data(show_spinner=False)
def load_data(sample_rows: int = None):
    # 1) VIP summary CTE
    vip_sql = f"""
    WITH user_raw AS (
      SELECT
        o.user_id,
        COUNT(DISTINCT o.order_id)                             AS total_orders,
        COUNT(op.product_id)                                   AS total_products,
        SUM(CASE WHEN o.order_number > 1 THEN 1 ELSE 0 END)*1.0
          / COUNT(DISTINCT o.order_id)                         AS reorder_rate,
        COUNT(op.product_id)*1.0
          / COUNT(DISTINCT o.order_id)                         AS avg_cart_size,
        AVG(COALESCE(o.days_since_prior_order,0))              AS avg_reorder_interval,
        MAX(o.order_number) - 1                                 AS recency
      FROM orders AS o
      JOIN order_products__prior AS op USING(order_id)
      GROUP BY o.user_id
    ),
    user_max AS (
      SELECT
        MAX(total_orders)         AS max_orders,
        MAX(total_products)       AS max_products,
        MAX(reorder_rate)         AS max_reorder_rate,
        MAX(avg_cart_size)        AS max_cart_size,
        MAX(avg_reorder_interval) AS max_interval,
        MAX(recency)              AS max_recency
      FROM user_raw
    ),
    user_scored AS (
      SELECT
        ur.*,
        ROUND(
          100.0*(
            (ur.total_orders          / um.max_orders )   *0.30
          + (ur.total_products        / um.max_products ) *0.25
          + (ur.reorder_rate          / um.max_reorder_rate)*0.20
          + (ur.avg_cart_size         / um.max_cart_size )*0.15
          + ((um.max_interval - ur.avg_reorder_interval)
             / um.max_interval)                         *0.05
          + ((um.max_recency - ur.recency)
             / um.max_recency)                           *0.05
          )
        ,1) AS vip_score
      FROM user_raw ur
      CROSS JOIN user_max um
    )
    SELECT
      user_id, total_orders, total_products,
      ROUND(reorder_rate,3)         AS reorder_rate,
      ROUND(avg_cart_size,2)        AS avg_cart_size,
      ROUND(avg_reorder_interval,1) AS avg_reorder_interval,
      recency,
      vip_score,
      CASE
        WHEN vip_score>=90 THEN '1.Diamond'
        WHEN vip_score>=80 THEN '2.Platinum'
        WHEN vip_score>=70 THEN '3.Gold'
        WHEN vip_score>=60 THEN '4.Silver'
        ELSE '5.Bronze'
      END AS vip_grade
    FROM user_scored
    ORDER BY vip_score DESC
    {f"LIMIT {sample_rows}" if sample_rows else ""}
    """
    vip_df = con.execute(vip_sql).df()

    # 2) 나머지 테이블
    products       = con.execute("SELECT * FROM products").df()
    orders         = con.execute(f"""
        SELECT order_id, user_id, order_number,
               days_since_prior_order, order_dow, order_hour_of_day
        FROM orders
        {f"LIMIT {sample_rows}" if sample_rows else ""}
    """).df()
    order_products = con.execute(f"""
        SELECT order_id, product_id
        FROM order_products__prior
        {f"LIMIT {sample_rows}" if sample_rows else ""}
    """).df()

    return vip_df, products, orders, order_products

vip_df, products, orders, order_products = load_data()

# ── 5) 모델 로드 ─────────────────────────
@st.cache_resource(show_spinner=False)
def load_model():
    with open(DATA_DIR/"diamond_2_3_lightfm_model.pkl", 'rb') as f:
        return pickle.load(f)

model, user_id_map, product_id_map = load_model()

# ── 6) 추천 함수 준비 ─────────────────────────
inv_user_map    = {v:k for k,v in user_id_map.items()}
inv_product_map = {v:k for k,v in product_id_map.items()}

@st.cache_data(show_spinner=False)
def cached_recommend(user_id, N=5):
    if user_id not in user_id_map:
        return []
    ux     = user_id_map[user_id]
    scores = model.predict(ux, np.arange(len(product_id_map)))
    topn   = np.argsort(-scores)[:N]
    return [inv_product_map[i] for i in topn]

# ── 7) 전략용 추가 지표 계산 ─────────────────────────
@st.cache_data(show_spinner=False)
def prepare_strategy(vip_df, orders, order_products):
    op_u = order_products.merge(orders[['order_id','user_id']], on='order_id')
    diversity = op_u.groupby('user_id')['product_id'].nunique().rename('unique_product_count')
    vip2 = vip_df.set_index('user_id').join(diversity).reset_index()
    g1 = vip2[vip2['vip_grade']=='1.Diamond'].copy();  g1['group']='1등급'
    g23= vip2[vip2['vip_grade'].isin(['2.Platinum','3.Gold'])].copy(); g23['group']='2~3등급'
    compare_df = pd.concat([g1,g23])

    du = g1['user_id']
    dorders = orders[orders['user_id'].isin(du)].copy()
    dorders['days_since_prior_order'].fillna(0, inplace=True)
    avg_int = dorders.groupby('user_id')['days_since_prior_order']\
                     .mean().rename('avg_reorder_interval').reset_index()

    return compare_df, avg_int

compare_df, avg_interval_df = prepare_strategy(vip_df, orders, order_products)

# ── 8) 대시보드 렌더링 ─────────────────────────
tabs = st.tabs(["🏠개요","📊등급분포","🔎1등급분석","💡전략","🎯추천"])
tab0,tab1,tab2,tab3,tab4 = tabs

with tab0:
    st.header("🚀 InstaCart VIP 분석 개요")
    pct = (vip_df['vip_grade'].value_counts(normalize=True)
           .reindex(['1.Diamond','2.Platinum','3.Gold','4.Silver','5.Bronze'], fill_value=0)*100).round(1)
    cols = st.columns(5)
    for col,lab in zip(cols, pct.index):
        col.metric(lab, f"{pct[lab]}%")
    st.markdown("---")
    c1,c2,c3 = st.columns(3)
    c1.metric("전체 고객", f"{len(vip_df):,}")
    c2.metric("1등급 비율", f"{pct['1.Diamond']}%")
    c3.metric("평균 VIP Score", f"{vip_df['vip_score'].mean():.2f}")

with tab1:
    st.header("📊 고객 등급 분포")
    fig=px.bar(x=pct.index,y=pct.values,
               labels={'x':'등급','y':'비율(%)'},
               color=pct.index)
    st.plotly_chart(fig,use_container_width=True)
    with st.expander("상세 비교"):
        metrics=['total_orders','total_products','reorder_rate',
                 'avg_cart_size','recency','unique_product_count']
        fig2,axes=plt.subplots(2,3,figsize=(18,8))
        for i,m in enumerate(metrics):
            ax=axes[i//3,i%3]
            sns.boxplot(x='group',y=m,data=compare_df,palette='Set2',ax=ax)
            ax.set_title(m)
        fig2.delaxes(axes[1][2])
        st.pyplot(fig2)

with tab2:
    st.header("🔎 1등급 고객 집중 분석")
    top_u=vip_df[vip_df['vip_grade']=='1.Diamond']['user_id']
    op=order_products.merge(orders[['order_id','user_id','order_dow','order_hour_of_day']],
                            on='order_id').merge(products[['product_id','product_name']],
                                                 on='product_id')
    tp=op[op['user_id'].isin(top_u)]
    with st.expander("TOP 상품"):
        cnt=tp['product_name'].value_counts().head(10)
        fig3,ax3=plt.subplots(); sns.barplot(x=cnt.values,y=cnt.index,ax=ax3)
        st.pyplot(fig3)
    with st.expander("재구매 주기"):
        fig4,ax4=plt.subplots(figsize=(10,5))
        sns.histplot(avg_interval_df['avg_reorder_interval'],bins=30,kde=True,ax=ax4)
        st.pyplot(fig4)

with tab3:
    st.header("💡 전환 전략")
    strategies=[
      ('상품 다양성','unique_product_count'),
      ('재구매율','reorder_rate'),
      ('최근성','recency'),
      ('장바구니크기','avg_cart_size')
    ]
    for title,metric in strategies:
        with st.expander(title):
            dfm=compare_df.groupby('group')[metric].mean().reset_index()
            fig5,ax5=plt.subplots(); sns.barplot(x=metric,y='group',data=dfm,ax=ax5)
            st.pyplot(fig5)

with tab4:
    st.header("🎯 맞춤형 추천")
    sel=st.selectbox("등급 선택",["1.Diamond","2~3등급"])
    grades=['1.Diamond'] if sel=="1.Diamond" else ['2.Platinum','3.Gold']
    users=vip_df[vip_df['vip_grade'].isin(grades)]['user_id']
    uid=st.selectbox("고객 선택",users)
    # 프로필
    info=vip_df.set_index('user_id').loc[uid]
    st.table(pd.DataFrame({
      '지표':['총주문','상품수','재구매율','평균카트크기','최근성'],
      '값':[info.total_orders,info.total_products,
           round(info.reorder_rate,3),round(info.avg_cart_size,2),info.recency]
    }))
    if st.button("추천"):
        recs=cached_recommend(uid,5)
        st.write([products.loc[products.product_id==pid,'product_name'].values[0] for pid in recs])

st.success("✅ DuckDB 기반 대시보드 로드 완료")
