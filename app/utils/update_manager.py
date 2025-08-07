"""
修正版 update_manager.py - 日付指定同期機能付き
既存のFlask-SQLAlchemyデータベース構造に対応
"""

import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import os
import traceback
import logging
import requests

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定管理をインポート（エラーハンドリング付き）
CONFIG_AVAILABLE = False
try:
    from app.config import get_config, check_config_status, get_twitch_headers
    CONFIG_AVAILABLE = True
    logger.info("設定モジュールを正常に読み込みました")
except ImportError as e:
    logger.warning(f"設定モジュールが見つかりません: {e}")
    # 直接環境変数から読み込む
    try:
        from dotenv import load_dotenv
        # 複数のenvファイルを試行
        if os.path.exists('.env'):
            load_dotenv('.env')
            logger.info("標準の.envファイルを読み込みました")
        elif os.path.exists('API.env'):
            load_dotenv('API.env')
            logger.info("API.envファイルを読み込みました")
        else:
            logger.warning("envファイルが見つかりません")
        CONFIG_AVAILABLE = True
    except ImportError:
        logger.error("dotenvモジュールも見つかりません")

class SimpleConfig:
    """簡易設定クラス（config.pyが使えない場合のフォールバック）"""
    def __init__(self):
        self.client_id = os.getenv('TWITCH_CLIENT_ID')
        self.client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        self.access_token = os.getenv('TWITCH_ACCESS_TOKEN')
        
        # 複数の環境変数名に対応
        self.channel_name = (
            os.getenv('TWITCH_CHANNEL_NAME') or 
            os.getenv('TWITCH_USER_LOGIN') or 
            'midorokun'  # デフォルト値
        )
        
        self.user_id = os.getenv('TWITCH_USER_ID')
        
        # デバッグ情報をログ出力
        logger.info(f"設定読み込み - Channel: {self.channel_name}, ClientID: {'設定済み' if self.client_id else '未設定'}")
    
    def is_configured(self):
        return bool(self.client_id and self.client_secret and self.channel_name)
    
    def get_missing_configs(self):
        missing = []
        if not self.client_id: missing.append('TWITCH_CLIENT_ID')
        if not self.client_secret: missing.append('TWITCH_CLIENT_SECRET')
        if not self.channel_name: missing.append('TWITCH_CHANNEL_NAME')
        return missing

def get_twitch_config():
    """Twitch設定を取得（複数のソースから試行）"""
    if CONFIG_AVAILABLE:
        try:
            return get_config().twitch
        except:
            pass
    
    # フォールバック: 簡易設定
    return SimpleConfig()

def check_api_configuration():
    """API設定をチェック"""
    try:
        config = get_twitch_config()
        if not config.is_configured():
            missing = config.get_missing_configs()
            return False, f"設定が不足: {', '.join(missing)}"
        return True, "設定OK"
    except Exception as e:
        return False, f"設定チェックエラー: {str(e)}"

