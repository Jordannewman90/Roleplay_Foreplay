import os
import json
import random
import asyncio
import discord
from discord.ext import commands, tasks

from google import genai
from google.genai import types
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
from datetime import datetime
from ai_persona import get_dungeon_master_prompt

# --- CONFIGURATION ---
load_dotenv()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini Setup
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = 'gemini-1.5-pro-002'

# Define settings to allow the "Spicy" content
# In google-genai, we use types.SafetySetting
safety_settings = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
]

generate_config = types.GenerateContentConfig(
    safety_settings=safety_settings
)
# imagen_model = genai.GenerativeModel('nano-banana-pro-preview')

# File Paths (Railway Persistence Logic)
# If /data exists (Railway Volume), use it. Otherwise use local folder.
DATA_DIR = "/data" if os.path.exists("/data") else "."
STATE_FILE = os.path.join(DATA_DIR, "campaign_state.json")
RULES_FILE = "rules.json"

# Global State
creation_sessions = {}
players = {}
RULES = {}
chat_history = [] # List of strings: "Name: Message"
start_time = datetime.now()
last_thought = "Waiting for the adventure to begin..."

# --- DATA MANAGEMENT ---
def load_data():
    """Loads rules and game state."""
    global players, RULES, chat_history
    # Load Rules
    try:
        with open(RULES_FILE, "r") as f:
            RULES = json.load(f)
        print("[OK] Rules loaded.")
    except FileNotFoundError:
        print("[ERROR] CRITICAL: rules.json not found!")
        RULES = {}

    # Load Game State
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                players = data.get("players", {})
                chat_history = data.get("chat_history", [])
            print(f"[INFO] Game State Loaded from {STATE_FILE}")
        except Exception as e:
            print(f"[WARN] Error loading state: {e}")

def save_state():
    """Saves game state to local disk (Railway Volume)."""
    state = {
        "players": players,
        "chat_history": chat_history,
        "last_updated": str(datetime.now())
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)
    print("[INFO] State Saved to Disk.")

# --- GOOGLE DRIVE BACKUP ---
async def backup_to_drive():
    """Uploads campaign_state.json to Google Drive."""
    raw_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    if not raw_creds or not folder_id:
        print("[INFO] Drive Backup Skipped (Missing Credentials).")
        return "Backup skipped (Check logs)."

    print("[INFO] Starting Google Drive Backup...")
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
            print("[INFO] Backup Updated.")
            return "Backup Successful (Updated)."
        else:
            # Create new file
            file_metadata = {'name': 'campaign_state.json', 'parents': [folder_id]}
            service.files().create(body=file_metadata, media_body=media).execute()
            print("[INFO] Backup Created.")
            return "Backup Successful (Created)."
            
    except Exception as e:
        print(f"[ERROR] Drive Error: {e}")
        return f"Backup Failed: {e}"

@tasks.loop(hours=168) # Run once a week
async def weekly_backup_task():
    await backup_to_drive()

# --- AI NARRATOR ---
async def get_ai_response(user_input, user_name):
    global last_thought, chat_history
    last_thought = f"Processing input from {user_name}..."
    
    # 1. Prepare temporary context (Don't commit to history yet)
    temp_history = chat_history.copy()
    temp_history.append(f"{user_name}: {user_input}")
    
    context_str = "\n".join(temp_history[-200:]) # Keep last 200
    current_state_json = json.dumps(players, indent=2)
    
    prompt = get_dungeon_master_prompt(context_str, current_state_json)
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_ID,
            contents=prompt,
            config=generate_config
        )
        text_response = response.text
        
        # 2. Success! Now commit both to history
        chat_history.append(f"{user_name}: {user_input}")
        chat_history.append(f"DM: {text_response}")
        
        last_thought = f"Waiting for next move."
        return text_response
        
    except Exception as e:
        print(f"[ERROR] AI Generation failed: {e}")
        last_thought = f"Error: {e}"
        # Do NOT append to chat_history, so the user can try again without duplicate inputs
        return "⚠️ *The DM is distracted (API Error). Please try saying that again.*"

# --- COMMANDS ---

@bot.event
async def on_ready():
    load_data()
    if not weekly_backup_task.is_running():
        weekly_backup_task.start()
    print(f'Logged in as {bot.user}')

