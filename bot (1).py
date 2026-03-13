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
# Helper functions
# ============================================================

def find_player(name: str):
    """Find a player by key, alias or partial name."""
    key = name.lower().strip()
    if key in PLAYERS:
        return key, PLAYERS[key]
    if key in ALIASES:
        resolved = ALIASES[key]
        return resolved, PLAYERS[resolved]
    for k in PLAYERS:
        if key in k:
            return k, PLAYERS[k]
    for k, p in PLAYERS.items():
        if key in p["name"].lower():
            return k, p
    return None, None


def find_tournament(name: str):
    """Find a tournament by key or partial name."""
    key = name.lower().strip()
    if key in TOURNAMENTS:
        return TOURNAMENTS[key]
    for k, t in TOURNAMENTS.items():
        if key in k or key in t["name"].lower():
            return t
    return None


def calculate_scores(p1_data, p2_data, tourn_data):
    """Calculate advantage scores per factor. Returns {factor: [p1_pts, p2_pts]}."""
    surface = tourn_data["surface"]
    scores = {
        "style":    [0, 0],
        "surface":  [0, 0],
        "ranking":  [0, 0],
        "form":     [0, 0],
        "category": [0, 0],
    }

    # 1. Playing style matchup (max 3 pts)
    matchup = STYLE_MATCHUP.get((p1_data["style_key"], p2_data["style_key"]), 0)
    if matchup > 0:
        scores["style"][0] = min(matchup, 3)
    elif matchup < 0:
        scores["style"][1] = min(abs(matchup), 3)

    # 2. Surface advantage (max 2 pts)
    adv = SURFACE_ADVANTAGE.get(surface, SURFACE_ADVANTAGE.get("Hard (outdoor)", {}))
    s1  = adv.get(p1_data["style_key"], 0)
    s2  = adv.get(p2_data["style_key"], 0)
    diff = s1 - s2
    if diff > 0:
        scores["surface"][0] = min(diff, 2)
    elif diff < 0:
        scores["surface"][1] = min(abs(diff), 2)

    # 3. Ranking advantage (1 pt)
    if p1_data["rank"] < p2_data["rank"]:
        scores["ranking"][0] = 1
    elif p2_data["rank"] < p1_data["rank"]:
        scores["ranking"][1] = 1

    # 4. Recent form 2025 (max 2 pts) + 2024 bonus (1 pt)
    p1_name = p1_data["name"].split()[-1]
    p2_name = p2_data["name"].split()[-1]
    w25 = tourn_data.get("winner_2025", "")
    f25 = tourn_data.get("finalist_2025", "")
    w24 = tourn_data.get("winner_2024", "")

    form_p1 = min(
        (2 if p1_name.lower() in w25.lower() else 1 if p1_name.lower() in f25.lower() else 0)
        + (1 if p1_name.lower() in w24.lower() else 0), 2)
    form_p2 = min(
        (2 if p2_name.lower() in w25.lower() else 1 if p2_name.lower() in f25.lower() else 0)
        + (1 if p2_name.lower() in w24.lower() else 0), 2)

    if form_p1 > form_p2:
        scores["form"][0] = form_p1 - form_p2
    elif form_p2 > form_p1:
        scores["form"][1] = form_p2 - form_p1

    # 5. Tournament category fit (1 pt)
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
    """Generate a short analysis sentence."""
    p1_total = sum(v[0] for v in scores.values())
    p2_total = sum(v[1] for v in scores.values())
    winner  = p1_data["name"] if p1_total >= p2_total else p2_data["name"]
    surface = tourn_data["surface"]
    reasons = []

    if scores["style"][0] > 0:
        reasons.append(f"{p1_data['name']}'s playing style is a better fit")
    elif scores["style"][1] > 0:
        reasons.append(f"{p2_data['name']}'s playing style is a better fit")
    if scores["surface"][0] > 0:
        reasons.append(f"{p1_data['name']} performs better on {surface}")
    elif scores["surface"][1] > 0:
        reasons.append(f"{p2_data['name']} performs better on {surface}")
    if scores["form"][0] > 0:
        reasons.append(f"{p1_data['name']} has better recent form here")
    elif scores["form"][1] > 0:
        reasons.append(f"{p2_data['name']} has better recent form here")
    if not reasons:
        reasons.append("ranking gives the edge")

    return f"{winner} is the favourite: {', '.join(reasons[:2])}."


# ============================================================
# Embed builder
# ============================================================

def make_bar(s1, s2):
    """Simple ASCII progress bar."""
    total = s1 + s2
    if total == 0:
        return "▓▓▓▓▓░░░░░"
    filled = round((s1 / total) * 10)
    return "▓" * filled + "░" * (10 - filled)