def get_twitch_access_token():
    """アクセストークンを取得（自動取得機能付き）"""
    config = get_twitch_config()
    
    # 既存のアクセストークンがある場合はそれを使用
    if config.access_token:
        return config.access_token
    
    # アクセストークンがない場合は自動取得を試行
    if config.client_id and config.client_secret:
        try:
            logger.info("アクセストークンを自動取得中...")
            
            # Client Credentials Flowでアクセストークンを取得
            auth_url = 'https://id.twitch.tv/oauth2/token'
            auth_data = {
                'client_id': config.client_id,
                'client_secret': config.client_secret,
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(auth_url, data=auth_data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                
                # 環境変数に一時的に保存（セッション中のみ有効）
                os.environ['TWITCH_ACCESS_TOKEN'] = access_token
                config.access_token = access_token
                
                logger.info("アクセストークンの自動取得に成功")
                return access_token
            else:
                logger.error(f"トークン取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"トークン自動取得エラー: {str(e)}")
            return None
    
    return None

def get_user_id_from_channel_name(channel_name, client_id, access_token):
    """チャンネル名からユーザーIDを取得"""
    try:
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(
            f'https://api.twitch.tv/helix/users?login={channel_name}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return data['data'][0]['id']
        
        logger.error(f"ユーザー情報取得失敗: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"ユーザーID取得エラー: {str(e)}")
        return None

def get_table_columns(cursor, table_name):
    """テーブルのカラム情報を取得"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return columns
    except Exception as e:
        logger.error(f"テーブル情報取得エラー ({table_name}): {str(e)}")
        return []

def migrate_database_if_needed(cursor):
    """データベースのマイグレーション（既存構造に必要なカラムを追加）"""
    try:
        # vodsテーブルのカラムチェック・追加
        vods_columns = get_table_columns(cursor, 'vods')
        logger.info(f"既存のvodsカラム: {vods_columns}")
        
        if 'duration' not in vods_columns:
            logger.info("vodsテーブルにdurationカラムを追加中...")
            cursor.execute("ALTER TABLE vods ADD COLUMN duration TEXT")
        
        if 'view_count' not in vods_columns:
            logger.info("vodsテーブルにview_countカラムを追加中...")
            cursor.execute("ALTER TABLE vods ADD COLUMN view_count INTEGER DEFAULT 0")
        
        if 'game_name' not in vods_columns:
            logger.info("vodsテーブルにgame_nameカラムを追加中...")
            cursor.execute("ALTER TABLE vods ADD COLUMN game_name TEXT")
        
        if 'thumbnail_url' not in vods_columns:
            logger.info("vodsテーブルにthumbnail_urlカラムを追加中...")
            cursor.execute("ALTER TABLE vods ADD COLUMN thumbnail_url TEXT")
        
        # clipsテーブルのカラムチェック・追加
        clips_columns = get_table_columns(cursor, 'clips')
        logger.info(f"既存のclipsカラム: {clips_columns}")
        
        if 'duration' not in clips_columns:
            logger.info("clipsテーブルにdurationカラムを追加中...")
            cursor.execute("ALTER TABLE clips ADD COLUMN duration REAL")
        
        if 'view_count' not in clips_columns:
            logger.info("clipsテーブルにview_countカラムを追加中...")
            cursor.execute("ALTER TABLE clips ADD COLUMN view_count INTEGER DEFAULT 0")
        
        if 'game_name' not in clips_columns:
            logger.info("clipsテーブルにgame_nameカラムを追加中...")
            cursor.execute("ALTER TABLE clips ADD COLUMN game_name TEXT")
        
        if 'creator_name' not in clips_columns:
            logger.info("clipsテーブルにcreator_nameカラムを追加中...")
            cursor.execute("ALTER TABLE clips ADD COLUMN creator_name TEXT")
        
        logger.info("データベースマイグレーション完了")
        
    except Exception as e:
        logger.error(f"データベースマイグレーションエラー: {str(e)}")

def ensure_tables(cursor):
    """必要なテーブルを作成（既存のFlask-SQLAlchemy構造を尊重）"""
    # sync_logテーブルのみ作成（他は既存のものを使用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            last_sync_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 既存テーブルにカラムを追加（必要に応じて）
    migrate_database_if_needed(cursor)

def sync_twitch_data_direct(date_range=None):
    """Twitch APIから直接データを同期（日付指定対応）"""
    try:
        # API設定チェック
        config_ok, config_msg = check_api_configuration()
        if not config_ok:
            return {"success": False, "error": f"API設定エラー: {config_msg}"}
        
        config = get_twitch_config()
        
        # アクセストークンを取得
        access_token = get_twitch_access_token()
        if not access_token:
            return {"success": False, "error": "アクセストークンの取得に失敗しました"}
        
        # ユーザーIDを取得
        user_id = config.user_id
        if not user_id:
            user_id = get_user_id_from_channel_name(config.channel_name, config.client_id, access_token)
            if not user_id:
                return {"success": False, "error": f"チャンネル '{config.channel_name}' のユーザーIDを取得できませんでした"}
        
        # データベース接続
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        # テーブル作成（存在しない場合）
        ensure_tables(c)
        
        # ヘッダー設定
        headers = {
            'Client-ID': config.client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        # 同期結果
        results = {
            'videos_added': 0,
            'clips_added': 0,
            'errors': [],
            'date_range': date_range
        }
        
        # 日付範囲のログ出力
        if date_range:
            logger.info(f"日付指定同期: {date_range['start_date']} ～ {date_range['end_date']}")
        else:
            logger.info("通常同期: 過去7日間")
        
        # VOD同期
        try:
            logger.info("VODデータを同期中...")
            vod_result = sync_videos(headers, user_id, c, date_range=date_range)
            results['videos_added'] = vod_result['added']
            if vod_result.get('errors'):
                results['errors'].extend(vod_result['errors'])
        except Exception as e:
            error_msg = f"VOD同期エラー: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        # クリップ同期
        try:
            logger.info("クリップデータを同期中...")
            clip_result = sync_clips(headers, user_id, c, date_range=date_range)
            results['clips_added'] = clip_result['added']
            if clip_result.get('errors'):
                results['errors'].extend(clip_result['errors'])
        except Exception as e:
            error_msg = f"クリップ同期エラー: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        # データベースをコミット
        conn.commit()
        conn.close()
        
        # 同期ログを記録
        sync_type = "日付指定同期" if date_range else "通常同期"
        record_sync_log(sync_type)
        
        # 結果メッセージ作成
        if date_range:
            period_info = f" ({date_range['start_date']} ～ {date_range['end_date']})"
        else:
            period_info = " (過去7日間)"
            
        result_msg = f"VOD: {results['videos_added']}件追加, クリップ: {results['clips_added']}件追加{period_info}"
        if results['errors']:
            result_msg += f"\n警告: {len(results['errors'])}件のエラーが発生"
        
        return {"success": True, "result": result_msg, "details": results}
        
    except Exception as e:
        logger.error(f"同期処理エラー: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": f"同期エラー: {str(e)}"}

def sync_videos(headers, user_id, cursor, date_range=None, limit=100):
    """VODを同期（既存のFlask-SQLAlchemy構造に対応 - 日付指定対応）"""
    try:
        # パラメータを設定
        params = {
            'user_id': user_id,
            'first': min(limit, 100)  # APIの上限は100
        }
        
        # 日付範囲が指定されている場合
        if date_range:
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            # ISO形式に変換
            start_iso = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
            end_iso = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
            
            params['started_at'] = start_iso
            params['ended_at'] = end_iso
            
            logger.info(f"VOD取得期間: {start_iso} ～ {end_iso}")
        
        response = requests.get(
            'https://api.twitch.tv/helix/videos',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            return {"added": 0, "errors": [f"VOD API エラー: {response.status_code}"]}

        data = response.json()
        videos = data.get('data', [])
        added_count = 0

        # テーブルのカラム情報を取得
        vods_columns = get_table_columns(cursor, 'vods')

        # ページネーション対応（日付指定時は複数ページ取得）
        all_videos = videos.copy()
        pagination = data.get('pagination', {})
        
        # 日付指定時は複数ページを取得（最大10ページまで）
        if date_range and pagination.get('cursor') and len(videos) == limit:
            page_count = 1
            max_pages = 10
            
            while pagination.get('cursor') and page_count < max_pages:
                params['after'] = pagination['cursor']
                
                logger.info(f"追加ページを取得中... (ページ {page_count + 1})")
                
                try:
                    next_response = requests.get(
                        'https://api.twitch.tv/helix/videos',
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    
                    if next_response.status_code == 200:
                        next_data = next_response.json()
                        next_videos = next_data.get('data', [])
                        
                        if not next_videos:
                            break
                            
                        all_videos.extend(next_videos)
                        pagination = next_data.get('pagination', {})
                        page_count += 1
                    else:
                        logger.warning(f"追加ページ取得失敗: {next_response.status_code}")
                        break
                        
                except Exception as e:
                    logger.warning(f"追加ページ取得エラー: {str(e)}")
                    break

        logger.info(f"取得したVOD数: {len(all_videos)}")

        for video in all_videos:
            try:
                video_id = video.get('id')
                if not video_id:
                    logger.warning(f"VODにIDが存在しないためスキップ: {video}")
                    continue

                # 既存チェック（twitch_idで確認）
                cursor.execute("SELECT id FROM vods WHERE twitch_id = ?", (video_id,))
                if cursor.fetchone():
                    continue  # 既に存在する場合はスキップ

                # 必須データ（Flask-SQLAlchemy構造に合わせる）
                insert_data = {
                    'twitch_id': video_id,
                    'title': video.get('title', ''),
                    'url': video.get('url', ''),
                    'created_at': video.get('created_at', datetime.now().isoformat()),
                    'category': video.get('game_id', ''),
                    'type': 'archive'
                }

                # オプションカラムを条件付きで追加
                if 'duration' in vods_columns:
                    insert_data['duration'] = video.get('duration', '')
                if 'view_count' in vods_columns:
                    insert_data['view_count'] = video.get('view_count', 0)
                if 'game_name' in vods_columns:
                    insert_data['game_name'] = video.get('game_name', '')
                if 'thumbnail_url' in vods_columns:
                    insert_data['thumbnail_url'] = video.get('thumbnail_url', '')

                # 動的にクエリを生成
                columns = ', '.join(insert_data.keys())
                placeholders = ', '.join(['?' for _ in insert_data])
                values = list(insert_data.values())

                cursor.execute(f"""
                    INSERT INTO vods ({columns})
                    VALUES ({placeholders})
                """, values)

                added_count += 1
                logger.info(f"VOD追加: {video.get('title', 'タイトル不明')}")

            except Exception as e:
                logger.error(f"VOD挿入エラー: {str(e)}")

        return {"added": added_count, "errors": []}

    except Exception as e:
        return {"added": 0, "errors": [f"VOD同期エラー: {str(e)}"]}


def sync_clips(headers, user_id, cursor, date_range=None, limit=100):
    """クリップを同期（既存のFlask-SQLAlchemy構造に対応 - 日付指定対応）"""
    try:
        # 日付範囲を設定（デフォルトは過去7日間）
        if date_range:
            start_date = date_range['start_date']
            end_date = date_range['end_date']
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
        
        # ISO形式に変換
        start_iso = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
        end_iso = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
        
        logger.info(f"クリップ取得期間: {start_iso} ～ {end_iso}")
        
        params = {
            'broadcaster_id': user_id,
            'first': min(limit, 100),  # APIの上限は100
            'started_at': start_iso,
            'ended_at': end_iso
        }
        
        response = requests.get(
            'https://api.twitch.tv/helix/clips',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            return {"added": 0, "errors": [f"クリップAPI エラー: {response.status_code}"]}
        
        data = response.json()
        clips = data.get('data', [])
        added_count = 0
        
        # テーブルのカラム情報を取得
        clips_columns = get_table_columns(cursor, 'clips')
        
        # ページネーション対応（日付指定時は複数ページ取得）
        all_clips = clips.copy()
        pagination = data.get('pagination', {})
        
        # 日付指定時は複数ページを取得（最大10ページまで）
        if date_range and pagination.get('cursor') and len(clips) == limit:
            page_count = 1
            max_pages = 10
            
            while pagination.get('cursor') and page_count < max_pages:
                params['after'] = pagination['cursor']
                
                logger.info(f"クリップの追加ページを取得中... (ページ {page_count + 1})")
                
                try:
                    next_response = requests.get(
                        'https://api.twitch.tv/helix/clips',
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    
                    if next_response.status_code == 200:
                        next_data = next_response.json()
                        next_clips = next_data.get('data', [])
                        
                        if not next_clips:
                            break
                            
                        all_clips.extend(next_clips)
                        pagination = next_data.get('pagination', {})
                        page_count += 1
                    else:
                        logger.warning(f"クリップ追加ページ取得失敗: {next_response.status_code}")
                        break
                        
                except Exception as e:
                    logger.warning(f"クリップ追加ページ取得エラー: {str(e)}")
                    break

        logger.info(f"取得したクリップ数: {len(all_clips)}")
        
        for clip in all_clips:
            try:
                # 既存チェック（twitch_idで確認）
                cursor.execute("SELECT id FROM clips WHERE twitch_id = ?", (clip['id'],))
                if cursor.fetchone():
                    continue  # 既に存在する場合はスキップ
                
                # 必須データ（Flask-SQLAlchemy構造に合わせる）
                insert_data = {
                    'twitch_id': clip['id'],  # ← 重要：twitch_idを使用
                    'title': clip.get('title', ''),
                    'url': clip.get('url', ''),
                    'created_at': clip.get('created_at', datetime.now().isoformat()),
                    'category': clip.get('game_id', ''),  # game_idをcategoryとして保存
                }
                
                # vod_twitch_idがある場合は追加
                if 'vod_twitch_id' in clips_columns and clip.get('video_id'):
                    insert_data['vod_twitch_id'] = clip['video_id']
                
                # thumbnail_urlがある場合は追加
                if 'thumbnail_url' in clips_columns:
                    insert_data['thumbnail_url'] = clip.get('thumbnail_url', '')
                
                # オプションカラムを条件付きで追加
                if 'duration' in clips_columns:
                    insert_data['duration'] = clip.get('duration', 0)
                if 'view_count' in clips_columns:
                    insert_data['view_count'] = clip.get('view_count', 0)
                if 'game_name' in clips_columns:
                    insert_data['game_name'] = clip.get('game_name', '')
                if 'creator_name' in clips_columns:
                    insert_data['creator_name'] = clip.get('creator_name', '')
                
                # is_favoriteのデフォルト値
                if 'is_favorite' in clips_columns:
                    insert_data['is_favorite'] = False
                
                # 動的にクエリを生成
                columns = ', '.join(insert_data.keys())
                placeholders = ', '.join(['?' for _ in insert_data])
                values = list(insert_data.values())
                
                cursor.execute(f"""
                    INSERT INTO clips ({columns})
                    VALUES ({placeholders})
                """, values)
                
                added_count += 1
                logger.info(f"クリップ追加: {clip.get('title', 'タイトル不明')}")
                
            except Exception as e:
                logger.error(f"クリップ挿入エラー: {str(e)}")
        
        return {"added": added_count, "errors": []}
        
    except Exception as e:
        return {"added": 0, "errors": [f"クリップ同期エラー: {str(e)}"]}

def record_sync_log(sync_type):
    """同期ログを記録"""
    try:
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        current_time = datetime.now().isoformat()
        c.execute("""
            INSERT INTO sync_log (sync_type, last_sync_time) 
            VALUES (?, ?)
        """, (sync_type, current_time))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"同期ログエラー: {str(e)}")

def refresh_data(date_range=None):
    """データを更新（メイン関数 - 日付指定対応）"""
    try:
        if date_range:
            logger.info(f"日付指定データ更新を開始します: {date_range['start_date']} ～ {date_range['end_date']}")
        else:
            logger.info("通常データ更新を開始します...")
        
        # 直接同期を実行
        sync_result = sync_twitch_data_direct(date_range=date_range)
        
        # キャッシュをクリア
        clear_cache()
        
        # 最終更新時刻を記録
        st.session_state.last_refresh_time = datetime.now()
        
        logger.info(f"データ更新完了: {sync_result}")
        return sync_result
        
    except Exception as e:
        logger.error(f"データ更新エラー: {str(e)}")
        # エラーが発生してもキャッシュクリアは実行
        clear_cache()
        st.session_state.last_refresh_time = datetime.now()
        
        return {"success": False, "error": str(e)}

def clear_cache():
    """キャッシュをクリア"""
    try:
        st.cache_data.clear()
        if hasattr(st.session_state, 'database_stats_cache'):
            del st.session_state.database_stats_cache
    except Exception as e:
        logger.error(f"キャッシュクリアエラー: {str(e)}")

@st.cache_data(ttl=60)  # 1分間キャッシュ
def get_database_stats():
    """データベースの統計情報を取得"""
    try:
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        # 各テーブルのレコード数を取得
        c.execute("SELECT COUNT(*) FROM vods")
        vods_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM clips")
        clips_count = c.fetchone()[0]
        
        # YouTubeリンクがある場合は取得
        try:
            c.execute("SELECT COUNT(*) FROM youtube_links")
            youtube_count = c.fetchone()[0]
        except:
            youtube_count = 0
        
        # 最新の追加日時を取得
        c.execute("SELECT MAX(created_at) FROM vods")
        latest_vod = c.fetchone()[0]
        
        c.execute("SELECT MAX(created_at) FROM clips")
        latest_clip = c.fetchone()[0]
        
        # 今日追加されたアイテム数
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM vods WHERE DATE(created_at) = ?", (today,))
        today_vods = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM clips WHERE DATE(created_at) = ?", (today,))
        today_clips = c.fetchone()[0]
        
        conn.close()
        
        return {
            "vods_count": vods_count,
            "clips_count": clips_count,
            "youtube_count": youtube_count,
            "latest_vod": latest_vod,
            "latest_clip": latest_clip,
            "today_vods": today_vods,
            "today_clips": today_clips,
            "total_items": vods_count + clips_count
        }
    except Exception as e:
        logger.error(f"データベース統計エラー: {str(e)}")
        return {"error": str(e)}

def test_twitch_connection():
    """Twitch API接続をテスト"""
    try:
        config_ok, config_msg = check_api_configuration()
        if not config_ok:
            st.error(f"❌ 設定エラー: {config_msg}")
            return
        
        config = get_twitch_config()
        access_token = get_twitch_access_token()
        
        if not access_token:
            st.error("❌ アクセストークンを取得できませんでした")
            return
        
        headers = {
            'Client-ID': config.client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        with st.spinner("🔍 Twitch APIに接続中..."):
            response = requests.get(
                f'https://api.twitch.tv/helix/users?login={config.channel_name}',
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
            st.error("❌ 認証エラー: 設定を確認してください")
        else:
            st.error(f"❌ API接続失敗: {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ 接続テストエラー: {str(e)}")

def show_config_guide():
    """設定ガイドを表示"""
    st.info("""
    **🔧 Twitch API設定方法:**
    
    1. **Twitch Developer Console**にアクセス
       - https://dev.twitch.tv/console
    
    2. **アプリケーションを作成**
       - 「Create App」をクリック
       - 名前: `VOD Archive Tool`
       - カテゴリ: `Application Integration`
       - OAuth Redirect URLs: `http://localhost`
    
    3. **認証情報を取得**
       - Client IDをコピー
       - Client Secretを生成してコピー
    
    4. **設定ファイルを作成**
       - プロジェクトルートに `.env` ファイルを作成
       - 以下の内容を記入:
       ```
       TWITCH_CLIENT_ID=your_client_id_here
       TWITCH_CLIENT_SECRET=your_client_secret_here
       TWITCH_CHANNEL_NAME=your_channel_name
       ```
    
    5. **アプリを再起動**
       - Streamlitアプリを再起動して設定を反映
    """)

def add_sidebar_sync_controls():
    """サイドバーに同期コントロールを追加（日付指定機能付き）"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔄 Twitch同期")
        
        # 設定チェック
        config_ok, config_msg = check_api_configuration()
        
        if config_ok:
            st.success("✅ API設定OK")
        else:
            st.error("❌ API設定エラー")
            st.caption(config_msg)
            
            if st.button("🔧 設定ガイド", key="sidebar_config_guide"):
                show_config_guide()
        
        # 同期モード選択（サイドバー版）
        sync_mode_sidebar = st.radio(
            "同期モード",
            ["通常同期", "日付指定"],
            key="sidebar_sync_mode",
            help="通常: 過去7日 / 日付指定: 期間指定"
        )
        
        # 日付指定セクション（サイドバー版）
        date_range_params_sidebar = None
        if sync_mode_sidebar == "日付指定":
            start_date_sidebar = st.date_input(
                "開始日",
                value=datetime.now().date() - timedelta(days=14),
                max_value=datetime.now().date(),
                key="sidebar_start_date"
            )
            
            end_date_sidebar = st.date_input(
                "終了日", 
                value=datetime.now().date(),
                min_value=start_date_sidebar,
                max_value=datetime.now().date(),
                key="sidebar_end_date"
            )
            
            days_diff_sidebar = (end_date_sidebar - start_date_sidebar).days
            if days_diff_sidebar > 0:
                st.caption(f"📅 {days_diff_sidebar + 1}日間")
                date_range_params_sidebar = {
                    'start_date': start_date_sidebar,
                    'end_date': end_date_sidebar
                }
            else:
                st.error("❌ 無効な期間")
        
        # 最終更新時刻の表示
        if "last_refresh_time" not in st.session_state:
            st.session_state.last_refresh_time = datetime.now()
        
        last_update = st.session_state.last_refresh_time.strftime('%H:%M:%S')
        st.caption(f"最終実行: {last_update}")
        
        # 同期ボタン（サイドバー版）
        sync_button_text_sidebar = "🔄 データ同期" if sync_mode_sidebar == "通常同期" else "📅 日付同期"
        sync_disabled_sidebar = not config_ok or (sync_mode_sidebar == "日付指定" and not date_range_params_sidebar)
        
        if st.button(sync_button_text_sidebar, key="sidebar_sync", use_container_width=True, disabled=sync_disabled_sidebar):
            if config_ok:
                spinner_text_sidebar = "📡 Twitchから同期中..." if sync_mode_sidebar == "通常同期" else f"📅 指定期間を同期中..."
                
                with st.spinner(spinner_text_sidebar):
                    result = refresh_data(date_range=date_range_params_sidebar)
                
                if result["success"]:
                    st.success("✅ 同期完了")
                    if "result" in result:
                        st.caption(result["result"])
                else:
                    st.error("❌ 同期失敗")
                    st.caption(result.get('error', '不明なエラー'))
                    
                st.rerun()
            else:
                st.error("設定が不完全です")
