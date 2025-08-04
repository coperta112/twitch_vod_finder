# pages/2_video_detail.py

import streamlit as st
import sqlite3
import sys
import os
from datetime import datetime
import uuid

# ページ設定 - デフォルトサイドバーを無効化
st.set_page_config(
    page_title="Video Detail - VOD Finder",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 修正されたCSS部分 - クリップレイアウトを横並びに変更
st.markdown("""
<style>
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }
    
    /* メインコンテナのリセット */
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
        max-width: 100% !important;
    }
    
    /* Streamlitの全てのデフォルトマージンを削除 */
    .element-container {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* サムネイルコンテナ */
    .thumbnail-container {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%;
        height: 0;
        overflow: hidden;
        border-radius: 12px;
        margin-bottom: 16px;
        background-color: #000;
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
        border-radius: 12px;
        border: 2px dashed #ccc;
        color: #666;
        font-size: 18px;
    }
    
    /* ビデオ情報 */
    .video-title {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 12px;
        color: #1f1f1f;
        line-height: 1.3;
    }
    
    .video-date {
        color: #666;
        font-size: 16px;
        margin-bottom: 20px;
    }
    
    .video-tags {
        margin: 20px 0;
    }
    
    .video-tag {
        display: inline-block;
        background-color: #e8f4f8;
        color: #1f77b4;
        padding: 8px 16px;
        margin: 4px 8px 4px 0;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* YouTubeリンク */
    .youtube-links {
        margin: 20px 0;
    }
    
    .youtube-link {
        display: block;
        padding: 14px 18px;
        margin: 10px 0;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 8px;
        text-decoration: none;
        color: #1f77b4;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .youtube-link:hover {
        background-color: #f0f8ff;
        border-color: #1f77b4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    /* クリップサイドバー */
    .clips-header {
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 20px;
        color: #1f1f1f;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 10px;
    }
    
    /* クリップカード - 横並びレイアウトに変更（背景とボーダーを削除） */
    .clip-card {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        margin-bottom: 20px;
        gap: 16px;
        padding: 8px 0;
        position: relative;
    }
    
    /* クリップカードの上に表示される棒線 */
    .clip-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #8fbc8f, #8fbc8f);
    }
    
    .clip-thumbnail {
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
    
    .clip-thumbnail img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .clip-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-width: 0;
        gap: 4px;
        height: 112px;
    }
    
    .clip-title {
        font-size: 16px;
        font-weight: bold;
        color: #ff6b6b;
        margin-bottom: 6px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.3;
    }
    
    .clip-meta {
        color: #666;
        font-size: 13px;
        margin-bottom: 12px;
    }
    
    .clip-actions {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-top: auto;
    }
    
    /* ヘッダー部分 */
    .back-button {
        margin-bottom: 20px;
    }
    
    /* 編集モード用スタイル */
    .edit-mode-panel {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 30px;
    }
    
    .admin-badge {
        background-color: #28a745;
        color: white;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .youtube-link-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px;
        margin: 8px 0;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    
    .danger-zone {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 20px;
        margin-top: 40px;
    }
    
    /* レスポンシブ対応 */
    @media (max-width: 1200px) {
        .custom-video-layout {
            flex-direction: column;
        }
        
        .clips-sidebar {
            max-width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)


# パス追加してサイドバー表示
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.components.sidebar import show_sidebar
show_sidebar()

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

# session_stateからVOD IDを取得（1_videos.pyからの遷移）
vod_id = st.session_state.get('selected_vod_id')

# フォールバック：クエリパラメータからも取得を試行
if not vod_id:
    vod_id = st.query_params.get("vod_id")

if not vod_id:
    st.error("❌ VOD ID が指定されていません")
    if st.button("📺 Videos ページに戻る"):
        st.switch_page("pages/1_videos.py")
    st.stop()

# --- DB接続とデータ取得 ---
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()

c.execute("SELECT id, title, category, created_at FROM vods WHERE id = ?", (vod_id,))
vod = c.fetchone()
if not vod:
    st.error("❌ 指定されたVODが存在しません")
    if st.button("📺 Videos ページに戻る"):
        st.switch_page("pages/1_videos.py")
    conn.close()
    st.stop()

vod_id, title, category, created_at = vod

c.execute("SELECT id, url, title, video_id FROM youtube_links WHERE vod_id = ? ORDER BY id", (vod_id,))
youtube_links = c.fetchall()

thumbnail_url = None
for link in youtube_links:
    if link[3]:
        thumbnail_url = f"https://img.youtube.com/vi/{link[3]}/maxresdefault.jpg"
        break

c.execute("SELECT id, title, created_at, thumbnail_url, (SELECT yl.video_id FROM youtube_links yl WHERE yl.vod_id = clips.vod_id AND yl.video_id IS NOT NULL LIMIT 1) as youtube_video_id FROM clips WHERE vod_id = ? ORDER BY created_at DESC", (vod_id,))
clips = c.fetchall()

conn.close()  # 一旦閉じる（必要時再接続）

# --- 削除処理関数群 ---

def delete_vod(vod_id):
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM youtube_links WHERE vod_id = ?", (vod_id,))
    c.execute("DELETE FROM vods WHERE id = ?", (vod_id,))
    conn.commit()
    conn.close()
    st.success("✅ VODを削除しました。")
    st.rerun()

def delete_youtube_link(link_id):
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM youtube_links WHERE id = ?", (link_id,))
    conn.commit()
    conn.close()
    st.success("YouTubeリンクを削除しました。")
    st.rerun()

# --- 編集モード切替関数 ---
def toggle_edit_mode():
    st.session_state.edit_mode = not st.session_state.edit_mode

# --- 戻るボタンとタイトル・編集切替 ---
col_back, col_title, col_admin = st.columns([1, 4, 1])

with col_back:
    if st.button("◀️ Videos一覧に戻る", use_container_width=False):
        st.switch_page("pages/1_videos.py")

with col_title:
    if st.session_state.edit_mode:
        st.markdown("### ✏️ VOD編集モード")
    else:
        st.markdown("### 📺 VOD詳細")

with col_admin:
    if st.session_state.is_admin:
        st.markdown('<span class="admin-badge">🔐 編集者</span>', unsafe_allow_html=True)
        if st.session_state.edit_mode:
            st.button("👁️ 表示モード", key="view_mode_btn", on_click=toggle_edit_mode)
        else:
            st.button("✏️ 編集モード", key="edit_mode_btn", on_click=toggle_edit_mode)

# --- 編集モードフォーム ---
if st.session_state.is_admin and st.session_state.edit_mode:
    with st.form("edit_vod_form"):
        st.markdown("### 📝 VOD情報を編集")
        
        new_title = st.text_input("タイトル", value=title, max_chars=200)
        
        try:
            current_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").date()
        except:
            current_date = datetime.now().date()
        new_date = st.date_input("追加日", value=current_date)
        
        current_category = category or ""
        new_category = st.text_input("ゲームカテゴリ（| で区切って複数指定可能）", value=current_category)
        
        if st.form_submit_button("💾 変更を保存", use_container_width=True):
            conn = sqlite3.connect("vods.db", check_same_thread=False)
            c = conn.cursor()
            new_created_at = new_date.strftime("%Y-%m-%d") + " " + created_at.split(" ")[1] if " " in created_at else new_date.strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                UPDATE vods 
                SET title = ?, category = ?, created_at = ? 
                WHERE id = ?
            """, (new_title, new_category, new_created_at, vod_id))
            conn.commit()
            conn.close()
            st.success("✅ VOD情報を更新しました！")
            st.session_state.edit_mode = False
            st.rerun()

    # YouTubeリンク管理
    st.markdown("### 🔗 YouTubeリンク管理")
    
    # 新しいリンク追加
    with st.expander("➕ 新しいYouTubeリンクを追加", expanded=False):
        with st.form("add_youtube_link"):
            new_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
            new_link_title = st.text_input("リンクタイトル（省略可）")
            
            if st.form_submit_button("🔗 リンクを追加"):
                if new_url:
                    video_id = None
                    if "youtube.com/watch?v=" in new_url:
                        video_id = new_url.split("watch?v=")[1].split("&")[0]
                    elif "youtu.be/" in new_url:
                        video_id = new_url.split("youtu.be/")[1].split("?")[0]
                    
                    conn = sqlite3.connect("vods.db", check_same_thread=False)
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO youtube_links (vod_id, url, title, video_id)
                        VALUES (?, ?, ?, ?)
                    """, (vod_id, new_url, new_link_title, video_id))
                    conn.commit()
                    conn.close()
                    st.success("✅ YouTubeリンクを追加しました！")
                    st.rerun()
                else:
                    st.warning("⚠️ YouTubeのURLを入力してください。")

    # 既存リンクの削除ボタン
    if youtube_links:
        st.markdown("#### 🗑️ 既存リンクの削除")
        for link_id, url, link_title, video_id in youtube_links:
            display_title = link_title if link_title else url[:50] + "..."
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f'<div class="youtube-link-item">🔗 {display_title}</div>', unsafe_allow_html=True)
            with col2:
                st.button(
                    "🗑️", 
                    key=f"delete_link_{link_id}", 
                    help="削除", 
                    on_click=delete_youtube_link, 
                    args=(link_id,)
                )

    # 危険ゾーン（VOD削除）
    with st.expander("⚠️ 危険ゾーン - VOD削除", expanded=False):
        st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
        st.warning("⚠️ この操作は取り消せません。VODとすべての関連データが削除されます。")
        if st.checkbox("削除することを理解しました", key="delete_confirm"):
            st.button(
                "🗑️ VODを完全に削除", 
                key="delete_vod", 
                type="primary", 
                on_click=delete_vod, 
                args=(vod_id,)
            )
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # 通常の表示モード - Streamlitのネイティブなカラムレイアウトを使用
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # サムネイル表示を修正
        if thumbnail_url:
            st.image(
                thumbnail_url, 
                use_container_width=True
            )
        else:
            # サムネイルがない場合の表示
            st.markdown("""
            <div style="
                width: 100%;
                height: 300px;
                background-color: #f0f0f0;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 12px;
                border: 2px dashed #ccc;
                color: #666;
                font-size: 18px;
                margin-bottom: 16px;
            ">
                📺 サムネイル画像なし
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f'<div class="video-title">📺 {title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="video-date">📅 追加日: {created_at}</div>', unsafe_allow_html=True)
        
        if youtube_links:
            st.markdown('<div class="youtube-links">', unsafe_allow_html=True)
            for idx, (link_id, url, yt_title, video_id) in enumerate(youtube_links, 1):
                link_label = yt_title if yt_title else f"YouTubeリンク#{idx}"
                st.markdown(f'<a href="{url}" target="_blank" class="youtube-link">▶️ {link_label}</a>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if category:
            tags = [tag.strip() for tag in category.split("|") if tag.strip()]
            if tags:
                st.markdown('<div class="video-tags">', unsafe_allow_html=True)
                tags_html = ""
                for tag in tags:
                    tags_html += f'<span class="video-tag">🎮 {tag}</span>'
                st.markdown(tags_html, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="clips-section">', unsafe_allow_html=True)
        st.markdown('<div class="clips-header">✂️ Clips for this stream</div>', unsafe_allow_html=True)
        
        if clips:
            st.markdown(f"**{len(clips)}件** のクリップが見つかりました")
            
            for clip_id, clip_title, clip_created_at, clip_thumbnail_url, clip_youtube_video_id in clips:
                fav_key = f"clip_fav_{clip_id}"
                if fav_key not in st.session_state:
                    st.session_state[fav_key] = False
                
                # 横並びレイアウトのクリップカード
                st.markdown('<div class="clip-card">', unsafe_allow_html=True)
                
                # カード内のレイアウト
                col_thumb, col_info = st.columns([1, 2])
                
                with col_thumb:
                    # サムネイル表示
                    if clip_thumbnail_url and clip_thumbnail_url.strip():
                        st.image(clip_thumbnail_url, use_container_width=True)
                    elif clip_youtube_video_id and clip_youtube_video_id.strip():
                        youtube_thumbnail = f"https://img.youtube.com/vi/{clip_youtube_video_id}/mqdefault.jpg"
                        st.image(youtube_thumbnail, use_container_width=True)
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
                            📹
                        </div>
                        """, unsafe_allow_html=True)
                
                with col_info:
                    # タイトル
                    st.markdown(f'<div class="clip-title">{clip_title}</div>', unsafe_allow_html=True)
                    
                    # 日付をフォーマット
                    try:
                        formatted_date = datetime.strptime(clip_created_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    except:
                        formatted_date = clip_created_at
                    st.markdown(f'<div class="clip-meta">追加日: {formatted_date}</div>', unsafe_allow_html=True)
                    
                    # アクションボタン
                    col_fav, col_detail = st.columns([1, 2])
                    
                    with col_fav:
                        fav_icon = "★" if st.session_state[fav_key] else "☆"
                        if st.button(
                            fav_icon, 
                            key=f"fav_btn_{clip_id}",
                            help="お気に入りに追加/削除"
                        ):
                            st.session_state[fav_key] = not st.session_state[fav_key]
                            if st.session_state[fav_key]:
                                st.success(f"'{clip_title[:20]}...' をお気に入りに追加しました！")
                            else:
                                st.info(f"'{clip_title[:20]}...' をお気に入りから削除しました")
                            st.rerun()
                    
                    with col_detail:
                        if st.button(f"詳細を見る", key=f"clip_detail_btn_{clip_id}", use_container_width=True):
                            st.session_state['selected_clip_id'] = clip_id
                            st.switch_page("pages/4_clip_detail.py")
                
                st.markdown('</div>', unsafe_allow_html=True)  # clip-card終了
        else:
            st.info("📝 このVODに関連するクリップはまだありません")
        
        st.markdown('</div>', unsafe_allow_html=True)