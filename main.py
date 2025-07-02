import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import validators
import yt_dlp


# Bot prefix used for writting commands
BOT_PREFIX = '.'
DISCORD_TOKEN = <<ADD DISCORD_TOKEN>>

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

dj_yasuo = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# Discord format audio re-encoding
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

@dj_yasuo.event
async def on_ready():
    print(f"DJ Yasuo connected as {dj_yasuo.user}")
    try:
        synced = await dj_yasuo.tree.sync()
        print(f"Synced {len(synced)} commands(s)")
    except Exception as e:
        print(f"Error encounteres: {e}")

@dj_yasuo.tree.command(name="join", description="DJ Yasuo will join the voice channel.")
async def join(ctx: discord.Interaction):
    if not ctx.user.voice:
        await ctx.response.send_message(f"Some mistakes you can\'t make twice. Join a voice channel.")
        return
    
    channel = ctx.user.voice.channel
    await channel.connect()
    await ctx.response.send_message(f"A wanderer isn\'t always lost. Joined {channel.name}")

@dj_yasuo.tree.command(name="leave", description="DJ Yasuo will leave the voice channel.")
async def leave(ctx: discord.Interaction):
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.response.send_message(f"No cure for fools.")
    else:
        await ctx.response.send_message(f"If you've come to kill me... I hope you brought friends. I am not in a voice channel.")

@dj_yasuo.tree.command(name="play", description="DJ Yasuo will play a song.")
@app_commands.describe(query="Song name and artist or youtube url")
async def play(ctx: discord.Interaction, query: str):
    await ctx.response.defer()

    if not ctx.guild.voice_client:
        if ctx.user.voice:
            channel = ctx.user.voice.channel
            await channel.connect()
            await ctx.followup.send(f"A wanderer isn\'t always lost. Joined {channel.name}")
        else:
            await ctx.followup.send(f"Some mistakes you can\'t make twice. Join a voice channel.")
            return
    
    channel = ctx.guild.voice_client

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
    await ctx.followup.send(f"Now playing: {song_title}")

@dj_yasuo.tree.command(name="stop", description="DJ Yasuo will stop playing the current song.")
async def stop(ctx: discord.Interaction):
    if ctx.guild.voice_client:
        ctx.guild.voice_client.stop()
        await ctx.response.send_message(f"Stopped playing.")
    else:
        await ctx.response.send_message(f"If you've come to kill me... I hope you brought friends. I am not in a voice channel.")


dj_yasuo.run(DISCORD_TOKEN)