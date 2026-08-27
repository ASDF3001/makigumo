import discord
from discord.ext import commands, tasks
import pg_shim as sqlite3
import contextlib
import aiohttp
import datetime

class NotificationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_earthquake_id = None
        self.check_earthquake.start()
        self.check_weather.start()

    def cog_unload(self):
        self.check_earthquake.cancel()
        self.check_weather.cancel()

    @tasks.loop(minutes=1)
    async def check_earthquake(self):
        try:
            url = "https://api.p2pquake.net/v2/history?codes=551&limit=1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data: return
                        
                        eq = data[0]
                        eq_id = eq.get("id")
                        
                        # 初回起動時はIDを覚えるだけ
                        if self.last_earthquake_id is None:
                            self.last_earthquake_id = eq_id
                            return
                            
                        # 新しい地震があった場合
                        if eq_id != self.last_earthquake_id:
                            self.last_earthquake_id = eq_id
                            
                            earthquake = eq.get("earthquake", {})
                            max_scale = earthquake.get("maxScale", 0)
                            
                            # 震度3(30)以上の場合のみ
                            if max_scale >= 30:
                                scale_str = str(max_scale)[0] # 30->3, 40->4, 50->5弱など簡易化
                                points = eq.get("points", [])
                                affected_prefs = set([p.get("pref") for p in points if p.get("scale", 0) >= 30])
                                
                                if not affected_prefs:
                                    return
                                    
                                with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                                    c = conn.cursor()
                                    c.execute("CREATE TABLE IF NOT EXISTS user_locations (user_id TEXT PRIMARY KEY, address TEXT, pref TEXT, lat REAL, lon REAL)")
                                    rows = c.execute("SELECT user_id, pref FROM user_locations").fetchall()
                                    
                                    for row in rows:
                                        user_id, pref = row[0], row[1]
                                        if pref in affected_prefs:
                                            # DM送信
                                            user = self.bot.get_user(int(user_id))
                                            if user:
                                                try:
                                                    await user.send(f"🚨 **【地震速報】**\nご主人様！ {pref} で震度{scale_str}以上の揺れがあったみたいです…！\nケガとかしてないですか！？机の下に隠れてくださいねっ…！💦")
                                                except Exception:
                                                    pass
        except Exception as e:
            print(f"Earthquake check error: {e}")

    @check_earthquake.before_loop
    async def before_check_earthquake(self):
        await self.bot.wait_until_ready()

    # 毎日朝7:00 JST (UTC 22:00)
    @tasks.loop(time=datetime.time(hour=22, minute=0, tzinfo=datetime.timezone.utc))
    async def check_weather(self):
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS user_locations (user_id TEXT PRIMARY KEY, address TEXT, pref TEXT, lat REAL, lon REAL)")
                rows = c.execute("SELECT user_id, lat, lon, address FROM user_locations").fetchall()
                
            for row in rows:
                user_id, lat, lon, address = row[0], row[1], row[2], row[3]
                if not lat or not lon: continue
                
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,precipitation_sum&timezone=Asia%2FTokyo&forecast_days=1"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            daily = data.get("daily", {})
                            code = daily.get("weathercode", [0])[0]
                            
                            # WMO Weather interpretation codes
                            # 51-67, 80-82 = Rain
                            # 71-77, 85-86 = Snow
                            is_rain = (51 <= code <= 67) or (80 <= code <= 82)
                            is_snow = (71 <= code <= 77) or (85 <= code <= 86)
                            
                            user = self.bot.get_user(int(user_id))
                            if user:
                                try:
                                    if is_rain:
                                        await user.send(f"☔ **【お天気アラート】**\nおはようございます、ご主人様！\n今日の {address} は雨が降るみたいです。絶対に傘を忘れないでくださいねっ！風邪引いたら怒るんですから！")
                                    elif is_snow:
                                        await user.send(f"⛄ **【お天気アラート】**\nおはようございます、ご主人様！\n今日の {address} は雪が降るみたいです。暖かくして出かけてくださいねっ！")
                                except Exception:
                                    pass
        except Exception as e:
            print(f"Weather check error: {e}")

    @check_weather.before_loop
    async def before_check_weather(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(NotificationsCog(bot))
