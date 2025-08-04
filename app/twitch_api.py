# twitch_api.py (修正版)

import requests
from datetime import datetime, timedelta
import sqlite3
import os
import re

BASE_URL = "https://api.twitch.tv/helix"

def get_access_token():
    """Twitchアクセストークンを取得"""
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": os.getenv("TWITCH_CLIENT_ID"),
        "client_secret": os.getenv("TWITCH_CLIENT_SECRET"),
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    return response.json()["access_token"]

def get_user_id(headers):
    """Twitchユーザーの内部IDを取得"""
    url = f"{BASE_URL}/users"
    params = {"login": os.getenv("TWITCH_USER_LOGIN")}
    response = requests.get(url, headers=headers, params=params)
    return response.json()["data"][0]["id"]

def ensure_tables_exist():
    """必要なテーブルが存在することを確認"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # vodsテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS vods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_id TEXT UNIQUE,
            title TEXT NOT NULL,
            category TEXT,
            url TEXT,
            created_at TIMESTAMP,
            type TEXT DEFAULT 'archive'
        )
    """)
    
    # clipsテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twitch_id TEXT UNIQUE,
            title TEXT NOT NULL,
            category TEXT,
            url TEXT,
            created_at TIMESTAMP,
            vod_twitch_id TEXT,
            vod_id INTEGER,
            thumbnail_url TEXT,
            FOREIGN KEY (vod_id) REFERENCES vods (id)
        )
    """)
    
    # youtube_linksテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS youtube_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vod_id INTEGER,
            url TEXT NOT NULL,
            title TEXT,
            video_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vod_id) REFERENCES vods (id)
        )
    """)
    
    # sync_logテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            last_sync_time TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_last_sync_time():
    """最後の同期時刻を取得"""
    try:
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        # 最後の同期時刻を取得
        c.execute("SELECT last_sync_time FROM sync_log WHERE sync_type = 'clips' ORDER BY created_at DESC LIMIT 1")
        result = c.fetchone()
        
        conn.close()
        
        if result:
            return datetime.fromisoformat(result[0])
        else:
            # 初回実行の場合は30日前から開始
            return datetime.utcnow() - timedelta(days=30)
            
    except Exception as e:
        print(f"⚠️ sync_log取得エラー: {e}")
        # エラーの場合は7日前から開始
        return datetime.utcnow() - timedelta(days=7)

def update_last_sync_time(sync_type="clips"):
    """最後の同期時刻を更新"""
    try:
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        current_time = datetime.utcnow().isoformat()
        
        # 既存の記録を更新または新規作成
        c.execute("""
            INSERT OR REPLACE INTO sync_log (sync_type, last_sync_time)
            VALUES (?, ?)
        """, (sync_type, current_time))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 同期時刻更新: {sync_type} - {current_time}")
        
    except Exception as e:
        print(f"⚠️ sync_log更新エラー: {e}")

