# メインエントリーポイント: main.py (修正版)
import streamlit as st
import sys
import os
import sqlite3
from datetime import datetime

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# データ同期管理（修正版）
from app.utils.update_manager import (
    refresh_data, 
    get_database_stats, 
    clear_cache, 
    add_sidebar_sync_controls,
    check_api_configuration,
    show_config_guide,
    test_twitch_connection
)

# ページ設定 - デフォルトのサイドバーを無効化
st.set_page_config(
    page_title="配信アーカイブ共有サイト",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"  # デフォルトのサイドバーを非表示
)

# 修正されたCSSとTwitchボタン部分
st.markdown("""
<style>
    .stAppDeployButton {
        display: none;
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem;
    }
    
    /* デフォルトのページナビゲーションを完全に非表示 */
    section[data-testid="stSidebar"] .stSelectbox {
        display: none !important;
    }
    
    /* デフォルトのページリストを非表示 */
    section[data-testid="stSidebar"] ul {
        display: none !important;
    }
    
    /* ページナビゲーション全体を非表示 */
    section[data-testid="stSidebar"] nav {
        display: none !important;
    }
    
    /* ページセレクタのコンテナを非表示 */
    section[data-testid="stSidebar"] > div > div:first-child {
        display: none !important;
    }
    
    /* Streamlitのデフォルトナビゲーションクラスを非表示 */
    .css-1d391kg, .css-1y0tads, .e1fqkh3o0, .css-17lntkn {
        display: none !important;
    }
    
    /* セレクトボックス全般を非表示 */
    .stSelectbox > div > div > div {
        display: none !important;
    }
    
    /* Twitchボタンを右上に固定（修正版） */
    .twitch-button-container {
        position: fixed;
        top: 20px;
        right: 30px;
        z-index: 9999 !important;  /* より高いz-indexに設定 */
        max-width: 200px;
        pointer-events: auto;  /* クリックイベントを有効化 */
    }
    
    .twitch-button {
        background: linear-gradient(135deg, #9146ff, #772ce8);
        color: white !important;
        padding: 10px 18px;
        border-radius: 20px;
        text-decoration: none !important;
        font-weight: bold;
        font-size: 13px;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(145, 70, 255, 0.3);
        transition: all 0.3s ease;
        border: none;
        white-space: nowrap;
        width: 100%;
        text-align: center;
        box-sizing: border-box;
        cursor: pointer !important;  /* カーソルを強制的にポインターに */
        pointer-events: auto !important;  /* クリックイベントを明示的に有効化 */
        position: relative;  /* z-indexを有効にするため */
        z-index: 10000 !important;  /* 最上位に配置 */
    }
    
    .twitch-button:hover {
        background: linear-gradient(135deg, #772ce8, #5c2099);
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(145, 70, 255, 0.4);
        color: white !important;
        text-decoration: none !important;
    }
    
    .twitch-button:visited {
        color: white !important;
    }
    
    .twitch-button:active {
        color: white !important;
        transform: translateY(0px);  /* クリック時の視覚的フィードバック */
    }
    
    /* Streamlit要素との重複を避ける */
    .stApp > header {
        z-index: 1 !important;
    }
    
    .stApp > div {
        z-index: 1 !important;
    }
    
    /* レスポンシブ対応 */
    @media (max-width: 768px) {
        .twitch-button-container {
            position: fixed;
            top: 15px;
            right: 15px;
            max-width: 150px;
        }
        
        .twitch-button {
            font-size: 12px;
            padding: 8px 14px;
        }
    }
    
    @media (max-width: 480px) {
        .twitch-button-container {
            position: fixed;
            top: 10px;
            right: 10px;
            max-width: 120px;
        }
        
        .twitch-button {
            font-size: 11px;
            padding: 6px 12px;
            border-radius: 15px;
        }
    }
    
    /* メインコンテンツエリアに余白を追加（ボタンとの重複回避） */
    .main > div {
        padding-top: 10px;
    }
    
    /* Streamlitのヘッダー部分との重複を避ける */
    header[data-testid="stHeader"] {
        background: transparent;
        z-index: 1 !important;
    }
    
    /* 更新ボタン用スタイル */

    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .stat-number {
        font-size: 2.2em;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 8px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .stat-label {
        color: #666;
        font-size: 0.95em;
        font-weight: 500;
    }
    
    .last-update {
        color: #666;
        font-size: 0.85em;
        margin-top: 10px;
        font-style: italic;
    }
    
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-ok { background-color: #28a745; }
    .status-warning { background-color: #ffc107; }
    .status-error { background-color: #dc3545; }
</style>

<script>
// JavaScriptでクリックイベントを強制的に有効化
document.addEventListener('DOMContentLoaded', function() {
    function ensureTwitchButtonWorks() {
        const twitchButton = document.querySelector('.twitch-button');
        if (twitchButton) {
            // 既存のイベントリスナーをクリア
            twitchButton.onclick = null;
            
            // 新しいクリックイベントを追加
            twitchButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const url = this.getAttribute('href');
                if (url) {
                    window.open(url, '_blank', 'noopener,noreferrer');
                }
                
                // デバッグ用
                console.log('Twitch button clicked:', url);
            }, true);
            
            // マウスオーバーイベントも追加（動作確認用）
            twitchButton.addEventListener('mouseover', function() {
                console.log('Twitch button hover detected');
            });
        }
    }
    
    // 初期実行
    ensureTwitchButtonWorks();
    
    // Streamlitの再描画後にも実行
    setTimeout(ensureTwitchButtonWorks, 500);
    setInterval(ensureTwitchButtonWorks, 2000);
});
</script>
""", unsafe_allow_html=True)

