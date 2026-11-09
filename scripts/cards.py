"""Build the profile cards (assets/stats.svg, assets/activity.svg) from live GitHub data.

Run by .github/workflows/cards.yml every day. Needs GITHUB_TOKEN in the environment.
Header (assets/header.svg) is built once by hand and is not touched here.
"""
import json
import os
import urllib.request
from datetime import date
from pathlib import Path

USER = "ShadowIzzHerZ"
OUT = Path(__file__).resolve().parent.parent / "assets"

# Palette taken from the avatar: navy night, cyan sky
BG, PANEL = "#060A12", "#0A1220"
TEXT, SECOND, MUTED = "#EAF6FF", "#8FA9C2", "#7F97B0"
ACCENT = "#22C3F6"
LEVELS = {  # contribution level -> cell colour, dim to bright cyan
    "NONE": "#0F1B2B",
    "FIRST_QUARTILE": "#0E4A66",
    "SECOND_QUARTILE": "#127FA8",
    "THIRD_QUARTILE": "#1BA9DB",
    "FOURTH_QUARTILE": "#5FD8FF",
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    body = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in body:
        raise SystemExit(f"GitHub API error: {body['errors']}")
    return body["data"]["user"]


def frame(w, h, inner):
    """Card shell: dark panel, soft cyan glow in two corners, hairline borders."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <radialGradient id="g1" cx="0.12" cy="0" r="0.6"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0.28"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx="0.95" cy="1" r="0.5"><stop offset="0" stop-color="#3B6BFF" stop-opacity="0.18"/><stop offset="1" stop-color="#3B6BFF" stop-opacity="0"/></radialGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0.7"/><stop offset="0.5" stop-color="{ACCENT}" stop-opacity="0.12"/><stop offset="1" stop-color="#3B6BFF" stop-opacity="0.5"/></linearGradient>
  </defs>
  <rect width="{w}" height="{h}" rx="20" fill="{BG}"/>
  <rect width="{w}" height="{h}" rx="20" fill="url(#g1)"/>
  <rect width="{w}" height="{h}" rx="20" fill="url(#g2)"/>
  <rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="19.25" fill="none" stroke="url(#edge)" stroke-width="1.5"/>
{inner}
</svg>
"""


def stats_svg(user):
    days = [d for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    tiles = [
        ("Contributions", f"{user['contributionsCollection']['contributionCalendar']['totalContributions']:,}", "last 12 months"),
        ("Active days", str(sum(d["contributionCount"] > 0 for d in days)), "last 12 months"),
        ("Public repos", str(user["repositories"]["totalCount"]), "not counting forks"),
        ("Stars", str(sum(n["stargazerCount"] for n in user["repositories"]["nodes"])), "across all repos"),
    ]
    w, h, pad, gap = 880, 200, 32, 16
    tw = (w - 2 * pad - 3 * gap) / 4
    parts = []
    for i, (label, value, note) in enumerate(tiles):
        x = pad + i * (tw + gap)
        parts.append(f"""  <rect x="{x:.1f}" y="{pad}" width="{tw:.1f}" height="{h - 2 * pad}" rx="14" fill="{PANEL}" fill-opacity="0.85" stroke="{ACCENT}" stroke-opacity="0.22"/>
  <text x="{x + 20:.1f}" y="{pad + 36}" fill="{SECOND}" font-family="{SANS}" font-size="15">{label}</text>
  <text x="{x + 20:.1f}" y="{pad + 90}" fill="{ACCENT if i == 0 else TEXT}" font-family="{SANS}" font-size="46" font-weight="600" letter-spacing="-1">{value}</text>
  <text x="{x + 20:.1f}" y="{pad + 116}" fill="{MUTED}" font-family="{MONO}" font-size="12">{note}</text>""")
    return frame(w, h, "\n".join(parts))


def activity_svg(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    cell, step = 11, 14
    w, h = 880, 230
    x0 = (w - len(weeks) * step + (step - cell)) / 2
    y0 = 88
    parts = [
        f'  <text x="{x0:.1f}" y="52" fill="{TEXT}" font-family="{SANS}" font-size="22" font-weight="600">{cal["totalContributions"]:,} contributions in the last year</text>',
        f'  <text x="{w - x0:.1f}" y="52" fill="{MUTED}" font-family="{MONO}" font-size="12" text-anchor="end">updated {date.today():%d %b %Y}</text>',
    ]
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            dow = date.fromisoformat(day["date"]).isoweekday() % 7  # Sunday = 0, like GitHub
            n = day["contributionCount"]
            parts.append(
                f'  <rect x="{x0 + wi * step:.1f}" y="{y0 + dow * step}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[day["contributionLevel"]]}">'
                f'<title>{n} on {day["date"]}</title></rect>'
            )
    ly = y0 + 7 * step + 18
    lx = w - x0 - 5 * step - 34
    parts.append(f'  <text x="{lx - 10:.1f}" y="{ly + 10}" fill="{MUTED}" font-family="{SANS}" font-size="12" text-anchor="end">Less</text>')
    for i, c in enumerate(LEVELS.values()):
        parts.append(f'  <rect x="{lx + i * step:.1f}" y="{ly}" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>')
    parts.append(f'  <text x="{lx + 5 * step + 6:.1f}" y="{ly + 10}" fill="{MUTED}" font-family="{SANS}" font-size="12">More</text>')
    return frame(w, h, "\n".join(parts))


if __name__ == "__main__":
    user = fetch()
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_svg(user))
    (OUT / "activity.svg").write_text(activity_svg(user))
    print("wrote stats.svg and activity.svg")
