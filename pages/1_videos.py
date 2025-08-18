# pages/1_videos.py (YouTube Live サムネイル対応版)

import streamlit as st
import sqlite3
from datetime import datetime
import sys, os
import re
import math
import requests
from urllib.parse import urlparse

# ページ設定 - デフォルトサイドバーを無効化
st.set_page_config(
    page_title="Videos - VOD Finder", 
    page_icon="📺", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 共通関数: YouTubeのvideo_idを抽出
def extract_youtube_video_id(url):
    """YouTubeのURLからvideo_idを抽出する改良版（ライブURL対応）"""
    if not url:
        return None
    
    # パターン1: https://www.youtube.com/watch?v=VIDEO_ID
    match = re.search(r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # パターン2: https://youtu.be/VIDEO_ID
    match = re.search(r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # パターン3: https://www.youtube.com/embed/VIDEO_ID
    match = re.search(r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # パターン4: https://www.youtube.com/live/VIDEO_ID (ライブ配信URL)
    match = re.search(r'(?:youtube\.com/live/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    return None

def get_platform_info(youtube_url, twitch_url):
    """URLからプラットフォーム情報を取得"""
    platforms = []
    
    # ニコニコ動画の判定（Twitch URLフィールドにniconicoが入力されている場合）
    if twitch_url and 'niconico' in twitch_url.lower():
        platforms.append(('niconico', '📹 ニコニコ'))
    
    return platforms

def is_youtube_live_url(url):
    """YouTubeのURLがライブ配信形式かを判定"""
    if not url:
        return False
    
    # ライブ配信の典型的なURLパターン
    live_patterns = [
        r'youtube\.com/live/',                    # https://www.youtube.com/live/VIDEO_ID
        r'youtube\.com/watch\?.*live_stream',     # ライブストリーム関連パラメータ
        r'youtube\.com/channel/.*/live',          # チャンネルライブページ
    ]
    
    for pattern in live_patterns:
        if re.search(pattern, url):
            return True
    
    return False

# YouTubeサムネイル取得の改良版関数
def get_youtube_thumbnail_urls(video_id):
    """
    YouTubeビデオIDから利用可能なサムネイルURLのリストを返す
    ライブ配信やプレミア公開にも対応した多段階フォールバック
    """
    if not video_id:
        return []
    
    thumbnail_urls = [
        # 高解像度サムネイル（通常動画用）
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",  # 1920x1080
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",      # 480x360
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",      # 320x180
        
        # ライブ配信・プレミア公開用の追加パターン
        f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",      # 640x480
        f"https://img.youtube.com/vi/{video_id}/hq720.jpg",          # 720p (一部動画)
        
        # 番号付きサムネイル（複数のサムネイルがある場合）
        f"https://img.youtube.com/vi/{video_id}/1.jpg",              # サムネイル1
        f"https://img.youtube.com/vi/{video_id}/2.jpg",              # サムネイル2
        f"https://img.youtube.com/vi/{video_id}/3.jpg",              # サムネイル3
        
        # 最後の手段
        f"https://img.youtube.com/vi/{video_id}/default.jpg"         # 120x90 (必ず存在)
    ]
    
    return thumbnail_urls

def check_thumbnail_exists(url):
    """
    サムネイルURLが有効かチェック（改良版）
    """
    try:
        response = requests.head(url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return response.status_code == 200 and 'image' in response.headers.get('content-type', '')
    except:
        return False

# 簡易版サムネイル表示（デバッグ用）
def display_simple_thumbnail(video_id, key=None):
    """
    シンプルなサムネイル表示（デバッグ用）
    """
    if not video_id:
        st.error("❌ Video ID が見つかりません")
        return
    
    # 基本的なサムネイルURLを試行
    urls_to_try = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg", 
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/default.jpg"
    ]
    
    st.write(f"🔍 Debug: Video ID = {video_id}")
    
    for i, url in enumerate(urls_to_try):
        st.write(f"📸 試行 {i+1}: {url}")
        try:
            st.image(url, use_container_width=True, caption=f"URL {i+1}")
            st.success(f"✅ 成功: {url}")
            return  # 最初に成功したものを表示して終了
        except Exception as e:
            st.warning(f"❌ 失敗: {str(e)}")
    
    st.error("❌ すべてのサムネイルURLが失敗しました")

# サムネイル表示用の改良された関数
def display_thumbnail_with_fallback(video_id, key=None):
    """
    Streamlit互換のフォールバック機能付きサムネイル表示（高さ統一版）
    """
    if not video_id:
        st.markdown('<div class="thumbnail-placeholder">📺 <br><i>サムネイル画像なし</i></div>', unsafe_allow_html=True)
        return
    
    thumbnail_urls = get_youtube_thumbnail_urls(video_id)
    
    # 最初に利用可能なサムネイルを見つける
    working_url = None
    for url in thumbnail_urls:
        try:
            # HEADリクエストで画像の存在を確認（タイムアウト短縮）
            response = requests.head(url, timeout=3)
            if response.status_code == 200:
                # Content-Typeが画像かチェック
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    working_url = url
                    break
        except:
            continue
    
    # 利用可能なサムネイルを表示（高さ統一）
    if working_url:
        # HTMLで高さを統一して表示
        st.markdown(f'''
        <div class="thumbnail-container">
            <img 
                src="{working_url}"
                class="thumbnail-image"
                alt="YouTube Thumbnail"
            />
        </div>
        ''', unsafe_allow_html=True)
    else:
        # すべてのURLが失敗した場合
        st.markdown('<div class="thumbnail-placeholder">📺 <br><i>サムネイル読み込みエラー<br>または未対応の動画形式</i></div>', unsafe_allow_html=True)

# データベース修復関数
def fix_youtube_video_ids():
    """既存のYouTubeリンクのvideo_idを修復"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # video_idがNULLまたは空のレコードを取得
    c.execute("SELECT id, url FROM youtube_links WHERE video_id IS NULL OR video_id = ''")
    records = c.fetchall()
    
    fixed_count = 0
    for record_id, url in records:
        video_id = extract_youtube_video_id(url)
        if video_id:
            c.execute("UPDATE youtube_links SET video_id = ? WHERE id = ?", (video_id, record_id))
            fixed_count += 1
    
    conn.commit()
    conn.close()
    return fixed_count

# VODとクリップの紐づけ修復関数
def fix_vod_clip_linking():
    """VODとクリップの紐づけを修復"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # 紐づけされていないクリップを取得
    c.execute("""
        SELECT c.id, c.vod_twitch_id 
        FROM clips c 
        WHERE c.vod_id IS NULL AND c.vod_twitch_id IS NOT NULL
    """)
    unlinked_clips = c.fetchall()
    
    linked_count = 0
    for clip_id, vod_twitch_id in unlinked_clips:
        # 対応するVODを検索
        c.execute("SELECT id FROM vods WHERE twitch_id = ?", (vod_twitch_id,))
        vod_result = c.fetchone()
        
        if vod_result:
            vod_id = vod_result[0]
            c.execute("UPDATE clips SET vod_id = ? WHERE id = ?", (vod_id, clip_id))
            linked_count += 1
    
    conn.commit()
    conn.close()
    return linked_count

# ページネーション用のデータ取得関数（修正版）
def get_vods_with_pagination(search_query="", selected_category="すべて", date_filter=None, 
                            page=1, items_per_page=20):
    """ページネーション対応でVODを取得（Twitch URLも取得）"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # 基本クエリ（Twitch URLも取得）
    base_query = """
    SELECT v.id, v.title, v.category, v.created_at, 
           (SELECT yl.video_id 
            FROM youtube_links yl 
            WHERE yl.vod_id = v.id 
              AND yl.video_id IS NOT NULL 
              AND yl.video_id != '' 
            ORDER BY yl.id ASC 
            LIMIT 1) as youtube_video_id,
           (SELECT COUNT(*) 
            FROM clips c 
            WHERE c.vod_id = v.id) as clip_count,
           (SELECT yl.url 
            FROM youtube_links yl 
            WHERE yl.vod_id = v.id 
            ORDER BY yl.id ASC 
            LIMIT 1) as youtube_url,
           v.url as twitch_url
    FROM vods v
    """
    
    # 件数取得用クエリ
    count_query = "SELECT COUNT(*) FROM vods v"
    
    # WHERE句の構築
    where_clauses = []
    params = []
    
    if search_query:
        where_clauses.append("v.title LIKE ?")
        params.append(f"%{search_query}%")
    if selected_category and selected_category != "すべて":
        where_clauses.append("v.category LIKE ?")
        params.append(f"%{selected_category}%")
    if date_filter:
        where_clauses.append("date(v.created_at) = date(?)")
        params.append(date_filter.strftime("%Y-%m-%d"))
    
    if where_clauses:
        where_clause = " WHERE " + " AND ".join(where_clauses)
        base_query += where_clause
        count_query += where_clause
    
    # 総件数を取得
    c.execute(count_query, params)
    total_count = c.fetchone()[0]
    
    # ページング用のクエリを完成
    offset = (page - 1) * items_per_page
    paginated_query = base_query + " ORDER BY v.created_at DESC LIMIT ? OFFSET ?"
    
    # データを取得
    c.execute(paginated_query, params + [items_per_page, offset])
    rows = c.fetchall()
    
    conn.close()
    return rows, total_count

# デフォルトのページナビゲーションを完全に非表示にするCSS
st.markdown("""
<style>
    /* デフォルトのページセレクトボックスを完全に削除 */
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }
    
    /* ページセレクタのコンテナ全体を非表示 */
    section[data-testid="stSidebar"] > div > div:first-child {
        display: none !important;
    }
    
    /* Streamlitデフォルトナビゲーションのクラスを非表示 */
    .css-1d391kg, .css-1y0tads, .e1fqkh3o0, .css-17lntkn {
        display: none !important;
    }
    
    /* カード形式のスタイリング（コンパクト版） */
    .vod-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .vod-card:hover {
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
        transition: box-shadow 0.3s ease;
    }
    
    .vod-title {
        font-size: 15px;
        font-weight: bold;
        margin-bottom: 6px;
        color: #1f77b4;
        text-decoration: none;
        line-height: 1.0;
        word-wrap: break-word;
        overflow-wrap: break-word;
        height: 6.0em;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    .vod-meta {
        color: #666;
        font-size: 12px;
        margin-bottom: 6px;
    }
    
    .vod-tags {
        margin-top: 6px;
        margin-bottom: 4px;
    }
    
    .vod-tag {
        display: inline-block;
        background-color: #f0f2f6;
        color: #262730;
        padding: 2px 6px;
        margin: 1px 2px 1px 0;
        border-radius: 3px;
        font-size: 10px;
    }
    
    /* YouTubeインジケーター */
    .youtube-indicator {
        display: inline-block;
        background-color: #ff0000;
        color: white;
        padding: 2px 6px;
        margin: 1px 2px 1px 0;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    }
    
    /* ニコニコ動画インジケーター */
    .niconico-indicator {
        display: inline-block;
        background-color: #252525;
        color: white;
        padding: 2px 6px;
        margin: 1px 2px 1px 0;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    }
    
    /* サムネイルコンテナの改良（高さ統一版） */
    .thumbnail-container {
        width: 100%;
        height: 210px;
        position: relative;
        overflow: hidden;
        border-radius: 4px;
        background-color: #f8f9fa;
        margin-bottom: 8px;
    }
    
    .thumbnail-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        transition: opacity 0.3s ease;
    }
    
    .thumbnail-image:hover {
        opacity: 0.9;
    }
    
    /* Streamlitデフォルトの画像コンテナを調整 */
    .stImage > div {
        height: 210px !important;
    }
    
    .stImage img {
        height: 210px !important;
        object-fit: cover !important;
    }
    
    /* ページネーションのスタイル */
    .pagination-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
        gap: 10px;
    }
    
    .pagination-info {
        background-color: #f8f9fa;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        color: #495057;
        border: 1px solid #e9ecef;
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
        width: 100%;
        height: 210px;
        background-color: #f0f0f0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        border: 2px dashed #ccc;
        color: #666;
        font-size: 14px;
        margin-bottom: 8px;
        text-align: center;
        line-height: 1.4;
    }
    
    .fix-button {
        background-color: #ffc107;
        color: #212529;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# サイドバー表示（修正版）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from app.components.sidebar import show_sidebar, safe_navigation
    
    # 安全なナビゲーション処理を実行
    safe_navigation()
    
    # サイドバーを表示
    show_sidebar()
except ImportError as e:
    st.error(f"サイドバーの読み込みに失敗しました: {e}")
    # サイドバーが利用できない場合の代替ナビゲーション
    st.sidebar.title("ナビゲーション")
    if st.sidebar.button("メインページ"):
        st.switch_page("main.py")

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ページネーション状態の初期化
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# メインコンテンツ開始
col_title, col_admin = st.columns([3, 1])

with col_title:
    st.title("📺 Videos")

# 管理者状態の表示
with col_admin:
    if st.session_state.is_admin:
        st.markdown('<div class="admin-badge">🔐 編集者モード</div>', unsafe_allow_html=True)
    else:
        if st.button("🔒 編集者ログイン", key="login_link"):
            try:
                st.switch_page("pages/6_login.py")
            except Exception as e:
                st.error(f"ページ遷移エラー: {e}")

# 管理者パネル（修復機能追加）
if st.session_state.is_admin:
    with st.expander("🛠️ 管理者メニュー", expanded=False):
        col_admin1, col_admin2, col_admin3 = st.columns(3)
        
        with col_admin1:
            if st.button("➕ 新しいVODを追加", key="add_vod"):
                try:
                    st.switch_page("pages/7_add_vod.py")
                except Exception as e:
                    st.error(f"ページ遷移エラー: {e}")
        
        with col_admin2:
            if st.button("🔧 サムネイル修復", key="fix_thumbnails", help="YouTubeのvideo_idを再抽出"):
                with st.spinner("修復中..."):
                    fixed = fix_youtube_video_ids()
                st.success(f"✅ {fixed}件のvideo_idを修復しました")
                st.rerun()
        
        with col_admin3:
            if st.button("🔗 クリップ紐づけ修復", key="fix_linking", help="VODとクリップの紐づけを修復"):
                with st.spinner("紐づけ修復中..."):
                    linked = fix_vod_clip_linking()
                st.success(f"✅ {linked}件のクリップを紐づけしました")
                st.rerun()
        
        # ログアウトボタンは別行に
        st.markdown("---")
        if st.button("🔓 ログアウト", key="logout"):
            st.session_state.is_admin = False
            st.success("ログアウトしました。")
            st.rerun()

# DB接続（カテゴリ取得用）
conn = sqlite3.connect("vods.db", check_same_thread=False)
c = conn.cursor()

# ----------------------------- フィルタ部分 -----------------------------
st.markdown("---")
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # サイドバーの検索クエリを優先
    default_search = st.session_state.get('search_query', '')
    search_query = st.text_input("🔍 タイトル検索", value=default_search, placeholder="タイトルやキーワードで検索...")
    # 検索クエリをクリア
    if 'search_query' in st.session_state:
        del st.session_state['search_query']

with col2:
    date_filter = st.date_input("📅 日付で絞り込み", value=None)

with col3:
    # カテゴリ取得
    c.execute("SELECT DISTINCT category FROM vods WHERE category IS NOT NULL")
    categories_raw = [row[0] for row in c.fetchall() if row[0]]
    categories = set()
    for cat in categories_raw:
        categories.update([c.strip() for c in cat.split("|") if c.strip()])
    selected_category = st.selectbox("🎮 ゲームカテゴリ", ["すべて"] + sorted(categories))

with col4:
    # 1ページあたりの表示件数を選択
    items_per_page = st.selectbox("📄 表示件数", [12, 20, 40, 60], index=1)

conn.close()

# フィルタが変更された場合は1ページ目に戻る
current_filters = {
    'search': search_query,
    'category': selected_category,
    'date': date_filter,
    'items_per_page': items_per_page
}

if 'previous_filters' not in st.session_state:
    st.session_state.previous_filters = current_filters
elif st.session_state.previous_filters != current_filters:
    st.session_state.current_page = 1
    st.session_state.previous_filters = current_filters

# ----------------------------- 削除処理 -----------------------------
if st.session_state.is_admin and 'delete_vod_id' in st.session_state:
    vod_id = st.session_state['delete_vod_id']
    del st.session_state['delete_vod_id']
    
    # 削除実行
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM vods WHERE id = ?", (vod_id,))
    conn.commit()
    conn.close()
    st.success(f"VOD（ID: {vod_id}）を削除しました。")
    st.rerun()

# ----------------------------- データ取得と表示 -----------------------------
# ページネーション対応でデータを取得
rows, total_count = get_vods_with_pagination(
    search_query=search_query,
    selected_category=selected_category,
    date_filter=date_filter,
    page=st.session_state.current_page,
    items_per_page=items_per_page
)

if total_count == 0:
    st.info("🔍 条件に一致するVODが見つかりませんでした。")
else:
    # ページネーション情報の計算
    total_pages = math.ceil(total_count / items_per_page)
    start_item = (st.session_state.current_page - 1) * items_per_page + 1
    end_item = min(st.session_state.current_page * items_per_page, total_count)
    
    # 結果情報の表示
    st.markdown(f"**{total_count}件中 {start_item}-{end_item}件目** を表示 (ページ {st.session_state.current_page}/{total_pages})")
    
    # ページネーションコントロール（上部）
    if total_pages > 1:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            if st.session_state.current_page > 1:
                if st.button("⏮️ 最初", use_container_width=True):
                    st.session_state.current_page = 1
                    st.rerun()
        
        with col2:
            if st.session_state.current_page > 1:
                if st.button("◀️ 前へ", use_container_width=True):
                    st.session_state.current_page -= 1
                    st.rerun()
        
        with col3:
            st.markdown(f'<div class="pagination-info" style="text-align: center; padding: 8px;">{st.session_state.current_page} / {total_pages}</div>', unsafe_allow_html=True)
        
        with col4:
            if st.session_state.current_page < total_pages:
                if st.button("次へ ▶️", use_container_width=True):
                    st.session_state.current_page += 1
                    st.rerun()
        
        with col5:
            if st.session_state.current_page < total_pages:
                if st.button("最後 ⏭️", use_container_width=True):
                    st.session_state.current_page = total_pages
                    st.rerun()
    
    st.markdown("---")
    
    # カード形式で表示（4列レイアウト）
    cols = st.columns(4)
    
    for idx, row in enumerate(rows):
        vid, title, category, created_at, youtube_video_id, clip_count, youtube_url, twitch_url = row
        
        # タイトルを適切な長さに制限
        display_title = title if len(title) <= 45 else title[:45] + "..."
        
        with cols[idx % 4]:
            # 改良されたサムネイル表示
            display_thumbnail_with_fallback(youtube_video_id, key=f"vid_{vid}_{idx}")
            
            # カードのHTMLを作成（サムネイル下部）
            card_html = f"""
            <div class="vod-card">
                <div class="vod-title">{display_title}</div>
                <div class="vod-meta">📅 {created_at}</div>
                <div class="vod-meta">✂️ クリップ: {clip_count}件</div>
            """
            
            # プラットフォーム情報を取得
            platforms = get_platform_info(youtube_url, twitch_url)
            
            # ライブ配信の判定（YouTubeのURLパターンで判定）
            is_live = is_youtube_live_url(youtube_url) if youtube_url else False
            
            # タグ表示部分（プラットフォームインジケーターとゲームタグを同じ行に）
            if category or platforms or is_live:
                card_html += '<div class="vod-tags">'
                
                # LIVEインジケーターを最初に表示（YouTube Live判定）
                if is_live:
                    card_html += '<span class="youtube-indicator">▶ YouTube</span>'
                
                # その他のプラットフォームインジケーターを表示
                for platform_id, platform_label in platforms:
                    if platform_id == 'niconico':
                        card_html += '<span class="niconico-indicator">📹 ニコニコ</span>'
                
                # カテゴリタグの表示
                if category:
                    tags = [tag.strip() for tag in category.split("|") if tag.strip()]
                    # プラットフォームまたはLIVEがある場合は1つ、ない場合は2つまで表示
                    max_tags = 1 if (platforms or is_live) else 2
                    for tag in tags[:max_tags]:
                        card_html += f'<span class="vod-tag">🎮 {tag}</span>'
                    if len(tags) > max_tags:
                        card_html += f'<span class="vod-tag">+{len(tags)-max_tags}</span>'
                
                card_html += '</div>'
            
            card_html += "</div>"
            
            # カードを表示
            st.markdown(card_html, unsafe_allow_html=True)
            
            # ボタンの表示（詳細ボタンのみ）
            if st.button("詳細を見る", key=f"detail_{vid}", use_container_width=True):
                st.session_state['selected_vod_id'] = vid
                try:
                    st.switch_page("pages/2_video_detail.py")
                except Exception as e:
                    st.error(f"ページ遷移エラー: {e}")
            
            st.markdown("<br>", unsafe_allow_html=True)

    # ページネーションコントロール（下部）
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            if st.session_state.current_page > 1:
                if st.button("⏮️ 最初", key="first_bottom", use_container_width=True):
                    st.session_state.current_page = 1
                    st.rerun()
        
        with col2:
            if st.session_state.current_page > 1:
                if st.button("◀️ 前へ", key="prev_bottom", use_container_width=True):
                    st.session_state.current_page -= 1
                    st.rerun()
        
        with col3:
            st.markdown(f'<div class="page-info" style="text-align: center; padding: 8px;">ページ {st.session_state.current_page} / {total_pages} (全{total_count}件)</div>', unsafe_allow_html=True)
        
        with col4:
            if st.session_state.current_page < total_pages:
                if st.button("次へ ▶️", key="next_bottom", use_container_width=True):
                    st.session_state.current_page += 1
                    st.rerun()
        
        with col5:
            if st.session_state.current_page < total_pages:
                if st.button("最後 ⏭️", key="last_bottom", use_container_width=True):
                    st.session_state.current_page = total_pages
                    st.rerun()