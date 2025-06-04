import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio

# Settings
TOKEN = "YOUR_BOT_TOKEN"
VPS_IP = "YOUR_VPS_IP"
VPS_ROOT_PASSWORD = "YOUR_VPS_ROOT_PASSWORD"
ADMIN_IDS = [123456789012345678]  # Replace with actual admin user IDs
DATA_FILE = "vps_users.json"
TEXT_FILE = "texts.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_texts():
    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE) as f:
            return json.load(f)
    return {}

def save_texts(texts):
    with open(TEXT_FILE, 'w') as f:
        json.dump(texts, f, indent=2)


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot ready as {bot.user}")


# Slash command: create-vps
@tree.command(name="create-vps", description="Create a VPS (admin only)")
@app_commands.describe(hostname="VPS hostname", ram="Amount of RAM", password="User password")
async def create_vps(interaction: discord.Interaction, hostname: str, ram: str, password: str):
    user_id = str(interaction.user.id)
    data = load_data()

    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    if user_id in data:
        await interaction.response.send_message("❌ You already have a VPS!", ephemeral=True)
        return

    port = random.randint(30000, 39999)

    data[user_id] = {
        "hostname": hostname,
        "ram": ram,
        "password": password,
        "port": port,
        "shared_with": [],
        "location": "in"
    }
    save_data(data)

    await interaction.response.send_message("⚙️ Creating your VPS...", ephemeral=True)

    await interaction.user.send(
        f"✅ **Your VPS has been created**\n"
        f"**IP:** `{VPS_IP}`\n"
        f"**Port:** `{port}`\n"
        f"**User:** `root`\n"
        f"**Pass:** `{password}`\n"
        f"**Hostname:** `{hostname}`\n"
        f"**RAM:** `{ram}`\n"
        f"**User ID:** `{user_id}`"
    )

# Prefix Commands
@bot.command()
async def sync(ctx):
    await tree.sync()
    await ctx.send("✅ Slash commands synced.")

@bot.command()
async def myvps(ctx):
    data = load_data()
    uid = str(ctx.author.id)
    for user, vps in data.items():
        if uid == user or uid in vps.get("shared_with", []):
            await ctx.send(f"🖥️ **Your VPS**\nHostname: `{vps['hostname']}`\nIP: `{VPS_IP}`\nPort: `{vps['port']}`\nPassword: `{vps['password']}`")
            return
    await ctx.send("❌ No VPS found for you.")

@bot.command()
async def share(ctx, userid, targetid):
    data = load_data()
    if userid in data:
        if targetid not in data[userid]["shared_with"]:
            data[userid]["shared_with"].append(targetid)
            save_data(data)
            await ctx.send(f"✅ Shared VPS access of `{userid}` with `{targetid}`.")
        else:
            await ctx.send("❗ Already shared.")
    else:
        await ctx.send("❌ User ID not found.")

@bot.command()
async def unshare(ctx, userid, targetid):
    data = load_data()
    if userid in data and targetid in data[userid]["shared_with"]:
        data[userid]["shared_with"].remove(targetid)
        save_data(data)
        await ctx.send(f"❌ Removed access of `{targetid}` from `{userid}` VPS.")
    else:
        await ctx.send("❌ No such shared access found.")

@bot.command()
async def list(ctx):
    data = load_data()
    msg = "**📋 VPS Users:**\n"
    for uid, vps in data.items():
        msg += f"• `{uid}` — Location: `{vps.get('location', 'n/a')}`\n"
    await ctx.send(msg)

@bot.command()
async def adminadd(ctx, uid: str):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You can't use this command.")
        return
    ADMIN_IDS.append(int(uid))
    await ctx.send(f"✅ `{uid}` added to admin list.")

@bot.command()
async def role(ctx, uid: str = None):
    if uid:
        role = "Admin ✅" if int(uid) in ADMIN_IDS else "User"
        await ctx.send(f"👤 User `{uid}` is a **{role}**")
    else:
        msg = "**👥 User Roles:**\n"
        for uid in load_data():
            role = "Admin ✅" if int(uid) in ADMIN_IDS else "User"
            msg += f"• `{uid}` - {role}\n"
        await ctx.send(msg)

@bot.command()
async def delete_vps(ctx, uid: str):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Admins only.")
        return
    data = load_data()
    if uid in data:
        del data[uid]
        save_data(data)
        await ctx.send(f"🗑 VPS for `{uid}` deleted.")
    else:
        await ctx.send("❌ No VPS found for that user.")

@bot.command()
async def node(ctx):
    await ctx.send("🧠 Node Info:\nCPU: 4vCore\nRAM: 8GB\nDisk: 100GB SSD\n📍 Location: India 🇮🇳\n🔳 Box: Made by Gamerzhacker")

@bot.command()
async def nodeadmin(ctx):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Admins only.")
        return
    data = load_data()
    msg = "**🧾 VPS Full List:**\n"
    for uid, vps in data.items():
        msg += f"• {uid}: Hostname={vps['hostname']}, Port={vps['port']}, Location={vps.get('location', 'in')}\n"
    await ctx.send(msg)

@bot.command()
async def create_text(ctx, name: str, *, message: str):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Only admins can create text blocks.")
        return
    texts = load_texts()
    texts[name] = message
    save_texts(texts)
    await ctx.send(f"✅ Text block `{name}` saved.")

@bot.command()
async def show_text(ctx, name: str):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Only admins can show text blocks.")
        return
    texts = load_texts()
    if name in texts:
        await ctx.send(f"📄 `{name}`:\n{texts[name]}")
    else:
        await ctx.send("❌ Text not found.")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

# Run bot
bot.run(TOKEN)
