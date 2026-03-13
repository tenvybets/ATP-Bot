import discord
import os
from discord.ext import commands
from data import PLAYERS, ALIASES, TOURNAMENTS, STYLE_MATCHUP, SURFACE_ADVANTAGE

# ============================================================
# Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ============================================================
# Helper functies
# ============================================================

def find_player(name: str):
    """Zoek speler op naam, alias of gedeeltelijke naam."""
    key = name.lower().strip()

    # Directe match
    if key in PLAYERS:
        return key, PLAYERS[key]

    # Alias match
    if key in ALIASES:
        resolved = ALIASES[key]
        return resolved, PLAYERS[resolved]

    # Gedeeltelijke match op key
    for k in PLAYERS:
        if key in k:
            return k, PLAYERS[k]

    # Gedeeltelijke match op naam
    for k, p in PLAYERS.items():
        if key in p["name"].lower():
            return k, p

    return None, None


def find_tournament(name: str):
    """Zoek toernooi op naam of gedeeltelijke naam."""
    key = name.lower().strip()

    if key in TOURNAMENTS:
        return TOURNAMENTS[key]

    for k, t in TOURNAMENTS.items():
        if key in k or key in t["name"].lower():
            return t

    return None


def calculate_scores(p1_data, p2_data, tourn_data):
    """
    Bereken voordelen per factor.
    Geeft dict terug met scores voor p1 en p2 per factor.
    """
    surface = tourn_data["surface"]
    speed = tourn_data["speed"]
    scores = {
        "style":    [0, 0],
        "surface":  [0, 0],
        "ranking":  [0, 0],
        "form":     [0, 0],
        "category": [0, 0],
    }

    # 1. Speelstijl matchup (max 3 pts totaal)
    matchup = STYLE_MATCHUP.get((p1_data["style_key"], p2_data["style_key"]), 0)
    if matchup > 0:
        scores["style"][0] = min(matchup, 3)
    elif matchup < 0:
        scores["style"][1] = min(abs(matchup), 3)
    # beide 0 bij gelijkspel

    # 2. Ondergrond voordeel (max 2 pts)
    base = surface.split(" ")[0]  # "Hard", "Clay", "Grass"
    surface_key = surface
    adv = SURFACE_ADVANTAGE.get(surface_key, SURFACE_ADVANTAGE.get("Hard (outdoor)", {}))
    s1 = adv.get(p1_data["style_key"], 0)
    s2 = adv.get(p2_data["style_key"], 0)
    diff = s1 - s2
    if diff > 0:
        scores["surface"][0] = min(diff, 2)
    elif diff < 0:
        scores["surface"][1] = min(abs(diff), 2)

    # 3. Ranking voordeel (1 pt voor hogere rank)
    if p1_data["rank"] < p2_data["rank"]:
        scores["ranking"][0] = 1
    elif p2_data["rank"] < p1_data["rank"]:
        scores["ranking"][1] = 1

    # 4. Recente vorm 2025 (2 pts)
    p1_name = p1_data["name"].split()[-1]  # achternaam
    p2_name = p2_data["name"].split()[-1]

    w25 = tourn_data.get("winner_2025", "")
    f25 = tourn_data.get("finalist_2025", "")

    p1_won  = p1_name.lower() in w25.lower() if w25 else False
    p1_fin  = p1_name.lower() in f25.lower() if f25 else False
    p2_won  = p2_name.lower() in w25.lower() if w25 else False
    p2_fin  = p2_name.lower() in f25.lower() if f25 else False

    # Ook 2024 meewegen (1 pt)
    w24 = tourn_data.get("winner_2024", "")
    f24 = tourn_data.get("finalist_2024", "")
    p1_won24 = p1_name.lower() in w24.lower() if w24 else False
    p2_won24 = p2_name.lower() in w24.lower() if w24 else False

    form_p1 = (2 if p1_won else 1 if p1_fin else 0) + (1 if p1_won24 else 0)
    form_p2 = (2 if p2_won else 1 if p2_fin else 0) + (1 if p2_won24 else 0)
    form_p1 = min(form_p1, 2)
    form_p2 = min(form_p2, 2)

    if form_p1 > form_p2:
        scores["form"][0] = form_p1 - form_p2
    elif form_p2 > form_p1:
        scores["form"][1] = form_p2 - form_p1

    # 5. Toernooi categorie fit (1 pt)
    # Grand Slam / Masters 1000 → voordeel voor speler met hogere ranking
    if tourn_data["category"] in ["Grand Slam", "Masters 1000", "ATP Finals"]:
        if p1_data["rank"] <= 10 and p2_data["rank"] > 10:
            scores["category"][0] = 1
        elif p2_data["rank"] <= 10 and p1_data["rank"] > 10:
            scores["category"][1] = 1
        elif p1_data["rank"] < p2_data["rank"]:
            scores["category"][0] = 1
        elif p2_data["rank"] < p1_data["rank"]:
            scores["category"][1] = 1

    return scores


