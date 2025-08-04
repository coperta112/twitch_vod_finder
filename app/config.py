"""
設定管理ファイル
環境変数から設定を読み込み、デフォルト値を提供
"""

import os
from dotenv import load_dotenv
import streamlit as st

# .envファイルを読み込み
load_dotenv()

class TwitchConfig:
    """Twitch API設定クラス"""
    
    def __init__(self):
        # 環境変数から設定を読み込み
        self.client_id = os.getenv('TWITCH_CLIENT_ID')
        self.client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        self.access_token = os.getenv('TWITCH_ACCESS_TOKEN')
        self.refresh_token = os.getenv('TWITCH_REFRESH_TOKEN')
        
        # チャンネル情報
        self.channel_name = os.getenv('TWITCH_CHANNEL_NAME')
        self.user_id = os.getenv('TWITCH_USER_ID')
        
        # Streamlitのsecrets機能からも読み込み（バックアップ）
        if not self.client_id and hasattr(st, 'secrets'):
            try:
                self.client_id = st.secrets.get('TWITCH_CLIENT_ID')
                self.client_secret = st.secrets.get('TWITCH_CLIENT_SECRET')
                self.access_token = st.secrets.get('TWITCH_ACCESS_TOKEN')
                self.refresh_token = st.secrets.get('TWITCH_REFRESH_TOKEN')
                self.channel_name = st.secrets.get('TWITCH_CHANNEL_NAME')
                self.user_id = st.secrets.get('TWITCH_USER_ID')
            except:
                pass
    
    def is_configured(self):
        """必要な設定が揃っているかチェック"""
        required_fields = [
            self.client_id,
            self.client_secret,
            self.channel_name
        ]
        return all(field for field in required_fields)
    
    def get_missing_configs(self):
        """不足している設定項目を返す"""
        missing = []
        if not self.client_id:
            missing.append('TWITCH_CLIENT_ID')
        if not self.client_secret:
            missing.append('TWITCH_CLIENT_SECRET')
        if not self.channel_name:
            missing.append('TWITCH_CHANNEL_NAME')
        return missing
    
    def to_dict(self):
        """設定を辞書形式で返す（秘密情報は除く）"""
        return {
            'channel_name': self.channel_name,
            'user_id': self.user_id,
            'has_client_id': bool(self.client_id),
            'has_client_secret': bool(self.client_secret),
            'has_access_token': bool(self.access_token),
            'is_configured': self.is_configured()
        }

