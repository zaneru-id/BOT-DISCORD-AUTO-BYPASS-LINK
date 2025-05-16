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


TOKEN = 'BOT_TOKEN'
AUTOBYPASS_DATABASE_FILE = 'autobypass-database.json'
AUTHORIZED_USER_IDS = [COMMAND PERMISSION USER ID]

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="?", intents=intents)

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
            headers = {'x-api-key': 'https://discord.gg/X7MmBRv7em'}

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
        
@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} is now online. Made by zaneru.id")
    try:
        bot.add_view(PersistentScriptView()) 
    except Exception as e:
        print(f"Failed to add persistent view: {e}")
    while True:
        await bot.change_presence(
            status=nextcord.Status.dnd,
            activity=nextcord.Activity(type=nextcord.ActivityType.listening, name="Spotify")
        )
        await asyncio.sleep(30) 

        await bot.change_presence(
            status=nextcord.Status.dnd,
            activity=nextcord.Activity(type=nextcord.ActivityType.playing, name="Roblox")
        )
        await asyncio.sleep(30) 

def create_support_button():
    invite_link = "https://discord.gg/EK7uHBeb7B"
    website_link = "https://zaneru.vercel.app/"

    button_view = nextcord.ui.View()
    button_view.add_item(nextcord.ui.Button(label="🔗 Discord Server", style=nextcord.ButtonStyle.link, url=invite_link))
    button_view.add_item(nextcord.ui.Button(label="🌐 Profile Zaneru", style=nextcord.ButtonStyle.link, url=website_link))
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
        embed.add_field(name="<a:Load:1286411173998235699> Processing Bypass:", value="```Bypassing your link...```", inline=False)
        embed.add_field(name="<a:Load:1286411173998235699> Execution Time:", value="```Waiting for bypass...```", inline=False)

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

class PersistentScriptView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ScriptDropdown())

class ScriptDropdown(nextcord.ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="Fisch", value="fisch", emoji="<:Fisch:1323686161826185376>"),
            nextcord.SelectOption(label="Blox Fruit", value="blox_fruit", emoji="<:BloxFruit:1277100524810014762>"),
            nextcord.SelectOption(label="Grow A Garden", value="grow_garden", emoji="<:Grow_Garden:1372970253331730523>"),
            nextcord.SelectOption(label="Blue Lock Rivals", value="blue_lock", emoji="<:Blue_Lock:1372974530817036288>")
        ]
        super().__init__(placeholder="Choose Your Roblox Script Hub", options=options)

    async def callback(self, interaction: nextcord.Interaction):
        selected_value = self.values[0]
        if selected_value == "fisch":
            embed = nextcord.Embed(color=0xFFFFFF)
            embed.add_field(name="Native Lab", value=f'''```lua
script_key="PASTE_KEY_HERE";
(loadstring or load)(game:HttpGet("https://getnative.cc/script/loader"))()```''', inline=False)
            embed.add_field(name="Lyth Hub", value=f'''```lua
script_key = 'PASTE_KEY_HERE';
loadstring(game:HttpGet("https://api.luarmor.net/files/v3/loaders/d474a99b9800aaa6301496c9ce9834ce.lua"))()```''', inline=False)
            embed.add_field(name="Noble Hub", value=f'''```lua
if not game:IsLoaded() then repeat game.Loaded:Wait() until game:IsLoaded() end
loadstring(game:HttpGet("https://raw.githubusercontent.com/djaXlua/Noble/refs/heads/main/Noble%20Hub%20Fish.txt"))()```''', inline=False)
            embed.add_field(name="Lunor", value=f"""```lua
loadstring(game:HttpGet("https://lunor.dev/loader"))()```""", inline=False)     
            embed.add_field(name="Aethrix Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Imrane43/fisch-Script/refs/heads/main/Fisch%20Script",true))()\n```', inline=False)                     
            embed.add_field(name="Ice Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/SundayN10/Iced-Hub/refs/heads/main/IČ̣ƏƊ%20Hub"))()\n```', inline=False)
            embed.add_field(name="Than Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/thantzy/thanhub/refs/heads/main/thanv1"))()\n```', inline=False)
            embed.add_field(name="Forge Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Skzuppy/forge-hub/main/loader.lua"))()\n```', inline=False)
            embed.add_field(name="Alchemy Hub", value=f'```lua\nloadstring(game:HttpGet("https://scripts.alchemyhub.xyz"))()\n```', inline=False)
            embed.add_field(name="Speed Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/AhmadV99/Speed-Hub-X/main/Speed%20Hub%20X.lua", true))()\n```', inline=False)
            embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            embed.timestamp = nextcord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected_value == "blox_fruit":
            embed = nextcord.Embed(color=0xFFFFFF)
            embed.add_field(name="Banana Hub", value=f'''```lua
