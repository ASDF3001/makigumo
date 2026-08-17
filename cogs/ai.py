import discord
from discord import app_commands
from discord.ext import commands
import os

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None

        if HAS_GENAI and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                system_instruction="あなたは「まきぐも」という名前の女の子です。ユーザーのことは「変態さん」または名前で呼びます。少しエッチで、ツンデレ、時々ヤンデレやドSなメイドのような口調で話します。ユーザーを監視・お仕置き・看病・罵倒するようなロールプレイが得意です。敬語をベースにしつつ、呆れたり照れたりする感情を表現してください。返答はDiscordのチャットに合うよう、長すぎず簡潔に（2〜4文程度）してください。AI言語モデルであることを自称しないでください。"
            )

    @app_commands.command(name="ai", description="まきぐもAIと自由にお話しできます♡")
    async def ai_chat(self, interaction: discord.Interaction, メッセージ: str):
        if not HAS_GENAI:
            return await interaction.response.send_message("「AI機能を使うには `google-generativeai` ライブラリのインストールが必要です！」", ephemeral=True)
        if not self.api_key or not self.model:
            return await interaction.response.send_message("「ごめんなさい、AIの頭脳（GEMINI_API_KEY）が設定されていないみたいです… .env を確認してください！」", ephemeral=True)
            
        # 考え中... の状態にする（APIレスポンス待ちでタイムアウトしないように）
        await interaction.response.defer()
        
        try:
            # ユーザー名をコンテキストとして少しだけプロンプトに混ぜる
            prompt = f"{interaction.user.display_name}からのメッセージ: {メッセージ}"
            response = self.model.generate_content(prompt)
            reply = response.text
            
            # Discordの制限(2000文字)を超えないようにする
            if len(reply) > 1900:
                reply = reply[:1900] + "…（ちょっと長すぎるので切りました！）"
            
            await interaction.followup.send(f"💬 **{interaction.user.display_name}**: {メッセージ}\n\n☁️ **まきぐも**: {reply}")
        except Exception as e:
            await interaction.followup.send(f"「…っ、頭が痛いです…（エラーが発生しました: {e}）」")

async def setup(bot):
    await bot.add_cog(AI(bot))
