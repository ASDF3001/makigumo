import os
import psycopg2
import psycopg2.pool

pool = None

def _translate_query(query):
    # Translate sqlite ? to postgres %s
    # Fast replace keeping track of strings would be safe, but realistically in this bot we don't have ? inside literals.
    query = query.replace("?", "%s")
    
    # Translate INSERT OR REPLACE INTO -> INSERT INTO ... ON CONFLICT (...) DO UPDATE SET ...
    if "INSERT OR REPLACE INTO" in query:
        if "user_memos" in query:
            query = query.replace("INSERT OR REPLACE INTO user_memos", "INSERT INTO user_memos")
            query += " ON CONFLICT(user_id) DO UPDATE SET memo=EXCLUDED.memo"
        elif "user_prompts" in query:
            query = query.replace("INSERT OR REPLACE INTO user_prompts", "INSERT INTO user_prompts")
            query += " ON CONFLICT(user_id) DO UPDATE SET prompt=EXCLUDED.prompt"
        elif "user_titles" in query:
            query = query.replace("INSERT OR REPLACE INTO user_titles", "INSERT INTO user_titles")
            query += " ON CONFLICT(user_id) DO UPDATE SET equipped_title=EXCLUDED.equipped_title"
        elif "omikuji_logs" in query:
            query = query.replace("INSERT OR REPLACE INTO omikuji_logs", "INSERT INTO omikuji_logs")
            query += " ON CONFLICT(user_id) DO UPDATE SET last_date=EXCLUDED.last_date"
        elif "birthdays" in query:
            query = query.replace("INSERT OR REPLACE INTO birthdays", "INSERT INTO birthdays")
            query += " ON CONFLICT(user_id) DO UPDATE SET month=EXCLUDED.month, day=EXCLUDED.day, last_notified=EXCLUDED.last_notified"
        elif "channel_settings" in query:
            query = query.replace("INSERT OR REPLACE INTO channel_settings", "INSERT INTO channel_settings")
            query += " ON CONFLICT(guild_id) DO UPDATE SET channels=EXCLUDED.channels"
        elif "economy" in query:
            query = query.replace("INSERT OR REPLACE INTO economy", "INSERT INTO economy")
            query += " ON CONFLICT(user_id) DO UPDATE SET data=EXCLUDED.data"
        elif "levels" in query:
            query = query.replace("INSERT OR REPLACE INTO levels", "INSERT INTO levels")
            query += " ON CONFLICT(user_id) DO UPDATE SET xp=EXCLUDED.xp, level=EXCLUDED.level"
        elif "user_locations" in query:
            query = query.replace("INSERT OR REPLACE INTO user_locations", "INSERT INTO user_locations")
            query += " ON CONFLICT(user_id) DO UPDATE SET address=EXCLUDED.address, pref=EXCLUDED.pref, lat=EXCLUDED.lat, lon=EXCLUDED.lon"
            
    if "INSERT OR IGNORE INTO economy" in query:
        query = query.replace("INSERT OR IGNORE INTO economy", "INSERT INTO economy")
        query += " ON CONFLICT(user_id) DO NOTHING"
    if "INSERT OR IGNORE INTO channel_settings" in query:
        query = query.replace("INSERT OR IGNORE INTO channel_settings", "INSERT INTO channel_settings")
        query += " ON CONFLICT(guild_id) DO NOTHING"
        
    return query

class PgShimCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, vars=None):
        if "PRAGMA" in query or "CREATE TABLE IF NOT EXISTS" in query:
            if "PRAGMA" in query:
                return self
            if "AUTOINCREMENT" in query:
                query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            
            # 既存テーブル以外の新規作成用
            if "user_locations" in query and "CREATE TABLE" in query:
                query = query.replace("REAL", "DOUBLE PRECISION")
        
        query = _translate_query(query)
        if vars:
            self.cursor.execute(query, vars)
        else:
            self.cursor.execute(query)
        return self

    def executemany(self, query, vars_list):
        query = _translate_query(query)
        self.cursor.executemany(query, vars_list)
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)

class PgShimConnection:
    def __init__(self, conn):
        self.conn = conn
        # In sqlite3, row_factory is used sometimes. But in this bot, no row_factory is used.

    def cursor(self):
        return PgShimCursor(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        global pool
        if pool:
            pool.putconn(self.conn)

    def __enter__(self):
        # sqlite3 enter just returns self (or starts transaction, actually psycopg2 connection acts as context manager for transaction too)
        # But wait, psycopg2 conn.__enter__ returns the connection and wraps in a transaction!
        self.conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.__exit__(exc_type, exc_val, exc_tb)

def connect(*args, **kwargs):
    global pool
    url = os.getenv("DATABASE_URL")
    if url:
        if pool is None:
            pool = psycopg2.pool.ThreadedConnectionPool(1, 20, dsn=url)
        conn = pool.getconn()
        return PgShimConnection(conn)
    else:
        # Fallback to local sqlite3 if DATABASE_URL is missing
        import sqlite3
        return sqlite3.connect(*args, **kwargs)