def fetch_vods(headers, user_id, vod_type="archive"):
    """VODデータを取得してSQLiteに保存"""
    url = f"{BASE_URL}/videos"
    params = {
        "user_id": user_id,
        "type": vod_type,
        "first": 50
    }
    
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    new_vods_count = 0
    updated_vods_count = 0
    
    while True:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("data", [])

        if not data:
            break

        for item in data:
            vod_id = item["id"]
            vod_url = item["url"]

            # 既存のVODをチェック
            c.execute("SELECT id, url FROM vods WHERE twitch_id = ?", (vod_id,))
            existing_vod = c.fetchone()

            if existing_vod:
                existing_id, existing_url = existing_vod
                # URLが「チャンネルページ」だった場合のみ、VOD形式URLに更新
                if "twitch.tv/videos/" in vod_url and (
                    "twitch.tv/videos/" not in existing_url
                ):
                    print(f"🔁 URL updated for VOD {vod_id}: {existing_url} → {vod_url}")
                    c.execute("UPDATE vods SET url = ? WHERE id = ?", (vod_url, existing_id))
                    updated_vods_count += 1
            else:
                # 新しいVODを追加
                c.execute("""
                    INSERT INTO vods (twitch_id, title, category, url, created_at, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    vod_id,
                    item["title"],
                    item.get("game_id", ""),
                    vod_url,
                    datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    vod_type
                ))
                new_vods_count += 1
                print(f"🆕 新しいVODを追加: {item['title']}")

        conn.commit()

        # 次ページへ（もし存在するなら）
        pagination = response.json().get("pagination", {})
        cursor = pagination.get("cursor")
        if cursor:
            params["after"] = cursor
        else:
            break
    
    conn.close()
    return {"new": new_vods_count, "updated": updated_vods_count}

def fetch_clips(headers, user_id, start_date: datetime, end_date: datetime):
    """クリップデータを取得してSQLiteに保存"""
    url = f"{BASE_URL}/clips"
    current_start = start_date
    
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    new_clips_count = 0
    updated_clips_count = 0

    print(f"🔍 クリップ取得範囲: {start_date.strftime('%Y-%m-%d %H:%M')} ～ {end_date.strftime('%Y-%m-%d %H:%M')}")

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=7), end_date)
        params = {
            "broadcaster_id": user_id,
            "first": 50,
            "started_at": current_start.isoformat("T") + "Z",
            "ended_at": current_end.isoformat("T") + "Z"
        }
        
        print(f"📅 期間: {current_start.date()} ～ {current_end.date()}")

        while True:
            response = requests.get(url, headers=headers, params=params)
            print(f"🔍 API Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ API エラー: {response.status_code} - {response.text}")
                break
                
            data = response.json().get("data", [])
            print(f"📊 取得クリップ数: {len(data)}")

            if not data:
                break

            for item in data:
                clip_title = item["title"]
                clip_id = item["id"]
                vod_twitch_id = item.get("video_id")
                
                # 既存のクリップをチェック
                c.execute("SELECT id, thumbnail_url FROM clips WHERE twitch_id = ?", (clip_id,))
                existing = c.fetchone()
                
                if not existing:
                    # 新しいクリップを追加
                    c.execute("""
                        INSERT INTO clips (twitch_id, title, category, url, created_at, vod_twitch_id, thumbnail_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        clip_id,
                        clip_title,
                        item.get("game_id", ""),
                        item["url"],
                        datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                        vod_twitch_id,
                        item.get("thumbnail_url")
                    ))
                    new_clips_count += 1
                    print(f"🆕 新しいクリップ追加: {clip_title}")
                    
                elif not existing[1] and item.get("thumbnail_url"):
                    # サムネイルを更新
                    c.execute("UPDATE clips SET thumbnail_url = ? WHERE twitch_id = ?", 
                             (item["thumbnail_url"], clip_id))
                    updated_clips_count += 1
                    print(f"🔁 サムネイル更新: {clip_title}")

            conn.commit()

            # 次ページへ（もしあれば）
            pagination = response.json().get("pagination", {})
            cursor = pagination.get("cursor")
            if not cursor or cursor == params.get("after"):
                break
            params["after"] = cursor

        current_start += timedelta(days=7)
    
    conn.close()
    return {"new": new_clips_count, "updated": updated_clips_count}

def link_clips_to_vods():
    """クリップとVODの紐づけを実行（SQLite用）"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # 紐づけされていないクリップを取得
    c.execute("""
        SELECT id, vod_twitch_id 
        FROM clips 
        WHERE vod_id IS NULL AND vod_twitch_id IS NOT NULL
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
            print(f"🔗 クリップ(ID:{clip_id})をVOD(ID:{vod_id})に紐づけしました")
    
    conn.commit()
    conn.close()
    return linked_count

def sync_data():
    """メインの同期処理（SQLite対応版）"""
    print("🚀 Twitch API同期開始...")
    sync_start_time = datetime.utcnow()
    
    try:
        # テーブルの存在確認
        ensure_tables_exist()
        
        # 認証
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID")
        }
        user_id = get_user_id(headers)
        print(f"✅ 認証成功 - User ID: {user_id}")

        # VODの取得（全タイプ）
        print("📺 VOD同期開始...")
        vod_results = {"new": 0, "updated": 0}
        
        for video_type in ["archive", "upload", "highlight"]:
            print(f"🔄 {video_type} タイプのVODを取得中...")
            result = fetch_vods(headers, user_id, video_type)
            vod_results["new"] += result["new"]
            vod_results["updated"] += result["updated"]

        # クリップの取得（前回同期時から今まで）
        print("✂️ クリップ同期開始...")
        last_sync = get_last_sync_time()
        current_time = datetime.utcnow()
        
        # 少し重複させて取得（漏れ防止）
        start_time = last_sync - timedelta(hours=1)  # 1時間前から
        
        clip_results = fetch_clips(headers, user_id, start_time, current_time)

        # VODとクリップの自動紐づけ
        print("🔗 VODとクリップの紐づけ処理...")
        linked_count = link_clips_to_vods()
        
        # 同期時刻を更新
        update_last_sync_time("clips")
        update_last_sync_time("vods")
        
        # 結果のサマリー
        sync_duration = (datetime.utcnow() - sync_start_time).total_seconds()
        
        result_summary = (
            f"✅ 同期完了 ({sync_duration:.1f}秒)\n"
            f"📺 VOD: 新規{vod_results['new']}件, 更新{vod_results['updated']}件\n"
            f"✂️ クリップ: 新規{clip_results['new']}件, 更新{clip_results['updated']}件\n"
            f"🔗 紐づけ: {linked_count}件"
        )
        
        print(result_summary)
        return result_summary
        
    except Exception as e:
        error_msg = f"❌ 同期エラー: {str(e)}"
        print(error_msg)
        return error_msg

