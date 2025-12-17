# roleplay_foreplay 🎲🌶️

**roleplay_foreplay** is your "Dungeon Master with Benefits"—a bespoke AI-powered Discord bot designed for private, couple-focused D&D 5e campaigns.

It combines legitimate tabletop RPG mechanics (stats, dice rolling, combat) with an immersive, spicy, and romance-novel-worthy narrative driven by Google's Gemini 1.5 Pro.

---

## ✨ Key Features

### 🧠 The "DM with Benefits"
*   **Persona-Driven AI:** The bot isn't just a text generator; it's a character. It's mischievous, flirtatious, and competent. It wants you to adventure *and* get close.
*   **Deep Memory:** Remembers the last **200 turns** of conversation, ensuring long-term storytelling continuity.
*   **Context Aware:** Knows your HP, inventory, and current location at all times.

### 🎮 Game Mechanics
*   **Character Creation:** Guided process to roll stats (4d6 drop lowest), pick a Race, and choose a Class.
*   **Combat System:**
    *   Initiative tracking (You vs. Monster).
    *   HP tracking (persists between sessions).
    *   **Monster Manual:** Simple JSON-based monster definitions (`rules.json`).
*   **Auto-Rolling:** Don't have dice? The DM will roll for you (e.g., "I rolled a 18 for your Persuasion check... nice.").

### ☁️ Cloud Persistence
*   **Auto-Save:** Every message and action saves the game state to `campaign_state.json`.
*   **Railway Support:** Configured for persistent storage on Railway (using `/data` volume).
*   **Google Drive Backups:** Automatically backs up your campaign to Google Drive once a week (or manually via `!backup`).

### 🛡️ Robust Architecture
*   **Google GenAI SDK:** Built on the latest `google-genai` Python SDK for stability.
*   **Error Handling:** Friendly error messages instead of silent crashes.
*   **Docker Ready:** Includes `Procfile` for easy cloud deployment.

---

## 📜 Commands

| Command | Description |
| :--- | :--- |
| `!start [premise]` | **Start a new campaign.** Optionally provide a premise (e.g. "Space pirates"), or let the AI invent one. |
| `!create` | **Create a character.** The bot walks you through rolling stats and picking a class. |
| `!sheet` | **View Character Sheet.** Shows Name, Race, Class, HP, and Stats. |
| `!fight [monster]` | **Start Combat.** Example: `!fight Goblin`. Rolls initiatives and sets the scene. |
| `!rest` | **Long Rest.** Fully restores HP and saves the game. |
| `!backup` | **Cloud Save.** Manually uploads `campaign_state.json` to Google Drive immediately. |
| `!catchup` | **Recap.** Prints the last 4 story turns in case you forgot where you left off. |
| `!status` | **Debug Info.** Shows bot uptime and the DM's internal "thought process" (fun for peeking behind the curtain). |
| `!fix` | **Mind Wipe.** Clears the AI's short-term memory (useful if it gets stuck in a loop), but keeps character stats. |

---

## 🚀 The Roadmap / Future Fun Stuff
*   **Relationship Tracking:** NPCs that have "Affection Points" and distinct relationship tiers (Strangers -> Lovers).
*   **Image Generation 2.0:** Re-enabling the `!snapshot` command with a better model to generate scene art on the fly.
*   **Voice Mode:** investigating ways to add TTS (Text-to-Speech) so the DM can *speak* the sultry narrations.
*   **Quest Log:** A persistent list of active quests and objectives managed by the AI.

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
