import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import random
import numpy as np

try:
    from discord.ext.voice_recv import VoiceRecvClient, BasicSink
    HAS_VOICE_RECV = True
except ImportError:
    HAS_VOICE_RECV = False

try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

class GeminiLiveSink(BasicSink):
    def __init__(self, target_user_id, loop, audio_queue):
        super().__init__(self._write_cb)
        self.target_user_id = target_user_id
        self.loop = loop
        self.audio_queue = audio_queue
        
    def _write_cb(self, user, data):
        if not user or user.id != self.target_user_id:
            return
        if not data.pcm:
            return
            
        # Convert 48kHz stereo to 16kHz mono
        try:
            arr = np.frombuffer(data.pcm, dtype=np.int16)
            mono = (arr[0::2] / 2 + arr[1::2] / 2).astype(np.int16)
            resampled = mono[::3]
            pcm_bytes = resampled.tobytes()
            # Push to asyncio queue thread-safely
            self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, pcm_bytes)
        except Exception as e:
            print(f"Audio conversion error: {e}")

class LiveCall(commands.Cog):
    def __init__(self, bot, api_keys):
        self.bot = bot
        self.api_keys = api_keys
        self.active_calls = {} # guild_id -> { 'session': ..., 'vc': ..., 'tasks': [...] }

    @app_commands.command(name="call", description="【Pro MAX限定】まきぐもとボイスチャンネルでお話しします！(聞き専)")
    @app_commands.describe(返信先="まきぐもの返信テキストを送る場所（未指定ならDM）")
    @app_commands.choices(返信先=[
        app_commands.Choice(name="DM (デフォルト)", value="dm"),
        app_commands.Choice(name="現在のテキストチャンネル", value="channel")
    ])
    async def call_cmd(self, interaction: discord.Interaction, 返信先: str = "dm"):
        await interaction.response.defer(ephemeral=True)
        
        if not HAS_VOICE_RECV or not HAS_NEW_GENAI:
            await interaction.followup.send("⚠️ 必要なライブラリ(discord-ext-voice-recv, google-genai)がインストールされていません。")
            return
            
        user_id = interaction.user.id
        is_promax = self.bot.is_promax(str(user_id))
        if not is_promax:
            await interaction.followup.send("「音声通話機能はPro MAXプラン限定ですっ！♡ (`/pro`)」")
            return
            
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("「先にボイスチャンネルに入ってから呼んでくださいね！」")
            return
            
        channel = interaction.user.voice.channel
        guild = interaction.guild
        
        if guild.id in self.active_calls:
            await interaction.followup.send("「すでにこのサーバーで通話中です！」")
            return
            
        try:
            vc = await channel.connect(cls=VoiceRecvClient, timeout=60.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("「接続がタイムアウトしました……！(ホストサーバーのUDP通信がブロックされている可能性があります！)」")
            return
        except Exception as e:
            await interaction.followup.send(f"「接続に失敗しました……」 ({e})")
            return
            
        key = random.choice(self.api_keys)
        client = genai.Client(api_key=key)
        
        # We need to run the live session in a background task
        loop = asyncio.get_event_loop()
        audio_queue = asyncio.Queue()
        
        sink = GeminiLiveSink(user_id, loop, audio_queue)
        vc.listen(sink)
        
        target_channel = interaction.channel if 返信先 == "channel" else interaction.user
        
        # Start the background task for this call
        call_task = asyncio.create_task(self._live_call_loop(guild.id, vc, client, interaction.user, target_channel, audio_queue))
        self.active_calls[guild.id] = {
            'vc': vc,
            'task': call_task
        }
        
        msg = "「繋がりましたよ！ボイスチャンネルで私に話しかけてみてくださいね。(返信はDMで送ります)」" if 返信先 == "dm" else "「繋がりましたよ！話しかけたら、このチャンネルで返信しますね！」"
        await interaction.followup.send(msg)

    async def _live_call_loop(self, guild_id, vc, client, user, target_channel, audio_queue):
        config = {"response_modalities": ["TEXT"]}
        # まきぐもの設定をシステムプロンプトに
        cog_ai = self.bot.get_cog("AI")
        system_instruction = cog_ai.system_instruction if cog_ai else "あなたはまきぐもです。"
        config["system_instruction"] = types.Content(parts=[types.Part.from_text(text=system_instruction)])
        config["tools"] = [{"google_search": {}}]
        
        try:
            async with client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
                
                async def send_audio():
                    while True:
                        try:
                            # チャンクをまとめる（約100msごとに送信）
                            chunks = []
                            chunk = await audio_queue.get()
                            chunks.append(chunk)
                            while not audio_queue.empty() and len(chunks) < 5:
                                chunks.append(audio_queue.get_nowait())
                            
                            data = b"".join(chunks)
                            await session.send(input={"data": data, "mime_type": "audio/pcm;rate=16000"})
                        except asyncio.CancelledError:
                            break
                        except Exception as e:
                            print(f"Live send error: {e}")
                            break

                async def receive_text():
                    current_reply = ""
                    async for response in session.receive():
                        if response.server_content:
                            if getattr(response.server_content, "interrupted", False):
                                # ユーザーが割り込んだら現在のテキストを破棄するか？
                                pass
                            
                            model_turn = response.server_content.model_turn
                            if model_turn:
                                for part in model_turn.parts:
                                    if part.text:
                                        current_reply += part.text
                            
                            if getattr(response.server_content, "turn_complete", False) and current_reply.strip():
                                try:
                                    await target_channel.send(f"{user.mention} {current_reply.strip()}" if isinstance(target_channel, discord.TextChannel) else current_reply.strip())
                                except:
                                    pass
                                current_reply = ""

                send_task = asyncio.create_task(send_audio())
                recv_task = asyncio.create_task(receive_text())
                
                # Wait until VC is disconnected
                while vc.is_connected():
                    await asyncio.sleep(1)
                    
                send_task.cancel()
                recv_task.cancel()
                
        except Exception as e:
            print(f"Live API error: {e}")
            try:
                await target_channel.send("「ごめんなさい、通話が途切れちゃいました……」")
            except:
                pass
        finally:
            if vc.is_connected():
                await vc.disconnect()
            if guild_id in self.active_calls:
                del self.active_calls[guild_id]

    @app_commands.command(name="end_call", description="まきぐもとの通話を終了します")
    async def end_call_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild or guild.id not in self.active_calls:
            await interaction.followup.send("「今は誰とも通話していませんよ？」")
            return
            
        call_info = self.active_calls[guild.id]
        vc = call_info['vc']
        await vc.disconnect()
        await interaction.followup.send("「通話を終了しました！またお話ししましょうね♡」")

async def setup(bot):
    api_keys = []
    for key, val in os.environ.items():
        if key.startswith("GEMINI_API_KEY_") and val:
            api_keys.append(val)
    await bot.add_cog(LiveCall(bot, api_keys))
