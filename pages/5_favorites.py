import streamlit as st
import sqlite3
import pandas as pd
import sys, os

# ページ設定
st.set_page_config(page_title="Favorites", page_icon="⭐", layout="wide")

# CSS: ナビゲーション非表示 + カード形式
st.markdown("""
<style>
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }

    .clip-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .clip-card:hover {
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
        transition: box-shadow 0.3s ease;
    }

    .clip-title {
        font-size: 15px;
        font-weight: bold;
        margin-bottom: 6px;
        color: #ff6b6b;
        text-decoration: none;
        line-height: 1.3;
        word-wrap: break-word;
        overflow-wrap: break-word;
        height: 2.6em;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    .clip-meta {
        color: #666;
        font-size: 12px;
        margin-bottom: 6px;
    }

    .clip-url {
        font-size: 12px;
        color: #1f77b4;
        word-break: break-all;
    }

    .download-button-container {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# サイドバー表示
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.components.sidebar import show_sidebar
show_sidebar()

# タイトルとCSVダウンロードを横並びに
col1, col2 = st.columns([6, 1])
with col1:
    st.title("⭐ お気に入りクリップ一覧")

# お気に入りclip IDをセッションから取得
clip_fav_ids = [
    key.replace("clip_fav_", "")
    for key in st.session_state
    if key.startswith("clip_fav_") and st.session_state[key] is True
]

if not clip_fav_ids:
    st.info("⭐ まだお気に入りに追加されたクリップはありません。")
    st.stop()

# DB接続
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()

# Clip情報取得
placeholder = ",".join(["?"] * len(clip_fav_ids))
query = f"""
    SELECT id, title, url, thumbnail_url, created_at, vod_id
    FROM clips
    WHERE id IN ({placeholder})
    ORDER BY created_at DESC
"""
c.execute(query, clip_fav_ids)
clips = c.fetchall()
conn.close()

# ダウンロード用データ
csv_data = [{"Title": title, "URL": url, "Created At": created_at} for _, title, url, _, created_at, _ in clips]
df = pd.DataFrame(csv_data)
csv = df.to_csv(index=False).encode("utf-8-sig")

# ダウンロードボタンを右上に配置
with col2:
    st.download_button(
        label="⬇️ CSV出力",
        data=csv,
        file_name="favorite_clips.csv",
        mime="text/csv",
        use_container_width=True
    )

# 4列表示
cols = st.columns(4)
for idx, (cid, title, url, thumbnail_url, created_at, vod_id) in enumerate(clips):
    with cols[idx % 4]:
        # サムネイル表示（VOD ID またはクリップサムネイルURL）
        if thumbnail_url:
            st.image(thumbnail_url, use_container_width=True)
        elif vod_id:
            st.image(f"https://img.youtube.com/vi/{vod_id}/mqdefault.jpg", use_container_width=True)
        else:
            st.markdown('<div style="height: 180px; background-color: #f5f5f5; display: flex; align-items: center; justify-content: center; border-radius: 4px; border: 2px dashed #ccc; font-size: 14px; color: #999;">No Thumbnail</div>', unsafe_allow_html=True)

        # カード情報
        card_html = f"""
        <div class="clip-card">
            <div class="clip-title">{title}</div>
            <div class="clip-meta">📅 {created_at}</div>
        """
        if url:
            card_html += f'<div class="clip-url">🔗 <a href="{url}" target="_blank">{url}</a></div>'
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        # 詳細ページへボタン
        if st.button("詳細を見る", key=f"clip_detail_{cid}", use_container_width=True):
            st.session_state['selected_clip_id'] = cid
            st.switch_page("pages/4_clip_detail.py")
