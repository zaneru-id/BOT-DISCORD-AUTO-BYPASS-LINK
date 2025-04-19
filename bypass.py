import json
import asyncio
import aiohttp
import nextcord
from nextcord.ext import commands
import re
import time
import psutil
import platform
import datetime


TOKEN = 'REPLACE_WITH_YOUR_TOKEN'
AUTOBYPASS_DATABASE_FILE = 'autobypass-database.json'
AUTHORIZED_USER_IDS = [1044986769331998780, 1078741697913159750]

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="-", intents=intents)

try:
    with open(AUTOBYPASS_DATABASE_FILE, 'r') as f:
        autobypass_channels = json.load(f)
except FileNotFoundError:
    autobypass_channels = []

def save_autobypass_channels():
    with open(AUTOBYPASS_DATABASE_FILE, 'w') as f:
        json.dump(autobypass_channels, f, indent=2)

def set_autobypass(channel_id):
    if channel_id not in autobypass_channels:
        autobypass_channels.append(channel_id)
        save_autobypass_channels()

def remove_autobypass(channel_id):
    if channel_id in autobypass_channels:
        autobypass_channels.remove(channel_id)
        save_autobypass_channels()

def is_auto_bypass(channel_id):
    return channel_id in autobypass_channels

async def call_all_api(link):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        try:
            create_task_url = 'https://api.voltar.lol/bypass/createTask'
            payload = {'url': link}
            headers = {'x-api-key': 'Buy Voltar API Key'}

            async with session.post(create_task_url, json=payload, headers=headers) as create_response:
                if create_response.status != 200:
                    return {"error": f"Failed to create task. Status Code: {create_response.status}"}
                
                response_json = await create_response.json()
                if 'taskId' not in response_json:
                    return {"error": "Failed to retrieve task ID from response."}

                task_id = response_json['taskId']

            get_task_result_url = f'https://api.voltar.lol/bypass/getTaskResult/{task_id}'
            while True:  
                async with session.get(get_task_result_url, headers=headers) as result_response:
                    if result_response.status != 200:
                        return {"error": f"Failed to get task result. Status Code: {result_response.status}"}
                    
                    result_data = await result_response.json()
                    if result_data.get('status') == 'success':
                        return {"result": result_data.get('result')}
                    elif result_data.get('status') == 'error':
                        return {"error": result_data.get('message')}

        except asyncio.TimeoutError:
            return {"error": "Request timed out."}
        except Exception as error:
            return {"error": str(error)}

def create_support_button():
    invite_link = "https://discord.gg/EK7uHBeb7B"
    website_link = "https://zaneru-official.vercel.app/"

    button_view = nextcord.ui.View()
    button_view.add_item(nextcord.ui.Button(label="🔗 Discord Server", style=nextcord.ButtonStyle.link, url=invite_link))
    button_view.add_item(nextcord.ui.Button(label="🌐 Zaneru Official", style=nextcord.ButtonStyle.link, url=website_link))
    return button_view

