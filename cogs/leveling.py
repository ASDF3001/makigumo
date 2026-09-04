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
                
        # 保存フラグを立てる
        self.bot.mark_economy_dirty()

async def setup(bot):
    await bot.add_cog(Leveling(bot))
