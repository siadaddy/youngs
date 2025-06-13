import streamlit as st
import os
import duckdb
import gdown
from pathlib import Path

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
