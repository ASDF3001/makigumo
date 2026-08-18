import discord
from discord import app_commands
from discord.ext import commands
import os
import random

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
        
        try:
            key = random.choice(self.api_keys)
            user_id = str(interaction.user.id)
            if user_id not in self.histories:
                self.histories[user_id] = []
                
            history = self.histories[user_id]
            user_msg = f"{interaction.user.display_name}からのメッセージ: {メッセージ}"
            
            if HAS_NEW_GENAI:
                client = genai.Client(api_key=key)
                
                contents = []
                for item in history:
                    contents.append(types.Content(
                        role=item["role"],
                        parts=[types.Part.from_text(text=item["parts"][0])]
                    ))
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_msg)]
                ))
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction
                    )
                )
                reply = response.text
                
                history.append({"role": "user", "parts": [user_msg]})
                history.append({"role": "model", "parts": [reply]})
            else:
                legacy_genai.configure(api_key=key)
                model = legacy_genai.GenerativeModel('gemini-3.5-flash-lite', system_instruction=self.system_instruction)
                history.append({"role": "user", "parts": [user_msg]})
                response = model.generate_content(history)
                reply = response.text
                history.append({"role": "model", "parts": [reply]})
            
            if len(history) > 10:
                self.histories[user_id] = history[-10:]
            
            if len(reply) > 1900:
                reply = reply[:1900] + "…（ちょっと長すぎるので切りました！）"
            
            await interaction.followup.send(f"💬 **{interaction.user.display_name}**: {メッセージ}\n\n☁️ **まきぐも**: {reply}")
        except Exception as e:
            await interaction.followup.send(f"「…っ、頭が痛いです…（エラーが発生しました: {e}）」")

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
