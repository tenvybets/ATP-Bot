# 🎾 ATPBot — Discord Tennis Predictor

Een Discord bot die ATP tenniswedstrijden analyseert op basis van speelstijl,
ondergrond, ranking en recente vorm.

---

## Commando's

| Commando | Beschrijving | Voorbeeld |
|---|---|---|
| `!predict [p1] [p2] "[toernooi]"` | Analyseer een match | `!predict Sinner Alcaraz "Roland Garros"` |
| `!speler [naam]` | Spelerprofiel bekijken | `!speler Draper` |
| `!toernooi [naam]` | Toernooi-info bekijken | `!toernooi Wimbledon` |
| `!spelers` | Alle spelers in de database | `!spelers` |
| `!toernooien [categorie]` | Alle toernooien | `!toernooien Masters` |
| `!help` | Toon dit overzicht | `!help` |

---

## Deploy op Railway

### Stap 1 — Bestanden uploaden naar GitHub

1. Ga naar je GitHub repo (`atp-bot`)
2. Klik **"Add file" → "Upload files"**
3. Sleep alle 4 bestanden erin:
   - `bot.py`
   - `data.py`
   - `requirements.txt`
   - `Procfile`
4. Klik **"Commit changes"**

### Stap 2 — Railway koppelen

1. Ga naar **railway.app**
2. Open je project → klik op je GitHub repo
3. Railway detecteert de bestanden automatisch

### Stap 3 — Bot token toevoegen

1. In Railway: ga naar je service → tabblad **"Variables"**
2. Klik **"+ New Variable"**
3. Naam: `DISCORD_TOKEN`
4. Waarde: plak hier je bot token (die je in stap 1 van het stappenplan had gekopieerd)
5. Klik **"Add"**

### Stap 4 — Deployen

1. Railway deployt automatisch zodra je de variabele hebt toegevoegd
2. Ga naar het **"Deployments"** tabblad
3. Wacht tot je `✅ Success` ziet
4. De bot is nu 24/7 online!

---

## Troubleshooting

**Bot reageert niet:**
- Check of `Message Content Intent` aan staat in Discord Developer Portal → Bot
- Check de Railway logs op fouten

**"DISCORD_TOKEN niet gevonden":**
- Controleer of de variabele exact `DISCORD_TOKEN` heet in Railway

**Speler niet gevonden:**
- Probeer alleen de achternaam: `!predict Sinner Alcaraz "Roland Garros"`
- Gebruik `!spelers` om de exacte naam te zien

---

## Bestanden

- `bot.py` — Hoofdbot met alle commando's
- `data.py` — Alle spelers (100+) en toernooien (57) met 2024/2025 data
- `requirements.txt` — Python packages
- `Procfile` — Railway startcommando
