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
import dice_engine
import character_creator

# --- CONFIGURATION ---
load_dotenv()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini Setup
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = 'gemini-1.5-pro-002'

# Tool Definition
dice_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="roll_dice",
            description="Rolls dice using true RNG. Use this WHENEVER a die roll is needed for combat, checks, or random events.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "expression": types.Schema(
                        type=types.Type.STRING,
                        description="The dice expression to roll (e.g., '1d20+5', '2d6', '1d8-1')."
                    )
                },
                required=["expression"]
            )
        )
    ]
)

# Character Creator Tool
creation_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="finalize_character",
            description="Call this ONLY when the user is happy with their character and explicitly agrees to save it.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "race_key": types.Schema(type=types.Type.STRING, description="The EXACT key from the rules list (e.g. 'tiefling', 'high_elf')."),
                    "class_key": types.Schema(type=types.Type.STRING, description="The EXACT key from the rules list (e.g. 'bard', 'fighter')."),
                    "description": types.Schema(type=types.Type.STRING, description="Physical appearance."),
                    "lore": types.Schema(type=types.Type.STRING, description="Backstory and vibes.")
                },
                required=["name", "race_key", "class_key", "description", "lore"]
            )
        )
    ]
)

# Define settings to allow the "Spicy" content
# In google-genai, we use types.SafetySetting
safety_settings = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
]

# Combat Tool
combat_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="start_combat",
            description="Initiates combat with a monster. Returns initiatives and monster stats. Use when the user says 'I fight' or 'I attack'.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "monster_name": types.Schema(type=types.Type.STRING, description="Name of the monster (e.g. 'Goblin')"),
                },
                required=["monster_name"]
            )
        )
    ]
)

# Rest Tool
rest_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="take_long_rest",
            description="Restores player HP and saves game. Use when user says 'I rest', 'camp', or 'sleep'.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}, required=[])
        )
    ]
)

# Relationship & Quest Tools
gameplay_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="update_quest",
            description="Manage quests. Use when a quest is started, updated, or completed.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action": types.Schema(type=types.Type.STRING, description="One of: 'ADD', 'COMPLETE', 'FAIL'"),
                    "quest_name": types.Schema(type=types.Type.STRING, description="Name/Objective of the quest"),
                    "status": types.Schema(type=types.Type.STRING, description="Current status info (e.g. 'Goblin King dead')")
                },
                required=["action", "quest_name"]
            )
        ),
        types.FunctionDeclaration(
            name="add_loot",
            description="Add item to player inventory.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "item_name": types.Schema(type=types.Type.STRING, description="Name of the item"),
                    "quantity": types.Schema(type=types.Type.INTEGER, description="Count (default 1)")
                },
                required=["item_name"]
            )
        ),
        types.FunctionDeclaration(
            name="update_relationship",
            description="Update NPC affection score (0-100). Baseline is 0/50 depending on NPC.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "npc_name": types.Schema(type=types.Type.STRING, description="Name of NPC"),
                    "change": types.Schema(type=types.Type.INTEGER, description="Amount to change (+5, -10, etc.)"),
                    "reason": types.Schema(type=types.Type.STRING, description="Why it changed")
                },
                required=["npc_name", "change"]
            )
        )
    ]
)

# Economy & Progression Tools
economy_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="update_inventory_gold",
            description="Manage inventory and gold. Use for buying, selling, looting, or paying info.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "items_added": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="List of items added"),
                    "items_removed": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="List of items removed"),
                    "gold_change": types.Schema(type=types.Type.INTEGER, description="Change in Gold (+ or -)"),
                    "reason": types.Schema(type=types.Type.STRING, description="Reason (e.g. 'Bought sword', 'Looted chest')")
                },
                required=["gold_change"]
            )
        ),
        types.FunctionDeclaration(
            name="grant_xp",
            description="Award XP to player. Check for level up.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "amount": types.Schema(type=types.Type.INTEGER, description="XP Amount"),
                    "reason": types.Schema(type=types.Type.STRING, description="Reason for XP")
                },
                required=["amount"]
            )
        )
    ]
)

generate_config = types.GenerateContentConfig(
    safety_settings=safety_settings,
    tools=[dice_tool, combat_tool, rest_tool, gameplay_tool, economy_tool],
    temperature=0.9 # High creativity
)

