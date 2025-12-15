import os
import json
import random
import asyncio
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURATION ---
load_dotenv()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# File Paths (Railway Persistence Logic)
# If /data exists (Railway Volume), use it. Otherwise use local folder.
DATA_DIR = "/data" if os.path.exists("/data") else "."
STATE_FILE = os.path.join(DATA_DIR, "campaign_state.json")
RULES_FILE = "rules.json"

# Global State
creation_sessions = {}
players = {}
RULES = {}

# --- DATA MANAGEMENT ---
def load_data():
    """Loads rules and game state."""
    global players, RULES
    # Load Rules
    try:
        with open(RULES_FILE, "r") as f:
            RULES = json.load(f)
        print("✅ Rules loaded.")
    except FileNotFoundError:
        print("❌ CRITICAL: rules.json not found!")
        RULES = {}

    # Load Game State
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                players = data.get("players", {})
            print(f"📂 Game State Loaded from {STATE_FILE}")
        except Exception as e:
            print(f"⚠️ Error loading state: {e}")

def save_state():
    """Saves game state to local disk (Railway Volume)."""
    state = {
        "players": players,
        "last_updated": str(datetime.now())
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)
    print("💾 State Saved to Disk.")

# --- GOOGLE DRIVE BACKUP ---
async def backup_to_drive():
    """Uploads campaign_state.json to Google Drive."""
    raw_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    if not raw_creds or not folder_id:
        print("☁️ Drive Backup Skipped (Missing Credentials).")
        return "Backup skipped (Check logs)."

    print("☁️ Starting Google Drive Backup...")
    try:
        creds_dict = json.loads(raw_creds)
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        service = build('drive', 'v3', credentials=creds)

        # Check if file exists in folder
        query = f"'{folder_id}' in parents and name = 'campaign_state.json' and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])

        media = MediaFileUpload(STATE_FILE, mimetype='application/json')

        if files:
            # Update existing file
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print("☁️ Backup Updated.")
            return "Backup Successful (Updated)."
        else:
            # Create new file
            file_metadata = {'name': 'campaign_state.json', 'parents': [folder_id]}
            service.files().create(body=file_metadata, media_body=media).execute()
            print("☁️ Backup Created.")
            return "Backup Successful (Created)."
            
    except Exception as e:
        print(f"❌ Drive Error: {e}")
        return f"Backup Failed: {e}"

@tasks.loop(hours=168) # Run once a week
async def weekly_backup_task():
    await backup_to_drive()

# --- AI NARRATOR ---
async def get_ai_response(history, user_input, user_name):
    prompt = (
        "SYSTEM: You are a D&D 5e Dungeon Master running a private campaign. "
        "Style: Vivid, concise (under 1000 chars), engaging. "
        "Rules: If a player acts, narrate the result. If they need to roll, ask them. "
        f"CONTEXT: {history}\nPLAYER ({user_name}): {user_input}"
    )
    response = await asyncio.to_thread(model.generate_content, prompt)
    return response.text

# --- COMMANDS ---

@bot.event
async def on_ready():
    load_data()
    if not weekly_backup_task.is_running():
        weekly_backup_task.start()
    print(f'Logged in as {bot.user}')

@bot.command()
async def create(ctx):
    """Start Character Creation."""
    if str(ctx.author.id) in players:
        await ctx.send("You already have a character! Type `!sheet`.")
        return
    creation_sessions[str(ctx.author.id)] = {'step': 'ROLL'}
    
    # Auto-roll stats immediately
    rolls = [sum(sorted([random.randint(1,6) for _ in range(4)])[1:]) for _ in range(6)]
    creation_sessions[str(ctx.author.id)]['stats'] = sorted(rolls, reverse=True)
    
    await ctx.send(f"🎲 **Stats Rolled:** {creation_sessions[str(ctx.author.id)]['stats']}\n"
                   f"Next: Choose Race. Options: `{', '.join(RULES['races'].keys())}`")

@bot.command()
async def fight(ctx, monster_name: str):
    """Roll Initiative vs a Monster."""
    monster = RULES['monsters'].get(monster_name.lower())
    if not monster:
        await ctx.send(f"⚠️ Unknown monster. Try: {', '.join(RULES['monsters'].keys())}")
        return
    
    m_init = random.randint(1, 20) + monster['init_bonus']
    p_init = random.randint(1, 20)
    await ctx.send(f"⚔️ **{monster['name']}** (HP: {monster['hp']}) appears!\n"
                   f"Monster Init: {m_init} | Your Init: {p_init}\n"
                   f"**{'You' if p_init >= m_init else 'Monster'} go first!**")

@bot.command()
async def rest(ctx):
    """Full Heal."""
    uid = str(ctx.author.id)
    if uid in players:
        players[uid]['hp_current'] = players[uid]['hp_max']
        save_state()
        await ctx.send(f"💤 **{players[uid]['name']}** takes a Long Rest. HP restored.")

@bot.command()
async def backup(ctx):
    """Manual Backup to Drive."""
    msg = await ctx.send("☁️ Uploading...")
    result = await backup_to_drive()
    await msg.edit(content=f"☁️ {result}")

@bot.command()
async def sheet(ctx):
    """View Character."""
    p = players.get(str(ctx.author.id))
    if p:
        await ctx.send(f"📜 **{p['name']}** ({p['race']} {p['class']})\nHP: {p['hp_current']}/{p['hp_max']}\nStats: {p['stats']}")

@bot.command()
async def recap(ctx):
    """Ask AI for story summary."""
    res = await get_ai_response("Summarize current story state.", "Recap please.", "System")
    await ctx.send(f"📅 **Story So Far:**\n{res}")

@bot.command()
async def fix(ctx):
    """Clear AI short-term memory."""
    await ctx.send("🧹 **Memory Cleaned.** (I still know your character stats, but context is reset).")

@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)

    # Character Creation Logic
    if uid in creation_sessions and not message.content.startswith("!"):
        sess = creation_sessions[uid]
        content = message.content.lower().strip().replace(" ", "_")
        
        if sess['step'] == 'ROLL': # Actually waiting for Race
            if content in RULES['races']:
                sess['race'] = RULES['races'][content]
                sess['step'] = 'CLASS'
                await message.channel.send(f"✅ Race: {sess['race']['name']}. Next: Choose Class.\nOptions: `{', '.join(RULES['classes'].keys())}`")
            else:
                await message.channel.send("⚠️ Invalid Race.")
        
        elif sess['step'] == 'CLASS':
            if content in RULES['classes']:
                cls = RULES['classes'][content]
                # Finalize
                players[uid] = {
                    "name": message.author.display_name,
                    "race": sess['race']['name'],
                    "class": cls['name'],
                    "hp_max": cls['hit_die'] + 2,
                    "hp_current": cls['hit_die'] + 2,
                    "stats": sess['stats'],
                    "inventory": cls['equipment']
                }
                del creation_sessions[uid]
                save_state()
                await message.channel.send(f"🎉 **Character Saved!** Welcome, {players[uid]['race']} {players[uid]['class']}.")
            else:
                await message.channel.send("⚠️ Invalid Class.")
        return

    await bot.process_commands(message)

    # Roleplay Logic
    if not message.content.startswith("!") and uid in players:
        async with message.channel.typing():
            response = await get_ai_response("Game Context", message.content, message.author.display_name)
            await message.channel.send(response)
            save_state() # SAVE IMMEDIATELY

bot.run(os.getenv("DISCORD_TOKEN"))
