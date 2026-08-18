import discord
from discord import app_commands
from discord.ext import commands
import random
import os

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    def get_embed(self, category):
        if category == "home":
            e = discord.Embed(title="☁️ まきぐもちゃん 総合ヘルプガイド", description="サーバーに常駐して、あなたたち「変態さん」を監視・癒やし・お仕置きするBotです♡", color=0xffb6c1)
            e.add_field(name="💬 チャット自動反応ワード", value="`まきぐも` / `おはよ` / `おやすみ` / `かわいい` / `抜いた`", inline=False)
            return e
        elif category == "rp":
            e = discord.Embed(title="💕 シチュエーション・お遊び", color=0xffb6c1)
            e.add_field(name="コマンド一覧", value="`/gacha` : まきぐもガチャ\n`/お仕置き` : 悪い子に宣告\n`/罵倒` : ドM向けご褒美\n`/看病` / `/嫉妬` / `/喘げ` / `/おねだり` / `/添い寝` / `/耳打ち` / `/相性` / `/豆知識`\n`/update` : アップデート情報を確認\n`/version` : 閲覧可能なバージョン一覧を確認", inline=False)
            return e
        elif category == "game":
            e = discord.Embed(title="🎰 カジノ・ギャンブルシステム", color=0xffb6c1)
            e.add_field(name="コマンド一覧", value="`/daily` / `/gamble` / `/slot` / `/ダイス_罰ゲーム` / `/shop` / `/work` / `/pay` / `/ranking` / `/use` / `/stats`", inline=False)
            return e
        elif category == "admin":
            e = discord.Embed(title="⚙️ サーバー管理者向け機能", color=0xffb6c1)
            e.add_field(name="動作管理", value="`/setting` : 反応チャンネルを指定\n`/invite` : 別サーバーに招待", inline=False)
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
        view = HelpView()
        await interaction.response.send_message(embed=view.get_embed("home"), view=view)

    @app_commands.command(name="update", description="まきぐもちゃんのアップデート内容を確認します")
    @app_commands.describe(version="確認したいバージョン（例: v3.0）。空欄で最新のものを表示します")
    async def update_cmd(self, interaction: discord.Interaction, version: str = None):
        update_dir = "update"
        
        if not os.path.exists(update_dir):
            return await interaction.response.send_message("「まだアップデート情報がないみたいです…」", ephemeral=True)

        files = [f for f in os.listdir(update_dir) if f.endswith(".txt")]
        if not files:
            return await interaction.response.send_message("「アップデート情報が空っぽです！」", ephemeral=True)

        if version:
            target_file = f"{version}.txt" if not version.endswith(".txt") else version
            if target_file not in files:
                return await interaction.response.send_message(f"「{version} のアップデート情報は見つかりませんでした…」", ephemeral=True)
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
        # 修正: 本人しか見えないように ephemeral=True を追加
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="version", description="確認できるアップデートのバージョン一覧を表示します（最新10件まで）")
    async def version_cmd(self, interaction: discord.Interaction):
        update_dir = "update"
        
        if not os.path.exists(update_dir):
            return await interaction.response.send_message("「まだアップデート情報がないみたいです…」", ephemeral=True)

        files = [f for f in os.listdir(update_dir) if f.endswith(".txt")]
        if not files:
            return await interaction.response.send_message("「アップデート情報が空っぽです！」", ephemeral=True)

        files.sort(reverse=True)
        recent_files = files[:10]

        version_list = "\n".join([f"- **{f.replace('.txt', '')}**" for f in recent_files])

        embed = discord.Embed(title="☁️ 閲覧可能なバージョン一覧", description=version_list, color=0x87ceeb)
        embed.set_footer(text="内容を見るには /update [バージョン] と入力してね！")
        
        # 修正: 本人しか見えないように ephemeral=True を追加
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setting", description="まきぐもが反応するチャンネルを設定します")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setting(self, interaction: discord.Interaction, メイン: discord.TextChannel, サブ1: discord.TextChannel = None, サブ2: discord.TextChannel = None, サブ3: discord.TextChannel = None, サブ4: discord.TextChannel = None):
        guild_id = str(interaction.guild_id)
        raw_channels = [メイン.id]
        if サブ1: raw_channels.append(サブ1.id)
        if サブ2: raw_channels.append(サブ2.id)
        if サブ3: raw_channels.append(サブ3.id)
        if サブ4: raw_channels.append(サブ4.id)

        valid = [cid for cid in set(raw_channels) if isinstance(self.bot.get_channel(cid), discord.TextChannel)]
        if not valid: return await interaction.response.send_message("❌ 指定チャンネルが無効です", ephemeral=True)

        self.bot.channel_settings[guild_id] = valid
        self.bot.save_settings()
        await interaction.response.send_message(f"了解です♡ これから指定されたチャンネルでのみお返事しますね。")

    @app_commands.command(name="invite", description="まきぐもちゃんを別のサーバーに招待するリンクを表示します")
    async def invite(self, interaction: discord.Interaction):
        url = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=277025508352&scope=bot%20applications.commands"
        await interaction.response.send_message(f"「こちらのリンクから招待してくださいね！」\n{url}")

    @app_commands.command(name="豆知識", description="まきぐもちゃんのヒミツの豆知識を披露します")
    async def mamechishiki(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(f"💡 **まきぐも豆知識**\n{self.bot.get_line('mamechishiki.txt')}")

    @app_commands.command(name="喘げ", description="まきぐもにちょっと色っぽい声を上げさせます")
    async def aege(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("aege.txt").format(user=interaction.user.mention))

    @app_commands.command(name="おねだり", description="まきぐもがあなたにワガママを言います")
    async def onedari(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("onedari.txt").format(user=interaction.user.mention))

    @app_commands.command(name="添い寝", description="夜、まきぐもがあなたと一緒にベッドに入ります")
    async def soine(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("soine.txt").format(user=interaction.user.mention))

    @app_commands.command(name="耳打ち", description="【あなただけにしか見えません】まきぐもが耳元でコッソリ囁きます……♡")
    async def mimiuchi(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(self.bot.get_line("mimiuchi.txt").format(user=interaction.user.mention), ephemeral=True)

    @app_commands.command(name="罵倒", description="まきぐもがゴミを見るような目であなたを叱り飛ばします")
    async def batou(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("batou.txt").format(user=interaction.user.mention))

    @app_commands.command(name="看病", description="風邪を引いたあなたを、まきぐもが看病します")
    async def kanbyou(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("kanbyou.txt").format(user=interaction.user.mention))

    @app_commands.command(name="嫉妬", description="他の子の話をしたあなたに、まきぐもが嫉妬します")
    async def shitto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("shitto.txt").format(user=interaction.user.mention))

    @app_commands.command(name="お仕置き", description="変態なあなたに、まきぐもがお仕置きをします")
    async def oshioki(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(self.bot.get_line("oshioki.txt").format(user=interaction.user.mention))

    @app_commands.command(name="ガチャ", description="まきぐもガチャを引きます。激甘から激辛まで全4クラス♡")
    async def gacha(self, interaction: discord.Interaction):
        await interaction.response.defer()
        r = random.random()
        if r < 0.05: rarity, file = "🔮 【SSR】限界突破", "gacha_ssr.txt"
        elif r < 0.25: rarity, file = "💖 【SR】超デレ", "gacha_sr.txt"
        elif r < 0.60: rarity, file = "✨ 【R】ツンデレ", "gacha_r.txt"
        else: rarity, file = "🍃 【N】ノーマル", "gacha_n.txt"
        await interaction.followup.send(f"🎲 **ガチャ結果** 🎲\n【 {rarity} 】\n\n{self.bot.get_line(file).format(user=interaction.user.mention)}")

    @app_commands.command(name="相性", description="あなたとまきぐものの今日の相性（意味深）を占います")
    async def aishou(self, interaction: discord.Interaction):
        await interaction.response.defer()
        p = random.randint(1, 100)
        if p <= 20: c = "「…うぅ、今はちょっと直視できないです…」"
        elif p <= 60: c = "「普通の相性、ですね。これからもっと深めていけますよね？」"
        else: c = "「100%……！？ 嘘……っ、もう結ばれる運命だったってことですか……っ！？♡」"
        await interaction.followup.send(f"💘 **相性** 💘\n【 **{p}%** 】\n{c}")

    @app_commands.command(name="ダイス_罰ゲーム", description="サイコロを振って身内鯖用の罰ゲームを言い渡します")
    async def dice_game(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(f"🎲 **ダイスの目: 【 {random.randint(1, 6)} 】**\n{interaction.user.mention} さんへの罰ゲーム告知です♡\n\n**「{self.bot.get_line('dice_games.txt')}」**")

async def setup(bot):
    await bot.add_cog(Roleplay(bot))