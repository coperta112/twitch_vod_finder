# 共通サイドバーコンポーネント: app/components/sidebar.py
import streamlit as st
import os

def show_sidebar():
    """全ページで共通のサイドバーを表示"""
    
    # デフォルトのマルチページナビゲーションを完全に非表示にするCSS
    st.markdown("""
    <style>
        /* デフォルトのページセレクトボックスを完全に非表示 */
        section[data-testid="stSidebar"] .stSelectbox {
            display: none !important;
        }
        
        /* デフォルトのページナビゲーション全体を非表示 */
        section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            display: none !important;
        }
        
        /* ページセレクタのコンテナも非表示 */
        section[data-testid="stSidebar"] > div > div:first-child {
            display: none !important;
        }
        
        /* Streamlitのデフォルトナビゲーションを強制的に非表示 */
        .css-1d391kg, .css-1y0tads, .e1fqkh3o0 {
            display: none !important;
        }
        
        /* より具体的なセレクタでStreamlitのページリストを非表示 */
        section[data-testid="stSidebar"] ul {
            display: none !important;
        }
        
        /* ページリンクのリストを非表示 */
        section[data-testid="stSidebar"] nav {
            display: none !important;
        }
        
        /* サイドバー内の最初の要素（デフォルトナビ）を強制非表示 */
        section[data-testid="stSidebar"] > div:first-child > div:first-child {
            display: none !important;
        }
        
        /* サイドバーの上部パディングを調整 */
        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
        }
        
        /* カスタムボタンのスタイリング */
        .stButton > button {
            width: 100%;
            margin-bottom: 0.25rem;
            text-align: left;
        }
        
        /* アクティブページのスタイル */
        .active-page {
            background-color: #e8f4f8 !important;
            border-left: 4px solid #1f77b4 !important;
        }
    </style>
    
    <script>
    // JavaScriptでもデフォルトナビゲーションを動的に削除
    setTimeout(function() {
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            // Streamlitのデフォルトナビゲーション要素を削除
            const navElements = sidebar.querySelectorAll('ul, nav, .css-1d391kg, .e1fqkh3o0');
            navElements.forEach(el => el.remove());
            
            // ページセレクタも削除
            const selectBoxes = sidebar.querySelectorAll('[data-testid="stSelectbox"]');
            selectBoxes.forEach(el => el.remove());
        }
    }, 100);
    
    // 定期的にチェックしてデフォルトナビを削除
    setInterval(function() {
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            const unwantedElements = sidebar.querySelectorAll('ul:not(.custom-nav), nav:not(.custom-nav)');
            unwantedElements.forEach(el => {
                if (!el.classList.contains('custom-nav')) {
                    el.remove();
                }
            });
        }
    }, 500);
    </script>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.title("🎥 VOD Finder")
        
        # ナビゲーション
        st.markdown("---")
        
        # 現在のページを判定（デバッグ用）
        current_page = ""
        try:
            # Streamlitの内部状態から現在のページを取得
            if hasattr(st.session_state, '_main_script_path'):
                current_page = os.path.basename(st.session_state._main_script_path)
        except:
            pass
        
        # ページリンク - 正しいパスを使用
        pages = {
            "🏠 Home": "main.py",
            "📺 Videos": "pages/1_videos.py", 
            "✂️ Clips": "pages/3_clips.py",
            "🌟 favorites": "pages/5_favorites.py",
            "🔑 Login": "pages/6_login.py"
        }
        
        for page_name, page_file in pages.items():
            # 現在のページかどうかをチェック
            is_current = current_page == os.path.basename(page_file)
            
            if st.button(
                page_name, 
                use_container_width=True,
                key=f"nav_{page_file.replace('/', '_').replace('.py', '')}",
                help=f"Go to {page_name}"
            ):
                try:
                    st.switch_page(page_file)
                except Exception as e:
                    st.error(f"ページ遷移エラー: {e}")
                    # フォールバック: セッション状態での遷移
                    st.session_state['navigate_to'] = page_file
                    st.rerun()
        
        st.markdown("---")
        
        # 検索機能
        st.subheader("🔍 検索")
        search_query = st.text_input(
            "キーワード検索", 
            placeholder="動画やクリップを検索...",
            key="sidebar_search"
        )
        
        if search_query and st.button("検索実行", use_container_width=True):
            # 検索クエリをセッション状態に保存
            st.session_state['search_query'] = search_query
            try:
                st.switch_page("pages/1_videos.py")
            except Exception as e:
                st.session_state['navigate_to'] = "pages/1_videos.py"
                st.rerun()
        
        # 認証状態表示
        st.markdown("---")
        if st.session_state.get("is_admin", False):
            st.success("✅ 編集者ログイン中")
            
            # 管理者メニュー
            admin_pages = {
                "➕ VOD追加": "pages/7_add_vod.py",
                "✂️ Clip追加": "pages/8_add_clip.py"
            }
            
            for admin_page_name, admin_page_file in admin_pages.items():
                if st.button(admin_page_name, use_container_width=True):
                    try:
                        st.switch_page(admin_page_file)
                    except Exception as e:
                        st.session_state['navigate_to'] = admin_page_file
                        st.rerun()
            
            if st.button("🔓 ログアウト", use_container_width=True):
                st.session_state["is_admin"] = False
                st.success("ログアウトしました")
                st.rerun()
        else:
            st.info("🔒 閲覧モード")


def handle_navigation():
    """セッション状態ベースのナビゲーション処理"""
    if 'navigate_to' in st.session_state:
        target_page = st.session_state['navigate_to']
        del st.session_state['navigate_to']
        
        try:
            st.switch_page(target_page)
        except Exception as e:
            st.error(f"ページ遷移に失敗: {target_page}")


def safe_navigation():
    """各ページで呼び出すナビゲーション処理"""
    # ナビゲーション処理を最初に実行
    handle_navigation()
    
    # デフォルトのページナビゲーションを強制的に非表示
    st.markdown("""
    <script>
    // デフォルトのページセレクタを動的に非表示
    setTimeout(function() {
        const selectors = document.querySelectorAll('[data-testid="stSelectbox"]');
        selectors.forEach(selector => {
            if (selector.closest('[data-testid="stSidebar"]')) {
                selector.style.display = 'none';
            }
        });
    }, 100);
    </script>
    """, unsafe_allow_html=True)