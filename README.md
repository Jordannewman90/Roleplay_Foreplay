# Roleplay_Foreplay 🎲🌶️

**Roleplay_Foreplay** is a customized Discord bot designed to act as a "Dungeon Master with Benefits" for private, couple-focused D&D 5e campaigns. Powered by Google's Gemini AI, it offers a unique blend of tabletop RPG mechanics and spicy, immersive storytelling.

## ✨ Features

*   **AI Dungeon Master:** A persona-driven DM ("Spicy/Adult" style) that narrates the story, controls NPCs, and adapts to player actions.
*   **Dynamic Persona:** The AI's personality is defined in `ai_persona.py`, allowing for easy customization of tone (currently set to "Dungeon Master with Benefits").
*   **Game Mechanics:**
    *   Character Creation (Race, Class, Auto-rolled Stats).
    *   Dice Rolling (The DM handles rolls for players if requested).
    *   Combat System (Initiative, HP tracking).
    *   Inventory & Stats Management.
*   **Persistence:**
    *   Auto-saves game state to `campaign_state.json`.
    *   Weekly backups to Google Drive.
    *   Chat history memory (remembers the last 20 turns).
*   **Commands:**
    *   `!start [premise]`: Kick off a new campaign.
    *   `!create`: Create a new character.
    *   `!sheet`: View your character sheet.
    *   `!fight [monster]`: Start a combat encounter.
    *   `!rest`: Heal up.
    *   `!status`: Check the bot's uptime and current "thought".
    *   `!catchup`: Read the last few turns of the story.
    *   `!guide`: Ask the DM for a hint.
    *   `!fix`: Clear short-term memory (if the AI gets confused).
    *   `!snapshot`: *[Currently Disabled]* Generate an image of the current scene.

## 🛠️ Setup

1.  **Clone the Repo:**
    ```bash
    git clone https://github.com/Jordannewman90/Roleplay_Foreplay.git
    cd Roleplay_Foreplay
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    Create a `.env` file in the root directory with the following:
    ```env
    DISCORD_TOKEN=your_discord_bot_token
    GEMINI_API_KEY=your_google_gemini_api_key
    GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id_for_backups
    GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...} # Your full JSON credentials string
    ```

4.  **Run the Bot:**
    ```bash
    python main.py
    ```
    *Or use the provided `run_bot.bat` script on Windows.*

## 🧠 Customization

*   **AI Persona:** Edit `ai_persona.py` to change the system prompt and adjust how the DM behaves.
*   **Game Rules:** Modify `rules.json` to add new races, classes, or monsters.

## 📝 License

Private Project.
