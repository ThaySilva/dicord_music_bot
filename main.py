import asyncio
import discord
from discord.ext import commands
import validators
import yt_dlp


# Bot prefix used for writting commands
BOT_PREFIX = '.'
DISCORD_TOKEN = <<ADD DISCORD_TOKEN>>

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

dj_yasuo = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# Discord format audio re-encoding
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
}

@dj_yasuo.event
async def on_ready():
    print(f"DJ Yasuo connected as {dj_yasuo.user}")

@dj_yasuo.command(name='join')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f"Some mistakes you can\'t make twice. Join a voice channel.")
        return
    
    channel = ctx.message.author.voice.channel
    await channel.connect()
    await ctx.send(f"A wanderer isn\'t always lost. Joined {channel.name}")

@dj_yasuo.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send(f"No cure for fools.")
    else:
        await ctx.send(f"If you've come to kill me... I hope you brought friends. I am not in a voice channel.")

@dj_yasuo.command('play')
async def play(ctx, *, query):
    if not ctx.voice_client:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"A wanderer isn\'t always lost. Joined {channel.name}")
        else:
            await ctx.send(f"Some mistakes you can\'t make twice. Join a voice channel.")
            return
    
    channel = ctx.voice_client

    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            if validators.url(query):
                song = ydl.extract_info(query, download=False)
            else:
                song = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in song:
                    song = song['entries'][0]
                else:
                    song = song

            song_url = song['url']
            song_title = song.get('title')
        except Exception as e:
            await ctx.send(f"Could not find or play the song. Error: `{e}`")
            return
    
    if channel.is_playing():
        channel.stop()

    channel.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS))
    await ctx.send(f"Now playing: {song_title}")

@dj_yasuo.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send(f"Stopped playing.")
    else:
        await ctx.send(f"If you've come to kill me... I hope you brought friends. I am not in a voice channel.")


dj_yasuo.run(DISCORD_TOKEN)