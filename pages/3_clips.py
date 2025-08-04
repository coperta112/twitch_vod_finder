# pages/3_clips.py

import streamlit as st
import sqlite3
import math
from datetime import datetime
import sys, os

# ページ設定 - デフォルトサイドバーを無効化
st.set_page_config(
    page_title="Clips - VOD Finder", 
    page_icon="✂️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# デフォルトのページナビゲーションを非表示にするCSS
st.markdown("""
<style>
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }
    
    /* カード形式のスタイリング（コンパクト版） */
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
    
    .clip-tags {
        margin-top: 6px;
        margin-bottom: 4px;
    }
    
    .clip-tag {
        display: inline-block;
        background-color: #ffe0e0;
        color: #cc4444;
        padding: 2px 6px;
        margin: 1px 2px 1px 0;
        border-radius: 3px;
        font-size: 10px;
    }
    
    /* ページネーション */
    .pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
        gap: 10px;
    }
    
    .page-info {
        color: #666;
        font-size: 14px;
    }
    
    /* 管理者メニューのスタイル */
    .admin-panel {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 20px;
    }
    
    .admin-badge {
        background-color: #28a745;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .thumbnail-placeholder {
        height: 120px;
        background-color: #ffe0e0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        color: #cc4444;
        font-size: 14px;
        margin-bottom: 8px;
    }
    
    .thumbnail-no-vod {
        height: 120px;
        background-color: #f5f5f5;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        border: 2px dashed #ccc;
        font-size: 14px;
        color: #999;
        margin-bottom: 8px;
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

# メインタイトル
col_title, col_admin = st.columns([3, 1])
with col_title:
    st.title("✂️ Clips")

# 管理者状態の表示
with col_admin:
    if st.session_state.is_admin:
        st.markdown('<div class="admin-badge">🔐 編集者モード</div>', unsafe_allow_html=True)
    else:
        if st.button("🔒 編集者ログイン", key="login_link"):
            st.switch_page("pages/6_login.py")

# 管理者パネル
if st.session_state.is_admin:
    with st.expander("🛠️ 管理者メニュー", expanded=False):
        col_admin1, col_admin2 = st.columns(2)
        
        with col_admin1:
            if st.button("➕ 新しいクリップを追加", key="add_clip"):
                st.switch_page("pages/8_add_clip.py")
        
        with col_admin2:
            if st.button("🔓 ログアウト", key="logout"):
                st.session_state.is_admin = False
                st.success("ログアウトしました。")
                st.rerun()

# DB接続
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()

# ----------------------------- フィルタ部分 -----------------------------
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # サイドバーの検索クエリを優先
    default_search = st.session_state.get('search_query', '')
    search_query = st.text_input("🔍 クリップ検索", value=default_search, placeholder="クリップタイトルで検索...")
    # 検索クエリをクリア
    if 'search_query' in st.session_state:
        del st.session_state['search_query']

with col2:
    date_filter = st.date_input("📅 日付で絞り込み", value=None)

with col3:
    # VODタイトルでの絞り込み
    c.execute("SELECT DISTINCT v.title FROM clips c JOIN vods v ON c.vod_id = v.id ORDER BY v.title")
    vod_titles = [row[0] for row in c.fetchall() if row[0]]
    selected_vod = st.selectbox("📺 元VOD", ["すべて"] + vod_titles)

with col4:
    # VOD接続状態での絞り込み
    connection_filter = st.selectbox("🔗 接続状態", ["すべて", "接続済み", "未接続"])

# ----------------------------- クエリ構築 -----------------------------
# クリップとサムネイル情報を取得するクエリに変更
query = """
SELECT c.id, c.vod_id, c.title, c.created_at, c.thumbnail_url, v.title as vod_title, v.category,
       (SELECT yl.video_id FROM youtube_links yl WHERE yl.vod_id = c.vod_id AND yl.video_id IS NOT NULL LIMIT 1) as youtube_video_id
FROM clips c 
LEFT JOIN vods v ON c.vod_id = v.id
"""
where_clauses = []
params = []

if search_query:
    where_clauses.append("c.title LIKE ?")
    params.append(f"%{search_query}%")
if selected_vod and selected_vod != "すべて":
    where_clauses.append("v.title = ?")
    params.append(selected_vod)
if date_filter:
    where_clauses.append("date(c.created_at) = date(?)")
    params.append(date_filter.strftime("%Y-%m-%d"))
if connection_filter == "接続済み":
    where_clauses.append("c.vod_id IS NOT NULL")
elif connection_filter == "未接続":
    where_clauses.append("c.vod_id IS NULL")

if where_clauses:
    query += " WHERE " + " AND ".join(where_clauses)
query += " ORDER BY c.created_at DESC"

# 全件数取得
c.execute(query, params)
all_clips = c.fetchall()

if not all_clips:
    st.info("🔍 条件に一致するクリップが見つかりませんでした。")
    conn.close()
else:
    # ----------------------------- ページネーション設定 -----------------------------
    PER_PAGE = 40
    total_clips = len(all_clips)
    total_pages = math.ceil(total_clips / PER_PAGE)
    
    # ページ選択
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if total_pages > 1:
            page = st.number_input(
                "ページを選択", 
                min_value=1, 
                max_value=total_pages, 
                value=st.session_state.get('clips_page', 1), 
                step=1,
                help=f"全{total_pages}ページ（{total_clips}件のクリップ）"
            )
            st.session_state['clips_page'] = page
        else:
            page = 1
    
    # ページング処理
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    clips_page = all_clips[start:end]
    
    # ページ情報表示
    st.markdown(f"**{total_clips}件** のクリップが見つかりました（{page}/{total_pages}ページ目を表示中）")
    st.markdown("---")
    
    # ----------------------------- クリップ一覧表示（カード形式） -----------------------------
    # 4列レイアウト
    cols = st.columns(4)
    
    for idx, row in enumerate(clips_page):
        clip_id, vod_id, clip_title, created_at, thumbnail_url_clip, vod_title, category, youtube_video_id = row
        
        with cols[idx % 4]:
            # サムネイル画像を最初に表示
            thumbnail_displayed = False
            
            # 1. クリップ自体のサムネイルがある場合
            if thumbnail_url_clip:
                try:
                    st.image(thumbnail_url_clip, use_container_width=True)
                    thumbnail_displayed = True
                except:
                    pass
            
            # 2. クリップにサムネイルがない場合、YouTubeサムネイルを試す
            if not thumbnail_displayed and youtube_video_id:
                try:
                    st.image(f"https://img.youtube.com/vi/{youtube_video_id}/mqdefault.jpg", use_container_width=True)
                    thumbnail_displayed = True
                except:
                    pass
            
            # 3. どちらもない場合のプレースホルダー
            if not thumbnail_displayed:
                if vod_id:
                    # VODに接続されているがサムネイルがない場合
                    st.markdown('<div class="thumbnail-placeholder">✂️ <i>サムネイル取得中...</i></div>', unsafe_allow_html=True)
                else:
                    # VOD未接続の場合
                    st.markdown('<div class="thumbnail-no-vod"><div>⚠️</div><div><i>VOD未接続</i></div></div>', unsafe_allow_html=True)
            
            # カードのHTMLを作成（サムネイル下部）
            # タイトルを適切な長さに制限
            display_title = clip_title if len(clip_title) <= 45 else clip_title[:45] + "..."
            
            card_html = f"""
            <div class="clip-card">
                <div class="clip-title">{display_title}</div>
                <div class="clip-meta">📅 {created_at}</div>
            """
            
            # VODタイトルとカテゴリタグの表示
            if vod_title:
                # VODタイトルを短縮表示
                short_vod_title = vod_title if len(vod_title) <= 20 else vod_title[:20] + "..."
                card_html += f'<div class="clip-meta">📺 {short_vod_title}</div>'
                
                # カテゴリタグの表示（最大2つまで）
                if category:
                    tags = [tag.strip() for tag in category.split("|") if tag.strip()]
                    card_html += '<div class="clip-tags">'
                    for tag in tags[:2]:  # 最大2つのタグのみ表示
                        card_html += f'<span class="clip-tag">🎮 {tag}</span>'
                    if len(tags) > 2:
                        card_html += f'<span class="clip-tag">+{len(tags)-2}</span>'
                    card_html += '</div>'
            
            card_html += "</div>"
            
            # カードを表示
            st.markdown(card_html, unsafe_allow_html=True)
            
            # 詳細ページへのリンク
            if st.button(f"詳細を見る", key=f"clip_detail_{clip_id}", use_container_width=True):
                # 詳細ページに遷移（clipのIDをsession_stateに保存）
                st.session_state['selected_clip_id'] = clip_id
                st.switch_page("pages/4_clip_detail.py")
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    # ----------------------------- ページネーション表示 -----------------------------
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            if page > 1:
                if st.button("⏮️ 最初", use_container_width=True):
                    st.session_state['clips_page'] = 1
                    st.rerun()
        
        with col2:
            if page > 1:
                if st.button("◀️ 前へ", use_container_width=True):
                    st.session_state['clips_page'] = page - 1
                    st.rerun()
        
        with col3:
            st.markdown(f'<div class="page-info" style="text-align: center; padding: 8px;">{page} / {total_pages}</div>', unsafe_allow_html=True)
        
        with col4:
            if page < total_pages:
                if st.button("次へ ▶️", use_container_width=True):
                    st.session_state['clips_page'] = page + 1
                    st.rerun()
        
        with col5:
            if page < total_pages:
                if st.button("最後 ⏭️", use_container_width=True):
                    st.session_state['clips_page'] = total_pages
                    st.rerun()

conn.close()