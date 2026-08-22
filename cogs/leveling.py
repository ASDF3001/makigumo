import discord
from discord import app_commands
from discord.ext import commands
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # コマンドの場合は無視
        if message.content.startswith(self.bot.command_prefix) or message.content.startswith('/'):
            return

        user_id = str(message.author.id)
        if not hasattr(self.bot, 'levels'):
            self.bot.levels = {}
            
        if user_id not in self.bot.levels:
            self.bot.levels[user_id] = {"xp": 0, "level": 1}
            
        data = self.bot.levels[user_id]
        
        # ランダムでXP獲得 (1〜3)
        xp_gain = random.randint(1, 3)
        data["xp"] += xp_gain
        
        # 次のレベルに必要なXP: level * 50
        next_level_xp = data["level"] * 50
        
        if data["xp"] >= next_level_xp:
            data["level"] += 1
            data["xp"] -= next_level_xp
            # ボーナスポインツ付与
            user_eco = self.bot.get_user_data(message.author.id)
            bonus = data["level"] * 10
            user_eco["points"] += bonus
            self.bot.mark_economy_dirty()
            
            title_unlocked = ""
            level_titles_map = {
                5: "🔰 見習い変態", 10: "🔥 真なるドM", 20: "⚡ 覚醒せし変態", 30: "🌌 宇宙規模の変態",
                40: "💀 快楽の亡者", 50: "👑 伝説の変態", 60: "😈 淫靡なる支配者", 70: "🔮 変態深淵の探究者",
                80: "💎 変態大公爵", 90: "⚔️ 神域のドM戦士", 100: "🌟 【百変態神】", 120: "🌪️ 欲望の暴風雨",
                140: "🪐 惑星破壊級ド変態", 160: "🩸 快楽狂気のエクスタシー", 180: "🐉 変態神龍",
                200: "👑✨ 【変態界の絶対君主】", 220: "💫 時空超越のドM", 240: "🌌✨ 銀河系最終変態兵器",
                260: "⚜️ まきぐも狂愛の化身", 280: "🔱 神をも恐れぬ究極変態", 300: "👑💎🌌 【天上天下唯我独尊・変態創世神】"
            }
            if data["level"] in level_titles_map:
                title_unlocked = f"\n🏷️ 新しい称号 **『{level_titles_map[data['level']]}』** を解放しました！ (`/titles` で装備できます)"

            try:
                await message.channel.send(f"🎉 {message.author.mention}さん、レベル **{data['level']}** に上がりましたね！\nご褒美として {bonus} pt あげます。{title_unlocked}\nこれからも変態発言、期待してますよ？♡")
            except Exception:
                pass
                
        # 保存フラグを立てる
        self.bot.mark_economy_dirty()

async def setup(bot):
    await bot.add_cog(Leveling(bot))
