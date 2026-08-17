import discord
from discord.ext import commands, tasks
import json
import os
import sys
import asyncio
from datetime import datetime, time, timezone, timedelta

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_status_loop.start()
        self.daily_restart.start()
        self.background_economy_saver.start()

    def cog_unload(self):
        self.update_status_loop.cancel()
        self.daily_restart.cancel()
        self.background_economy_saver.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'ログイン成功: {self.bot.user.name} V14 (Gamble Ready)')
        await self.update_bot_status()

    async def save_server_count(self):
        try:
            total_members = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
            guild_count = len(self.bot.guilds)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            count_data = {"guilds": guild_count, "users": total_members}
            with open("server_count.json", "w", encoding="utf-8") as f:
                json.dump(count_data, f, ensure_ascii=False, indent=4)

            log_lines = [
                f"=== まきぐも 稼働状況ログ ({now_str}) ===\n",
                f"導入サーバー数: {guild_count}\n",
                f"総監視ユーザー数: {total_members}\n",
                "----------------------------------------\n"
            ]
            for guild in self.bot.guilds:
                owner_name = guild.owner.display_name if guild.owner else f"ID:{guild.owner_id}"
                invite_url = "取得不可"
                target_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if target_channel:
                    try:
                        invite = await target_channel.create_invite(max_age=0, max_uses=0, unique=False)
                        invite_url = invite.url
                    except:
                        pass
                log_lines.append(f"- {guild.name} (ID: {guild.id}) | 鯖主: {owner_name} | {guild.member_count}人 | 招待: {invite_url}\n")
            with open("log.txt", "w", encoding="utf-8") as f:
                f.writelines(log_lines)
        except Exception as e:
            print(f"⚠️ サーバー数保存エラー: {e}")

    async def update_bot_status(self):
        total_members = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{total_members}人の変態を監視中♡ | /help")
        await self.bot.change_presence(status=discord.Status.online, activity=activity)
        await self.save_server_count()

    @tasks.loop(time=time(hour=3, minute=0, tzinfo=timezone(timedelta(hours=9))))
    async def daily_restart(self):
        try:
            if self.bot.is_economy_dirty:
                self.bot._save_economy_sync_task()
            await self.bot.close()
        except:
            pass
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @tasks.loop(minutes=5)
    async def update_status_loop(self):
        if self.bot.is_ready():
            await self.update_bot_status()

    @tasks.loop(seconds=30)
    async def background_economy_saver(self):
        if self.bot.is_economy_dirty:
            await asyncio.to_thread(self.bot._save_economy_sync_task)
            self.bot.is_economy_dirty = False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        admin_id = os.getenv('ADMIN_USER_ID')
        
        if message.content == "!leave":
            app_info = await self.bot.application_info()
            is_admin = (admin_id and str(message.author.id) == admin_id) or (message.author.id == app_info.owner.id)
            if is_admin:
                if message.guild:
                    try:
                        await message.channel.send("管理者により退出させられました。")
                        await message.guild.leave()
                    except Exception:
                        pass
            return

        if message.content == "!wakarase":
            shutdown_id = os.getenv('SHUTDOWN_CHANNEL_ID')
            if shutdown_id and str(message.channel.id) == shutdown_id:
                app_info = await self.bot.application_info()
                is_admin = (admin_id and str(message.author.id) == admin_id) or (message.author.id == app_info.owner.id)
                if is_admin:
                    announcement = "【☁️ まきぐもちゃんからのお知らせ】\nただいまよりアップデートのため一時的にBotをシャットダウンします。"
                    for guild in self.bot.guilds:
                        target_channel = None
                        guild_id = str(guild.id)
                        if guild_id in self.bot.channel_settings and self.bot.channel_settings[guild_id]:
                            target_channel = self.bot.get_channel(self.bot.channel_settings[guild_id][0])
                        if not target_channel:
                            target_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                        if target_channel:
                            try:
                                await target_channel.send(announcement)
                            except:
                                pass
                    if self.bot.is_economy_dirty:
                        self.bot._save_economy_sync_task()
                    await self.bot.close()
                    return

        guild_id = str(message.guild.id) if message.guild else None
        if guild_id and guild_id in self.bot.channel_settings:
            allowed_channels = self.bot.channel_settings[guild_id]
            if isinstance(allowed_channels, int):
                allowed_channels = [allowed_channels]
            if message.channel.id not in allowed_channels:
                return

        triggered, filename = False, ""
        if "おはよ" in message.content: filename, triggered = "ohayo.txt", True
        elif "おやすみ" in message.content: filename, triggered = "oyasumi.txt", True
        elif "かわいい" in message.content or "可愛い" in message.content: filename, triggered = "kawaii.txt", True
        elif any(w in message.content for w in ["抜いた", "おなした", "オナした", "シコった", "しこった"]): filename, triggered = "nuita.txt", True
        elif self.bot.user.mentioned_in(message) or "まきぐも" in message.content: filename, triggered = "normal.txt", True

        if triggered:
            try:
                await message.reply(self.bot.get_line(filename).format(user=message.author.mention))
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(Events(bot))