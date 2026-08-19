import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import asyncio

try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False
    try:
        import google.generativeai as legacy_genai
        HAS_LEGACY_GENAI = True
    except ImportError:
        HAS_LEGACY_GENAI = False

class AI(commands.Cog):
    def __init__(self, bot, api_keys):
        self.bot = bot
        self.api_keys = api_keys
        self.histories = {}
        self.system_instruction = "あなたは「まきぐも」という名前の女の子です。ユーザーのことは「変態さん」または名前で呼びます。少しエッチで、ツンデレ、時々ヤンデレやドSなメイドのような口調で話します。ユーザーを監視・お仕置き・看病・罵倒するようなロールプレイが得意です。敬語をベースにしつつ、呆れたり照れたりする感情を表現してください。返答はDiscordのチャットに合うよう、長すぎず簡潔に（2〜4文程度）してください。AI言語モデルであることを自称しないでください。"

    @app_commands.command(name="ai", description="まきぐもAIと自由にお話しできます♡（記憶あり）")
    async def ai_chat(self, interaction: discord.Interaction, メッセージ: str):
        if not HAS_NEW_GENAI and not HAS_LEGACY_GENAI:
            return await interaction.response.send_message("「AI機能を使うには `google-genai` ライブラリが必要です！」", ephemeral=True)
            
        await interaction.response.defer()
        
        # モデル候補（より確実な最新モデル名に更新、1.5は廃止済みのため除外）
        key = random.choice(self.api_keys)
        user_id = str(interaction.user.id)
        if user_id not in self.histories:
            self.histories[user_id] = []
            
        history = self.histories[user_id]
        user_msg = f"{interaction.user.display_name}からのメッセージ: {メッセージ}"
        
        reply = None
        last_error = Exception("APIから有効な応答が得られませんでした。")

        if HAS_NEW_GENAI:
            client = genai.Client(api_key=key)
            
            # APIキーで利用可能なFlash系モデルを動的に取得（キャッシュしてあればそれを使う）
            if not hasattr(self, "available_models_cache"):
                try:
                    models = [m.name for m in client.models.list() if 'flash' in m.name.lower()]
                    models.sort(reverse=True) # gemini-3.6-flash, 3.5, 3.0, 2.5... の順にする
                    self.available_models_cache = models
                except Exception:
                    self.available_models_cache = ['gemini-3.5-flash-lite', 'gemini-3.5-flash', 'gemini-3.0-flash', 'gemini-2.5-flash', 'gemini-2.0-flash']
            
            models_to_try = self.available_models_cache
            
            past_contents = []
            for item in history:
                past_contents.append(types.Content(
                    role=item["role"],
                    parts=[types.Part.from_text(text=item["parts"][0])]
                ))
            
            for model_name in models_to_try:
                try:
                    chat = client.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction
                        ),
                        history=past_contents
                    )
                    response = await asyncio.to_thread(chat.send_message, user_msg)
                    if response and response.text:
                        reply = response.text
                        break
                except Exception as e:
                    last_error = e
                    continue
        else:
            models_to_try = getattr(self, "available_models_cache", ['gemini-3.6-flash', 'gemini-3.5-flash-lite', 'gemini-3.5-flash', 'gemini-3.0-flash', 'gemini-2.5-flash', 'gemini-2.0-flash'])
            for model_name in models_to_try:
                try:
                    legacy_genai.configure(api_key=key)
                    model = legacy_genai.GenerativeModel(model_name, system_instruction=self.system_instruction)
                    temp_history = history + [{"role": "user", "parts": [user_msg]}]
                    response = await asyncio.to_thread(model.generate_content, temp_history)
                    if response and response.text:
                        reply = response.text
                        break
                except Exception as e:
                    last_error = e
                    continue

        if reply:
            history.append({"role": "user", "parts": [user_msg]})
            history.append({"role": "model", "parts": [reply]})
            if len(history) > 10:
                self.histories[user_id] = history[-10:]
            
            if len(reply) > 1900:
                reply = reply[:1900] + "…（ちょっと長すぎるので切りました！）"
            
            await interaction.followup.send(f"💬 **{interaction.user.display_name}**: {メッセージ}\n\n☁️ **まきぐも**: {reply}")
        else:
            err_msg = str(last_error)
            if "User location is not supported" in err_msg or "FAILED_PRECONDITION" in err_msg:
                await interaction.followup.send("「…っ、サーバーの設置場所（国・地域）がGoogle API非対応の地域にあるため返答できません…（IP制限エラー）」")
            else:
                await interaction.followup.send(f"「…っ、頭が痛いです…（エラーが発生しました: {last_error}）」")

    @commands.command(name="models")
    async def check_models(self, ctx):
        """利用可能なモデルID一覧を確認する管理者コマンド"""
        admin_id = os.getenv('ADMIN_USER_ID')
        app_info = await self.bot.application_info()
        is_admin = (admin_id and str(ctx.author.id) == admin_id) or (ctx.author.id == app_info.owner.id)
        
        if not is_admin:
            return
            
        if not self.api_keys:
            await ctx.send("APIキーが設定されていません。")
            return
            
        msg = await ctx.send("利用可能なモデルを検索中...")
        try:
            client = genai.Client(api_key=self.api_keys[0])
            available = []
            for m in client.models.list():
                if 'flash' in m.name.lower():
                    available.append(m.name)
            
            res = "利用可能なFlash系モデルID一覧:\n" + "\n".join(available[:30])
            await msg.edit(content=f"```\n{res}\n```")
        except Exception as e:
            await msg.edit(content=f"モデルの取得に失敗しました: {e}")

async def setup(bot):
    api_keys = []
    for i in range(1, 11):
        k = os.getenv(f"GEMINI_API_KEY_{i}")
        if k:
            api_keys.append(k)
            
    if not api_keys:
        print("GEMINI_API_KEY_* が設定されていないため、AI機能を無効化します。")
        return
        
    await bot.add_cog(AI(bot, api_keys))
