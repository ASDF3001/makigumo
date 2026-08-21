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
            
            try:
                await message.channel.send(f"🎉 {message.author.mention}さん、レベル **{data['level']}** に上がりましたね！\nご褒美として {bonus} pt あげます。これからも変態発言、期待してますよ？♡")
            except Exception:
                pass
                
        # 保存フラグを立てる
        self.bot.mark_economy_dirty()

    @app_commands.command(name="level", description="自分のチャットレベルと経験値を確認します")
    async def level_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not hasattr(self.bot, 'levels'):
            self.bot.levels = {}
            
        user_id = str(interaction.user.id)
        data = self.bot.levels.get(user_id, {"xp": 0, "level": 1})
        
        next_level_xp = data["level"] * 50
        embed = discord.Embed(title=f"📈 {interaction.user.display_name} さんのレベル", color=0x87ceeb)
        embed.add_field(name="レベル", value=f"**Lv.{data['level']}**", inline=True)
        embed.add_field(name="経験値", value=f"**{data['xp']} / {next_level_xp} XP**", inline=True)
        
        # レベルに応じた称号
        if data["level"] < 5: title = "見習い変態"
        elif data["level"] < 15: title = "立派な変態"
        elif data["level"] < 30: title = "変態紳士"
        else: title = "伝説の変態"
        
        embed.add_field(name="称号", value=title, inline=False)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