def build_reason(p1_data, p2_data, tourn_data, scores):
    """Genereer een korte analysezin."""
    p1_total = sum(v[0] for v in scores.values())
    p2_total = sum(v[1] for v in scores.values())

    winner = p1_data["name"] if p1_total >= p2_total else p2_data["name"]
    loser  = p2_data["name"] if p1_total >= p2_total else p1_data["name"]

    reasons = []
    surface = tourn_data["surface"]

    if scores["style"][0] > 0:
        reasons.append(f"{p1_data['name']}'s speelstijl past beter")
    elif scores["style"][1] > 0:
        reasons.append(f"{p2_data['name']}'s speelstijl past beter")

    if scores["surface"][0] > 0:
        reasons.append(f"presteert {p1_data['name']} beter op {surface}")
    elif scores["surface"][1] > 0:
        reasons.append(f"presteert {p2_data['name']} beter op {surface}")

    if scores["form"][0] > 0:
        reasons.append(f"{p1_data['name']} heeft betere recente vorm hier")
    elif scores["form"][1] > 0:
        reasons.append(f"{p2_data['name']} heeft betere recente vorm hier")

    if not reasons:
        reasons.append(f"ranking geeft de doorslag")

    return f"{winner} is favoriet: {', '.join(reasons[:2])}."


# ============================================================
# Embeds
# ============================================================

def make_predict_embed(p1_data, p2_data, tourn_data, scores):
    """Bouw de Discord embed voor !predict."""
    p1_total = sum(v[0] for v in scores.values())
    p2_total = sum(v[1] for v in scores.values())
    total    = p1_total + p2_total

    # Kleur gebaseerd op winnaar
    if p1_total > p2_total:
        color = discord.Color.from_rgb(88, 200, 100)   # groen
    elif p2_total > p1_total:
        color = discord.Color.from_rgb(255, 140, 50)    # oranje
    else:
        color = discord.Color.from_rgb(150, 150, 150)   # grijs bij gelijkspel

    embed = discord.Embed(
        title=f"🎾  {p1_data['name']}  vs.  {p2_data['name']}",
        color=color,
    )
    embed.set_author(name=f"🏆 {tourn_data['name']} · {tourn_data['category']} · {tourn_data['surface']} · {tourn_data['speed_cat']} ({tourn_data['speed']})")

    # Score overzicht
    bar = make_bar(p1_total, p2_total)
    embed.add_field(
        name="📊 Score",
        value=f"**{p1_data['name']}** `{p1_total} pts`   {bar}   `{p2_total} pts` **{p2_data['name']}**",
        inline=False,
    )

    # Factor tabel
    factor_lines = []
    factor_labels = {
        "style":    "🎭 Speelstijl",
        "surface":  "🌍 Ondergrond",
        "ranking":  "📈 Ranking",
        "form":     "🔥 Vorm 2025",
        "category": "🏟️ Toernooi fit",
    }
    for key, label in factor_labels.items():
        s1, s2 = scores[key]
        if s1 > s2:
            line = f"{label}: **{p1_data['name']} +{s1}**"
        elif s2 > s1:
            line = f"{label}: **{p2_data['name']} +{s2}**"
        else:
            line = f"{label}: Gelijk"
        factor_lines.append(line)

    embed.add_field(name="⚡ Factoren", value="\n".join(factor_lines), inline=True)

    # Toernooi info
    w25 = tourn_data.get("winner_2025", "—")
    f25 = tourn_data.get("finalist_2025", "—")
    w24 = tourn_data.get("winner_2024", "—")
    f24 = tourn_data.get("finalist_2024", "—")
    embed.add_field(
        name="🏆 Toernooi info",
        value=f"**2025:** 🥇 {w25}  🥈 {f25}\n**2024:** 🥇 {w24}  🥈 {f24}",
        inline=True,
    )

    # Speelstijlen
    embed.add_field(
        name=f"👤 {p1_data['name']}",
        value=f"Stijl: {p1_data['style']}\nVerliest van: {p1_data['loses_to'][:40]}",
        inline=True,
    )
    embed.add_field(
        name=f"👤 {p2_data['name']}",
        value=f"Stijl: {p2_data['style']}\nVerliest van: {p2_data['loses_to'][:40]}",
        inline=True,
    )

    # Eindverdict
    if p1_total > p2_total:
        verdict = f"🎾 Favoriet: **{p1_data['name']}**  ({p1_total}/{max(total,1)} pts)"
    elif p2_total > p1_total:
        verdict = f"🎾 Favoriet: **{p2_data['name']}**  ({p2_total}/{max(total,1)} pts)"
    else:
        verdict = "🎾 Te close to call — gelijkspel in analyse!"

    reason = build_reason(p1_data, p2_data, tourn_data, scores)
    embed.add_field(name="🔮 Verdict", value=f"{verdict}\n*{reason}*", inline=False)
    embed.set_footer(text="ATPBot · !help voor alle commando's · Data: 2024-2025 seizoen")

    return embed