class DatabaseConfig:
    """データベース設定クラス"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///vods.db')
        self.db_file = os.getenv('DB_FILE', 'vods.db')

class AppConfig:
    """アプリケーション全体の設定クラス"""
    
    def __init__(self):
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Twitch設定
        self.twitch = TwitchConfig()
        
        # データベース設定
        self.database = DatabaseConfig()
    
    def validate_config(self):
        """設定の妥当性をチェック"""
        issues = []
        
        if not self.twitch.is_configured():
            missing = self.twitch.get_missing_configs()
            issues.append(f"Twitch API設定が不足: {', '.join(missing)}")
        
        return issues

# グローバル設定インスタンス
config = AppConfig()

def get_config():
    """設定インスタンスを取得"""
    return config

def check_config_status():
    """設定状態をチェックしてStreamlitに表示"""
    issues = config.validate_config()
    
    if issues:
        st.error("⚠️ 設定に問題があります:")
        for issue in issues:
            st.error(f"• {issue}")
        
        st.info("""
        **設定方法:**
        1. プロジェクトルートに `.env` ファイルを作成
        2. 以下の設定を記入:
        ```
        TWITCH_CLIENT_ID=your_client_id
        TWITCH_CLIENT_SECRET=your_client_secret
        TWITCH_CHANNEL_NAME=your_channel_name
        ```
        3. アプリを再起動
        """)
        return False
    else:
        st.success("✅ Twitch API設定は正常です")
        return True

def show_config_status():
    """設定状態を詳細表示（管理者用）"""
    if not st.session_state.get("is_admin", False):
        return
    
    with st.expander("🔧 API設定状態", expanded=False):
        config_dict = config.twitch.to_dict()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Twitch設定**")
            st.caption(f"チャンネル: {config_dict.get('channel_name', '未設定')}")
            st.caption(f"ユーザーID: {config_dict.get('user_id', '未設定')}")
        
        with col2:
            st.markdown("**認証情報**")
            client_icon = "✅" if config_dict.get('has_client_id') else "❌"
            secret_icon = "✅" if config_dict.get('has_client_secret') else "❌"
            token_icon = "✅" if config_dict.get('has_access_token') else "⚪"
            
            st.caption(f"{client_icon} Client ID")
            st.caption(f"{secret_icon} Client Secret")
            st.caption(f"{token_icon} Access Token")
        
        # 設定テスト
        if st.button("🧪 API接続テスト", key="config_test"):
            test_twitch_connection()

def test_twitch_connection():
    """Twitch API接続をテスト"""
    try:
        if not config.twitch.is_configured():
            st.error("❌ API設定が不完全です")
            return
        
        # 簡単な接続テスト
        import requests
        
        headers = {
            'Client-ID': config.twitch.client_id,
            'Authorization': f'Bearer {config.twitch.access_token}' if config.twitch.access_token else ''
        }
        
        with st.spinner("🔍 Twitch APIに接続中..."):
            # ユーザー情報取得テスト
            response = requests.get(
                f'https://api.twitch.tv/helix/users?login={config.twitch.channel_name}',
                headers=headers,
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                user_info = data['data'][0]
                st.success(f"✅ API接続成功!")
                st.info(f"チャンネル: {user_info.get('display_name')} (ID: {user_info.get('id')})")
            else:
                st.warning("⚠️ チャンネルが見つかりません")
        elif response.status_code == 401:
            st.error("❌ 認証エラー: アクセストークンを確認してください")
        else:
            st.error(f"❌ API接続失敗: {response.status_code}")
            
    except requests.exceptions.Timeout:
        st.error("❌ 接続タイムアウト")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ 接続エラー: {str(e)}")
    except Exception as e:
        st.error(f"❌ 予期しないエラー: {str(e)}")

def get_twitch_headers():
    """Twitch API用のヘッダーを取得"""
    if not config.twitch.is_configured():
        raise ValueError("Twitch API設定が不完全です")
    
    headers = {
        'Client-ID': config.twitch.client_id,
        'Content-Type': 'application/json'
    }
    
    if config.twitch.access_token:
        headers['Authorization'] = f'Bearer {config.twitch.access_token}'
    
    return headers

def refresh_access_token():
    """アクセストークンを更新"""
    if not config.twitch.refresh_token:
        raise ValueError("リフレッシュトークンが設定されていません")
    
    import requests
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': config.twitch.refresh_token,
        'client_id': config.twitch.client_id,
        'client_secret': config.twitch.client_secret
    }
    
    response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        
        # 新しいトークンを環境変数に設定（一時的）
        os.environ['TWITCH_ACCESS_TOKEN'] = token_data['access_token']
        if 'refresh_token' in token_data:
            os.environ['TWITCH_REFRESH_TOKEN'] = token_data['refresh_token']
        
        # 設定を再読み込み
        config.twitch.access_token = token_data['access_token']
        if 'refresh_token' in token_data:
            config.twitch.refresh_token = token_data['refresh_token']
        
        return token_data
    else:
        raise Exception(f"Token refresh failed: {response.status_code}")

# 使用例とヘルパー関数
def setup_twitch_config_ui():
    """Streamlitアプリに設定UIを追加"""
    
    # 設定状態のチェック
    is_configured = check_config_status()
    
    # 管理者用の詳細表示
    show_config_status()
    
    return is_configured

def get_safe_config_info():
    """安全な設定情報を取得（秘密情報を除く）"""
    return {
        'twitch_configured': config.twitch.is_configured(),
        'channel_name': config.twitch.channel_name,
        'debug_mode': config.debug
    }