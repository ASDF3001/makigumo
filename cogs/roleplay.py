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
            e.add_field(name="AI・カスタム機能", value="`/ai` : AI会話（往復50件記憶）\n`/ai_mode` : 性格モードワンタッチ変更\n`/reset_ai` : AI記憶リセット\n`/user_settings` : カスタムプロンプト設定\n`/update` / `/version`", inline=False)
            e.add_field(name="シチュエーション＆エンタメ", value="`/gacha` : まきぐもガチャ\n`/omikuji` : 変態おみくじ（1日1回）\n`/present` : まきぐもにお貢ぎ・プレゼント\n`/お仕置き` / `/罵倒` / `/看病` / `/嫉妬` / `/喘げ` / `/おねだり` / `/添い寝` / `/耳打ち` / `/相性` / `/豆知識`", inline=False)
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

    @app_commands.command(name="omikuji", description="1日1回ひけるまきぐもの変態おみくじ♡（ポインツも貰えます）")
    async def omikuji(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        import pg_shim as sqlite3
        already_drawn = False
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                row = c.execute("SELECT last_date FROM omikuji_logs WHERE user_id = ?", (user_id,)).fetchone()
                if row and row[0] == today_str:
                    already_drawn = True
        except Exception:
            pass

        if already_drawn:
            return await interaction.response.send_message("「おみくじは1日1回ですよ？ また明日ひきにきてくださいね♡」", ephemeral=True)

        await interaction.response.defer()

        r = random.random()
        if r < 0.05:
            rank, pts, msg = "🔮 【超変態SSR】限界突破運", 500, "「嘘…こんな奇跡的な運が出ちゃうなんて…！今日は私、あなたの何でも言うこと聞いちゃうかも…♡」"
        elif r < 0.25:
            rank, pts, msg = "💖 【大吉】デレデレ運", 300, "「大吉ですよ！ふん、まあ私に愛されてるって証拠ですね♡ 感謝しなさい！」"
        elif r < 0.60:
            rank, pts, msg = "✨ 【吉】ツンデレ運", 200, "「吉ですね。可もなく不可もなく、私のお仕置きを素直に受け入れなさい」"
        elif r < 0.85:
            rank, pts, msg = "🍃 【小吉】日常運", 100, "「小吉です。まあ、平和で普通の一日になりそうですね」"
        else:
            rank, pts, msg = "💀 【大凶】ドSお仕置き運", 50, "「ふふっ…大凶が出ましたね…♡ 今日は覚悟しておきなさい、たっぷりお仕置きしてあげますから」"

        # ポインツ付与
        u_data = self.bot.get_user_data(user_id)
        u_data["points"] += pts
        self.bot.mark_economy_dirty()

        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO omikuji_logs (user_id, last_date) VALUES (?, ?)", (user_id, today_str))
                conn.commit()
        except Exception:
            pass

        embed = discord.Embed(title="⛩️ まきぐも変態おみくじ ⛩️", description=f"【 **{rank}** 】\n\n{msg}", color=0xff69b4)
        embed.add_field(name="🎁 お給料ボーナス", value=f"`+{pts} pts` を獲得しました！（現在: `{u_data['points']} pts`）")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="present", description="まきぐもちゃんにプレゼント（お貢ぎ）を贈ります♡")
    @app_commands.choices(アイテム=[
        app_commands.Choice(name="☕ 高級アールグレイ紅茶 (100 pts)", value="tea"),
        app_commands.Choice(name="🍫 媚薬入り手作りチョコ (300 pts)", value="chocolat"),
        app_commands.Choice(name="🔒 鍵付きレザー首輪 (500 pts)", value="collar"),
        app_commands.Choice(name="👗 特注勝負メイド服 (1000 pts)", value="dress"),
    ])
    async def present(self, interaction: discord.Interaction, アイテム: app_commands.Choice[str]):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        costs = {"tea": 100, "chocolat": 300, "collar": 500, "dress": 1000}
        cost = costs.get(アイテム.value, 100)
        
        u_data = self.bot.get_user_data(user_id)
        if u_data["points"] < cost:
            return await interaction.followup.send(f"❌ ポインツが足りません！（必要: `{cost} pts` / 所持: `{u_data['points']} pts`）")

        u_data["points"] -= cost
        self.bot.mark_economy_dirty()

        import pg_shim as sqlite3
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                c.execute("INSERT INTO user_stats (user_id, stat_key, val) VALUES (?, 'present_count', 1) ON CONFLICT(user_id, stat_key) DO UPDATE SET val = val + 1", (user_id,))
                conn.commit()
        except Exception:
            pass

        reactions = {
            "tea": "「……あら？ 高級紅茶ですか……？ べ、別にあんたに喜んでほしいわけじゃないけど……ありがとう。淹れてあげますから、一緒に飲みなさい」",
            "chocolat": "「な、何ですかこの怪しいチョコ……！ 媚薬が入ってる！？ バカじゃないの変態さん！ ……っ、でも、せっかくだから後で1人でこっそり食べます……///」",
            "collar": "「首輪……！？ しかも鍵付き……？ ふっ……これを私につけろってこと？ それとも……あなたにつけて可愛がってほしいの……？♡」",
            "dress": "「き、着替えさせろって……こんな露出の激しいメイド服、着るわけないでしょ！？ …っ、でも……あんたがどうしてもって言うなら……今夜だけ特別に着てあげるわよ……///」"
        }

        reply_msg = reactions.get(アイテム.value, "「ありがとう、貰っておきますね」")
        embed = discord.Embed(title=f"🎁 まきぐもちゃんへのお貢ぎ ({アイテム.name.split(' (')[0]})", description=reply_msg, color=0xff1493)
        embed.set_footer(text=f"消費: {cost} pts | 残高: {u_data['points']} pts")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="birthday", description="あなたの誕生日をまきぐもに教えます（当日にツンデレなお祝いとポインツが貰えます♡）")
    @app_commands.describe(月="誕生月", 日="誕生日")
    async def birthday(self, interaction: discord.Interaction, 月: int, 日: int):
        await interaction.response.defer(ephemeral=True)
        if not (1 <= 月 <= 12) or not (1 <= 日 <= 31):
            return await interaction.followup.send("❌ 月は1〜12、日は1〜31の数字で入力してくださいね！", ephemeral=True)
            
        import pg_shim as sqlite3
        try:
            with contextlib.closing(sqlite3.connect("database.db", timeout=30.0)) as conn, conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO birthdays (user_id, month, day, last_notified) VALUES (?, ?, ?, 0)", (str(interaction.user.id), 月, 日))
                conn.commit()
            await interaction.followup.send(f"🎂 **誕生日を {月}月{日}日 に登録しました！**\n\n「……{月}月{日}日ですね。覚えておいてあげますから、当日は私に会いに来なさいよねっ！」", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 登録に失敗しました: {e}", ephemeral=True)

    @app_commands.command(name="suggest", description="作者への要望・新機能アイデアを匿名（作者にはバレます）で送ります")
    @app_commands.describe(内容="要望内容（どんな機能が欲しいか等）")
    async def suggest(self, interaction: discord.Interaction, 内容: str):
        await interaction.response.defer(ephemeral=True)
        from datetime import datetime
        try:
            with open("suggest.txt", "a", encoding="utf-8") as f:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{now}] {interaction.user.display_name} (@{interaction.user.name} / ID:{interaction.user.id})\n{内容}\n{'-'*30}\n")
            await interaction.followup.send("💌 **要望を作者(ゆーと)へ送信しました！**\n\n「あなたの要望、ちゃんと開発者に届けておきましたから。……まあ、採用されるかはその変態具合によりますけどね♡」", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 送信に失敗しました: {e}", ephemeral=True)

    @app_commands.command(name="command", description="まきぐもBotの全コマンド一覧をこっそり確認します")
    async def commands_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="📜 まきぐもコマンド早見表", color=0xadd8e6)
        
        rp_cmds = "`/喘げ` `/おねだり` `/添い寝` `/耳打ち` `/罵倒` `/看病` `/嫉妬` `/お仕置き`"
        eco_cmds = "`/slot` `/gamble` `/work` `/pay` `/daily` `/shop` `/use` `/ranking` `/stats` `/titles`"
        ai_cmds = "`/ai` `/reset_ai` `/ai_mode` `/user_settings` `/memo` `/diary`"
        pro_cmds = "`/pro` (Proプラン案内) `/plan` (プラン状況確認) `/pro_pay` (支払い申請)"
        misc_cmds = "`/omikuji` `/present` `/ガチャ` `/相性` `/ダイス_罰ゲーム` `/birthday` `/suggest` `/command` `/豆知識`"
        
        embed.add_field(name="🎀 ロールプレイ", value=rp_cmds, inline=False)
        embed.add_field(name="💰 経済・ランキング", value=eco_cmds, inline=False)
        embed.add_field(name="🧠 AI・記憶", value=ai_cmds, inline=False)
        embed.add_field(name="💎 Proプラン", value=pro_cmds, inline=False)
        embed.add_field(name="🎲 おみくじ・その他", value=misc_cmds, inline=False)
        
        embed.set_footer(text="※AI機能や一部コマンドには専用ポイント(pts)を消費するものもあります")
        await interaction.followup.send(embed=embed, ephemeral=True)
async def setup(bot):
    await bot.add_cog(Roleplay(bot))