creation_config = types.GenerateContentConfig(
    safety_settings=safety_settings,
    tools=[creation_tool], # Exclusive tool for creation mode
    temperature=1.0 # Max creativity for brainstorming
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
# --- AI NARRATOR ---
async def get_ai_response(user_input, user_name, uid):
    global last_thought, chat_history
    last_thought = f"Processing input from {user_name}..."
    
    # 1. Prepare temporary context (Don't commit to history yet)
    temp_history = chat_history.copy()
    temp_history.append(f"{user_name}: {user_input}")
    
    context_str = "\n".join(temp_history[-200:]) # Keep last 200
    current_state_json = json.dumps(players, indent=2)
    
    prompt = get_dungeon_master_prompt(context_str, current_state_json)
    
    try:
        # First Turn: Send Prompt
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_ID,
            contents=prompt,
            config=generate_config
        )

        # CHECK FOR TOOL CALLS
        while response.function_calls:
            for call in response.function_calls:
                if call.name == "roll_dice":
                    args = call.args
                    expression = args.get("expression", "1d20")
                    print(f"[TOOL] AI requested roll: {expression}")
                    result = dice_engine.roll_dice(expression)
                    
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[
                                types.Part(function_response=types.FunctionResponse(name=call.name, response=result))
                            ])
                        ],
                        config=generate_config
                    )

                elif call.name == "start_combat":
                    args = call.args
                    monster_name = args.get("monster_name").lower()
                    monster = RULES['monsters'].get(monster_name)
                    
                    if not monster:
                        res = {"error": f"Monster '{monster_name}' not found. Available: {', '.join(RULES['monsters'].keys())}"}
                    else:
                        m_init = random.randint(1, 20) + monster['init_bonus']
                        p_init = random.randint(1, 20)
                        res = {
                            "event": "COMBAT_STARTED",
                            "monster": monster['name'],
                            "monster_hp": monster['hp'],
                            "monster_init": m_init,
                            "player_init": p_init,
                            "instruction": "Describe the monster's entrance cinematically. Mention who goes first."
                        }
                    
                    print(f"[{call.name}] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[
                                types.Part(function_response=types.FunctionResponse(name=call.name, response=res))
                            ])
                        ],
                        config=generate_config
                    )

                    )

                # --- GAMEPLAY TOOLS ---
                elif call.name == "update_quest":
                    args = call.args
                    action = args.get("action")
                    quest = args.get("quest_name")
                    status = args.get("status", "")
                    
                    if uid in players:
                        if "quests" not in players[uid]: players[uid]["quests"] = []
                        
                        if action == "ADD":
                            players[uid]["quests"].append(f"{quest} (Active) - {status}")
                            res = f"Quest Added: {quest}"
                        elif action == "COMPLETE":
                            players[uid]["quests"] = [q for q in players[uid]["quests"] if quest not in q]
                            players[uid]["quests"].append(f"{quest} (COMPLETED)")
                            res = f"Quest Completed: {quest}"
                        elif action == "FAIL":
                            players[uid]["quests"] = [q for q in players[uid]["quests"] if quest not in q]
                            players[uid]["quests"].append(f"{quest} (FAILED)")
                            res = f"Quest Failed: {quest}"
                        save_state()
                    else:
                        res = "Error: Player not found."
                    
                    print(f"[TOOL] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=call.name, response={'result': res}))])
                        ],
                        config=generate_config
                    )

                elif call.name == "add_loot":
                    args = call.args
                    item = args.get("item_name")
                    qty = args.get("quantity", 1)
                    
                    if uid in players:
                        if "inventory" not in players[uid]: players[uid]["inventory"] = []
                        players[uid]["inventory"].append(f"{item} (x{qty})")
                        save_state()
                        res = f"Added {qty}x {item} to inventory."
                    else:
                        res = "Error: Player not found."

                    print(f"[TOOL] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=call.name, response={'result': res}))])
                        ],
                        config=generate_config
                    )

                elif call.name == "update_relationship":
                    args = call.args
                    npc = args.get("npc_name")
                    change = args.get("change")
                    reason = args.get("reason")
                    
                    if uid in players:
                        if "relationships" not in players[uid]: players[uid]["relationships"] = {}
                        current = players[uid]["relationships"].get(npc, 0) # Default 0 (Neutral)
                        new_score = max(0, min(100, current + change))
                        players[uid]["relationships"][npc] = new_score
                        save_state()
                        res = f"{npc} Relationship: {current} -> {new_score} ({reason})"
                    else:
                        res = "Error: Player not found."

                    print(f"[TOOL] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=call.name, response={'result': res}))])
                        ],
                        config=generate_config
                    )

                # --- ECONOMY & PROGRESSION TOOLS ---
                elif call.name == "update_inventory_gold":
                    args = call.args
                    added = args.get("items_added", [])
                    removed = args.get("items_removed", [])
                    gold_delta = args.get("gold_change", 0)
                    reason = args.get("reason", "Trade")
                    
                    if uid in players:
                        # Init keys if missing (Migration)
                        if "inventory" not in players[uid]: players[uid]["inventory"] = []
                        if "gold" not in players[uid]: players[uid]["gold"] = 10 
                        
                        # Gold
                        players[uid]["gold"] += gold_delta
                        
                        # Inventory
                        for item in added:
                            players[uid]["inventory"].append(item)
                        
                        for item in removed:
                            # Fuzzy remove (remove first match)
                            for inv_item in players[uid]["inventory"]:
                                if item.lower() in inv_item.lower():
                                    players[uid]["inventory"].remove(inv_item)
                                    break
                        
                        save_state()
                        res = f"Gold: {players[uid]['gold']} ({gold_delta}). Items: +{added} -{removed}."
                    else:
                        res = "Error: Player not found."
                        
                    print(f"[TOOL] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=call.name, response={'result': res}))])
                        ],
                        config=generate_config
                    )

                elif call.name == "grant_xp":
                    args = call.args
                    amt = args.get("amount", 0)
                    reason = args.get("reason", "Adventure")
                    
                    if uid in players:
                        # Init keys if missing
                        if "xp" not in players[uid]: players[uid]["xp"] = 0
                        if "level" not in players[uid]: players[uid]["level"] = 1
                        
                        players[uid]["xp"] += amt
                        current_xp = players[uid]["xp"]
                        current_lvl = players[uid]["level"]
                        
                        # Simple Leveling: Level * 1000 XP
                        next_lvl_xp = current_lvl * 1000
                        
                        levelup_msg = ""
                        if current_xp >= next_lvl_xp:
                            players[uid]["level"] += 1
                            players[uid]["hp_max"] += random.randint(4, 10) # Auto HP boost
                            players[uid]["hp_current"] = players[uid]["hp_max"]
                            levelup_msg = f"🎉 LEVEL UP! You are now Level {players[uid]['level']}! HP Increased."
                        
                        save_state()
                        res = f"XP: {current_xp} (+{amt}) [{reason}]. {levelup_msg}"
                    else:
                        res = "Error: Player not found."
                        
                    print(f"[TOOL] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=call.name, response={'result': res}))])
                        ],
                        config=generate_config
                    )

                elif call.name == "take_long_rest":
                    # Execute Logic
                    if uid in players:
                        players[uid]['hp_current'] = players[uid]['hp_max']
                        save_state()
                        
                    res = {
                        "event": "REST_COMPLETED",
                        "instruction": "The party rests. HP is restored. Describe a cozy campfire scene and ask the player a deep question."
                    }
                    
                    print(f"[{call.name}] {res}")
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=MODEL_ID,
                        contents=[
                            types.Content(role="user", parts=[types.Part(text=prompt)]),
                            response.candidates[0].content,
                            types.Content(role="user", parts=[
                                types.Part(function_response=types.FunctionResponse(name=call.name, response=res))
                            ])
                        ],
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
        text_response = "⚠️ *The DM is feeling a bit overwhelmed (Rate Limit or Error). Give me a moment and try again!*"
        last_thought = f"Error: {e}"
        return text_response

