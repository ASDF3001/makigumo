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
        self.status_index = 0
        self.update_status_loop.start()
        self.daily_restart.start()
        self.background_economy_saver.start()

    def cog_unload(self):
        self.update_status_loop.cancel()
        self.daily_restart.cancel()
        self.background_economy_saver.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        version = "V14"
        update_dir = "update"
        if os.path.exists(update_dir):
            files = [f for f in os.listdir(update_dir) if f.endswith(".txt")]
            if files:
                files.sort(reverse=True)
                version = files[0].replace('.txt', '')
        print(f'ログイン成功: {self.bot.user.name} {version} (Gamble Ready)')
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
        try:
            total_members = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
            guild_count = len(self.bot.guilds)
            
            try:
                latency_ms = round(self.bot.latency * 1000)
            except (OverflowError, ValueError):
                latency_ms = 0
                
            stream_url = "https://rds9.pages.dev/"

            chat_count, cmd_count = 0, 0
            import sqlite3
            try:
                with sqlite3.connect("database.db") as conn:
                    c = conn.cursor()
                    r1 = c.execute("SELECT val FROM bot_stats WHERE key = 'chat_count'").fetchone()
                    if r1: chat_count = r1[0]
                    r2 = c.execute("SELECT val FROM bot_stats WHERE key = 'cmd_count'").fetchone()
                    if r2: cmd_count = r2[0]
            except Exception:
                pass

            if self.status_index == 0:
                status_text = f"{total_members}人の変態を監視中♡ | /help"
            elif self.status_index == 1:
                status_text = f"{guild_count}サーバーで監視中♡"
            elif self.status_index == 2:
                status_text = f"💬 {chat_count}回の会話 | ⚡ {cmd_count}回のコマンド"
            elif self.status_index == 3:
                status_text = f"ping: {latency_ms}ms"
            else:
                status_text = "Powered by rds9"

            activity = discord.Streaming(name=status_text, url=stream_url)
            self.status_index = (self.status_index + 1) % 5

            await self.bot.change_presence(status=discord.Status.online, activity=activity)
            await self.save_server_count()
        except Exception as e:
            print(f"⚠️ ステータス更新エラー: {e}")

    @tasks.loop(time=time(hour=3, minute=0, tzinfo=timezone(timedelta(hours=9))))
    async def daily_restart(self):
        try:
            if self.bot.is_economy_dirty:
                self.bot._save_economy_sync_task()
            await self.bot.close()
        except:
            pass
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @tasks.loop(seconds=3)
    async def update_status_loop(self):
        if self.bot.is_ready():
            await self.update_bot_status()

    @tasks.loop(seconds=30)
    async def background_economy_saver(self):
        if self.bot.is_economy_dirty:
            await asyncio.to_thread(self.bot._save_economy_sync_task)
            self.bot.is_economy_dirty = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        
        # VCに参加した時
        if before.channel is None and after.channel is not None:
            # 1人だけの時（自分が入って1人＝誰もいないVCに入った）
            if len(after.channel.members) == 1:
                try:
                    # Voice Channel付属のテキストチャットへ送信
                    await after.channel.send(f"「{member.mention}さん、こんなところで1人で何やってるんですか…？ ちゃんと監視してますからね」")
                except Exception:
                    pass

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

        if not message.guild:
            return

        guild_id = str(message.guild.id)
        if guild_id in self.bot.channel_settings:
            allowed_channels = self.bot.channel_settings[guild_id]
            if isinstance(allowed_channels, int):
                allowed_channels = [allowed_channels]
            if message.channel.id not in allowed_channels:
                return

        triggered, filename = False, ""
        if "まきぐそ" in message.content:
            try:
                await message.reply("「……は？ 誰がまきぐそですか！？ ふざけないでください！ 次そんなこと言ったら本当に許しませんからね！この変態ゴミカス！💢💢」")
            except discord.Forbidden:
                pass
            return
        elif "おはよ" in message.content: filename, triggered = "ohayo.txt", True
        elif "おやすみ" in message.content: filename, triggered = "oyasumi.txt", True
        elif "かわいい" in message.content or "可愛い" in message.content: filename, triggered = "kawaii.txt", True
        elif any(w in message.content for w in ["抜いた", "おなした", "オナした", "シコった", "しこった"]): filename, triggered = "nuita.txt", True
        elif self.bot.user.mentioned_in(message) or "まきぐも" in message.content: filename, triggered = "normal.txt", True

        if triggered:
            try:
                import sqlite3
                with sqlite3.connect("database.db") as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO bot_stats (key, val) VALUES ('chat_count', 1) ON CONFLICT(key) DO UPDATE SET val = val + 1")
                    c.execute("INSERT INTO user_stats (user_id, stat_key, val) VALUES (?, 'chat_count', 1) ON CONFLICT(user_id, stat_key) DO UPDATE SET val = val + 1", (str(message.author.id),))
                    conn.commit()
            except Exception:
                pass
            try:
                await message.reply(self.bot.get_line(filename).format(user=message.author.mention))
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        try:
            import sqlite3
            user_id = str(interaction.user.id)
            cmd_name = command.name
            with sqlite3.connect("database.db") as conn:
                c = conn.cursor()
                c.execute("INSERT INTO bot_stats (key, val) VALUES ('cmd_count', 1) ON CONFLICT(key) DO UPDATE SET val = val + 1")
                c.execute("INSERT INTO user_stats (user_id, stat_key, val) VALUES (?, 'cmd_count', 1) ON CONFLICT(user_id, stat_key) DO UPDATE SET val = val + 1", (user_id,))
                # 個別コマンドカウント（お仕置き・罵倒等）
                c.execute("INSERT INTO user_stats (user_id, stat_key, val) VALUES (?, ?, 1) ON CONFLICT(user_id, stat_key) DO UPDATE SET val = val + 1", (user_id, f"cmd_{cmd_name}"))
                conn.commit()
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(Events(bot))