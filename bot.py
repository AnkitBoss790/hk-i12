import discord
from discord.ext import commands
from discord import app_commands
import paramiko
import json
import os
from datetime import datetime
import time

# CONFIG
TOKEN = "YOUR_BOT_TOKEN"
VPS_IP = "YOUR_VPS_IP"
VPS_ROOT_PASSWORD = "YOUR_VPS_PASSWORD"
BASE_PORT = 2200
DATA_FILE = "users.json"
TEXT_FILE = "texts.json"
ADMIN_IDS = [123456789012345678]  # Replace with your admin user IDs
ROLES_FILE = "roles.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
used_ports = set()
running_times = {}

# --- Helper Functions ---
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

def save_texts(data):
    with open(TEXT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_roles():
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE) as f:
            return json.load(f)
    return {}

def save_roles(data):
    with open(ROLES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# --- Bot Events ---
@bot.event
async def on_ready():
    await tree.sync()
    print("Bot is ready")

# --- Slash Command ---
@tree.command(name="create-vps", description="Create a new VPS user (Admins only)")
@app_commands.describe(
    hostname="Your hostname (e.g., myserver)",
    ram="Amount of RAM (e.g., 2GB)",
    password="Password for SSH user"
)
async def create_vps(interaction: discord.Interaction, hostname: str, ram: str, password: str):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id in data:
        await interaction.response.send_message("❌ You already have a VPS.", ephemeral=True)
        return

    await interaction.response.send_message("⚙️ Creating your VPS...", ephemeral=True)

    username = hostname.lower()
    port = BASE_PORT + len(data)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(VPS_IP, username='root', password=VPS_ROOT_PASSWORD)
        commands = f"""
        useradd -m {username}
        echo '{username}:{password}' | chpasswd
        echo 'Port {port}' >> /etc/ssh/sshd_config
        echo -e 'Match User {username}\\n    AllowTcpForwarding yes\\n    X11Forwarding yes' >> /etc/ssh/sshd_config
        systemctl restart ssh
        """
        ssh.exec_command(commands)
        ssh.close()

        data[user_id] = {"username": username, "port": port, "password": password, "hostname": hostname, "ram": ram, "location": "Unknown", "shared_with": [], "start_time": time.time()}
        save_data(data)

        await interaction.user.send(
            f"✅ **VPS Created Successfully!**\n\n"
            f"🔹 **IP**: `{VPS_IP}`\n"
            f"🔹 **Port**: `{port}`\n"
            f"🔹 **User**: `{username}`\n"
            f"🔹 **Pass**: `{password}`\n"
            f"🔹 **Hostname**: `{hostname}`\n"
            f"🔹 **RAM**: `{ram}`\n"
            f"🔹 **Your User ID**: `{user_id}`"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

# --- Admin Commands ---
@bot.command(name="adminadd")
async def admin_add(ctx, userid: str):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Only main admins can add new admins.")
    if int(userid) not in ADMIN_IDS:
        ADMIN_IDS.append(int(userid))
        await ctx.send(f"✅ User `{userid}` added to admin list.")
    else:
        await ctx.send("ℹ️ User is already an admin.")

@bot.command(name="role")
async def role_view(ctx, userid: str = None):
    roles = load_roles()
    if userid:
        if userid in roles:
            await ctx.send(f"🔑 User `{userid}` has role: `{roles[userid]}`")
        else:
            await ctx.send("❌ No role found for this user.")
    else:
        msg = "👥 **User Roles:**\n"
        for uid, role in roles.items():
            msg += f"- `{uid}`: {role}\n"
        await ctx.send(msg)

@bot.command(name="delete-vps")
async def delete_vps(ctx, userid: str):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Only admins can delete VPS.")
    data = load_data()
    if userid in data:
        del data[userid]
        save_data(data)
        await ctx.send(f"🗑 VPS for user `{userid}` has been deleted.")
    else:
        await ctx.send("❌ VPS not found for that user.")

# --- Share / Unshare VPS ---
@bot.command(name="share")
async def share_access(ctx, user_id: str, share_with: str):
    data = load_data()
    if user_id in data:
        if share_with not in data[user_id]['shared_with']:
            data[user_id]['shared_with'].append(share_with)
            save_data(data)
            await ctx.send(f"✅ VPS access for `{user_id}` shared with `{share_with}`.")
        else:
            await ctx.send("ℹ️ Already shared.")
    else:
        await ctx.send("❌ VPS owner user ID not found.")

@bot.command(name="unshare")
async def unshare_access(ctx, user_id: str, target_id: str):
    data = load_data()
    if user_id in data:
        if target_id in data[user_id]['shared_with']:
            data[user_id]['shared_with'].remove(target_id)
            save_data(data)
            await ctx.send(f"❌ Removed VPS access from `{target_id}` for `{user_id}`.")
        else:
            await ctx.send("ℹ️ This user wasn't shared with.")
    else:
        await ctx.send("❌ VPS owner user ID not found.")

# --- Utility ---
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command(name="myvps")
async def my_vps(ctx):
    uid = str(ctx.author.id)
    data = load_data()
    for owner_id, vps in data.items():
        if owner_id == uid or uid in vps.get('shared_with', []):
            uptime = time.time() - vps.get('start_time', time.time())
            await ctx.send(f"🔹 **Hostname:** {vps['hostname']}\n🔹 **User:** {vps['username']}\n🔹 **Port:** {vps['port']}\n🔹 **RAM:** {vps['ram']}\n🔹 **Running Time:** {int(uptime)}s")
            return
    await ctx.send("❌ No VPS found for you.")

@bot.command(name="list")
async def list_users(ctx):
    data = load_data()
    msg = "📋 **VPS Users:**\n"
    for uid, info in data.items():
        msg += f"- ID: `{uid}`, Location: {info.get('location', 'Unknown')}\n"
    await ctx.send(msg)

@bot.command(name="node")
async def node_info(ctx):
    await ctx.send("📦 **Node Location:** India\nCPU: 4 Cores\nRAM: 8GB\nDisk: 100GB\nMade by Gamerzhacker")

@bot.command(name="nodeadmin")
async def node_admin(ctx):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Only admins can use this.")
    data = load_data()
    msg = "📊 **All VPS Users:**\n"
    for uid, v in data.items():
        msg += f"- ID: {uid} | Host: {v['hostname']} | Port: {v['port']}\n"
    await ctx.send(msg)

@bot.command(name="create-text")
async def create_text(ctx, name: str, *, msg: str):
    texts = load_texts()
    texts[name] = msg
    save_texts(texts)
    await ctx.send(f"✅ Text saved under `{name}`.")

@bot.command(name="show-text")
async def show_text(ctx, name: str):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Admins only.")
    texts = load_texts()
    if name in texts:
        await ctx.send(f"📝 `{name}`: {texts[name]}")
    else:
        await ctx.send("❌ Text not found.")

bot.run(TOKEN)