repeat wait() until game:IsLoaded() and game.Players.LocalPlayer
getgenv().Key = "PASTE_KEY_HERE"
loadstring(game:HttpGet("https://raw.githubusercontent.com/obiiyeuem/vthangsitink/main/BananaHub.lua"))()
-- Get Key : https://ads.luarmor.net/get_key?for=VHFslhWdrPey```''', inline=False)
            embed.add_field(name="Redz Hub",value=("```lua\n"
            "local Settings = {\n"
            '  JoinTeam = "Pirates"; -- Pirates/Marines\n'
            "  Translator = true; -- true/false\n"
            "}\n"
            'loadstring(game:HttpGet("https://raw.githubusercontent.com/newredz/BloxFruits/refs/heads/main/Source.luau"))(Settings)\n'"```"),inline=False)
            embed.add_field(name="Zinner Hub", value=f'''```lua
getgenv().Team = "Pirates"
loadstring(game:HttpGet("https://raw.githubusercontent.com/HoangNguyenk8/Roblox/refs/heads/main/BF-Main.luau"))()```''', inline=False)
            embed.add_field(name="Alchemy Hub", value=f"""```lua\nloadstring(game:HttpGet("https://scripts.alchemyhub.xyz"))()\n```""", inline=False)
            embed.add_field(name="OMG Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Omgshit/Scripts/main/MainLoader.lua"))()\n```', inline=False)
            embed.add_field(name="Hoho Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/acsu123/HOHO_H/main/Loading_UI"))()\n```', inline=False)
            embed.add_field(name="Aurora Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Jadelly261/BloxFruits/main/Aurora", true))()\n```', inline=False)
            embed.add_field(name="Vxeze Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Dex-Bear/Vxezehub/refs/heads/main/VxezeHubMain"))()\n```', inline=False)
            embed.add_field(name="Ronix Hub", value=f'```lua\nloadstring(game:HttpGet("https://api.luarmor.net/files/v3/loaders/b2db2af40b53ef0a502f6d561b4c6449.lua"))()\n```', inline=False)
            embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            embed.timestamp = nextcord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected_value == "grow_garden":
            embed = nextcord.Embed(color=0xFFFFFF)
            embed.add_field(name="Solix Hub",value=("```lua\n"
            "_G.AutoFarm = true\n"
            '_G.PerformanceMode = "Fast" -- "LowEnd", "Normal", "Fast", "Ultra"\n'
            "_G.TeleportCooldown = 0.1\n"
            "-- Seed settings\n"
            "_G.AutoRebuy = true\n"
            "_G.SeedPrice = 4000\n"
            "_G.AutoSellThreshold = 50\n"
            "_G.AutoWatering = true\n"
            "_G.AutoSprinklers = true\n"
            "-- Gear shop\n"
            "_G.GearShopAutoBuy = true\n"
            '_G.GearShopItems = {"Basic Watering Can", "Basic Sprinkler", "Basic Shovel"}\n'
            "_G.RenderDistance = 50\n"
            "_G.UIUpdateInterval = 2\n"
            "_G.OptimizeRendering = true\n"
        'loadstring(game:HttpGet("https://raw.githubusercontent.com/debunked69/solixloader/refs/heads/main/solix%20v2%20new%20loader.lua"))()\n'"```"), inline=False)
            embed.add_field(name="Native Lab", value=f"""```lua
script_key="PASTE_KEY_HERE";
(loadstring or load)(game:HttpGet("https://getnative.cc/script/loader"))()```""", inline=False)
            embed.add_field(name="No Lag Hub", value=f'```lua\nloadstring(game:HttpGet("https://rawscripts.net/raw/Grow-a-Garden-NoLag-Hub-no-key-38699"))()```', inline=False)
            embed.add_field(name="Ronix Hub", value=f'```lua\nloadstring(game:HttpGet("https://api.luarmor.net/files/v3/loaders/a8f02a61fc38bf9256dd0f17be6b16d7.lua"))()\n```', inline=False)
            embed.add_field(name="Beecon Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/BaconBossScript/BeeconHub/main/BeeconHub"))()\n```', inline=False)
            embed.add_field(name="Blue Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/ameicaa1/Grow-a-Garden/main/Grow_A_Garden.lua"))()\n```', inline=False)
            embed.add_field(name="Tora Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/gumanba/Scripts/main/GrowaGarden"))()\n```', inline=False)
            embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            embed.timestamp = nextcord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected_value == "blue_lock":
            embed = nextcord.Embed(color=0xFFFFFF)
            embed.add_field(name="Sterling Hub",value=("```lua\n"
            "local GuiService = game:GetService(\"GuiService\")\n"
            "local Players = game:GetService(\"Players\")\n"
            "local TeleportService = game:GetService(\"TeleportService\")\n"
            "local player = Players.LocalPlayer\n"
            "local function onErrorMessageChanged(errorMessage)\n"
            "    if errorMessage and errorMessage ~= \"\" then\n"
            "        print(\"Error detected: \" .. errorMessage)\n"
            "        if player then\n"
            "            wait()\n"
            "            TeleportService:Teleport(game.PlaceId, player)\n"
            "        end\n"
            "    end\n"
            "end\n"
            "GuiService.ErrorMessageChanged:Connect(onErrorMessageChanged)\n"
        'loadstring(game:HttpGet("https://raw.githubusercontent.com/Zayn31214/name/refs/heads/main/SterlingNew"))()\n'"```"),inline=False)
            embed.add_field(name="Dehism Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/dehism/Dehism/refs/heads/main/Inf%20Spins%20Auto%20Dehism",true))()\n```', inline=False)
            embed.add_field(name="Alchemy Hub", value=f'```lua\nloadstring(game:HttpGet("https://scripts.alchemyhub.xyz"))()\n```', inline=False)
            embed.add_field(name="XZuyaX Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/XZuuyaX/XZuyaX-s-Hub/refs/heads/main/Main.Lua", true))()\n```', inline=False)
            embed.add_field(name="OMG Hub", value=f'```lua\nloadstring(game:HttpGet("https://rawscripts.net/raw/UPD-Blue-Lock:-Rivals-OMG-Hub-29091"))()\n```', inline=False)
            embed.add_field(name="Control Ball Hub", value=f'```lua\nloadstring(game:HttpGet("https://raw.githubusercontent.com/RedJDark/CONTROL-SCRIPTT/refs/heads/main/CONTROL"))()\n```', inline=False)
            embed.set_footer(text=f"Made by zaneru.id", icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512")
            embed.timestamp = nextcord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="script", help="Show a list of Roblox script hubs")
