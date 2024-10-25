import discord
from discord.ext import commands
import youtube_dl
import os
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necesario para acceder a los miembros del canal
bot = commands.Bot(command_prefix='!', intents=intents)

GAMES = {
    1: ['TFT'],
    2: ['Fortnite', 'LoL', 'Valorant'],
    3: ['Fortnite', 'LoL', 'Valorant'],
    4: ['Fortnite', 'LoL', 'Valorant']
}

GIF_POOL = {
    'TFT': 'https://media.giphy.com/media/l0HlQ7LRal2QRfiA4/giphy.gif',
    'Fortnite': 'https://media.giphy.com/media/3o6MbkD4r9pqupzC/giphy.gif',
    'LoL': 'https://media.giphy.com/media/l0MYEqEzwMWFCg8rm/giphy.gif',
    'Valorant': 'https://media.giphy.com/media/l0HlQ7LRal2QRfiA4/giphy.gif'  # Añade más GIFs según necesites
}

PLAYER_LIST = ['Player1_ID', 'Player2_ID', 'Player3_ID', 'Player4_ID', 'Player5_ID']  # Reemplaza con los IDs de los jugadores

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def tplay(ctx, url):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send('Necesitas estar conectado en un canal de voz para usar el comando.')
        return
    vc = await voice_channel.connect()
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['formats'][0]['url']
        vc.play(discord.FFmpegPCMAudio(url2))

@bot.command()
async def tstop(ctx):
    for vc in bot.voice_clients:
        if vc.guild == ctx.guild:
            await vc.disconnect()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if str(message.author.id) == "cqx":
        await message.channel.send(f'Adiós, {message.author.name}!')
    if str(message.author.id) == "thecrx8":
        await message.channel.send('Media tula rey')
    
    await bot.process_commands(message)

@bot.command()
async def tulajuego(ctx, players: int):
    if players in GAMES:
        game = random.choice(GAMES[players])
        gif_url = GIF_POOL[game]
        await ctx.send(f'**Con {players} jugadores, pueden jugar {game}!** \n{gif_url}')
    else:
        await ctx.send('No hay juegos disponibles para esa cantidad de jugadores.')

@bot.command()
async def tinvocarvalo(ctx):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send('Debes estar en un canal de voz para usar este comando.')
        return

    missing_players = [member for member in PLAYER_LIST if discord.utils.get(ctx.guild.members, id=int(member)) not in voice_channel.members]
    
    if missing_players:
        mentions = ' '.join(f'<@{player}>' for player in missing_players)
        gif_url = random.choice(list(GIF_POOL.values()))
        await ctx.send(f'**Oye {mentions}, te estamos esperando!** \n{gif_url}')
    else:
        await ctx.send('¡Todos los jugadores están presentes!')

bot.run(os.environ["DISCORD_BOT_TOKEN"])
