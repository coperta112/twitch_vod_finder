import streamlit as st
import sqlite3
import sys
import os
from datetime import datetime
from dateutil import parser

# ページ設定
st.set_page_config(
    page_title="Clip Detail - VOD Finder",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSSで不要なナビゲーション等を非表示 + 高さ揃える
st.markdown("""
<style>
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }

    .columns-container {
        display: flex;
        align-items: stretch;
        gap: 30px;
    }

    .thumbnail-container {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%;
        height: 0;
        overflow: hidden;
        border-radius: 8px;
        margin-bottom: 20px;
    }

    .thumbnail-container img {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .no-thumbnail {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: #f0f0f0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        border: 2px dashed #ccc;
        color: #666;
        font-size: 18px;
    }

    .clip-title {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1f1f1f;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .clip-date {
        color: #666;
        font-size: 16px;
        margin-bottom: 20px;
    }
    
    /* Linked Video用の横並びレイアウト */
    .linked-video-card {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        margin-bottom: 20px;
        gap: 16px;
        padding: 8px 0;
        position: relative;
    }
    
    .linked-video-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #1f77b4, #4fc3f7);
    }
    
    .linked-video-thumbnail {
        width: 200px;
        height: 112px;
        background-color: #f0f0f0;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
        font-size: 16px;
        border: 1px solid #ddd;
        overflow: hidden;
        flex-shrink: 0;
    }
    
    .linked-video-thumbnail img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .linked-video-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-width: 0;
        gap: 4px;
        height: 112px;
    }
    
    .linked-video-title {
        font-size: 16px;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 6px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.3;
    }
    
    .linked-video-meta {
        color: #666;
        font-size: 13px;
        margin-bottom: 12px;
    }
    
    .linked-video-actions {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-top: auto;
    }
    
    /* 編集モード用スタイル */
    .edit-mode-panel {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 6px;
        padding: 15px;
        margin-bottom: 20px;
    }
    
    .admin-badge {
        background-color: #dc3545;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .danger-zone {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 6px;
        padding: 15px;
        margin-top: 30px;
    }
    
    .vod-connection-status {
        padding: 10px;
        border-radius: 6px;
        margin: 10px 0;
        font-weight: bold;
    }
    
    .connected {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .disconnected {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# サイドバー表示
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.components.sidebar import show_sidebar
show_sidebar()

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "is_edit_mode" not in st.session_state:
    st.session_state.is_edit_mode = False

# Clip ID の取得
clip_id = st.session_state.get('selected_clip_id') or st.query_params.get("clip_id")
if not clip_id:
    st.error("❌ Clip ID が指定されていません")
    if st.button("✂️ Clips ページに戻る"):
        st.switch_page("pages/3_clips.py")
    st.stop()

# DB接続
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()

# Clip 情報取得（urlも含める）
c.execute("""
    SELECT id, title, category, created_at, thumbnail_url, url, vod_id
    FROM clips WHERE id = ?
""", (clip_id,))
clip = c.fetchone()
if not clip:
    st.error("❌ 指定されたClipが見つかりません")
    if st.button("✂️ Clips ページに戻る"):
        st.switch_page("pages/3_clips.py")
    conn.close()
    st.stop()

cid, title, category, created_at, thumbnail_url, url, vod_id = clip

# VOD 情報取得
vod_info = None
if vod_id:
    c.execute("SELECT id, title, created_at FROM vods WHERE id = ?", (vod_id,))
    vod_info = c.fetchone()

# ----------------------------- 編集処理 -----------------------------

# クリップ削除処理
if st.session_state.is_admin and st.session_state.get('delete_clip_confirmed', False):
    c.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
    conn.commit()
    conn.close()
    
    st.success("✅ クリップを削除しました。")
    del st.session_state['delete_clip_confirmed']
    if st.button("✂️ Clips一覧に戻る"):
        st.switch_page("pages/3_clips.py")
    st.stop()

conn.close()

# ---------------------- 表示 ----------------------

# 戻るボタンとタイトル
col_back, col_title, col_admin = st.columns([1, 4, 1])

with col_back:
    if st.button("◀️ Clips一覧に戻る"):
        st.switch_page("pages/3_clips.py")

with col_title:
    if st.session_state.is_edit_mode:
        st.markdown("### ✏️ クリップ編集モード")
    else:
        st.markdown("### ✂️ クリップ詳細")

# 編集モード切り替え用のコールバック関数
def toggle_edit_mode():
    st.session_state.is_edit_mode = not st.session_state.is_edit_mode

with col_admin:
    if st.session_state.is_admin:
        st.markdown('<span class="admin-badge">🔐 編集者</span>', unsafe_allow_html=True)
        if st.session_state.is_edit_mode:
            if st.button("👁️ 表示モード", key="view_mode_btn", on_click=toggle_edit_mode):
                pass
        else:
            if st.button("✏️ 編集モード", key="edit_mode_btn", on_click=toggle_edit_mode):
                pass

# 編集モード処理
if st.session_state.is_admin and st.session_state.is_edit_mode:
    with st.form("edit_clip_form"):
        st.markdown("### 📝 クリップ情報を編集")
        
        # 基本情報編集
        new_title = st.text_input("タイトル", value=title)
        new_url = st.text_input("URL", value=url or "")
        new_thumbnail = st.text_input("サムネイルURL", value=thumbnail_url or "")
        new_date = st.date_input("作成日", value=parser.parse(created_at).date())
        
        # VOD紐づけ選択
        st.markdown("#### 🔗 VOD紐づけ")
        
        # 現在の紐づけ状態表示
        if vod_info:
            st.markdown(f'''
            <div class="vod-connection-status connected">
                ✅ 現在紐づけ中: {vod_info[1]} (ID: {vod_info[0]})
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="vod-connection-status disconnected">
                ⚠️ VODに紐づけられていません
            </div>
            ''', unsafe_allow_html=True)
        
        # VOD選択
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT id, title FROM vods ORDER BY created_at DESC")
        all_vods = c.fetchall()
        conn.close()
        
        vod_options = ["紐づけなし"] + [f"{vod[1]} (ID: {vod[0]})" for vod in all_vods]
        
        # 現在選択されているVODのインデックスを取得
        current_selection = 0  # デフォルトは「紐づけなし」
        if vod_id:
            for i, (vid, vtitle) in enumerate(all_vods):
                if vid == vod_id:
                    current_selection = i + 1  # +1 because of "紐づけなし" at index 0
                    break
        
        selected_vod = st.selectbox(
            "紐づけるVODを選択",
            options=vod_options,
            index=current_selection,
            help="クリップを特定のVODに紐づけることができます"
        )
        
        # 保存ボタン
        if st.form_submit_button("💾 変更を保存", use_container_width=True):
            # 選択されたVOD IDを取得
            new_vod_id = None
            if selected_vod != "紐づけなし":
                # "タイトル (ID: 123)" の形式から ID を抽出
                new_vod_id = selected_vod.split("ID: ")[1].rstrip(")")
            
            conn = sqlite3.connect("vods.db", check_same_thread=False)
            c = conn.cursor()
            
            new_created_at = new_date.strftime("%Y-%m-%d") + " " + created_at.split(" ")[1] if " " in created_at else new_date.strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("""
                UPDATE clips 
                SET title = ?, url = ?, thumbnail_url = ?, created_at = ?, vod_id = ?
                WHERE id = ?
            """, (new_title, new_url, new_thumbnail, new_created_at, new_vod_id, clip_id))
            
            conn.commit()
            conn.close()
            
            st.success("✅ クリップ情報を更新しました！")
            st.session_state.is_edit_mode = False
            st.rerun()
    
    # 危険ゾーン
    with st.expander("⚠️ 危険ゾーン - クリップ削除", expanded=False):
        st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
        st.warning("⚠️ この操作は取り消せません。クリップが完全に削除されます。")
        
        if st.checkbox("削除することを理解しました", key="delete_confirm"):
            if st.button("🗑️ クリップを完全に削除", key="delete_clip", type="primary"):
                st.session_state['delete_clip_confirmed'] = True
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # 通常の表示モード
    # 高さ揃えるための外部div
    st.markdown('<div class="columns-container">', unsafe_allow_html=True)
    
    left, right = st.columns([3, 2])
    
    # ---------- 左カラム ----------
    with left:
        # サムネイルを上部に表示
        if thumbnail_url:
            st.image(
                thumbnail_url, 
                use_container_width=True
            )
        else:
            st.markdown("""
            <div style="
                width: 100%;
                height: 300px;
                background-color: #f0f0f0;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                border: 2px dashed #ccc;
                color: #666;
                font-size: 18px;
                margin-bottom: 20px;
            ">
                ✂️ サムネイル画像なし
            </div>
            """, unsafe_allow_html=True)
    
        st.markdown(f'<div class="clip-title">✂️ {title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="clip-date">📅 追加日: {created_at}</div>', unsafe_allow_html=True)
    
        if url:
            st.markdown("### 🔗 クリップURL")
            st.markdown(f"[{url}]({url})")
    
        # お気に入り機能
        st.markdown("### ⭐ お気に入り")
        fav_key = f"clip_fav_{cid}"
        if fav_key not in st.session_state:
            st.session_state[fav_key] = False
    
        fav_text = "★ お気に入りから削除" if st.session_state[fav_key] else "☆ お気に入りに追加"
        if st.button(fav_text, key="fav_toggle", use_container_width=True):
            st.session_state[fav_key] = not st.session_state[fav_key]
            st.rerun()
    
    # ---------- 右カラム ----------
    with right:
        st.markdown("### 📺 Linked Video")
        if vod_info:
            vod_id_info, vod_title, vod_date = vod_info
    
            # VOD情報を横並びで表示
            st.markdown('<div class="linked-video-card">', unsafe_allow_html=True)
            
            col_vod_thumb, col_vod_info = st.columns([1, 2])
            
            with col_vod_thumb:
                # VODのサムネイル（YouTubeリンクから取得）
                conn = sqlite3.connect("vods.db", check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT video_id FROM youtube_links WHERE vod_id = ? AND video_id IS NOT NULL LIMIT 1", (vod_id_info,))
                vod_video_id = c.fetchone()
                
                if vod_video_id and vod_video_id[0]:
                    vod_thumbnail = f"https://img.youtube.com/vi/{vod_video_id[0]}/mqdefault.jpg"
                    st.image(vod_thumbnail, use_container_width=True)
                else:
                    st.markdown("""
                    <div style="
                        width: 100%;
                        height: 112px;
                        background-color: #f0f0f0;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 8px;
                        border: 1px solid #ddd;
                        color: #666;
                        font-size: 16px;
                    ">
                        📺
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_vod_info:
                # VODタイトル
                st.markdown(f'<div class="linked-video-title">{vod_title}</div>', unsafe_allow_html=True)
                
                # VOD追加日
                try:
                    formatted_vod_date = datetime.strptime(vod_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                except:
                    formatted_vod_date = vod_date
                st.markdown(f'<div class="linked-video-meta">追加日: {formatted_vod_date}</div>', unsafe_allow_html=True)
                
                # VOD詳細ページへのボタン
                if st.button("詳細を見る", key="vod_detail", use_container_width=True):
                    st.session_state['selected_vod_id'] = vod_id_info
                    st.switch_page("pages/2_video_detail.py")
            
            st.markdown('</div>', unsafe_allow_html=True)  # linked-video-card終了
            conn.close()
    
        else:
            st.info("このクリップには関連付けられたVODがありません")
            
            # 管理者の場合、紐づけ推奨メッセージ
            if st.session_state.is_admin:
                st.warning("💡 編集モードでVODとの紐づけを設定できます")
    
    st.markdown('</div>', unsafe_allow_html=True)  # columns-container