def make_predict_embed(p1_data, p2_data, tourn_data, scores):
    """Build the Discord embed for !predict."""
    p1_total = sum(v[0] for v in scores.values())
    p2_total = sum(v[1] for v in scores.values())
    total    = p1_total + p2_total

    if p1_total > p2_total:
        color = discord.Color.from_rgb(88, 200, 100)
    elif p2_total > p1_total:
        color = discord.Color.from_rgb(255, 140, 50)
    else:
        color = discord.Color.from_rgb(150, 150, 150)

    embed = discord.Embed(
        title=f"🎾  {p1_data['name']}  vs.  {p2_data['name']}",
        color=color,
    )
    embed.set_author(
        name=f"🏆 {tourn_data['name']} · {tourn_data['category']} · {tourn_data['surface']} · {tourn_data['speed_cat']} ({tourn_data['speed']})"
    )

    bar = make_bar(p1_total, p2_total)
    embed.add_field(
        name="📊 Score",
        value=f"**{p1_data['name']}** `{p1_total} pts`   {bar}   `{p2_total} pts` **{p2_data['name']}**",
        inline=False,
    )

    factor_labels = {
        "style":    "🎭 Playing Style",
        "surface":  "🌍 Surface",
        "ranking":  "📈 Ranking",
        "form":     "🔥 2025 Form",
        "category": "🏟️ Tournament Fit",
    }
    factor_lines = []
    for key, label in factor_labels.items():
        s1, s2 = scores[key]
        if s1 > s2:
            factor_lines.append(f"{label}: **{p1_data['name']} +{s1}**")
        elif s2 > s1:
            factor_lines.append(f"{label}: **{p2_data['name']} +{s2}**")
        else:
            factor_lines.append(f"{label}: Even")

    embed.add_field(name="⚡ Factors", value="\n".join(factor_lines), inline=True)

    w25 = tourn_data.get("winner_2025", "—")
    f25 = tourn_data.get("finalist_2025", "—")
    w24 = tourn_data.get("winner_2024", "—")
    f24 = tourn_data.get("finalist_2024", "—")
    embed.add_field(
        name="🏆 Tournament History",
        value=f"**2025:** 🥇 {w25}  🥈 {f25}\n**2024:** 🥇 {w24}  🥈 {f24}",
        inline=True,
    )

    embed.add_field(
        name=f"👤 {p1_data['name']}",
        value=f"Style: {p1_data['style']}\nLoses to: {p1_data['loses_to'][:40]}",
        inline=True,
    )
    embed.add_field(
        name=f"👤 {p2_data['name']}",
        value=f"Style: {p2_data['style']}\nLoses to: {p2_data['loses_to'][:40]}",
        inline=True,
    )

    if p1_total > p2_total:
        verdict = f"🎾 Favourite: **{p1_data['name']}**  ({p1_total}/{max(total, 1)} pts)"
    elif p2_total > p1_total:
        verdict = f"🎾 Favourite: **{p2_data['name']}**  ({p2_total}/{max(total, 1)} pts)"
    else:
        verdict = "🎾 Too close to call — analysis is a draw!"

    reason = build_reason(p1_data, p2_data, tourn_data, scores)
    embed.add_field(name="🔮 Verdict", value=f"{verdict}\n*{reason}*", inline=False)
    embed.set_footer(text="ATPBot · !help for all commands · Data: 2024–2025 season")

    return embed


# ============================================================
# Commands
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ ATPBot online as {bot.user}")


@bot.command(name="predict")
async def predict(ctx, player1: str = None, player2: str = None, *, tournament: str = None):
    """Analyse a match. Usage: !predict Sinner Alcaraz "Roland Garros" """
    if not player1 or not player2 or not tournament:
        await ctx.send(
            "❌ Usage: `!predict [player1] [player2] \"[tournament]\"`\n"
            "Example: `!predict Sinner Alcaraz \"Roland Garros\"`"
        )
        return

    tournament_clean = tournament.strip('"').strip("'")
    _, p1  = find_player(player1)
    _, p2  = find_player(player2)
    tourn  = find_tournament(tournament_clean)

    if not p1:
        await ctx.send(f"❌ Player **{player1}** not found. Use `!players` for the full list.")
        return
    if not p2:
        await ctx.send(f"❌ Player **{player2}** not found. Use `!players` for the full list.")
        return
    if not tourn:
        await ctx.send(f"❌ Tournament **{tournament_clean}** not found. Use `!tournaments` for the full list.")
        return

    scores = calculate_scores(p1, p2, tourn)
    embed  = make_predict_embed(p1, p2, tourn, scores)
    await ctx.send(embed=embed)


