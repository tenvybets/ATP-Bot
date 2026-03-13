# 🎾 ATPBot — Discord Tennis Predictor

A Discord bot that analyses ATP tennis matches based on playing style,
surface, ranking and recent form.

---

## Commands

| Command | Description | Example |
|---|---|---|
| `!predict [p1] [p2] "[tournament]"` | Analyse a match | `!predict Sinner Alcaraz "Roland Garros"` |
| `!player [name]` | View a player's profile | `!player Draper` |
| `!tournament [name]` | View tournament info | `!tournament Wimbledon` |
| `!players` | List all players in the database | `!players` |
| `!tournaments [category]` | List all tournaments | `!tournaments Masters` |
| `!help` | Show this overview | `!help` |

---

## Deploy on Railway

### Step 1 — Upload files to GitHub

1. Go to your GitHub repo (`atp-bot`)
2. Click **"Add file" → "Upload files"**
3. Drag all 4 files in:
   - `bot.py`
   - `data.py`
   - `requirements.txt`
   - `Procfile`
4. Click **"Commit changes"**

### Step 2 — Connect Railway

1. Go to **railway.app**
2. Open your project → click on your GitHub repo
3. Railway will detect the files automatically

### Step 3 — Add the bot token

1. In Railway: go to your service → **"Variables"** tab
2. Click **"+ New Variable"**
3. Name: `DISCORD_TOKEN`
4. Value: paste your bot token here
5. Click **"Add"**

### Step 4 — Deploy

1. Railway deploys automatically once the variable is added
2. Go to the **"Deployments"** tab
3. Wait for `✅ Success`
4. The bot is now online 24/7!

---

## Troubleshooting

**Bot not responding:**
- Check that "Message Content Intent" is enabled in Discord Developer Portal → Bot
- Check Railway logs for errors

**"DISCORD_TOKEN not found":**
- Make sure the variable is named exactly `DISCORD_TOKEN` in Railway

**Player not found:**
- Try using just the surname: `!predict Sinner Alcaraz "Roland Garros"`
- Use `!players` to see the exact names

---

## Files

- `bot.py` — Main bot with all commands
- `data.py` — All players (100+) and tournaments (57) with 2024/2025 data
- `requirements.txt` — Python packages
- `Procfile` — Railway start command
