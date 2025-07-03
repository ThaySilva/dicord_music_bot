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
        self.url = song.get('url')
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

        return cls(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS),
                   song=song, requester=requester)

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

async def play_next(ctx, guild):
    if song_queues.get(guild.id):
        next_song = song_queues[guild.id].pop(0)
        song_title = next_song['title']
        current_song = next_song['song']

        channel = guild.voice_client

        source = discord.FFmpegPCMAudio(current_song.url, **FFMPEG_OPTIONS)

        def after_playing(error):
            r = asyncio.run_coroutine_threadsafe(play_next(ctx, guild),
                                                 dj_yasuo.loop)
            try:
                r.result()
            except Exception as e:
                print(f"Error encountered {e}")

        channel.play(source, after=after_playing)

        embed_player = discord.Embed(
            title="Now Playing",
            description=f"{song_title}",
            color=discord.Color.blue()
        )

        embed_player.add_field(
            name="Requested By",
            value=current_song.requester.mention,
            inline=True
        )

        embed_player.add_field(
            name="Duration",
            value=current_song.duration,
            inline=True
        )

        if current_song.thumbnail:
            embed_player.set_thumbnail(url=current_song.thumbnail)
        await ctx.followup.send(embed=embed_player)

@dj_yasuo.event
async def on_ready():
    print(f"DJ Yasuo connected as {dj_yasuo.user}")
    try:
        synced = await dj_yasuo.tree.sync()
        print(f"Synced {len(synced)} commands(s)")
    except Exception as e:
        print(f"Error encounteres: {e}")

@dj_yasuo.tree.command(name="join",
                       description="DJ Yasuo will join the voice channel.")
async def join(ctx: discord.Interaction):
    if not ctx.user.voice:
        embed_response = discord.Embed(
            description="Some mistakes you can\'t make twice. Join a voice channel.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)
        return

    channel = ctx.user.voice.channel
    await channel.connect()
    embed_response = discord.Embed(
        description=f"A wanderer isn\'t always lost. Joined {channel.name}",
        color=discord.Color.green()
    )
    await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(name="leave",
                       description="DJ Yasuo will leave the voice channel.")
async def leave(ctx: discord.Interaction):
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        song_queues.pop(ctx.guild.id, None)
        embed_response = discord.Embed(
            description="No cure for fools.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)
    else:
        embed_response = discord.Embed(
            description="If you've come to kill me... " \
            "I hope you brought friends. I am not in a voice channel.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(name="play", description="DJ Yasuo will play a song.")
@app_commands.describe(query="Song name and artist or youtube url")
async def play(ctx: discord.Interaction, query: str):
    await ctx.response.defer()

    if not ctx.guild.voice_client:
        if ctx.user.voice:
            channel = ctx.user.voice.channel
            await channel.connect()
            embed_response = discord.Embed(
                description=f"A wanderer isn\'t always lost. " \
                            f"Joined {channel.name}",
                color=discord.Color.green()
            )
            await ctx.followup.send(embed=embed_response)
        else:
            embed_response = discord.Embed(
                description="Some mistakes you can\'t make twice. " \
                            "Join a voice channel.",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed_response)
            return

    channel = ctx.guild.voice_client

    embed_response = discord.Embed(
        description=f"Sorye! Searching for {query}...",
        color=discord.Color.purple()
    )
    await ctx.followup.send(embed=embed_response)
    try:
        song = await Song.from_query(query,
                                     loop=dj_yasuo.loop,
                                     stream=True,
                                     requester=ctx.user)

        queue = song_queues.get(ctx.guild.id, [])
        queue.append({'title': song.title, 'song': song})
        song_queues[ctx.guild.id] = queue

        if not channel.is_playing():
            await play_next(ctx, ctx.guild)
        else:
            embed_player = discord.Embed(
                title="Added song to queue",
                description=song.title,
                color=discord.Color.orange()
            )
            await ctx.followup.send(embed=embed_player)
    except Exception as e:
        await ctx.followup.send(f"Could not find or play the song. Error: {e}")
        print(f"Error in play command: {e}")

@dj_yasuo.tree.command(name="pause",
                       description="DJ Yasuo will pause the current song.")
async def pause(ctx: discord.Interaction):
    channel = ctx.guild.voice_client
    if channel and channel.is_playing():
        channel.pause()
        embed_player = discord.Embed(
            description="Song Paused.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_player)
    else:
        embed_response = discord.Embed(
            description="There is no song playing to pause.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(
        name="resume",
        description="DJ Yasuo will resume the current paused song.")
async def resume(ctx: discord.Interaction):
    channel = ctx.guild.voice_client
    if channel and channel.is_paused():
        channel.resume()
        embed_player = discord.Embed(
            description="Song Resumed.",
            color=discord.Color.blue()
        )
        await ctx.response.send_message(embed=embed_player)
    else:
        embed_response = discord.Embed(
            description="There is no song currently paused.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(
        name="stop",
        description="DJ Yasuo will stop playing the current song.")
async def stop(ctx: discord.Interaction):
    channel = ctx.guild.voice_client
    if ctx.guild.voice_client:
        channel.stop()
        song_queues.pop(ctx.guild.id, None)
        embed_response = discord.Embed(
            description="Stopped playing and cleared the playlist.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)
    else:
        embed_response = discord.Embed(
            description="If you've come to kill me... " \
            "I hope you brought friends. I am not in a voice channel.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(name="skip",
                       description="DJ Yasuo will skip to the next song")
async def skip(ctx: discord.Interaction):
    channel = ctx.guild.voice_client
    if channel and channel.is_playing():
        channel.stop()
        embed_response = discord.Embed(
            description="Skipped to the next song.",
            color=discord.Color.orange()
        )
        await ctx.response.send_message(embed=embed_response)
    else:
        embed_response = discord.Embed(
            description="There is no song currently playing.",
            color=discord.Color.red()
        )
        await ctx.response.send_message(embed=embed_response)

@dj_yasuo.tree.command(name="playlist",
                       description="View the current playlist")
async def playlist(ctx: discord.Interaction):
    queue = song_queues.get(ctx.guild.id, [])
    if not queue:
        embed_response = discord.Embed(
            description="The playlist is empty.",
            color=discord.Color.brand_red()
        )
        await ctx.response.send_message(embed=embed_response)
        return

    queue_list = "\n".join([f"**{id+1}.** {song['title']}" 
                            for id, song in enumerate(queue)])
    embed_player = discord.Embed(
        title="Playlist",
        description=queue_list,
        color=discord.Color.blurple()
    )
    await ctx.response.send_message(embed=embed_player)


dj_yasuo.run(DISCORD_TOKEN)