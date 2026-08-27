import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import contextlib

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    def get_embed(self, category):
        if category == "home":
            e = discord.Embed(title="☁️ まきぐもちゃん 総合ヘルプガイド", description="サーバー＆DMに常駐して、あなたたち「変態さん」を監視・癒やし・お仕置きするBotです♡", color=0xffb6c1)
            e.add_field(name="🤖 まきぐもAI (ZETA機能)", value="`/ai [メッセージ]` : まきぐもAIとチャット（無料100回 / Pro300回 / Pro Max 1000回・記憶最大200件）\n`/user_settings [プロンプト]` : AIの性格・プロンプトを自分専用にカスタム\n📩 **DM送信** : Bot宛てに直接DMを送るだけでタイマンAIチャット可能！", inline=False)
            e.add_field(name="💬 チャット自動反応ワード (サーバー内)", value="`まきぐも` / `おはよ` / `おやすみ` / `かわいい` / `抜いた` / `まきぐそ`", inline=False)
            e.add_field(name="🔗 公式リンク・有料プラン", value="`/pro` : Pro / Pro Maxプラン案内＆申込（Pro:月100円/買切500円, Pro Max:月250円/買切1500円）\n`/plan` : 現在のプラン＆残り会話数確認\n`/server` : 公式Discordサーバー", inline=False)
            return e
        elif category == "rp":
            e = discord.Embed(title="💕 シチュエーション・お遊び", color=0xffb6c1)
            e.add_field(name="AI・カスタム機能", value="`/ai` : AI会話（往復50件記憶）\n`/ai_mode` : 性格モードワンタッチ変更\n`/reset_ai` : AI記憶リセット\n`/user_settings` : カスタムプロンプト設定\n`/profile` : 誕生日・所在地（AI自動補正）・メモの設定\n`/update` / `/version`", inline=False)
            e.add_field(name="シチュエーション＆エンタメ", value="`/play` : 各種シチュエーション（お仕置き/罵倒/看病/嫉妬/喘ぐ/おねだり/添い寝/耳打ち）\n`/gacha` : まきぐもガチャ\n`/omikuji` : 変態おみくじ（1日1回）\n`/present` : まきぐもにお貢ぎ・プレゼント\n`/相性` / `/豆知識`", inline=False)
            return e
        elif category == "game":
            e = discord.Embed(title="🎰 ギャンブル＆レベル・ステータス", color=0xffb6c1)
            e.add_field(name="レベル＆カルテシステム", value="`/stats` : あなたの変態カルテ（レベル・XP・称号・勝率・AI対話数・所持品）を表示", inline=False)
            e.add_field(name="カジノ・経済コマンド", value="`/daily` / `/gamble` / `/slot` / `/ダイス_罰ゲーム` / `/shop` / `/work` / `/pay` / `/ranking` / `/use`", inline=False)
            return e
        elif category == "admin":
            e = discord.Embed(title="⚙️ サーバー管理者向け機能", color=0xffb6c1)
            e.add_field(name="動作管理", value="`/setting` : 反応チャンネルを指定\n`/invite` : 別サーバーに招待\n`/server` : 公式サーバー\n`/donate` : 寄付案内", inline=False)
            return e

    @discord.ui.button(label="🏠 ホーム", style=discord.ButtonStyle.blurple)
    async def btn_home(self, interaction, button): await interaction.response.edit_message(embed=self.get_embed("home"))
    @discord.ui.button(label="💕 シチュエーション", style=discord.ButtonStyle.secondary)
    async def btn_rp(self, interaction, button): await interaction.response.edit_message(embed=self.get_embed("rp"))
    @discord.ui.button(label="🎰 ギャンブル", style=discord.ButtonStyle.success)
    async def btn_game(self, interaction, button): await interaction.response.edit_message(embed=self.get_embed("game"))
    @discord.ui.button(label="⚙️ 管理設定", style=discord.ButtonStyle.danger)
    async def btn_admin(self, interaction, button): await interaction.response.edit_message(embed=self.get_embed("admin"))

class Roleplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="まきぐもちゃんの使い方・コマンド一覧を表示します")
    async def help_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = HelpView()
        await interaction.followup.send(embed=view.get_embed("home"), view=view)

    @app_commands.command(name="update", description="まきぐもちゃんのアップデート内容を確認します")
    @app_commands.describe(version="確認したいバージョン（例: v3.0）。空欄で最新のものを表示します")
    async def update_cmd(self, interaction: discord.Interaction, version: str = None):
        await interaction.response.defer(ephemeral=True)
        update_dir = "update"
        
        if not os.path.exists(update_dir):
            return await interaction.followup.send("「まだアップデート情報がないみたいです…」", ephemeral=True)

        files = [f for f in os.listdir(update_dir) if f.endswith(".txt")]
        if not files:
            return await interaction.followup.send("「アップデート情報が空っぽです！」", ephemeral=True)

        if version:
            target_file = f"{version}.txt" if not version.endswith(".txt") else version
            if target_file not in files:
                return await interaction.followup.send(f"「{version} のアップデート情報は見つかりませんでした…」", ephemeral=True)
        else:
            files.sort(reverse=True)
            target_file = files[0]

        try:
            with open(os.path.join(update_dir, target_file), "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                content = "現在、新しいアップデート情報はありません。"
        except Exception:
            content = "ファイルの読み込みに失敗しました。"

        display_version = target_file.replace('.txt', '')
        embed = discord.Embed(title=f"☁️ まきぐも アップデート情報 ({display_version})", description=content, color=0x87ceeb)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="version", description="確認できるアップデートのバージョン一覧を表示します（最新10件まで）")
    async def version_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        update_dir = "update"
        
        if not os.path.exists(update_dir):
            return await interaction.followup.send("「まだアップデート情報がないみたいです…」", ephemeral=True)

        files = [f for f in os.listdir(update_dir) if f.endswith(".txt")]
        if not files:
            return await interaction.followup.send("「アップデート情報が空っぽです！」", ephemeral=True)

        files.sort(reverse=True)
        recent_files = files[:10]

        version_list = "\n".join([f"- **{f.replace('.txt', '')}**" for f in recent_files])

        embed = discord.Embed(title="☁️ 閲覧可能なバージョン一覧", description=version_list, color=0x87ceeb)
        embed.set_footer(text="内容を見るには /update [バージョン] と入力してね！")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setting", description="まきぐもが反応するチャンネルを設定します")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setting(self, interaction: discord.Interaction, メイン: discord.TextChannel, サブ1: discord.TextChannel = None, サブ2: discord.TextChannel = None, サブ3: discord.TextChannel = None, サブ4: discord.TextChannel = None):
        await interaction.response.defer()
        guild_id = str(interaction.guild_id)
        raw_channels = [メイン.id]
        if サブ1: raw_channels.append(サブ1.id)
        if サブ2: raw_channels.append(サブ2.id)
        if サブ3: raw_channels.append(サブ3.id)
        if サブ4: raw_channels.append(サブ4.id)

        valid = [cid for cid in set(raw_channels) if isinstance(self.bot.get_channel(cid), discord.TextChannel)]
        if not valid: return await interaction.followup.send("❌ 指定チャンネルが無効です", ephemeral=True)

        self.bot.channel_settings[guild_id] = valid
        self.bot.save_settings()
        await interaction.followup.send(f"了解です♡ これから指定されたチャンネルでのみお返事しますね。")

    @app_commands.command(name="invite", description="まきぐもちゃんを別のサーバーに招待するリンクを表示します")
    async def invite(self, interaction: discord.Interaction):
        await interaction.response.defer()
        url = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=277025508352&scope=bot%20applications.commands"
        await interaction.followup.send(f"「こちらのリンクから招待してくださいね！」\n{url}")

    @app_commands.command(name="server", description="まきぐもぼっと公式Discordサーバーの招待リンクを表示します")
    async def server(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("☁️ **まきぐもぼっと 公式Discordサーバー**\nhttps://discord.gg/kxFCwCj2eX")

    @app_commands.command(name="donate", description="まきぐもちゃん＆開発者（rds9）への寄付・支援方法をご案内します")
    async def donate(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        msg = (
            "💖 **まきぐもちゃん 寄付・支援のご案内** 💖\n\n"
            "まきぐもちゃんの開発・サーバー維持費用をサポートしていただける変態さんは、"
            "ぜひ Discord で **rds9** へ直接ご連絡いただくか、\n"
            "メール: [rds9discord@outlook.jp](mailto:rds9discord@outlook.jp) までご連絡いただけますと非常に助かります！✨\n\n"
            "温かいご支援、心よりお待ちしております！♡"
        )
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="豆知識", description="まきぐもちゃんのヒミツの豆知識を披露します")
    async def mamechishiki(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(f"💡 **まきぐも豆知識**\n{self.bot.get_line('mamechishiki.txt')}")



    @app_commands.command(name="play", description="まきぐもといろんなシチュエーションで遊びます")
    @app_commands.choices(シチュエーション=[
        app_commands.Choice(name="喘ぐ", value="nuita.txt"),
        app_commands.Choice(name="おねだり", value="onedari.txt"),
        app_commands.Choice(name="添い寝", value="soine.txt"),
        app_commands.Choice(name="耳打ち", value="mimiuchi.txt"),
        app_commands.Choice(name="罵倒", value="batou.txt"),
        app_commands.Choice(name="看病", value="kanbyou.txt"),
        app_commands.Choice(name="嫉妬", value="shitto.txt"),
        app_commands.Choice(name="お仕置き", value="oshioki.txt"),
    ])
    async def play(self, interaction: discord.Interaction, シチュエーション: app_commands.Choice[str]):
        is_ephemeral = (シチュエーション.value == "mimiuchi.txt")
        await interaction.response.defer(ephemeral=is_ephemeral)
        try:
            with open(f"lines/{シチュエーション.value}", "r", encoding="utf-8") as file:
                lines = file.readlines()
            reply = random.choice(lines).strip()
            await interaction.followup.send(reply, ephemeral=is_ephemeral)
        except Exception as e:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=is_ephemeral)


    @app_commands.command(name="info", description="まきぐもの各種リンクをご案内します")
    @app_commands.choices(項目=[
        app_commands.Choice(name="全コマンド一覧 (command)", value="command"),
        app_commands.Choice(name="サーバー招待リンク (invite)", value="invite"),
        app_commands.Choice(name="公式サポートサーバー (server)", value="server"),
        app_commands.Choice(name="寄付・支援について (donate)", value="donate"),
    ])
    async def info(self, interaction: discord.Interaction, 項目: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        if 項目.value == "command":
            embed = discord.Embed(title="📜 まきぐもコマンド早見表", color=0xadd8e6)
            rp_cmds = "`/play` (各種シチュエーション統合)"
            eco_cmds = "`/slot` `/gamble` `/work` `/pay` `/daily` `/shop` `/use` `/ranking` `/stats` `/titles`"
            ai_cmds = "`/ai` `/reset_ai` `/ai_mode` `/user_settings` `/profile` `/diary`"
            pro_cmds = "`/pro` `/plan` `/pro_pay` `/call` (通話)"
            misc_cmds = "`/info` `/update` `/version` `/omikuji` `/present` `/ガチャ` `/相性` `/ダイス_罰ゲーム` `/suggest` `/豆知識`"
            embed.add_field(name="🎀 ロールプレイ", value=rp_cmds, inline=False)
            embed.add_field(name="💰 経済・ランキング", value=eco_cmds, inline=False)
            embed.add_field(name="🧠 AI・記憶", value=ai_cmds, inline=False)
            embed.add_field(name="💎 Proプラン・通話", value=pro_cmds, inline=False)
            embed.add_field(name="🎲 その他・情報", value=misc_cmds, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif 項目.value == "invite":
            await interaction.followup.send("🔗 **まきぐもBot 招待リンク**\n[ここをクリックして別のサーバーに招待する](https://discord.com/api/oauth2/authorize?client_id=1255554705573449830&permissions=8&scope=bot%20applications.commands)", ephemeral=True)
            
        elif 項目.value == "server":
            await interaction.followup.send("🔗 **まきぐもぼっと 公式サポートサーバー**\n[ここをクリックして参加する](https://discord.gg/C67X8e34yJ)", ephemeral=True)
            
        elif 項目.value == "donate":
            msg = "**【まきぐも開発者へのご支援について】**\n\nまきぐもは個人開発で、サーバー代やAIのAPI利用料が毎月かかっています。\nもし「まきぐも可愛い！」「応援したい！」と思っていただけたら、以下の方法でご支援いただけると本当に助かります…！🙇‍♂️\n\n**◆ PayPay / Amazonギフト券**\n`/pro_pay` コマンドから申請することで、ご支援いただいた方に特典(Proプラン)を付与しています！\n\nその他、DiscordのDM (`rds9`) での直接の激励メッセージもお待ちしております！"

            await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roleplay(bot))