def get_sync_status():
    """同期状態の詳細情報を取得"""
    try:
        conn = sqlite3.connect("vods.db", check_same_thread=False)
        c = conn.cursor()
        
        # 最後の同期時刻
        c.execute("SELECT sync_type, last_sync_time FROM sync_log ORDER BY created_at DESC")
        sync_logs = c.fetchall()
        
        # データ数
        c.execute("SELECT COUNT(*) FROM vods")
        vod_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM clips")
        clip_count = c.fetchone()[0]
        
        # 紐づけ済みクリップ数
        c.execute("SELECT COUNT(*) FROM clips WHERE vod_id IS NOT NULL")
        linked_clips = c.fetchone()[0]
        
        # 今日追加されたデータ
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM vods WHERE DATE(created_at) = ?", (today,))
        today_vods = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM clips WHERE DATE(created_at) = ?", (today,))
        today_clips = c.fetchone()[0]
        
        # YouTubeリンク数
        c.execute("SELECT COUNT(*) FROM youtube_links")
        youtube_links_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            "sync_logs": sync_logs,
            "vod_count": vod_count,
            "clip_count": clip_count,
            "linked_clips": linked_clips,
            "today_vods": today_vods,
            "today_clips": today_clips,
            "youtube_links_count": youtube_links_count
        }
        
    except Exception as e:
        return {"error": str(e)}

def manual_sync_range(start_date: datetime, end_date: datetime):
    """手動で期間を指定して同期"""
    print(f"🔧 手動同期: {start_date.date()} ～ {end_date.date()}")
    
    try:
        ensure_tables_exist()
        
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID")
        }
        user_id = get_user_id(headers)
        
        # 指定期間のクリップを取得
        clip_results = fetch_clips(headers, user_id, start_date, end_date)
        
        # 紐づけ処理
        linked_count = link_clips_to_vods()
        
        result = (
            f"✅ 手動同期完了\n"
            f"✂️ クリップ: 新規{clip_results['new']}件, 更新{clip_results['updated']}件\n"
            f"🔗 紐づけ: {linked_count}件"
        )
        
        print(result)
        return result
        
    except Exception as e:
        error_msg = f"❌ 手動同期エラー: {str(e)}"
        print(error_msg)
        return error_msg

def fix_all_youtube_links():
    """すべてのYouTubeリンクのvideo_idを修復"""
    conn = sqlite3.connect("vods.db", check_same_thread=False)
    c = conn.cursor()
    
    # すべてのYouTubeリンクを取得
    c.execute("SELECT id, url, video_id FROM youtube_links")
    all_links = c.fetchall()
    
    fixed_count = 0
    
    for link_id, url, current_video_id in all_links:
        # video_idを再抽出
        video_id = extract_youtube_video_id(url)
        
        # 現在のvideo_idと異なる場合、または空の場合に更新
        if video_id and video_id != current_video_id:
            c.execute("UPDATE youtube_links SET video_id = ? WHERE id = ?", (video_id, link_id))
            fixed_count += 1
            print(f"🔧 修復: {url} → video_id: {video_id}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ {fixed_count}件のYouTubeリンクを修復しました")
    return fixed_count

def extract_youtube_video_id(url):
    """YouTubeのURLからvideo_idを抽出する関数"""
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
    
    return None

# Streamlit用の簡単な管理関数
def streamlit_sync():
    """Streamlitから呼び出す同期処理"""
    return sync_data()

def streamlit_fix_links():
    """Streamlitから呼び出すリンク修復処理"""
    youtube_fixed = fix_all_youtube_links()
    clip_linked = link_clips_to_vods()
    
    return {
        "youtube_fixed": youtube_fixed,
        "clips_linked": clip_linked
    }