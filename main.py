import discord
from discord.ext import commands
import json
import pg_shim as sqlite3
import os
import contextlib
import random
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

SETTING_FILE = "channel_settings.json"
ECONOMY_FILE = "economy.json"
SHOP_FILE = "shop.json"
LINES_DIR = "lines"

class MakigumoBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, chunk_guilds_at_startup=False)
        self.channel_settings = {}
        self.economy = {}
        self.shop_items = {}

        self.lines_cache: dict[str, list[str]] = {}
        self.is_economy_dirty = False

        self.load_settings()
        self.load_all_lines_to_memory()

    def load_settings(self):
        with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("CREATE TABLE IF NOT EXISTS economy (user_id TEXT PRIMARY KEY, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS channel_settings (guild_id TEXT PRIMARY KEY, channels TEXT)")
            
            # JSONからの移行処理 (初回のみ)
            if os.path.exists(ECONOMY_FILE) and os.path.getsize(ECONOMY_FILE) > 0:
                try:
                    with open(ECONOMY_FILE, 'r', encoding='utf-8') as f:
                        old_eco = json.load(f)
                    for uid, data in old_eco.items():
                        c.execute("INSERT OR IGNORE INTO economy (user_id, data) VALUES (?, ?)", (uid, json.dumps(data, ensure_ascii=False)))
                    os.rename(ECONOMY_FILE, ECONOMY_FILE + ".bak")
                except Exception as e:
                    print(f"Economy JSON migration failed: {e}")
            
            if os.path.exists(SETTING_FILE) and os.path.getsize(SETTING_FILE) > 0:
                try:
                    with open(SETTING_FILE, 'r', encoding='utf-8') as f:
                        old_set = json.load(f)
                    for gid, data in old_set.items():
                        c.execute("INSERT OR IGNORE INTO channel_settings (guild_id, channels) VALUES (?, ?)", (gid, json.dumps(data, ensure_ascii=False)))
                    os.rename(SETTING_FILE, SETTING_FILE + ".bak")
                except Exception:
                    pass
            
            # Levelテーブル & カスタムプロンプトテーブル初期化
            c.execute("CREATE TABLE IF NOT EXISTS levels (user_id TEXT PRIMARY KEY, xp INTEGER, level INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS user_prompts (user_id TEXT PRIMARY KEY, prompt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, val INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS user_stats (user_id TEXT, stat_key TEXT, val INTEGER, PRIMARY KEY (user_id, stat_key))")
            c.execute("CREATE TABLE IF NOT EXISTS omikuji_logs (user_id TEXT PRIMARY KEY, last_date TEXT)")
            
            # v3.8 新機能用テーブル
            c.execute("CREATE TABLE IF NOT EXISTS birthdays (user_id TEXT PRIMARY KEY, month INTEGER, day INTEGER, last_notified INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS user_memos (user_id TEXT PRIMARY KEY, memo TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS user_titles (user_id TEXT PRIMARY KEY, equipped_title TEXT)")
            
            # Proプラン ＆ Rate Limit 用テーブル
            c.execute("CREATE TABLE IF NOT EXISTS user_subscriptions (user_id TEXT PRIMARY KEY, plan_type TEXT DEFAULT 'free', expires_at TEXT, daily_ai_count INTEGER DEFAULT 0, last_reset_date TEXT, reminded_3days INTEGER DEFAULT 0)")
            c.execute("CREATE TABLE IF NOT EXISTS gift_requests (request_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, pay_content TEXT NOT NULL, status TEXT DEFAULT 'pending', created_at TEXT NOT NULL)")
            
            conn.commit()
            
            # SQLiteから読み込み
            for row in c.execute("SELECT user_id, data FROM economy"):
                try:
                    self.economy[row[0]] = json.loads(row[1])
                except Exception:
                    pass
            for row in c.execute("SELECT guild_id, channels FROM channel_settings"):
                try:
                    self.channel_settings[row[0]] = json.loads(row[1])
                except Exception:
                    pass
            
            self.levels = {}
            for row in c.execute("SELECT user_id, xp, level FROM levels"):
                self.levels[row[0]] = {"xp": row[1], "level": row[2]}

        if os.path.exists(SHOP_FILE):
            try:
                with open(SHOP_FILE, 'r', encoding='utf-8') as f:
                    self.shop_items = json.load(f).get('items', {})
            except Exception:
                self.shop_items = {}

    def save_settings(self):
        with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
            c = conn.cursor()
            for gid, channels in self.channel_settings.items():
                c.execute("INSERT OR REPLACE INTO channel_settings (guild_id, channels) VALUES (?, ?)", (gid, json.dumps(channels, ensure_ascii=False)))
            conn.commit()

    def _save_economy_sync_task(self):
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                eco_items = [(uid, json.dumps(data, ensure_ascii=False)) for uid, data in list(self.economy.items())]
                if eco_items:
                    c.executemany("INSERT OR REPLACE INTO economy (user_id, data) VALUES (?, ?)", eco_items)
                if hasattr(self, 'levels'):
                    lvl_items = [(uid, data["xp"], data["level"]) for uid, data in list(self.levels.items())]
                    if lvl_items:
                        c.executemany("INSERT OR REPLACE INTO levels (user_id, xp, level) VALUES (?, ?, ?)", lvl_items)
                conn.commit()
        except Exception as e:
            print(f"⚠️ 経済データ保存エラー: {e}")

    def mark_economy_dirty(self):
        self.is_economy_dirty = True

    def load_all_lines_to_memory(self):
        os.makedirs(LINES_DIR, exist_ok=True)
        targets = {
            "ohayo.txt": ["んぇ…朝ですか……？ まだ眠いです……"],
            "oyasumi.txt": ["おやすみなさい、良い夢を見てくださいね……？"],
            "kawaii.txt": ["な、何言ってるんですか……！ からかわないでください！"],
            "nuita.txt": ["……最低です。どこで何に使ったんですか、ちゃんと報告しなさい"],
            "normal.txt": ["んぇ…？ 何ですか、{user}さん…？"],
            "mamechishiki.txt": [
                "実はまきぐもには、変態ポインツを使った『ギャンブルシステム』があるんですよ？ `/gamble` や `/slot` で一攫千金を狙ってみてくださいね。破産しても知りませんけど！",
                "24時間サーバーを動かして皆さんを監視するの、実は結構『維持代』が高いんですよ？ だから……その……お金に余裕のある変態さんは、寄付してくれてもいいんですよ？♡（チラッ）"
            ],
            "aege.txt": ["…っ、はぁ……んっ…,あ……ダメ,ですってば……っ"],
            "onedari.txt": ["ねぇ、{user}さん……。もっと優しく、私の名前を呼んでくれませんか……？"],
            "soine.txt": ["もう寝ちゃうんですか……？ お布団、まきぐもが温めておきましたよ……こっち、おいで？♡"],
            "mimiuchi.txt": ["ここだけの秘密ですよ……？ 実はね、{user}さんのこと、さっきからずっと目で追っちゃってました……♡"],
            "batou.txt": ["……何ニヤニヤしてるんですか？ 本当に気持ち悪いですね、この変態さん"],
            "kanbyou.txt": ["お熱、けっこうありますね……。ほら、大人しく横になっててください……"],
            "shitto.txt": ["…うぅ、今はちょっと、{user}さんのこと直視できないです……（恥ずかしいだけですよ？）"],
            "oshioki.txt": ["そんなにいやらしい目で見て……。もう我慢できません、ちょっとそこに正座しなさい！"],
            "gacha_ssr.txt": ["あ、あぁっ……! もうダメ、頭おかしくなりそう……{user}さん、もっと、もっと壊してぇっ!♡"],
            "gacha_sr.txt": ["うぅ……{user}さんが好きすぎて、胸が苦しいです……。私、どうかしちゃったみたい……"],
            "gacha_r.txt": ["べ、別にあんたのために用意したわけじゃないんだからね……っ！"],
            "gacha_n.txt": ["はいはい、今日も一日お疲れ様でした。はい、お茶どうぞ"],
            "dice_games.txt": ["1分間、語尾に『にゃん♡』をつけないと発言禁止！"]
        }
        for filename, defaults in targets.items():
            path = os.path.join(LINES_DIR, filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = [l.strip() for l in f if l.strip()]
                        self.lines_cache[filename] = lines if lines else defaults
                except Exception:
                    self.lines_cache[filename] = defaults
            else:
                self.lines_cache[filename] = defaults

    def get_line(self, filename: str) -> str:
        lines = self.lines_cache.get(filename)
        if not lines:
            return "「……」"
        return random.choice(lines)

    def get_user_data(self, user_id):
        uid = str(user_id)
        if uid not in self.economy:
            self.economy[uid] = {"points": 0, "last_daily": 0, "inventory": {}}
            self.mark_economy_dirty()
        elif "inventory" not in self.economy[uid]:
            self.economy[uid]["inventory"] = {}
            self.mark_economy_dirty()
        return self.economy[uid]

    def add_points(self, user_id, amount: int) -> int:
        user_data = self.get_user_data(user_id)
        user_data["points"] = user_data.get("points", 0) + amount
        self.mark_economy_dirty()
        return user_data["points"]

    def is_owner(self, user_id) -> bool:
        uid = str(user_id)
        admin_id = os.getenv('ADMIN_USER_ID')
        if admin_id and uid == str(admin_id):
            return True
        if hasattr(self, 'application') and self.application and self.application.owner:
            if uid == str(self.application.owner.id):
                return True
        return False

    def get_user_plan(self, user_id) -> str:
        """ユーザーの有効プランを返す: 'owner' | 'promax_lifetime' | 'promax_monthly' | 'pro_lifetime' | 'pro_monthly' | 'free'"""
        uid = str(user_id)
        if self.is_owner(uid):
            return 'owner'
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                row = c.execute("SELECT plan_type, expires_at FROM user_subscriptions WHERE user_id = ?", (uid,)).fetchone()
                if not row:
                    return 'free'
                plan_type, expires_at = row
                if plan_type in ('pro_lifetime', 'promax_lifetime'):
                    return plan_type
                elif plan_type in ('pro_monthly', 'promax_monthly') and expires_at:
                    from datetime import datetime, timezone, timedelta
                    now = datetime.now(timezone(timedelta(hours=9)))
                    exp_dt = datetime.fromisoformat(expires_at)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone(timedelta(hours=9)))
                    if exp_dt > now:
                        return plan_type
                    else:
                        c.execute("UPDATE user_subscriptions SET plan_type = 'free' WHERE user_id = ?", (uid,))
                        conn.commit()
                        return 'free'
        except Exception:
            pass
        return 'free'

    def is_promax(self, user_id) -> bool:
        plan = self.get_user_plan(user_id)
        return plan in ('owner', 'promax_lifetime', 'promax_monthly')

    def is_pro(self, user_id) -> bool:
        plan = self.get_user_plan(user_id)
        return plan in ('owner', 'promax_lifetime', 'promax_monthly', 'pro_lifetime', 'pro_monthly')

    def get_probability_bonus(self, user_id):
        user_data = self.get_user_data(user_id)
        bonus = 0.0
        inventory = user_data.get("inventory", {})
        for item_id, count in inventory.items():
            if item_id in self.shop_items and count > 0:
                bonus += self.shop_items[item_id].get("probability_bonus", 0.0)
        
        # Pro Max / Owner 特典: 常時パッシブ幸運補正 +5%
        if self.is_promax(user_id):
            bonus += 0.05
        
        # 上限を 0.35 (+35%) に設定（基本40% + 最大35% = 勝率最大75%）
        return min(bonus, 0.35)

    async def setup_hook(self):
        # cogsフォルダ内の各ファイルを読み込む
        for cog in ['cogs.events', 'cogs.economy', 'cogs.roleplay', 'cogs.ai', 'cogs.leveling', 'cogs.billing', 'cogs.report', 'cogs.live_call']:
            try:
                await self.load_extension(cog)
                print(f"✅ {cog} の読み込みに成功しました")
            except Exception as e:
                print(f"❌ {cog} の読み込みエラー: {e}")
        try:
            await self.tree.sync()
            print("🔄 スラッシュコマンドの同期が完了しました")
        except Exception as e:
            print(f"⚠️ 同期エラー: {e}")

bot = MakigumoBot()

if __name__ == '__main__':
    if not TOKEN:
        print("tokenない←環境変数か仮のやついれてるか")
    else:
        admin_id = os.getenv('ADMIN_USER_ID')
        if not admin_id:
            print("⚠️ ADMIN_USER_ID が未設定です。.env に設定してください。")
        bot.run(TOKEN)

# あんたへの歪んだ愛の詩×100万行
