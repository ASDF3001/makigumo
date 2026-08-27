import discord
from discord.ext import commands
from discord import app_commands
import pg_shim as sqlite3
import contextlib
import urllib.parse
import aiohttp

class ProfileModal(discord.ui.Modal, title="まきぐも プロフィール設定"):
    birthday_input = discord.ui.TextInput(
        label="誕生日 (例: 12/25) ※空欄でクリア",
        style=discord.TextStyle.short,
        required=False,
        placeholder="12/25"
    )
    memo_input = discord.ui.TextInput(
        label="あなたに関する秘密のメモ (AIの記憶用)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        placeholder="好きなものや呼ばれ方などを書いてください。"
    )
    location_input = discord.ui.TextInput(
        label="所在地 (都道府県や市区町村) ※通知用",
        style=discord.TextStyle.short,
        required=False,
        placeholder="東京都新宿区"
    )

    def __init__(self, bot, current_birthday, current_memo, current_location):
        super().__init__()
        self.bot = bot
        if current_birthday:
            self.birthday_input.default = current_birthday
        if current_memo:
            self.memo_input.default = current_memo
        if current_location:
            self.location_input.default = current_location

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        
        bday_str = self.birthday_input.value.strip()
        memo_str = self.memo_input.value.strip()
        loc_str = self.location_input.value.strip()
        
        # 1. Birthday
        month, day = None, None
        if bday_str:
            import re
            m = re.match(r'^(\d{1,2})[/月-]\s*(\d{1,2})', bday_str)
            if m:
                month, day = int(m.group(1)), int(m.group(2))
        
        # 2. Location Geocoding
        lat, lon, pref = None, None, None
        address = loc_str
        if loc_str:
            try:
                url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(loc_str)}&count=1&language=ja&format=json"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "results" in data and len(data["results"]) > 0:
                                res = data["results"][0]
                                lat = res.get("latitude")
                                lon = res.get("longitude")
                                pref = res.get("admin1", res.get("name"))
                                address = res.get("name")
            except Exception as e:
                print(f"Geocoding error: {e}")
                
            # Open-Meteoで検索失敗した場合、Gemini APIで校正・座標取得を試みる
            if (lat is None or lon is None) and self.bot:
                ai_cog = self.bot.get_cog("AI")
                if ai_cog and hasattr(ai_cog, "api_keys") and ai_cog.api_keys:
                    import random
                    import json
                    import re
                    api_key = random.choice(ai_cog.api_keys)
                    prompt = f"地名 '{loc_str}' の緯度(lat)、経度(lon)、都道府県(pref)、市区町村(address)をJSON形式で出力してください。\n出力例: {{\"lat\": 35.6895, \"lon\": 139.6917, \"pref\": \"東京都\", \"address\": \"新宿区\"}}\nマークダウンは使わず純粋なJSON文字列のみを出力してください。"
                    text = ""
                    try:
                        from google import genai
                        client = genai.Client(api_key=api_key)
                        # ai_cogのキャッシュがあればそれを使う、なければ適当なflashモデル
                        model_name = getattr(ai_cog, "available_models_cache", ["gemini-2.5-flash"])[0]
                        resp = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        text = resp.text
                    except ImportError:
                        try:
                            import google.generativeai as legacy_genai
                            legacy_genai.configure(api_key=api_key)
                            model_name = getattr(ai_cog, "available_models_cache", ["gemini-1.5-flash"])[0]
                            model = legacy_genai.GenerativeModel(model_name)
                            resp = model.generate_content(prompt)
                            text = resp.text
                        except Exception as e:
                            print(f"Legacy Gemini geocoding error: {e}")
                    except Exception as e:
                        print(f"Gemini geocoding error: {e}")
                        
                    if text:
                        m = re.search(r'\{.*\}', text, re.DOTALL)
                        if m:
                            try:
                                js = json.loads(m.group(0))
                                lat = float(js.get("lat", 0)) if js.get("lat") else None
                                lon = float(js.get("lon", 0)) if js.get("lon") else None
                                pref = str(js.get("pref", ""))
                                address = str(js.get("address", ""))
                            except Exception as e:
                                print(f"Gemini geocoding json parse error: {e}")


        # Save to DB
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                
                # Birthday
                if month and day:
                    c.execute("INSERT OR REPLACE INTO birthdays (user_id, month, day, last_notified) VALUES (?, ?, ?, 0)", (user_id, month, day))
                else:
                    c.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
                    
                # Memo
                if memo_str:
                    c.execute("INSERT OR REPLACE INTO user_memos (user_id, memo) VALUES (?, ?)", (user_id, memo_str))
                else:
                    c.execute("DELETE FROM user_memos WHERE user_id = ?", (user_id,))
                    
                # Location
                c.execute("CREATE TABLE IF NOT EXISTS user_locations (user_id TEXT PRIMARY KEY, address TEXT, pref TEXT, lat REAL, lon REAL)")
                if loc_str and pref and lat and lon:
                    c.execute("INSERT OR REPLACE INTO user_locations (user_id, address, pref, lat, lon) VALUES (?, ?, ?, ?, ?)", (user_id, address, pref, lat, lon))
                else:
                    c.execute("DELETE FROM user_locations WHERE user_id = ?", (user_id,))
                    
                conn.commit()
                
            msg = "✅ **プロフィールを一括保存しました！**\n\n"
            if month and day:
                msg += f"🎂 **誕生日**: {month}月{day}日\n"
            if memo_str:
                msg += f"📝 **メモ**: {len(memo_str)}文字\n"
            if loc_str:
                if pref:
                    msg += f"📍 **所在地**: {pref} {address}\n"
                else:
                    msg += f"📍 **所在地**: 検索失敗 (正確な地名を入力してください)\n"
            
            if not month and not memo_str and not loc_str:
                msg += "🗑️ 全て空欄だったため、登録情報をクリアしました。"
                    
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 保存に失敗しました: {e}", ephemeral=True)

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="あなたの誕生日・メモ・所在地をまとめて確認・設定します")
    async def profile_cmd(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_bday = ""
        current_memo = ""
        current_loc = ""
        
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                # Birthday
                c.execute("CREATE TABLE IF NOT EXISTS birthdays (user_id TEXT PRIMARY KEY, month INTEGER, day INTEGER, last_notified INTEGER)")
                row_bday = c.execute("SELECT month, day FROM birthdays WHERE user_id = ?", (user_id,)).fetchone()
                if row_bday:
                    current_bday = f"{row_bday[0]}/{row_bday[1]}"
                
                # Memo
                c.execute("CREATE TABLE IF NOT EXISTS user_memos (user_id TEXT PRIMARY KEY, memo TEXT)")
                row_memo = c.execute("SELECT memo FROM user_memos WHERE user_id = ?", (user_id,)).fetchone()
                if row_memo:
                    current_memo = row_memo[0]
                    
                # Location
                c.execute("CREATE TABLE IF NOT EXISTS user_locations (user_id TEXT PRIMARY KEY, address TEXT, pref TEXT, lat REAL, lon REAL)")
                row_loc = c.execute("SELECT address FROM user_locations WHERE user_id = ?", (user_id,)).fetchone()
                if row_loc:
                    current_loc = row_loc[0]
        except Exception as e:
            print(f"Profile fetch error: {e}")
            
        modal = ProfileModal(self.bot, current_bday, current_memo, current_loc)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
