import streamlit as st
import sqlite3
from datetime import datetime
import uuid
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.components.sidebar import show_sidebar

selected = show_sidebar()

st.set_page_config(layout="wide")
st.title("VOD追加")

if not st.session_state.get("is_admin"):
    st.error("このページは編集者のみアクセスできます。")
    st.stop()

with st.form("vod_form"):
    title = st.text_input("タイトル", max_chars=200)
    category = st.text_input("カテゴリ（任意、複数ある場合は | 区切り）")
    url = st.text_input("Twitch URL")
    submitted = st.form_submit_button("追加")

    if submitted:
        if not title or not url:
            st.warning("タイトルとURLは必須です。")
        else:
            conn = sqlite3.connect("vods.db", check_same_thread=False)
            c = conn.cursor()
            twitch_id = "manual_" + uuid.uuid4().hex[:8]
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute("""
                INSERT INTO vods (twitch_id, title, category, url, created_at, type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (twitch_id, title, category, url, created_at, "upload_manual"))

            conn.commit()
            conn.close()

            st.success("✅ VODを追加しました。")