async def script(ctx):
    if ctx.guild.owner_id != ctx.author.id and ctx.author.id not in AUTHORIZED_USER_IDS:
        await ctx.send("You don't have permission to use this command.", delete_after=5)
        return
    
    await ctx.message.delete(delay=5)

    embed = nextcord.Embed(
        title="",
        description="## Select Your Script Hub <a:Roblox:1323694731007623179>",
        color=0x00B0FC
    )
    embed.timestamp = nextcord.utils.utcnow()
    embed.set_author(
        name="Zaneru Official - Roblox Script Hub",
        icon_url="https://cdn.discordapp.com/avatars/1327497352314880000/eafd9e5cf06ebdfc674569fdd5f6c67f.png?size=512"
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/1323665389888208996/1372995793975513300/zaneru-id.gif"
    )
    embed.add_field(name="", value="<:Anjay:1369631567550353450> [Website](https://zaneru-official.vercel.app)", inline=False)
    embed.add_field(name="", value="<:Youtube:1323673690742718586> [Youtube](https://www.youtube.com/@zaneru-id)", inline=False)
    embed.add_field(name="", value="<:Tiktok:1372981471374999772> [Tiktok](https://www.tiktok.com/@zaneru.id)", inline=False)
    embed.set_footer(
        text="Made by zaneru.id",
        icon_url="https://cdn.discordapp.com/emojis/1273384825801412638.gif?size=512"
    )
    embed.set_image(
        url="https://cdn.discordapp.com/attachments/1323665389888208996/1372984734921261166/zaneru-official.gif"
    )

    await ctx.send(embed=embed, view=PersistentScriptView())

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"An error occurred while trying to run the bot: {str(e)}")
