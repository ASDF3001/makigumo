import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime

class ShopView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
        options = []
        if self.bot.shop_items:
            for item_id, item in self.bot.shop_items.items():
                options.append(discord.SelectOption(label=item["name"], description=f"{item['price']} pt", value=item_id))
        else:
            options.append(discord.SelectOption(label="品切れ", value="none"))

        self.select = discord.ui.Select(placeholder="買いたいアイテムを選んでね♡", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if self.select.values[0] == "none":
            await interaction.response.send_message("品切れです…", ephemeral=True)
            return

        item_id = self.select.values[0]
        item = self.bot.shop_items.get(item_id)
        if not item:
            return await interaction.response.send_message("アイテムが存在しません。", ephemeral=True)

        user_data = self.bot.get_user_data(interaction.user.id)
        if user_data["points"] < item["price"]:
            return await interaction.response.send_message(f"「ポインツが足りないですよ！ あと {item['price'] - user_data['points']} pt 必要です！」", ephemeral=True)

        user_data["points"] -= item["price"]
        inventory = user_data.setdefault("inventory", {})
        inventory[item_id] = inventory.get(item_id, 0) + 1
        self.bot.mark_economy_dirty()

        await interaction.response.send_message(f"「{item['name']}をゲットしました♡ 残り: {user_data['points']} pt」", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="daily", description="1日1回まきぐもから変態ポインツをもらえます")
    async def daily(self, interaction: discord.Interaction):
        user_data = self.bot.get_user_data(interaction.user.id)
        now = datetime.now().timestamp()
        if now - user_data["last_daily"] < 86400:
            left = 86400 - (now - user_data["last_daily"])
            h, m = int(left // 3600), int((left % 3600) // 60)
            return await interaction.response.send_message(f"「次は {h}時間{m}分後 ですからね！」", ephemeral=True)

        user_data["points"] += 500
        user_data["last_daily"] = now
        self.bot.mark_economy_dirty()
        await interaction.response.send_message(f"「ほら、今日の配給【500 pt】です。現在の所持金は {user_data['points']} ptですよ。」")

    @app_commands.command(name="gamble", description="まきぐもと変態ポインツを賭けて勝負します（倍率はランダム）")
    async def gamble(self, interaction: discord.Interaction, 賭け金: int):
        user_data = self.bot.get_user_data(interaction.user.id)
        if 賭け金 <= 0 or user_data["points"] < 賭け金:
            return await interaction.response.send_message("「ポインツが足りないか、賭け金がおかしいですよ！」", ephemeral=True)

        roll = random.randint(1, 100)
        bonus = self.bot.get_probability_bonus(interaction.user.id)
        # 修正: 上限を90%に統一
        win_threshold = min(90, 40 + int(bonus * 100))

        if roll <= win_threshold:
            user_data["points"] += 賭け金
            bonus_note = f"\n（🎲 幸運補正: +{int(bonus*100)}%）" if bonus > 0 else ""
            msg = f"🎲 **カジノ**\n「ちっ…{interaction.user.mention}さんの勝ちです。{賭け金*2} ptにして返してあげます。」{bonus_note}"
        else:
            user_data["points"] -= 賭け金
            msg = f"🎲 **カジノ**\n「あははっ！ まきぐものの勝ちです！ {賭け金} ptは没収ですからね！」"

        self.bot.mark_economy_dirty()
        await interaction.response.send_message(msg)

    @app_commands.command(name="slot", description="変態ポインツを賭けてまきぐもスロットを回します")
    async def slot(self, interaction: discord.Interaction, 賭け金: int):
        user_data = self.bot.get_user_data(interaction.user.id)
        if 賭け金 <= 0 or user_data["points"] < 賭け金:
            return await interaction.response.send_message("「賭け金が足りないですよ？」", ephemeral=True)

        user_data["points"] -= 賭け金
        symbols = ["🍒", "🍇", "🍉", "💖", "💡"]
        bonus = self.bot.get_probability_bonus(interaction.user.id)

        if bonus > 0 and random.random() < bonus:
            target = random.choice(symbols)
            res = [target, target, target]
        else:
            res = [random.choice(symbols) for _ in range(3)]

        if res[0] == res[1] == res[2]:
            if res[0] == "💖": winnings, msg = 賭け金 * 10, f"「えっ、大・大・大当り……！？ {賭け金*10} ptあげます！」"
            elif res[0] == "💡": winnings, msg = 0, f"「怒りマークが揃いました！ お仕置き確定です！ 没収！」"
            else: winnings, msg = 賭け金 * 3, f"「当たりですね。{賭け金*3} pt返してあげます。」"
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            winnings, msg = int(賭け金 * 1.5), f"「小当たりですね。{int(賭け金 * 1.5)} ptです。」"
        else:
            winnings, msg = 0, f"「ハズレです！ {賭け金} ptいただきまーーす！」"

        user_data["points"] += winnings
        self.bot.mark_economy_dirty()

        embed = discord.Embed(title="🎰 まきぐもスロット", color=0xffb6c1)
        embed.add_field(name="結果", value=f"**[ {res[0]} | {res[1]} | {res[2]} ]**", inline=False)
        embed.add_field(name="一言", value=msg, inline=False)
        embed.set_footer(text=f"💰 所持金: {user_data['points']} pt" + (f" | 🎲 幸運補正: +{int(bonus*100)}%" if bonus > 0 else ""))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="変態ポインツで色々なアイテムを購入できます♡")
    async def shop(self, interaction: discord.Interaction):
        if not self.bot.shop_items:
            return await interaction.response.send_message("「ショップがまだ空っぽです…」", ephemeral=True)

        embed = discord.Embed(title="🛍️ まきぐも特製ショップ", description="ポインツを使ってアイテムを購入できるよ♡", color=0xffb6c1)
        for item_id, item in self.bot.shop_items.items():
            b = item.get("probability_bonus", 0)
            b_txt = f"\n🎲 ギャンブル勝率 +{b*100:.0f}%" if b > 0 else ""
            embed.add_field(name=f"{item['name']}", value=f"{item['description']}{b_txt}\n💰 {item['price']} pt", inline=False)

        await interaction.response.send_message(embed=embed, view=ShopView(self.bot))

    @app_commands.command(name="work", description="まきぐものお手伝いをしてポインツを稼ぎます（3時間に1回）")
    async def work(self, interaction: discord.Interaction):
        user_data = self.bot.get_user_data(interaction.user.id)
        now = datetime.now().timestamp()

        last_work = user_data.get("last_work", 0)
        if now - last_work < 10800:
            left = 10800 - (now - last_work)
            h, m = int(left // 3600), int((left % 3600) // 60)
            return await interaction.response.send_message(f"「さっき働いたばかりじゃないですか！次は {h}時間{m}分後 です！」", ephemeral=True)

        user_data["last_work"] = now

        scenarios = [
            {"msg": "まきぐもの肩たたきをしてあげました。「んっ…そこ、気持ちいいです……」", "pt": 300},
            {"msg": "まきぐもの代わりにお茶を淹れました。「ふふっ、ありがとうございます。美味しいです♡」", "pt": 200},
            {"msg": "まきぐもと一緒に監視業務を手伝いました。「…っ、変なところ見ないでください！」", "pt": 400},
            {"msg": "まきぐものお部屋の掃除をしました。「勝手に触らないでって言いましたよね！？ 罰金です！」", "pt": -100}
        ]

        scenario = random.choice(scenarios)
        user_data["points"] += scenario["pt"]
        if user_data["points"] < 0:
            user_data["points"] = 0

        self.bot.mark_economy_dirty()

        action_text = "獲得" if scenario["pt"] > 0 else "没収"
        pt_abs = abs(scenario["pt"])
        await interaction.response.send_message(f"🧹 **アルバイト**\n{scenario['msg']}\n\n(💰 {pt_abs} pt {action_text}！ 現在: {user_data['points']} pt)")

    @app_commands.command(name="pay", description="他の変態さんにポインツを貢ぎます（送金）")
    async def pay(self, interaction: discord.Interaction, 相手: discord.Member, 額: int):
        if 額 <= 0:
            return await interaction.response.send_message("「1pt以上じゃないと送れませんよ！」", ephemeral=True)
        if 相手.bot:
            return await interaction.response.send_message("「Botに貢いでどうするんですか……私にください！」", ephemeral=True)
        if 相手.id == interaction.user.id:
            return await interaction.response.send_message("「自分に送ってどうするんですか？ 虚しくないですか？」", ephemeral=True)

        sender_data = self.bot.get_user_data(interaction.user.id)
        if sender_data["points"] < 額:
            return await interaction.response.send_message("「ポインツが足りないですよ！ 見栄を張らないでください！」", ephemeral=True)

        receiver_data = self.bot.get_user_data(相手.id)

        sender_data["points"] -= 額
        receiver_data["points"] += 額
        self.bot.mark_economy_dirty()

        await interaction.response.send_message(f"💸 **送金完了**\n「{interaction.user.mention}さんが、{相手.mention}さんに {額} pt 貢ぎましたよ！ 何を企んでるんですか…？」")

    @app_commands.command(name="ranking", description="変態長者番付（ポインツランキングトップ10）を表示します")
    async def ranking(self, interaction: discord.Interaction):
        sorted_users = sorted(self.bot.economy.items(), key=lambda x: x[1].get("points", 0), reverse=True)

        embed = discord.Embed(title="🏆 変態長者番付トップ10", description="現在最もポインツを貯め込んでいる変態さんたちです♡", color=0xffd700)

        desc = ""
        for i, (uid, data) in enumerate(sorted_users[:10]):
            pts = data.get("points", 0)
            if pts > 0:
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}位**"
                desc += f"{medal} <@{uid}> : **{pts}** pt\n"

        if not desc:
            desc = "まだ誰もポインツを持っていません。"

        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="所持している消費アイテムを使います")
    async def use(self, interaction: discord.Interaction, アイテムid: str):
        user_data = self.bot.get_user_data(interaction.user.id)
        inventory = user_data.get("inventory", {})

        if inventory.get(アイテムid, 0) <= 0:
            return await interaction.response.send_message("「そのアイテムは持っていませんよ！」", ephemeral=True)

        if アイテムid == "apology_parfait":
            inventory[アイテムid] -= 1
            user_data["points"] += 1000
            self.bot.mark_economy_dirty()
            await interaction.response.send_message("🍨 **お詫びの高級パフェを使用**\n「あむ……んっ、美味しいです♡ まぁ、少しは許してあげなくもないです。（ボーナス 1000 pt もらった！）」")

        elif アイテムid == "coffee":
            inventory[アイテムid] -= 1
            self.bot.mark_economy_dirty()
            await interaction.response.send_message("☕ **まきぐも特製コーヒーを飲んだ**\n「ほら、熱いから気をつけて飲んでくださいね……？ ふふっ、美味しいですか？♡」")

        elif アイテムid == "cheat_note":
            inventory[アイテムid] -= 1
            user_data["points"] += 300
            self.bot.mark_economy_dirty()
            await interaction.response.send_message("📝 **カンニングペーパーを使用**\n「ふふっ、そんなの見て勉強してるんですか？……可愛いところありますね♡（300 pt ゲット！）」")

        else:
            await interaction.response.send_message("「そのアイテムは持っているだけで効果がある装備アイテム（幸運の雲など）ですよ！」", ephemeral=True)

    @app_commands.command(name="stats", description="現在の所持ポインツや所持アイテム、ステータスを確認します")
    async def stats(self, interaction: discord.Interaction):
        user_data = self.bot.get_user_data(interaction.user.id)
        points = user_data.get("points", 0)
        inventory = user_data.get("inventory", {})
        bonus = self.bot.get_probability_bonus(interaction.user.id)

        embed = discord.Embed(title=f"📊 {interaction.user.display_name} さんのステータス", color=0x87ceeb)
        embed.add_field(name="💰 所持ポインツ", value=f"**{points}** pt", inline=False)

        # 修正: 上限90%表記に変更
        win_rate = min(90, 40 + int(bonus * 100))
        embed.add_field(name="🎲 ギャンブル勝率", value=f"基本40% ＋ アイテム補正{int(bonus * 100)}% ＝ **現在 {win_rate}%** (※勝率上限90%)", inline=False)

        inv_text = ""
        for item_id, count in inventory.items():
            if count > 0:
                item_name = self.bot.shop_items.get(item_id, {}).get("name", "謎のアイテム")
                inv_text += f"・{item_name} × {count}\n"

        if not inv_text:
            inv_text = "何も持っていません。"

        embed.add_field(name="🎒 所持アイテム", value=inv_text, inline=False)

        # 修正: 本人しか見えないように ephemeral=True を追加
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))