# Twitchボタンを右上に配置（修正版 - JavaScriptでも動作するように）
twitch_url = "https://www.twitch.tv/midorokun"  # ← 適宜変更可
st.markdown(
    f'''
    <div class="twitch-button-container">
        <a href="{twitch_url}" target="_blank" class="twitch-button" 
           onclick="window.open('{twitch_url}', '_blank', 'noopener,noreferrer'); return false;">
            Twitch
        </a>
    </div>
    ''',
    unsafe_allow_html=True
)

# 手動更新機能（改良版）
def add_manual_update_section():
    """手動更新セクションを追加"""
    
    st.markdown('<div class="update-section">', unsafe_allow_html=True)
    
    # API設定状態チェック
    config_ok, config_msg = check_api_configuration()
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.markdown("### 🔄 データ更新")
        
        # API設定状態表示
        if config_ok:
            st.markdown('<span class="status-indicator status-ok"></span>**API設定**: 正常', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-error"></span>**API設定**: エラー', unsafe_allow_html=True)
            st.caption(config_msg)
        
        # 最終更新時刻の表示
        if "last_manual_refresh" not in st.session_state:
            st.session_state.last_manual_refresh = datetime.now()
        
        last_update = st.session_state.last_manual_refresh.strftime('%Y-%m-%d %H:%M:%S')
        st.markdown(f'<div class="last-update">最終更新: {last_update}</div>', unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Twitch同期", key="manual_refresh_main", use_container_width=True, type="primary", disabled=not config_ok):
            if config_ok:
                with st.spinner("📡 Twitchからデータを同期中..."):
                    result = refresh_data()

                if result.get("success"):
                    st.success("✅ データを更新しました！")
                    
                    # 結果詳細を表示
                    if "result" in result:
                        st.info(f"📊 {result['result']}")
                    
                    # 統計キャッシュをクリア
                    get_database_stats.clear()
                    st.session_state.last_manual_refresh = datetime.now()
                    st.rerun()
                else:
                    st.error("❌ 更新に失敗しました")
                    error_msg = result.get("error", "不明なエラー")
                    st.caption(error_msg)
                    
                    # 設定エラーの場合はガイドを表示
                    if "設定" in error_msg or "API" in error_msg:
                        if st.expander("🔧 設定ヘルプ", expanded=True):
                            show_config_guide()
            else:
                st.error("API設定を完了してください")
    
    with col3:
        if st.button("🧪 接続テスト", key="test_connection_main", use_container_width=True):
            test_twitch_connection()
    
    with col4:
        if st.button("🗑️ キャッシュクリア", key="clear_cache_main", use_container_width=True):
            clear_cache()
            st.info("🔄 キャッシュをクリアしました")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# データベース統計表示（改良版）
def show_database_overview():
    """データベース概要を表示"""
    
    st.markdown("### 📊 データベース概要")
    
    stats = get_database_stats()
    
    if "error" in stats:
        st.error(f"❌ データベース接続エラー: {stats['error']}")
        
        # データベースファイルの存在確認
        if not os.path.exists("vods.db"):
            st.warning("⚠️ データベースファイルが存在しません。初回同期を実行してください。")
        
        return
    
    # 統計カードを表示
    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    
    # メインの統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-number">{stats["vods_count"]}</div>
            <div class="stat-label">📺 配信動画</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-number">{stats["clips_count"]}</div>
            <div class="stat-label">✂️ クリップ</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-number">{stats["youtube_count"]}</div>
            <div class="stat-label">🎥 YouTubeリンク</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-number">{stats["total_items"]}</div>
            <div class="stat-label">📚 総コンテンツ数</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 今日の追加数
    if stats["today_vods"] > 0 or stats["today_clips"] > 0:
        st.success(f"🆕 本日追加: VOD {stats['today_vods']}件、クリップ {stats['today_clips']}件")
    
    # 最新更新情報
    col1, col2 = st.columns(2)
    
    with col1:
        if stats["latest_vod"]:
            vod_time = stats['latest_vod']
            try:
                # 日時フォーマットを調整
                if 'T' in vod_time:
                    vod_dt = datetime.fromisoformat(vod_time.replace('Z', '+00:00'))
                    formatted_time = vod_dt.strftime('%m/%d %H:%M')
                else:
                    formatted_time = vod_time
                st.caption(f"📺 最新VOD: {formatted_time}")
            except:
                st.caption(f"📺 最新VOD: {vod_time}")
        else:
            st.caption("📺 VODデータがありません")
    
    with col2:
        if stats["latest_clip"]:
            clip_time = stats['latest_clip']
            try:
                if 'T' in clip_time:
                    clip_dt = datetime.fromisoformat(clip_time.replace('Z', '+00:00'))
                    formatted_time = clip_dt.strftime('%m/%d %H:%M')
                else:
                    formatted_time = clip_time
                st.caption(f"✂️ 最新クリップ: {formatted_time}")
            except:
                st.caption(f"✂️ 最新クリップ: {clip_time}")
        else:
            st.caption("✂️ クリップデータがありません")

# 共通サイドバー関数（改良版）
def show_sidebar():
    with st.sidebar:
        st.title("🎥 VOD Finder")
        
        # Twitch同期コントロール
        add_sidebar_sync_controls()
        
        st.markdown("---")
        
        # ナビゲーション
        st.markdown("### 📍 ナビゲーション")
        
        # ページリンク
        pages = {
            "🏠 Home": "main.py",
            "📺 Videos": "pages/1_videos.py", 
            "✂️ Clips": "pages/3_clips.py",
            "⭐ Favorites": "pages/5_favorites.py",
            "🔑 Login": "pages/6_login.py"
        }
        
        for page_name, page_file in pages.items():
            if st.button(page_name, use_container_width=True):
                st.switch_page(page_file)
        
        st.markdown("---")
        
        # 検索ボックス
        st.markdown("### 🔍 クイック検索")
        search_query = st.text_input("検索", placeholder="タイトルやゲーム名で検索...", label_visibility="collapsed")
        if search_query:
            st.session_state['search_query'] = search_query
            st.switch_page("pages/1_videos.py")
        
        # 認証状態表示
        st.markdown("---")
        st.markdown("### 👤 ユーザー状態")
        
        if st.session_state.get("is_admin", False):
            st.success("✅ 編集者ログイン中")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("VOD追加", use_container_width=True):
                    st.switch_page("pages/7_add_vod.py")
            with col2:
                if st.button("Clip追加", use_container_width=True):
                    st.switch_page("pages/8_add_clip.py")
            
            if st.button("🚪 ログアウト", use_container_width=True, type="secondary"):
                st.session_state["is_admin"] = False
                st.success("ログアウトしました")
                st.rerun()
        else:
            st.info("🔒 閲覧モード")
            if st.button("🔑 編集者ログイン", use_container_width=True):
                st.switch_page("pages/6_login.py")

# サイドバー表示
show_sidebar()

# メインコンテンツ（ホームページ）
st.title("🎥 配信アーカイブ共有サイト")
st.markdown("---")

# 手動更新セクション
add_manual_update_section()

# データベース概要
show_database_overview()

# サイト紹介
st.markdown("""
### 🔍 このサイトについて
このサイトは、みどりくんの**配信アーカイブ（VOD）やクリップ動画**を整理・共有するための非公式データベースです。  
個人制作のため、抜けや漏れがある可能性があります。ご承知おきください。

#### 📁 主な機能
- **📺 Videos**：配信アーカイブの一覧・検索・視聴
- **✂️ Clips**：切り抜き動画の一覧・検索・視聴  
- **⭐ Favorites**：お気に入りに追加したクリップ管理
- **🔑 Login**：編集者用ログイン（データ追加・編集）

#### 🎯 使い方
1. **左サイドバー**から各ページに移動
2. **検索ボックス**でコンテンツを検索
3. **お気に入り機能**でクリップを保存(サイトを離れるとリセットされます。)
4. **編集者権限**でデータの追加・修正

#### 🔄 データ更新
- データは**Twitch API**から自動取得
- **手動更新ボタン**で最新データを同期
- **接続テスト**でAPI設定を確認
- **Youtubeリンクは手動で登録してます**
""")

# 操作ガイド
with st.expander("📖 詳細操作ガイド", expanded=False):
    st.markdown("""
    #### 🔧 初期設定（管理者向け）
    1. **Twitch Developer Console**でアプリケーションを作成
    2. **Client ID**と**Client Secret**を取得
    3. **`.env`ファイル**に設定情報を記入
    4. **接続テスト**で設定を確認
    
    #### 📱 日常の使い方
    1. **データ同期**：定期的に「Twitch同期」ボタンをクリック
    2. **動画検索**：Videosページで配信アーカイブを検索
    3. **クリップ視聴**：Clipsページで切り抜き動画を視聴
    4. **お気に入り**：気に入ったクリップを保存・管理
    
    #### ⚠️ トラブルシューティング
    - **同期エラー**：接続テストでAPI設定を確認
    - **データが古い**：手動で「Twitch同期」を実行
    - **表示異常**：「キャッシュクリア」を実行
    """)

# システム状態表示
if st.session_state.get("is_admin", False):
    with st.expander("🔧 システム情報（管理者用）", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**データベース**")
            if os.path.exists("vods.db"):
                db_size = os.path.getsize("vods.db") / 1024 / 1024  # MB
                st.caption(f"📁 ファイルサイズ: {db_size:.2f} MB")
                
                db_mtime = os.path.getmtime("vods.db")
                db_update = datetime.fromtimestamp(db_mtime)
                st.caption(f"🕒 最終変更: {db_update.strftime('%m/%d %H:%M')}")
            else:
                st.caption("❌ データベースファイルなし")
        
        with col2:
            st.markdown("**API設定**")
            config_ok, config_msg = check_api_configuration()
            if config_ok:
                st.caption("✅ 設定正常")
            else:
                st.caption("❌ 設定エラー")
                st.caption(config_msg)
        
        with col3:
            st.markdown("**セッション情報**")
            st.caption(f"🔑 管理者: {'有効' if st.session_state.get('is_admin') else '無効'}")
            if "last_manual_refresh" in st.session_state:
                last_refresh = st.session_state.last_manual_refresh
                st.caption(f"🔄 最終同期: {last_refresh.strftime('%H:%M')}")

# 認証状態の詳細表示
st.markdown("---")
if st.session_state.get("is_admin"):
    st.success("✅ 編集者としてログイン中です。")
    st.markdown("サイドバーから新しいVODやClipを追加できます。データの同期や管理機能をご利用ください。")
else:
    st.info("🔒 現在は閲覧モードです。")
    st.markdown("動画の検索・視聴・お気に入り機能をご利用いただけます。編集者権限が必要な場合はログインしてください。")

# フッター情報
st.markdown("---")
st.markdown(
    '''
    <div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px;">
        <p>🎥 <strong>配信アーカイブ共有サイト</strong></p>
        <p>データはTwitch APIから取得・定期更新されます | 
        <a href="https://www.twitch.tv/midorokun" target="_blank">配信チャンネル</a> | 
        <a href="https://x.com/blank_et4869" target="_blank">お問い合わせ</a> </p>
    </div>
    ''',
    unsafe_allow_html=True
)