@bot.command()
async def start(ctx, *, premise=None):
    """Start a new campaign. Usage: !start [optional premise]"""
    async with ctx.typing():
        if not premise:
            # Generate a random premise if none provided
            premise_prompt = "Generate a short, exciting, and slightly spicy D&D 5e campaign premise for a couple. Include a hook for adventure and intimacy."
            premise_resp = await asyncio.to_thread(client.models.generate_content, model=MODEL_ID, contents=premise_prompt, config=generate_config)
            premise = premise_resp.text

        # Generate the opening narration
        prompt = (
            f"SYSTEM: You are starting a new campaign based on this premise: '{premise}'. "
            "Set the scene. Describe the environment, the atmosphere (make it alluring), and where the characters are. "
            "End with a call to action or a question to the players."
        )
        
        response = await get_ai_response(f"Start the campaign with premise: {premise}", "System")
        await ctx.send(f"📜 **The Adventure Begins...**\n\n**Premise:** {premise}\n\n{response}")

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
    res = await get_ai_response("Recap please.", "System")
    await ctx.send(f"📅 **Story So Far:**\n{res}")

@bot.command()
async def guide(ctx):
    """Ask the DM for a hint."""
    res = await get_ai_response("I'm stuck, what should I do?", "System")
    await ctx.send(f"💡 **DM's Guide:**\n{res}")

@bot.command()
async def status(ctx):
    """Check the DM's mental state."""
    uptime = str(datetime.now() - start_time).split('.')[0]
    await ctx.send(f"🧠 **DM Status**\n**Uptime:** {uptime}\n**Current Thought:** {last_thought}")

@bot.command()
async def catchup(ctx):
    """Show the last few turns of the story."""
    if not chat_history:
        await ctx.send("📭 **No story history yet!**")
        return
        
    # Get last 4 messages
    recent = chat_history[-4:]
    summary = "\n\n".join(recent)
    await ctx.send(f"📜 **Last 4 Turns:**\n\n{summary}")

@bot.command()
async def snapshot(ctx):
    """Generate a picture of the current scene."""
    async with ctx.typing():
        # Step 1: Get a SFW description from the Text Model
        # We explicitly ask for an 'Oil Painting' style to avoid photorealistic NSFW triggers
        prompt = (
            f"Based on the last message: '{chat_history[-1] if chat_history else ''}', "
            "describe the scene for an image generator. "
            "Focus on lighting, atmosphere, and fantasy armor. "
            "Avoid explicit anatomy; focus on the romantic tension and facial expressions. "
            "Style: Fantasy Oil Painting."
        )
        
        try:
            desc_resp = await asyncio.to_thread(
                client.models.generate_content, 
                model=MODEL_ID, 
                contents=prompt
            )
            scene_description = desc_resp.text
            await ctx.send(f"🎨 **Painting the scene:** _{scene_description[:150]}..._")
        except Exception as e:
            await ctx.send(f"⚠️ Snapshot Error: {e}")
            return

        # Step 2: Image Generation (Placeholder for Future Implementation)
        # Note: Requires a valid visual model or external API. 
        # For now, we provide the vivid text description.

@bot.command()
async def fix(ctx):
    """Clear AI short-term memory."""
    global chat_history
    chat_history.clear()
    await ctx.send("🧹 **Memory Cleaned.** (I still know your character stats, but context is reset).")

@bot.event
async def on_message(message):
    if message.author.bot: return

    # 1. IGNORE OOC (Lines starting with // or >>)
    if message.content.startswith("//") or message.content.startswith(">>"):
        return

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
    
    # Allow natural language to trigger commands
    if message.content.lower().startswith("start game") or message.content.lower().startswith("begin adventure"):
        ctx = await bot.get_context(message)
        await start(ctx)
        return

    await bot.process_commands(message)

    # Roleplay Logic
    if not message.content.startswith("!") and uid in players:
        async with message.channel.typing():
            response = await get_ai_response(message.content, message.author.display_name)
            await message.channel.send(response)
            save_state() # SAVE IMMEDIATELY

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for bot commands."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ **Missing Argument:** `{error.param.name}` is required.")
    elif isinstance(error, commands.CommandNotFound):
        pass # Ignore unknown commands (prevents spam if users type random stuff)
    elif isinstance(error, commands.CommandInvokeError):
        print(f"[ERROR] Command Error: {error}")
        await ctx.send("⚠️ **Something went wrong.** (Check logs)")
    else:
        print(f"[ERROR] Unhandled Error: {error}")
        await ctx.send(f"⚠️ **Error:** {error}")

bot.run(os.getenv("DISCORD_TOKEN"))
