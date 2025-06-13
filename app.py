import streamlit as st
import os
import duckdb
import gdown
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

import plotly.express as px    # ← 이 줄이 반드시 최상단 import 모음에 있어야 합니다
import pickle
import traceback

DATA_DIR = Path("data_InstaCart")
os.makedirs(DATA_DIR, exist_ok=True)

# ── 2) DuckDB 파일 다운로드 ─────────────────────────
FILE_IDS = {
    "instacart.duckdb": "1BY8nUq5OfyrDnxyZRiuSACf3TDbrdx7m",
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

# ── 4) VIP 스코어링 + 등급 조회 ─────────────────────────
@st.cache_data(show_spinner=False)
def load_vip_scores(limit: int = 1000):
    vip_sql = """
    WITH user_raw AS (
      SELECT
        o.user_id,
        COUNT(DISTINCT o.order_id)                             AS total_orders,
        COUNT(op.product_id)                                   AS total_products,
        SUM(CASE WHEN o.order_number > 1 THEN 1 ELSE 0 END)*1.0
          / COUNT(DISTINCT o.order_id)                         AS reorder_rate,
        COUNT(op.product_id)*1.0
          / COUNT(DISTINCT o.order_id)                         AS avg_cart_size,
        AVG(COALESCE(o.days_since_prior_order,0))              AS avg_reorder_interval
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
        MAX(avg_reorder_interval) AS max_interval
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
             / um.max_interval)                         *0.10
          )
        ,1) AS vip_score
      FROM user_raw ur
      CROSS JOIN user_max um
    )
    SELECT
      user_id,
      total_orders,
      total_products,
      ROUND(reorder_rate,3)         AS reorder_rate,
      ROUND(avg_cart_size,2)        AS avg_cart_size,
      ROUND(avg_reorder_interval,1) AS avg_reorder_interval,
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
    LIMIT {{limit}};
    """
    return con.execute(vip_sql.replace("{{limit}}", str(limit))).df()

# 실제 로드
vip_df = load_vip_scores(limit=500)

# ── 5) Streamlit에 표시 ─────────────────────────
st.header("🎖️ VIP Score & Grade Top 10")
st.dataframe(vip_df.head(10), use_container_width=True)

# 등급 분포 차트
st.header("📊 VIP Grade Distribution")
grade_counts = vip_df['vip_grade'].value_counts().reindex(
    ['1.Diamond','2.Platinum','3.Gold','4.Silver','5.Bronze']
).fillna(0)
fig = px.bar(
    x=grade_counts.index, 
    y=grade_counts.values,
    labels={'x':'VIP Grade','y':'Count'},
    title='VIP Grade Distribution'
)
st.plotly_chart(fig, use_container_width=True)

