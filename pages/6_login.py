# pages/6_login.py

import streamlit as st
import sys, os

# ページ設定
st.set_page_config(page_title="Login", page_icon="🔒", layout="wide")

# サイドバー表示
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.components.sidebar import show_sidebar
show_sidebar()

# タイトル
st.title("🔐 編集者ログイン")

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# すでにログイン済みの場合
if st.session_state.is_admin:
    st.success("✅ 編集者としてログイン中です。")
    if st.button("ログアウト", key="logout_btn"):
        st.session_state.is_admin = False
        st.success("🔓 ログアウトしました。")
        st.rerun()
    st.stop()

# パスワードが未設定の場合の警告
if "ADMIN_PASSWORD" not in st.secrets:
    st.error("⚠️ 管理者パスワード（ADMIN_PASSWORD）が未設定です。 `.streamlit/secrets.toml` に設定してください。")
    st.stop()

# ログインフォーム
with st.form("login_form", clear_on_submit=True):
    pw = st.text_input("パスワードを入力してください", type="password")
    submitted = st.form_submit_button("ログイン")

    if submitted:
        if pw == st.secrets["ADMIN_PASSWORD"]:
            st.session_state.is_admin = True
            st.success("✅ ログインに成功しました。")
            st.rerun()
        else:
            st.error("❌ パスワードが正しくありません。")

