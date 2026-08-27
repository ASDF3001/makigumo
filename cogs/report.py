import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
from datetime import datetime

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="report", description="【緊急バグ報告】まきぐもBotのバグや異常を開発者に報告します")
    @app_commands.describe(内容="発生している問題の詳細を記述してください")
    async def report_cmd(self, interaction: discord.Interaction, 内容: str):
        await interaction.response.defer(ephemeral=True)
        
        user = interaction.user
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_text = f"[{now_str}] 報告者: {user.display_name} (ID: {user.id})\\n内容: {内容}\\n"
        
        admin_id = os.getenv('ADMIN_USER_ID')
        success_dm = False
        
        # 1. 開発者へのDM送信を試みる
        if admin_id:
            try:
                target = await self.bot.fetch_user(int(admin_id))
                if target:
                    embed = discord.Embed(
                        title="🚨 まきぐも 緊急バグ報告 🚨",
                        description=f"**送信者**: {user.mention}\\n**サーバー**: {interaction.guild.name if interaction.guild else 'DM'}\\n\\n**【内容】**\\n{内容}",
                        color=0xFF0000
                    )
                    await target.send(embed=embed)
                    success_dm = True
            except Exception as e:
                print(f"⚠️ 管理者DM送信失敗: {e}")
                success_dm = False

        # 2. DMに失敗した場合、または確実に残すためにローカルファイルへ出力 (緊急ログ)
        try:
            with open("CRITICAL_REPORTS.txt", "a", encoding="utf-8") as f:
                f.write(report_text + "-"*40 + "\\n")
            
            # コンソールに目立つように出力 (ANSIレッド) + ベル文字
            print(f"\\033[91m\\a\\n{'='*50}\\n🚨 【緊急レポート受信】 🚨\\n{report_text}{'='*50}\\n\\033[0m")
        except Exception as e:
            print(f"CRITICAL ERROR writing report: {e}")

        # 3. ユーザーへ完了メッセージ
        if success_dm:
            await interaction.followup.send("✅ 報告を受け付けました！開発者に直接DMで通知しました。", ephemeral=True)
        else:
            await interaction.followup.send("✅ 報告を受け付けました！ネットワークが不安定なため、サーバーの緊急ログファイルに直接書き込みました。", ephemeral=True)


    @app_commands.command(name="download_db", description="【開発者専用】現在のデータベースファイルをDiscord経由でダウンロードします")
    async def download_db_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.bot.is_owner(str(interaction.user.id)):
            await interaction.followup.send("このコマンドは開発者専用です。")
            return
            
        import os
        if not os.path.exists("database.db"):
            await interaction.followup.send("database.db が見つかりません。")
            return
            
        file = discord.File("database.db", filename="database.db")
        await interaction.followup.send("📦 データベースのバックアップファイルです！", file=file)


    @app_commands.command(name="rescue_files", description="【開発者専用】database.dbと.envをDMに送信して救出します")
    async def rescue_files_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.bot.is_owner(str(interaction.user.id)):
            await interaction.followup.send("このコマンドは開発者専用です。")
            return
            
        import os
        files_to_send = []
        if os.path.exists("database.db"):
            files_to_send.append(discord.File("database.db", filename="database.db"))
        if os.path.exists(".env"):
            files_to_send.append(discord.File(".env", filename=".env"))
            
        if not files_to_send:
            await interaction.followup.send("ファイルが見つかりません。")
            return
            
        try:
            await interaction.user.send("📦 救出ファイルのお届けです！取扱注意！", files=files_to_send)
            await interaction.followup.send("✅ DMにファイルを送信しました！")
        except Exception as e:
            await interaction.followup.send(f"⚠️ DMの送信に失敗しました（DM設定が閉じているかも？）：{e}")

async def setup(bot):
    await bot.add_cog(Report(bot))