# ... (Previous code)

@bot.command()
async def fight(ctx, monster_name: str=""):
    """Start Combat (Cinematic). Usage: !fight [monster]"""
    # If no argument, maybe asking for list?
    if not monster_name:
        await ctx.send(f"⚠️ Usage: `!fight [Monster]`. Available: {', '.join(RULES['monsters'].keys())}")
        return

    async with ctx.typing():
        # Invoke AI to handle the fight logic
        uid = str(ctx.author.id)
        response = await get_ai_response(f"(Command: Start Combat with {monster_name})", ctx.author.display_name, uid)
        await ctx.send(response)
        save_state()

@bot.command()
async def rest(ctx):
    """Long Rest (Cinematic)."""
    async with ctx.typing():
        uid = str(ctx.author.id)
        response = await get_ai_response(f"(Command: Take Long Rest)", ctx.author.display_name, uid)
        await ctx.send(response)
        save_state()


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
        
        # Use a dummy UID for start since players might not be initialized, 
        # BUT ideally we need to know who is playing. For now, use author ID.
        uid = str(ctx.author.id)
        response = await get_ai_response(f"Start the campaign with premise: {premise}", "System", uid)
        await ctx.send(f"📜 **The Adventure Begins...**\n\n**Premise:** {premise}\n\n{response}")

