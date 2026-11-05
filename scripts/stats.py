#!/usr/bin/env python3
"""Genera assets/stats.svg y assets/langs.svg con animaciones, en tonos morados.

Se ejecuta desde la GitHub Action (.github/workflows/stats.yml), que le pasa
GITHUB_TOKEN. Sin dependencias externas: solo la biblioteca estándar.

Uso local para previsualizar sin token:  python3 scripts/stats.py --demo
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "Angelius6573")
OUT = Path(__file__).resolve().parent.parent / "assets"

# Paleta
BG1, BG2 = "#1a0b2e", "#2d1155"
BORDER1, BORDER2 = "#a855f7", "#e879f9"
TITLE = "#e9d5ff"
TEXT = "#d8b4fe"
VALUE = "#ffffff"
ICON = "#c084fc"
TRACK = "#3b1d63"
LANG_COLORS = ["#a855f7", "#e879f9", "#7c3aed", "#c084fc", "#f0abfc", "#6d28d9"]

# datos
def graphql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"Error de GraphQL: {body['errors']}")
    return body["data"]

MAIN_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      contributionYears
      totalCommitContributions
      restrictedContributionsCount
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
    }
  }
}"""

def fetch(token):
    u = graphql(MAIN_QUERY, {"login": USER}, token)["user"]
    cc = u["contributionsCollection"]

    total_contrib = 0
    for year in cc["contributionYears"]:
        y = graphql(
            YEAR_QUERY,
            {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
            token,
        )
        total_contrib += y["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]

    return {
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "contributions": total_contrib,
        "langs": langs,
    }

def demo():
    return {
        "stars": 3, "commits": 142, "prs": 7, "issues": 4, "repos": 3, "followers": 5,
        "contributions": 318,
        "langs": {"C++": 52000, "C": 21000, "Rust": 9000, "TypeScript": 6000, "Shell": 2500},
    }

# SVG
STYLE = f"""
<style>
  .title {{ font: 700 19px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: {TITLE}; }}
  .label {{ font: 400 14px 'Segoe UI', Ubuntu, sans-serif; fill: {TEXT}; }}
  .value {{ font: 700 14px 'Segoe UI', Ubuntu, sans-serif; fill: {VALUE}; }}
  .small {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: {TEXT}; }}
  .row {{ opacity: 0; animation: fadeIn .6s ease-out forwards; }}
  .bar {{ transform: scaleX(0); transform-box: fill-box; transform-origin: left;
          animation: grow 1.2s cubic-bezier(.2,.8,.2,1) forwards; }}
  .glow {{ animation: pulse 3s ease-in-out infinite; }}
  .spin {{ transform-box: fill-box; transform-origin: center; animation: spin 8s linear infinite; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateX(-12px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes grow {{ to {{ transform: scaleX(1); }} }}
  @keyframes pulse {{ 0%,100% {{ stroke-opacity: .55; }} 50% {{ stroke-opacity: 1; }} }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>"""

def frame(w, h, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BG1}"/><stop offset="1" stop-color="{BG2}"/>
  </linearGradient>
  <linearGradient id="border" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{BORDER1}"/><stop offset="1" stop-color="{BORDER2}"/>
  </linearGradient>
</defs>{STYLE}
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="url(#bg)"/>
<rect class="glow" x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="none" stroke="url(#border)" stroke-width="2"/>
<text class="title" x="25" y="38">{escape(title)}</text>
{body}
</svg>
"""

# Iconos simples (trazos de 16x16)
ICONS = {
    "star": "M8 .5l2.3 4.7 5.2.8-3.8 3.6.9 5.2L8 12.3 3.4 14.8l.9-5.2L.5 6l5.2-.8z",
    "commit": "M8 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM0 7h4.6v2H0zm11.4 0H16v2h-4.6z",
    "pr": "M4 1a2 2 0 0 1 1 3.7v6.6A2 2 0 1 1 3 11.3V4.7A2 2 0 0 1 4 1zm8 10.3V6a2 2 0 0 0-2-2H8.5V2L5.5 5l3 3V6H10v5.3a2 2 0 1 0 2 0z",
    "issue": "M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 2a5 5 0 1 0 0 10A5 5 0 0 0 8 3zm0 3a2 2 0 1 1 0 4 2 2 0 0 1 0-4z",
    "contrib": "M1 1h4v4H1zm5 0h4v4H6zm5 0h4v4h-4zM1 6h4v4H1zm5 0h4v4H6zm5 0h4v4h-4zM1 11h4v4H1zm5 0h4v4H6z",
    "repo": "M3 1h10a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2zm0 10a1 1 0 0 0 0 2h9v-2z",
}

def stats_svg(d):
    year = datetime.now(timezone.utc).year
    rows = [
        ("star", "Estrellas totales", d["stars"]),
        ("commit", "Commits (último año)", d["commits"]),
        ("contrib", "Contribuciones totales", d["contributions"]),
        ("pr", "Pull requests", d["prs"]),
        ("issue", "Issues", d["issues"]),
        ("repo", "Repositorios", d["repos"]),
    ]
    body = []
    for i, (icon, label, value) in enumerate(rows):
        y = 70 + i * 28
        body.append(
            f'<g class="row" style="animation-delay:{150 + i * 150}ms">'
            f'<path transform="translate(25 {y - 12})" d="{ICONS[icon]}" fill="{ICON}"/>'
            f'<text class="label" x="52" y="{y}">{label}:</text>'
            f'<text class="value" x="250" y="{y}">{value}</text></g>'
        )
    # Anillo animado con el total de contribuciones
    cx, cy, r = 370, 125, 50
    body.append(
        f'<g class="row" style="animation-delay:300ms">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="7"/>'
        f'<circle class="spin" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#border)" stroke-width="7" '
        f'stroke-linecap="round" stroke-dasharray="{3.1416 * r * 1.4:.1f} {3.1416 * r * 0.6:.1f}"/>'
        f'<text class="title" x="{cx}" y="{cy + 7}" text-anchor="middle">{d["contributions"]}</text>'
        f'<text class="small" x="{cx}" y="{cy + r + 24}" text-anchor="middle">contribuciones</text></g>'
    )
    return frame(450, 245, f"Estadísticas de {USER} · {year}", "\n".join(body))

def langs_svg(d):
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:6]
    body = []
    # Barra apilada
    x, w_total = 25, 300
    for i, (name, size) in enumerate(top):
        w = w_total * size / total
        body.append(
            f'<rect class="bar" style="animation-delay:{i * 120}ms" x="{x:.1f}" y="55" '
            f'width="{max(w, 2):.1f}" height="10" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
        )
        x += w
    body.insert(0, f'<rect x="25" y="55" width="{w_total}" height="10" rx="5" fill="{TRACK}"/>')
    # Leyenda en dos columnas
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 25 + col * 155, 98 + row * 30
        body.append(
            f'<g class="row" style="animation-delay:{400 + i * 120}ms">'
            f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
            f'<text class="label" x="{lx + 16}" y="{ly}">{escape(name)}</text>'
            f'<text class="small" x="{lx + 140}" y="{ly}" text-anchor="end">{100 * size / total:.1f}%</text></g>'
        )
    return frame(350, 245, "Lenguajes más usados", "\n".join(body))

def main():
    data = demo() if "--demo" in sys.argv else fetch(os.environ["GITHUB_TOKEN"])
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_svg(data), encoding="utf-8")
    (OUT / "langs.svg").write_text(langs_svg(data), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}))


if __name__ == "__main__":
    main()
