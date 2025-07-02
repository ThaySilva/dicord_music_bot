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

class Song:
    def __init__(self, source, song, requester):
        self.source = source
        self.song = song
        self.title = song.get('title')
        self.url = song.get('webpage_url')
        self.uri = song['url']
        self.duration = self._format_duration(song.get('duration'))
        self.thumbnail = song.get('thumbnail')
        self.requester = requester

    @classmethod
    async def from_query(cls, query, *, loop=None, stream=False, requester=None):
        loop = loop or asyncio.get_event_loop()

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
            except Exception as e:
                await print(f"Could not find or play the song. Error: `{e}`")
                return

        return cls(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS), song=song, requester=requester)

    def _format_duration(self, seconds):
        if seconds is None:
            return "N/A"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        return f"{int(minutes):02}:{int(seconds):02}"

# Store playlists per guilds
song_queues = {}

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
    
    if channel.is_playing():
        channel.stop()

    await ctx.followup.send(f"Sorye! Searching for `{query}`...")
    try:
        song = await Song.from_query(query, loop=dj_yasuo.loop, stream=True, requester=ctx.user)
        embed_player = discord.Embed(title="Now Playing", description=f"{song.title}", color=discord.Color.blue())
        embed_player.add_field(name="Requested By", value=song.requester.mention, inline=True)
        embed_player.add_field(name="Duration", value=song.duration, inline=True)
        if song.thumbnail:
            embed_player.set_thumbnail(url=song.thumbnail)

        channel.play(discord.FFmpegPCMAudio(song.uri, **FFMPEG_OPTIONS))
        await ctx.followup.send(embed=embed_player)
    except Exception as e:
        await ctx.followup.send(f"Could not find or play the song. Error: `{e}`")
        print(f"Error in play command: {e}")

@dj_yasuo.tree.command(name="stop", description="DJ Yasuo will stop playing the current song.")
async def stop(ctx: discord.Interaction):
    if ctx.guild.voice_client:
        ctx.guild.voice_client.stop()
        await ctx.response.send_message(f"Stopped playing.")
    else:
        await ctx.response.send_message(f"If you've come to kill me... I hope you brought friends. I am not in a voice channel.")


dj_yasuo.run(DISCORD_TOKEN)