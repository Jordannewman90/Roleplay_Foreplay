# roleplay_foreplay 🎲🌶️

**roleplay_foreplay** is your "Dungeon Master with Benefits"—a bespoke AI-powered Discord bot designed for private, couple-focused D&D 5e campaigns.

It combines legitimate tabletop RPG mechanics (stats, dice rolling, combat) with an immersive, spicy, and romance-novel-worthy narrative driven by Google's Gemini 1.5 Pro.

---

## ✨ Key Features

## ✨ Key Features

### 🎬 Cinematic Gameplay
*   **Narrative First:** No more boring stats. `!fight` triggers a dramatic opening scene, and resting (`!rest`) starts a cozy campfire roleplay moment.
*   **Natural Language Trigger:** You don't need commands. Just tell the bot "I attack the goblin" or "I want to pitch a tent," and it instinctively knows what to do.
*   **"The Legend":** Type `!legend` to hear a bardic retelling of your entire campaign so far.

### 💰 Economy & Progression (Lite)
*   **Gold Logic:** The AI tracks your purse. Buy ales, bribe guards, or purchase magic items naturally in chat.
*   **XP & Leveling:** The DM awards XP for heroic deeds. Level up to gain HP and status.
*   **Quest Log:** Never get lost. Use `!quests` to see your current objectives.
*   **Deep Relationships:** NPCs remember how you treat them. `!relationships` shows if they are your Enemy, Friend, or Lover.

### 🧠 The "DM with Benefits"
*   **Persona-Driven AI:** The bot isn't just a text generator; it's a character. It's mischievous, flirtatious, and competent. It wants you to adventure *and* get close.
*   **Deep Memory:** Remembers the last **200 turns** of conversation, ensuring long-term storytelling continuity.
*   **Context Aware:** Knows your HP, inventory, and current location at all times.

### 💄 Conversational Character Creator
*   **No More Forms:** Forget boring menus. Type `!create` to summon the **Fantasy Consultant**, a specialized AI persona who interviews you about your desires.
*   **Lore & Look:** Discuss your character's vibe, appearance, and backstory naturally. "I want to be a scary demon lady" -> "Ah, a Tiefling Barbarian? Let's give you some horns..."
*   **Auto-Finalization:** When you're happy, the Consultant automatically generates your sheet and saves it to the database.

### 🎲 True RNG Dice Engine
*   **No Hallucinations:** The AI uses a Python-based deterministic dice engine (`dice_engine.py`) for all rolls. It cannot "fake" or "guess" numbers.
*   **Function Calling:** The AI instinctively knows when to roll. If you say "I attack," it calls the dice engine tool, gets a real result (e.g., `1d20+5 = 18`), and narrates the outcome based on that math.

### ⚔️ Expanded D&D 5e Rules
*   **Full Roster:** Now supports all 12 Classes (including **Bard**, Paladin, Warlock) and 9 Races (including **Tiefling**, Dragonborn, Half-Orc).
*   **Combat System:** Tracks Initiative and HP.
*   **Auto-Save:** Every action saves to the cloud (`/data` volume on Railway) and backs up weekly to Google Drive.

---

## 📜 Commands

| Command | Description |
| :--- | :--- |
| Command | Description |
| :--- | :--- |
| `!start [premise]` | **Start a new campaign.** Optionally provide a premise (e.g. "Space pirates"), or let the AI invent one. |
| `!create` | **Design your character.** Starts a chat session with the AI Consultant to build your new persona. |
| `!sheet` | **View Character Sheet.** Shows Health, Stats, Gold, Level, and Inventory. |
| `!quests` | **Quest Log.** View active objectives tracked by the AI. |
| `!relationships` | **Social Connections.** See how much NPCs like (or hate) you. |
| `!legend` | **Cinematic Recap.** The AI narrates the "Epic Tale" of your hero so far. |
| `!roll [expr]` | **Manual Dice Roll.** e.g., `!roll 1d20+5` or `!roll 4d6`. Uses true RNG. |
| `!fight [monster]` | **Start Combat.** Example: `!fight Goblin`. Triggers a cinematic encounter. |
| `!rest` | **Long Rest.** Fully restores HP and starts a campground roleplay scene. |
| `!backup` | **Cloud Save.** Manually uploads `campaign_state.json` to Google Drive immediately. |
| `!catchup` | **Recap.** Prints the last 4 story turns in case you forgot where you left off. |
| `!snapshot` | **Scene Painting.** Generates a vivid text description of the current scene. |
| `!status` | **Debug Info.** Shows bot uptime and the DM's internal "thought process". |
| `!fix` | **Mind Wipe.** Clears the AI's short-term memory (useful if it gets stuck in a loop), but keeps character stats. |

---

## 🚀 The Roadmap / Future Fun Stuff
*   **Image Generation 2.0:** Re-enabling actual image generation (Stable Diffusion or Imagen) for the `!snapshot` command.
*   **Voice Mode:** investigating ways to add TTS (Text-to-Speech) so the DM can *speak* the sultry narrations.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   Python 3.10+
*   A Discord Bot Token
*   Google Gemini API Key
*   Google Cloud Service Account (for Drive backups)

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/Jordannewman90/Roleplay_Foreplay.git
cd Roleplay_Foreplay

# create virtual environment
python -m venv venv
# Windows
.\venv\Scripts\activate 
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables (.env)
Create a `.env` file in the root:
```env
DISCORD_TOKEN=your_discord_token_here
GEMINI_API_KEY=your_gemini_key_here
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...} # Compact JSON string
```

### 4. Running
```bash
python main.py
```

---

## 📝 License
Private Personal Project.