@bot.command()
async def create(ctx):
    """Start Character Creation (Conversational Mode)."""
    uid = str(ctx.author.id)
    if uid in players:
        await ctx.send("You already have a character! Type `!sheet`.")
        return
    
    # 1. Roll Stats in Background
    rolls = [sum(sorted([random.randint(1,6) for _ in range(4)])[1:]) for _ in range(6)]
    stats = sorted(rolls, reverse=True)
    
    # 2. Initialize Session
    creation_sessions[uid] = {
        'stats': stats,
        'history': [] # Chat history for the consultant
    }
    
    await ctx.send(f"🎲 **Stats Rolled:** {stats}\n"
                   f"✨ **Summoning Character Consultant...**\n"
                   f"_(A stylish projection appears)_ 'Darling, you look essentially formless. Let's fix that. What kind of fantasy are we building today?'")

# --- CREATION LOOP ---
async def run_creation_step(message):
    uid = str(message.author.id)
    sess = creation_sessions[uid]
    user_input = message.content
    
    # Update History
    sess['history'].append(f"User: {user_input}")
    
    # Build Prompt
    history_str = "\n".join(sess['history'][-20:])
    rules_str = json.dumps(RULES, indent=2)
    prompt = character_creator.get_creation_prompt(history_str, rules_str)
    
    async with message.channel.typing():
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL_ID,
                contents=prompt,
                config=creation_config
            )
            
            # Check for Finalization Tool
            if response.function_calls:
                for call in response.function_calls:
                    if call.name == "finalize_character":
                        args = call.args
                        
                        # Validate Keys
                        race_key = args['race_key'].lower()
                        class_key = args['class_key'].lower()
                        
                        if race_key not in RULES['races'] or class_key not in RULES['classes']:
                            sess['history'].append("System: Error - Invalid Race/Class Key. Consulting Rules...")
                            # Retry (handled by loop or user input, but for now just warn)
                            await message.channel.send("⚠️ Consultant Error: Invalid Race/Class selected. Please clarify.")
                            return

                        # SAVE CHARACTER
                        race_data = RULES['races'][race_key]
                        class_data = RULES['classes'][class_key]
                        
                        players[uid] = {
                            "name": args['name'],
                            "race": race_data['name'],
                            "class": class_data['name'],
                            "description": args['description'],
                            "lore": args['lore'],
                            "hp_max": class_data['hit_die'] + 2,
                            "hp_current": class_data['hit_die'] + 2,
                            "stats": sess['stats'],
                            "inventory": class_data['equipment'],
                            "quests": [], 
                            "relationships": {},
                            "gold": 10,  # Startup Capital
                            "xp": 0,
                            "level": 1
                        }
                        
                        save_state()
                        del creation_sessions[uid]
                        
                        await message.channel.send(
                            f"🎉 **Character Saved!**\n"
                            f"**Name:** {players[uid]['name']}\n"
                            f"**{players[uid]['race']} {players[uid]['class']}**\n"
                            f"_{players[uid]['description']}_\n"
                            f"STATS: {players[uid]['stats']}\n"
                            f"💰 Gold: 10 | 🌟 Level: 1\n"
                            f"(Type `!start` to begin adventure!)"
                        )
                        return

            # Normal Reply
            text = response.text
            sess['history'].append(f"Consultant: {text}")
            await message.channel.send(text)
            
        except Exception as e:
            print(f"[ERROR] Creation Loop: {e}")
            await message.channel.send("⚠️ Consultant brain freeze. Try again.")