def make_bar(s1, s2):
    """Maak een simpele ASCII progress bar."""
    total = s1 + s2
    if total == 0:
        return "▓▓▓▓▓░░░░░"
    filled = round((s1 / total) * 10)
    return "▓" * filled + "░" * (10 - filled)


# ============================================================
# Commando's
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ ATPBot online als {bot.user}")


@bot.command(name="predict")
async def predict(ctx, speler1: str = None, speler2: str = None, *, toernooi: str = None):
    """
    Analyseer een match.
    Gebruik: !predict Sinner Alcaraz "Roland Garros"
    """
    if not speler1 or not speler2 or not toernooi:
        await ctx.send(
            "❌ Gebruik: `!predict [speler1] [speler2] \"[toernooi]\"`\n"
            "Voorbeeld: `!predict Sinner Alcaraz \"Roland Garros\"`"
        )
        return

    toernooi_clean = toernooi.strip('"').strip("'")

    _, p1 = find_player(speler1)
    _, p2 = find_player(speler2)
    tourn = find_tournament(toernooi_clean)

    if not p1:
        await ctx.send(f"❌ Speler **{speler1}** niet gevonden. Gebruik `!spelers` voor de volledige lijst.")
        return
    if not p2:
        await ctx.send(f"❌ Speler **{speler2}** niet gevonden. Gebruik `!spelers` voor de volledige lijst.")
        return
    if not tourn:
        await ctx.send(f"❌ Toernooi **{toernooi_clean}** niet gevonden. Gebruik `!toernooien` voor de volledige lijst.")
        return

    scores = calculate_scores(p1, p2, tourn)
    embed  = make_predict_embed(p1, p2, tourn, scores)
    await ctx.send(embed=embed)


@bot.command(name="spelers")
async def spelers(ctx):
    """Toon alle beschikbare spelers."""
    # Unieke spelers op naam
    seen = set()
    lines = []
    for k, p in PLAYERS.items():
        if p["name"] not in seen:
            seen.add(p["name"])
            lines.append(f"#{p['rank']:>3}  {p['name']} ({p['country']})")

    # Splits in meerdere embeds als te lang
    chunks = []
    chunk  = []
    for line in sorted(lines, key=lambda x: int(x[1:4])):
        chunk.append(line)
        if len(chunk) == 25:
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)

    for i, c in enumerate(chunks):
        embed = discord.Embed(
            title=f"🎾 Beschikbare Spelers ({i+1}/{len(chunks)})",
            description="```\n" + "\n".join(c) + "\n```",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)


@bot.command(name="toernooien")
async def toernooien_cmd(ctx, categorie: str = None):
    """Toon alle toernooien. Optioneel filter: !toernooien Masters"""
    seen = set()
    lines = []
    for k, t in TOURNAMENTS.items():
        if t["name"] not in seen:
            if categorie is None or categorie.lower() in t["category"].lower():
                seen.add(t["name"])
                lines.append(f"{t['name']:<35} {t['category']:<15} {t['surface']:<18} {t['speed_cat']}")

    if not lines:
        await ctx.send(f"❌ Geen toernooien gevonden voor categorie: **{categorie}**")
        return

    chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
    for i, c in enumerate(chunks):
        embed = discord.Embed(
            title=f"🏆 Toernooien ({i+1}/{len(chunks)})",
            description="```\n" + "\n".join(c) + "\n```",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)


