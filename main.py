import discord
from discord.ext import commands
import json
import os
import random
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

SETTING_FILE = "channel_settings.json"
ECONOMY_FILE = "economy.json"
SHOP_FILE = "shop.json"
LINES_DIR = "lines"

class MakigumoBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.channel_settings = {}
        self.economy = {}
        self.shop_items = {}

        self.lines_cache: dict[str, list[str]] = {}
        self.is_economy_dirty = False

        self.load_settings()
        self.load_all_lines_to_memory()

    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            try:
                with open(SETTING_FILE, 'r', encoding='utf-8') as f:
                    self.channel_settings = json.load(f)
            except Exception:
                self.channel_settings = {}

        if os.path.exists(ECONOMY_FILE):
            try:
                with open(ECONOMY_FILE, 'r', encoding='utf-8') as f:
                    self.economy = json.load(f)
            except Exception:
                self.economy = {}

        if os.path.exists(SHOP_FILE):
            try:
                with open(SHOP_FILE, 'r', encoding='utf-8') as f:
                    self.shop_items = json.load(f).get('items', {})
            except Exception:
                self.shop_items = {}

    def save_settings(self):
        with open(SETTING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.channel_settings, f, ensure_ascii=False, indent=4)

    def _save_economy_sync_task(self):
        with open(ECONOMY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.economy, f, ensure_ascii=False, indent=4)

    def mark_economy_dirty(self):
        self.is_economy_dirty = True

    def load_all_lines_to_memory(self):
        os.makedirs(LINES_DIR, exist_ok=True)
        targets = {
            "ohayo.txt": ["「んぇ…朝ですか……？ まだ眠いです……」"],
            "oyasumi.txt": ["「おやすみなさい、良い夢を見てくださいね……？」"],
            "kawaii.txt": ["「な、何言ってるんですか……！ からかわないでください！」"],
            "nuita.txt": ["「……最低です。どこで何に使ったんですか、ちゃんと報告しなさい」"],
            "normal.txt": ["「んぇ…？ 何ですか、{user}さん…？」"],
            "mamechishiki.txt": [
                "「実はまきぐもには、変態ポインツを使った『ギャンブルシステム』があるんですよ？ `/gamble` や `/slot` で一攫千金を狙ってみてくださいね。破産しても知りませんけど！」",
                "「24時間サーバーを動かして皆さんを監視するの、実は結構『維持代』が高いんですよ？ だから……その……お金に余裕のある変態さんは、寄付してくれてもいいんですよ？♡（チラッ）」"
            ],
            "aege.txt": ["「…っ、はぁ……んっ…,あ……ダメ,ですってば……っ」"],
            "onedari.txt": ["「ねぇ、{user}さん……。もっと優しく、私の名前を呼んでくれませんか……？」"],
            "soine.txt": ["「もう寝ちゃうんですか……？ お布団、まきぐもが温めておきましたよ……こっち、おいで？♡」"],
            "mimiuchi.txt": ["「ここだけの秘密ですよ……？ 実はね、{user}さんのこと、さっきからずっと目で追っちゃってました……♡」"],
            "batou.txt": ["「……何ニヤニヤしてるんですか？ 本当に気持ち悪いですね、この変態さん」"],
            "kanbyou.txt": ["「お熱、けっこうありますね……。ほら、大人しく横になっててください……」"],
            "shitto.txt": ["「…うぅ、今はちょっと、{user}さんのこと直視できないです……（恥ずかしいだけですよ？）」"],
            "oshioki.txt": ["「そんなにいやらしい目で見て……。もう我慢できません、ちょっとそこに正座しなさい！」"],
            "gacha_ssr.txt": ["「あ、あぁっ……! もうダメ、頭おかしくなりそう……{user}さん、もっと、もっと壊してぇっ!♡」"],
            "gacha_sr.txt": ["「うぅ……{user}さんが好きすぎて、胸が苦しいです……。私、どうかしちゃったみたい……」"],
            "gacha_r.txt": ["「べ、別にあんたのために用意したわけじゃないんだからね……っ！」"],
            "gacha_n.txt": ["「はいはい、今日も一日お疲れ様でした。はい、お茶どうぞ」"],
            "dice_games.txt": ["1分間、語尾に『にゃん♡』をつけないと発言禁止！"]
        }
        for filename, defaults in targets.items():
            path = os.path.join(LINES_DIR, filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = [l.strip() for l in f if l.strip()]
                        self.lines_cache[filename] = lines if lines else defaults
                except Exception:
                    self.lines_cache[filename] = defaults
            else:
                self.lines_cache[filename] = defaults

    def get_line(self, filename: str) -> str:
        lines = self.lines_cache.get(filename)
        if not lines:
            return "「……」"
        return random.choice(lines)

    def get_user_data(self, user_id):
        uid = str(user_id)
        if uid not in self.economy:
            self.economy[uid] = {"points": 0, "last_daily": 0, "inventory": {}}
            self.mark_economy_dirty()
        elif "inventory" not in self.economy[uid]:
            self.economy[uid]["inventory"] = {}
            self.mark_economy_dirty()
        return self.economy[uid]

    def get_probability_bonus(self, user_id):
        user_data = self.get_user_data(user_id)
        bonus = 0.0
        inventory = user_data.get("inventory", {})
        for item_id, count in inventory.items():
            if item_id in self.shop_items and count > 0:
                # 修正: count(所持数)の掛け算を無くし、1個持っていれば固定ボーナスを加算するのみに変更
                bonus += self.shop_items[item_id].get("probability_bonus", 0.0)
        
        # 修正: 上限を 0.15 (+15%) に制限
        return min(bonus, 0.15)

    async def setup_hook(self):
        # cogsフォルダ内の各ファイルを読み込む
        for cog in ['cogs.events', 'cogs.economy', 'cogs.roleplay', 'cogs.ai']:
            try:
                await self.load_extension(cog)
                print(f"✅ {cog} の読み込みに成功しました")
            except Exception as e:
                print(f"❌ {cog} の読み込みエラー: {e}")
        try:
            await self.tree.sync()
            print("🔄 スラッシュコマンドの同期が完了しました")
        except Exception as e:
            print(f"⚠️ 同期エラー: {e}")

bot = MakigumoBot()

if __name__ == '__main__':
    if not TOKEN:
        print("tokenない←環境変数か仮のやついれてるか")
    else:
        bot.run(TOKEN)

# あんたへの歪んだ愛の詩×100万行