@bot.command()
async def backup(ctx):
    """Manual Backup to Drive."""
    msg = await ctx.send("☁️ Uploading...")
    result = await backup_to_drive()
    await msg.edit(content=f"☁️ {result}")

@bot.command()
async def sheet(ctx):
    """View Character Sheet, Inventory, and Status."""
    uid = str(ctx.author.id)
    p = players.get(uid)
    if p:
        desc = p.get('description', 'No description yet.')
        inv = ", ".join(p.get('inventory', [])) or "Empty"
        gold = p.get('gold', 0)
        lvl = p.get('level', 1)
        xp = p.get('xp', 0)
        
        embed = f"📜 **{p['name']}** ({p['race']} {p['class']})\n" \
                f"_{desc}_\n\n" \
                f"❤️ **HP:** {p['hp_current']}/{p['hp_max']}\n" \
                f"💰 **Gold:** {gold} | 🌟 **Level:** {lvl} ({xp} XP)\n" \
                f"📊 **Stats:** {p['stats']}\n" \
                f"🎒 **Inventory:** {inv}"
        await ctx.send(embed)
    else:
        await ctx.send("No character found. Type `!create`.")

@bot.command()
async def legend(ctx):
    """Cinematic Recap of the Hero's Journey."""
    async with ctx.typing():
        uid = str(ctx.author.id)
        # Ask AI to generate a bard-style song or tale
        prompt = (
            "SYSTEM: Generate a 'Legend' or 'Epic Tale' summary of the campaign so far. "
            "Write it in the style of a bard telling a story at a tavern. "
            "Focus on the hero's achievements, relationships, and current quest."
        )
        response = await get_ai_response(prompt, "System", uid)
        await ctx.send(f"🎻 **The Legend of {ctx.author.display_name}**\n\n{response}")

@bot.command()
async def quests(ctx):
    """View Active Quests."""
    uid = str(ctx.author.id)
    p = players.get(uid)
    if p:
        qs = p.get('quests', [])
        if not qs:
            await ctx.send("📭 **Quest Log Empty**\n_Example: 'Find the lost amulet'_")
        else:
            txt = "\n".join([f"🔹 {q}" for q in qs])
            await ctx.send(f"🗺️ **Quest Log**\n{txt}")

@bot.command()
async def relationships(ctx):
    """View NPC Relationships."""
    uid = str(ctx.author.id)
    p = players.get(uid)
    if p:
        rels = p.get('relationships', {})
        if not rels:
            await ctx.send("💔 **No Relationships yet.** (Talk to people!)")
        else:
            # Sort by affection
            sorted_rels = sorted(rels.items(), key=lambda x: x[1], reverse=True)
            txt = ""
            for name, score in sorted_rels:
                status = "😐 Neutral"
                if score >= 90: status = "💍 Soulmate"
                elif score >= 70: status = "😍 Lover"
                elif score >= 50: status = "😊 Friend"
                elif score <= 20: status = "😡 Enemy"
                
                txt += f"**{name}**: {score}/100 ({status})\n"
                
            await ctx.send(f"💕 **Relationships**\n{txt}")

@bot.command()
async def recap(ctx):
    """Ask AI for story summary."""
    # Pass '0' or 'System' as default UID since recap usually doesn't change state
    res = await get_ai_response("Recap please.", "System", "0")
    await ctx.send(f"📅 **Story So Far:**\n{res}")

@bot.command()
async def guide(ctx):
    """Ask the DM for a hint."""
    res = await get_ai_response("I'm stuck, what should I do?", "System", "0")
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
        await run_creation_step(message)
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
            response = await get_ai_response(message.content, message.author.display_name, uid)
            await message.channel.send(response)
            save_state() # SAVE IMMEDIATELY

@bot.command()
async def roll(ctx, expression: str):
    """Roll dice manually (e.g. !roll 2d20)."""
    res = dice_engine.roll_dice(expression)
    if "error" in res:
        await ctx.send(f"⚠️ {res['error']}")
    else:
        await ctx.send(f"🎲 **Result:** {res['total']} (Rolls: {res['rolls']})")

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
