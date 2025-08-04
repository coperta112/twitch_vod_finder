import streamlit as st
import sqlite3
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.components.sidebar import show_sidebar

selected = show_sidebar()

st.set_page_config(layout="wide")
st.title("Clip追加")

if not st.session_state.get("is_admin"):
    st.error("このページは編集者のみアクセスできます。")
    st.stop()

# DB接続 & VOD一覧取得（プルダウン用）
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()
c.execute("SELECT id, title FROM vods ORDER BY created_at DESC")
vod_choices = c.fetchall()
conn.close()

vod_titles = [f"{vid} - {title}" for vid, title in vod_choices]
vod_map = {f"{vid} - {title}": vid for vid, title in vod_choices}

with st.form("clip_form"):
    title = st.text_input("タイトル", max_chars=200)
    category = st.text_input("カテゴリ（任意、複数ある場合は | 区切り）")
    url = st.text_input("Twitch Clip URL")
    thumbnail = st.text_input("サムネイルURL（任意）")
    selected_vod = st.selectbox("紐づけるVOD（タイトル検索可）", [""]
                                + vod_titles, index=0)
    submitted = st.form_submit_button("追加")

    if submitted:
        if not title or not url:
            st.warning("タイトルとURLは必須です。")
        else:
            vod_id = vod_map.get(selected_vod) if selected_vod else None
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect("vods.db", check_same_thread=False)
            c = conn.cursor()
            twitch_id = "manual_" + datetime.now().strftime("%Y%m%d%H%M%S")
            c.execute("""
                INSERT INTO clips
                (twitch_id, title, category, url, created_at, vod_id, thumbnail_url, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (twitch_id, title, category, url, created_at, vod_id, thumbnail))
            conn.commit()
            conn.close()

            st.success("✅ Clipを追加しました。")
