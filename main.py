import asyncio
import dataclasses
import json
import os
import re
import subprocess
import wave
from typing import Optional, Dict

import discord
from discord import VoiceClient, VoiceState, Status
from discord.ext import commands
from gtts import gTTS
from piper.voice import PiperVoice

with open('config.json', 'r') as f:
    cfg = json.loads(f.read())
bot = commands.Bot(command_prefix="-", intents=discord.Intents.all(), status=Status.idle,
                   activity=discord.Game(name='-connect'))
cfg_say_name = False


@dataclasses.dataclass
class TTSUser:
    user_id: int
    channel_id: int
    voice: str


current_watching: Dict[int, TTSUser] = {

}

models = ["models/en_US-hfc_female-medium.onnx", "models/en_GB-cori-high.onnx", "models/en_US-kristin-medium.onnx",
          "models/en_US-lessac-high.onnx", "models/en_US-libritts-high.onnx", "models/en_US-amy-medium.onnx",
          "models/en_US-ryan-high.onnx.json"]
voices = {}


def make_audio_file(text, voice: str):
    wav_file = wave.open("/tmp/hazelbot.wav", "wb")
    voices[voice].synthesize(text, wav_file)
    os.system("rm /tmp/hazelbot.opus")
    os.system("ffmpeg -i /tmp/hazelbot.wav -c:a libopus -b:a 96000 /tmp/hazelbot.opus")


def get_audio_stream(text):
    tts = gTTS(text)
    return tts.stream()


@bot.event
async def on_ready():
    print(f"Connected as {bot.user.name}!")


async def vc_mute(channel, guild: discord.Guild):
    await asyncio.sleep(0.4)
    await guild.change_voice_state(channel=channel, self_mute=True, self_deaf=True)


@bot.event
async def on_message(message: discord.Message):
    if message.content.startswith("-"):
        await bot.process_commands(message)
        return
    if message.author.id not in current_watching:
        await bot.process_commands(message)
        return
    if not current_watching[message.author.id].channel_id == message.channel.id:
        await bot.process_commands(message)
        return

    if len(message.content) > 0:
        print(f"Content - {message.clean_content}")
        ctx = await bot.get_context(message)
        await ctx.guild.change_voice_state(channel=message.channel, self_mute=False, self_deaf=False)

        ctx = await bot.get_context(message)
        vc: VoiceClient = ctx.guild.voice_client
        if vc is None:
            vc = await message.channel.connect(self_mute=False, self_deaf=False)
        # urlremoved_content = re.sub(r'http\S+', '', message.clean_content())
        # print(urlremoved_content)
        urlremoved_content = message.clean_content
        if cfg_say_name or len(current_watching) > 1:
            # stream = get_audio_stream(f"{message.author.nick} says {message.content}")
            make_audio_file(f"{message.author.display_name} says {urlremoved_content}",
                            current_watching[message.author.id].voice)
        else:
            # stream = get_audio_stream(message.content)
            make_audio_file(urlremoved_content, current_watching[message.author.id].voice)

        if vc is not None:
            # vc.play(discord.FFmpegPCMAudio(stream, pipe=True, options='-filter:a loudnorm'),
            #         after=lambda e: asyncio.run_coroutine_threadsafe(vc_mute(ctx.channel, ctx.guild), bot.loop))

            vc.play(discord.FFmpegOpusAudio("/tmp/hazelbot.opus", bitrate=96),
                    #, options='-ar 22050'), #, options='-filter:a "setpts=0.7*PTS"'),
                    after=lambda e: asyncio.run_coroutine_threadsafe(vc_mute(ctx.channel, ctx.guild), bot.loop),
                    signal_type='voice', bandwidth='full', bitrate=96, application='audio')


def load_voice(index):
    global voices
    if models[index] not in voices:
        voices[models[index]] = PiperVoice.load(models[index])


def unload_voice():
    for voice in voices.keys():
        if voice not in [l.voice for l in current_watching.values()]:
            del voices[voice]


@bot.command()
async def connect(ctx: commands.Context, voice: Optional[int] = 0):
    global current_watching
    voice_state = ctx.author.voice

    if voice_state is None:
        # Exiting if the user is not in a voice channel
        await ctx.send('You need to be in a voice channel to use this command')
        return
    await ctx.reply(f"Using model `{models[voice]}`")
    load_voice(voice)
    current_watching[ctx.author.id] = TTSUser(ctx.author.id, voice_state.channel.id, models[voice])
    await ctx.message.add_reaction('✅')
    vcid = voice_state.channel.id
    channel = await bot.fetch_channel(vcid)
    await channel.connect()
    await ctx.guild.change_voice_state(channel=ctx.channel, self_mute=True, self_deaf=True)
    await bot.change_presence(status=Status.online, activity=discord.Activity(type=discord.ActivityType.listening,
                                                                              name='Committing identity theft'))


@bot.event
async def on_voice_state_update(member, before: VoiceState, after: VoiceState):
    global current_watching
    voice_state = member.guild.voice_client

    if voice_state is None:
        # Exiting if the bot is not connected to a voice channel
        return
    if member.id in current_watching:
        if after.channel is None:
            current_watching.pop(member.id, None)
    if len(current_watching) == 0:
        await voice_state.disconnect()
        await bot.change_presence(status=Status.idle, activity=discord.Game(name='-connect'))
        unload_voice()
    if len(voice_state.channel.members) == 1:
        await voice_state.disconnect()
        await bot.change_presence(status=Status.idle, activity=discord.Game(name='-connect'))
        unload_voice()


@bot.command()
async def disconnect(ctx: commands.Context):
    global current_watching
    current_watching.pop(ctx.author.id, None)
    if len(current_watching) == 0:
        await ctx.voice_client.disconnect(force=False)
        await bot.change_presence(status=Status.idle, activity=discord.Game(name='-connect'))
        unload_voice()
    await ctx.message.add_reaction('✅')


@bot.command(name="voices")
async def voices_list(ctx: commands.Context):
    str = "Voices: "
    for a in models:
        str += "\n" + f"`{a}`"
    await ctx.reply(str)


@bot.command()
async def update(ctx: commands.Context):
    print(f"Update on command of {ctx.author.name}")
    if ctx.author.id not in cfg['developers']:
        await ctx.reply("Not authorized")
        return
    if len(current_watching):
        await ctx.voice_client.disconnect(force=False)
    res = os.popen("git pull").read()
    if res.startswith('Already up to date.'):
        await ctx.send(embed=discord.Embed(description='```\n' + res + '```', color=discord.Color.orange()))
    else:
        await ctx.send(embed=discord.Embed(title="Updated", description='```\n' + res + '```',
                                           color=discord.Color.orange()))
        subprocess.run("sudo systemctl restart hazelbot.service".split(' '))


@bot.event
async def on_application_command_error(ctx: commands.Context, error: discord.DiscordException):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply("This command is currently on cooldown!")
    else:
        await ctx.send(f"ERROR: \n {str(error)}")
        raise error  # Here we raise other errors to ensure they aren't ignored


asyncio.run(bot.start(cfg['TOKEN']))