@bot.slash_command(name='set-auto-bypass', description='Set an auto-bypass for this channel')
async def set_auto_bypass(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    if interaction.guild.owner_id != interaction.user.id and interaction.user.id not in AUTHORIZED_USER_IDS:
        await interaction.response.send_message('You don\'t have permission to use this command.', ephemeral=True)
        return
    set_autobypass(channel.id)
    await interaction.response.send_message(f'Auto-Bypass set for this channel: "<#{channel.id}>"', ephemeral=True)

@bot.slash_command(name='remove-auto-bypass', description='Remove an auto-bypass for this channel')
async def remove_auto_bypass(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    if interaction.guild.owner_id != interaction.user.id and interaction.user.id not in AUTHORIZED_USER_IDS:
        await interaction.response.send_message('You don\'t have permission to use this command.', ephemeral=True)
        return
    remove_autobypass(channel.id)
    await interaction.response.send_message(f'Auto-Bypass removed for this channel: "<#{channel.id}>"', ephemeral=True)

def contains_link(message_content):
    url_pattern = r'https?://[^\s]+'
    return re.search(url_pattern, message_content) is not None

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if contains_link(message.content) and is_auto_bypass(message.channel.id):
        await handle_auto_bypass(message)

    await bot.process_commands(message)

async def handle_auto_bypass(message):
    original_author = message.author
    username = original_author.mention

    try:
        loading_message = None
        start_time = time.time()
        avatar_url = message.author.display_avatar.url

        link_to_bypass = message.content

        embed = nextcord.Embed(color=0x04ABEE)
        embed.add_field(name="<a:Load:1286411173998235699> Processing Bypass:", value="```Waiting for result...```", inline=False)
        embed.add_field(name="<a:Load:1286411173998235699> Execution Time:", value="```Processing bypass...```", inline=False)

        embed.set_footer(text=f"Requested by {original_author.name}", icon_url=avatar_url)
        loading_message = await message.reply(content=f"<a:Loading:1273384850568777738> **Bypassing for** {username}", embed=embed)

        response = await call_all_api(link_to_bypass)
        time_taken = time.time() - start_time

        if "error" in response:
            error_embed = nextcord.Embed(color=nextcord.Color.red())
            error_embed.timestamp = nextcord.utils.utcnow()
            error_embed.add_field(name="<a:RedCross:1273746045700018277> Bypass Failed:", value=f"```{response['error']}```", inline=False)
            error_embed.add_field(name="<a:Clock:1273385315578675272> Execution Time:", value=f"```{time_taken:.2f} seconds```", inline=False)
            error_embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            if loading_message:
                await loading_message.edit(content=f"<a:Failed:1279267934690349098> **Bypass Failed** {username}.", embed=error_embed)
        else:
            bypass_result = response.get("result")

            result_embed = nextcord.Embed(color=nextcord.Color.green())
            result_embed.timestamp = nextcord.utils.utcnow()
            result_embed.add_field(name="<a:Check:1273746027647729674> Bypassed Result:", value=f"```\n{bypass_result}\n```", inline=False)
            result_embed.add_field(name="<a:Clock:1273385315578675272> Execution Time:", value=f"```{time_taken:.2f} seconds```", inline=False)
            result_embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            if loading_message:
                await loading_message.edit(content=f"<a:Done:1279267918135169095> **Bypass Completed** {username}.", embed=result_embed, view=create_support_button())

    except Exception as e:
        error_embed = nextcord.Embed(color=nextcord.Color.red())
        error_embed.timestamp = nextcord.utils.utcnow()
        error_embed.add_field(name="<a:RedCross:1273746045700018277> Error Message:", value=f"```{str(e)}```", inline=False)
        error_embed.set_thumbnail(url=avatar_url)
        error_embed.set_footer(text=f"Requested by {original_author.name}", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")

        if loading_message:
            await loading_message.edit(content=f"<a:Failed:1279267934690349098> **Bypass Error** {username}.", embed=error_embed)
        else:
            await message.channel.send(content=f"<a:Failed:1279267934690349098> **Bypass Error** {username}.", embed=error_embed)

        print(f"An error occurred: {str(e)}")

bot_start_time = datetime.datetime.now() 

@bot.slash_command(name='bot-info', description="Fetch the bot's statistics.")
async def bot_info(interaction: nextcord.Interaction):
    latency = round(bot.latency * 1000)
    process = psutil.Process()
    memory_usage = process.memory_info().rss / (1024 ** 2)
    cache_size = round(len(bot.cached_messages) / (1024 ** 2), 2)
    uptime_delta = datetime.datetime.now() - bot_start_time
    uptime_hours, remainder = divmod(uptime_delta.total_seconds(), 3600)
    uptime_minutes, uptime_seconds = divmod(remainder, 60)
    discord_py_version = nextcord.__version__
    servers = len(bot.guilds)
    users = sum(guild.member_count for guild in bot.guilds)

    embed = nextcord.Embed(color=0x04B8F7)
    description = (
        f"## <a:Bot:1273718793495121992> Zaneru Official - Bot Statistic\n\n"
        + "-" * 51 + "\n"  
        f"**__Latency__**\n"
        f"🟢 **API Latency: {latency} ms**\n\n"
        f"**__Memory__**\n"
        f"💾 **Memory Usage: {memory_usage:.2f} MB**\n"
        f"♻️ **Cache Size: {cache_size:.2f} MB**\n\n"
        f"**__System__**\n"
        f"⚙️ **Nextcord Version: {discord_py_version}**\n"
        f"⚙️ **Python Version: {platform.python_version()}**\n\n"
        f"**__Stats__**\n"
        f"🌐 **Total Servers: {servers}**\n"
        f"💻 **Total Users: {users}**\n\n"
        f"**__Uptime__**\n"
        f"📊 **I've been online for {int(uptime_hours)} hours, {int(uptime_minutes)} minutes, and {int(uptime_seconds)} seconds**\n"
    )

    embed.description = description
    embed.timestamp = nextcord.utils.utcnow()
    embed.set_footer(text="Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")

    await interaction.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} Now is online. Made by zaneru.id")
    while True:
        await bot.change_presence(
            status=nextcord.Status.dnd,
            activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="zaneru.id")
        )
        await asyncio.sleep(30) 

        await bot.change_presence(
            status=nextcord.Status.dnd,
            activity=nextcord.Activity(type=nextcord.ActivityType.playing, name="Roblox")
        )
        await asyncio.sleep(30) 

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"An error occurred while trying to run the bot: {str(e)}")