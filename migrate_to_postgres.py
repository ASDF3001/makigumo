import asyncio
import sqlite3
import os
import sys

try:
    import asyncpg
    from dotenv import load_dotenv
except ImportError:
    print("必要なライブラリがありません。実行前に以下をインストールしてください:")
    print("pip install asyncpg python-dotenv")
    sys.exit(1)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ .envファイルに DATABASE_URL が設定されていません！")
    print("例: DATABASE_URL=postgresql://postgres.xxx:YOUR_PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres")
    sys.exit(1)

if not os.path.exists("database.db"):
    print("❌ database.db が見つかりません！同じフォルダに置いてください。")
    sys.exit(1)

async def main():
    print("🔌 Supabase (PostgreSQL) に接続中...")
    try:
        conn_pg = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return

    print("✅ 接続成功！テーブルを作成します...")
    
    # 1. テーブル作成
    await conn_pg.execute("""
        CREATE TABLE IF NOT EXISTS economy (user_id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS channel_settings (guild_id TEXT PRIMARY KEY, channels TEXT);
        CREATE TABLE IF NOT EXISTS levels (user_id TEXT PRIMARY KEY, xp INTEGER, level INTEGER);
        CREATE TABLE IF NOT EXISTS user_prompts (user_id TEXT PRIMARY KEY, prompt TEXT);
        CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, val INTEGER);
        CREATE TABLE IF NOT EXISTS user_stats (user_id TEXT, stat_key TEXT, val INTEGER, PRIMARY KEY (user_id, stat_key));
        CREATE TABLE IF NOT EXISTS omikuji_logs (user_id TEXT PRIMARY KEY, last_date TEXT);
        CREATE TABLE IF NOT EXISTS birthdays (user_id TEXT PRIMARY KEY, month INTEGER, day INTEGER, last_notified INTEGER);
        CREATE TABLE IF NOT EXISTS user_memos (user_id TEXT PRIMARY KEY, memo TEXT);
        CREATE TABLE IF NOT EXISTS user_titles (user_id TEXT PRIMARY KEY, equipped_title TEXT);
        CREATE TABLE IF NOT EXISTS user_subscriptions (user_id TEXT PRIMARY KEY, plan_type TEXT DEFAULT 'free', expires_at TEXT, daily_ai_count INTEGER DEFAULT 0, last_reset_date TEXT, reminded_3days INTEGER DEFAULT 0);
        
        -- gift_requests is special because it has AUTOINCREMENT in SQLite (SERIAL in PG)
        CREATE TABLE IF NOT EXISTS gift_requests (
            request_id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            pay_content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
    """)

    print("✅ テーブル作成完了！データの流し込みを開始します...")

    conn_sl = sqlite3.connect("database.db")
    c = conn_sl.cursor()
    
    tables = [
        "economy", "channel_settings", "levels", "user_prompts", "bot_stats",
        "user_stats", "omikuji_logs", "birthdays", "user_memos", "user_titles",
        "user_subscriptions", "gift_requests"
    ]

    for table in tables:
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        if not rows:
            print(f"⏩ {table} は空なのでスキップします")
            continue
            
        print(f"📥 {table} のデータを転送中 ({len(rows)} 件)...")
        
        # Get column names
        c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in c.fetchall()]
        
        col_names = ", ".join(columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        
        # ON CONFLICT DOES NOTHING 
        if table == "user_stats":
            conflict = "ON CONFLICT (user_id, stat_key) DO NOTHING"
        elif table == "gift_requests":
            conflict = "ON CONFLICT (request_id) DO NOTHING"
        else:
            conflict = f"ON CONFLICT ({columns[0]}) DO NOTHING"

        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) {conflict}"
        
        # executemany in asyncpg
        await conn_pg.executemany(query, rows)

    conn_sl.close()
    await conn_pg.close()
    print("🎉 データの移行がすべて完了しました！！！")

if __name__ == "__main__":
    asyncio.run(main())