@bot.command(name="players")
async def players_cmd(ctx):
    """List all available players."""
    seen, lines = set(), []
    for k, p in PLAYERS.items():
        if p["name"] not in seen:
            seen.add(p["name"])
            lines.append(f"#{p['rank']:>3}  {p['name']} ({p['country']})")

    sorted_lines = sorted(lines, key=lambda x: int(x[1:4].strip()))
    chunks = [sorted_lines[i:i+25] for i in range(0, len(sorted_lines), 25)]

    for i, c in enumerate(chunks):
        embed = discord.Embed(
            title=f"🎾 Available Players ({i+1}/{len(chunks)})",
            description="```\n" + "\n".join(c) + "\n```",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)


@bot.command(name="tournaments")
async def tournaments_cmd(ctx, category: str = None):
    """List all tournaments. Optional filter: !tournaments Masters"""
    seen, lines = set(), []
    for k, t in TOURNAMENTS.items():
        if t["name"] not in seen:
            if category is None or category.lower() in t["category"].lower():
                seen.add(t["name"])
                lines.append(f"{t['name']:<35} {t['category']:<15} {t['surface']:<18} {t['speed_cat']}")

    if not lines:
        await ctx.send(f"❌ No tournaments found for category: **{category}**")
        return

    chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
    for i, c in enumerate(chunks):
        embed = discord.Embed(
            title=f"🏆 Tournaments ({i+1}/{len(chunks)})",
            description="```\n" + "\n".join(c) + "\n```",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)


@bot.command(name="player")
async def player_info(ctx, *, name: str = None):
    """View a player's profile. Usage: !player Sinner"""
    if not name:
        await ctx.send("❌ Usage: `!player [name]`\nExample: `!player Sinner`")
        return
    _, p = find_player(name)
    if not p:
        await ctx.send(f"❌ Player **{name}** not found.")
        return

    embed = discord.Embed(title=f"👤 {p['name']}", color=discord.Color.green())
    embed.add_field(name="🌍 Country",       value=p["country"],      inline=True)
    embed.add_field(name="📈 Ranking",       value=f"#{p['rank']}",   inline=True)
    embed.add_field(name="🎭 Playing Style", value=p["style"],        inline=False)
    embed.add_field(name="❌ Loses to",      value=p["loses_to"],     inline=False)
    embed.add_field(name="✅ Beats",         value=p["wins_against"], inline=False)
    embed.add_field(name="🎾 Surface",       value=p["surface"],      inline=False)
    embed.set_footer(text="ATPBot · !predict to analyse a match")
    await ctx.send(embed=embed)


@bot.command(name="tournament")
async def tournament_info(ctx, *, name: str = None):
    """View tournament info. Usage: !tournament Wimbledon"""
    if not name:
        await ctx.send("❌ Usage: `!tournament [name]`\nExample: `!tournament Wimbledon`")
        return
    t = find_tournament(name)
    if not t:
        await ctx.send(f"❌ Tournament **{name}** not found.")
        return

    embed = discord.Embed(title=f"🏆 {t['name']}", color=discord.Color.gold())
    embed.add_field(name="Category",         value=t["category"],  inline=True)
    embed.add_field(name="Surface",          value=t["surface"],   inline=True)
    embed.add_field(name="Speed",            value=f"{t['speed']} ({t['speed_cat']})", inline=True)
    embed.add_field(name="🥇 2025 Winner",   value=t.get("winner_2025",   "—"), inline=True)
    embed.add_field(name="🥈 2025 Finalist", value=t.get("finalist_2025", "—"), inline=True)
    embed.add_field(name="🥇 2024 Winner",   value=t.get("winner_2024",   "—"), inline=True)
    embed.add_field(name="🥈 2024 Finalist", value=t.get("finalist_2024", "—"), inline=True)
    embed.set_footer(text="ATPBot · !predict to analyse a match")
    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_cmd(ctx):
    """Show all available commands."""
    embed = discord.Embed(title="🎾 ATPBot — Commands", color=discord.Color.blue())
    embed.add_field(
        name='🔮  !predict [player1] [player2] "[tournament]"',
        value='Analyse who is the favourite.\n*Example: `!predict Sinner Alcaraz "Roland Garros"`*',
        inline=False,
    )
    embed.add_field(
        name="👤  !player [name]",
        value="View a player's profile.\n*Example: `!player Draper`*",
        inline=False,
    )
    embed.add_field(
        name="🏆  !tournament [name]",
        value="View tournament info.\n*Example: `!tournament Wimbledon`*",
        inline=False,
    )
    embed.add_field(
        name="📋  !players",
        value="List all players in the database.",
        inline=False,
    )
    embed.add_field(
        name="📅  !tournaments [category]",
        value="List all tournaments. Optional category filter.\n*Example: `!tournaments Masters`*",
        inline=False,
    )
    embed.set_footer(text="💡 Player names are case-insensitive")
    await ctx.send(embed=embed)


# ============================================================
# Start bot
# ============================================================
token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN not found! Add it as an environment variable in Railway.")

bot.run(token)