@bot.command(name="speler")
async def speler_info(ctx, *, naam: str = None):
    """Bekijk info over een speler. Gebruik: !speler Sinner"""
    if not naam:
        await ctx.send("❌ Gebruik: `!speler [naam]`\nVoorbeeld: `!speler Sinner`")
        return

    _, p = find_player(naam)
    if not p:
        await ctx.send(f"❌ Speler **{naam}** niet gevonden.")
        return

    embed = discord.Embed(
        title=f"👤 {p['name']}",
        color=discord.Color.green(),
    )
    embed.add_field(name="🌍 Land",         value=p["country"],       inline=True)
    embed.add_field(name="📈 Ranking",       value=f"#{p['rank']}",   inline=True)
    embed.add_field(name="🎭 Speelstijl",    value=p["style"],         inline=False)
    embed.add_field(name="❌ Verliest van",   value=p["loses_to"],      inline=False)
    embed.add_field(name="✅ Wint van",       value=p["wins_against"],  inline=False)
    embed.add_field(name="🎾 Ondergrond",    value=p["surface"],       inline=False)
    embed.set_footer(text="ATPBot · !predict om een match te analyseren")
    await ctx.send(embed=embed)


@bot.command(name="toernooi")
async def toernooi_info(ctx, *, naam: str = None):
    """Bekijk info over een toernooi. Gebruik: !toernooi Wimbledon"""
    if not naam:
        await ctx.send("❌ Gebruik: `!toernooi [naam]`\nVoorbeeld: `!toernooi Wimbledon`")
        return

    t = find_tournament(naam)
    if not t:
        await ctx.send(f"❌ Toernooi **{naam}** niet gevonden.")
        return

    embed = discord.Embed(title=f"🏆 {t['name']}", color=discord.Color.gold())
    embed.add_field(name="Categorie",    value=t["category"],    inline=True)
    embed.add_field(name="Ondergrond",   value=t["surface"],     inline=True)
    embed.add_field(name="Snelheid",     value=f"{t['speed']} ({t['speed_cat']})", inline=True)
    embed.add_field(name="🥇 2025",      value=t.get("winner_2025", "—"),    inline=True)
    embed.add_field(name="🥈 2025",      value=t.get("finalist_2025", "—"),  inline=True)
    embed.add_field(name="🥇 2024",      value=t.get("winner_2024", "—"),    inline=True)
    embed.add_field(name="🥈 2024",      value=t.get("finalist_2024", "—"),  inline=True)
    embed.set_footer(text="ATPBot · !predict om een match te analyseren")
    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_cmd(ctx):
    """Toon alle beschikbare commando's."""
    embed = discord.Embed(
        title="🎾 ATPBot — Commando's",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="🔮  !predict [speler1] [speler2] \"[toernooi]\"",
        value="Analyseer wie favoriet is.\n*Voorbeeld: `!predict Sinner Alcaraz \"Roland Garros\"`*",
        inline=False,
    )
    embed.add_field(
        name="👤  !speler [naam]",
        value="Bekijk profiel van een speler.\n*Voorbeeld: `!speler Draper`*",
        inline=False,
    )
    embed.add_field(
        name="🏆  !toernooi [naam]",
        value="Bekijk info over een toernooi.\n*Voorbeeld: `!toernooi Wimbledon`*",
        inline=False,
    )
    embed.add_field(
        name="📋  !spelers",
        value="Lijst van alle spelers in de database.",
        inline=False,
    )
    embed.add_field(
        name="📅  !toernooien [categorie]",
        value="Lijst van alle toernooien. Filter optioneel op categorie.\n*Voorbeeld: `!toernooien Masters`*",
        inline=False,
    )
    embed.set_footer(text="💡 Spelersnamen zijn hoofdletterongevoelig")
    await ctx.send(embed=embed)


# ============================================================
# Start bot
# ============================================================
token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN niet gevonden! Voeg hem toe als omgevingsvariabele.")

bot.run(token)
