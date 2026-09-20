#!/usr/bin/env python3
"""Regenerate assets/scouting-report.svg from live GitHub data.

Usage: GH_TOKEN=... python scripts/build_scouting_report.py <username>
Requires only the standard library.
"""
import json, os, sys, collections, urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "https-shubhamsahu"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

QUERY = """
{ user(login:"%s"){
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      totalCount
      nodes{ stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{name color} } } }
    }
    contributionsCollection{ totalCommitContributions totalPullRequestContributions }
    followers{ totalCount }
} }""" % USER


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": "bearer " + TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def build(d):
    repos, contrib = d["repositories"], d["contributionsCollection"]
    lang = collections.Counter()
    for n in repos["nodes"]:
        for e in n["languages"]["edges"]:
            lang[(e["node"]["name"], e["node"]["color"] or "#6366f1")] += e["size"]
    total = sum(lang.values()) or 1
    langs = [{"name": k[0], "color": k[1], "pct": round(v * 100 / total, 1)}
             for k, v in lang.most_common(5)]
    stats = [("REPOS", repos["totalCount"]),
             ("COMMITS", contrib["totalCommitContributions"]),
             ("PULL REQS", contrib["totalPullRequestContributions"]),
             ("FOLLOWERS", d["followers"]["totalCount"])]

    alt = ("Scouting report: %d repositories, %d commits, %d pull requests, %d followers. "
           "Language proficiency: %s." % (
               repos["totalCount"], contrib["totalCommitContributions"],
               contrib["totalPullRequestContributions"], d["followers"]["totalCount"],
               ", ".join("%s %s%%" % (l["name"], l["pct"]) for l in langs)))

    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="250" '
         'viewBox="0 0 480 250" role="img" aria-label="%s">' % alt]
    p.append('''<style>
 @keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
 @keyframes gw{from{transform:scaleX(0)}to{transform:scaleX(1)}}
 @keyframes pu{0%,100%{opacity:.35}50%{opacity:.9}}
 .hd{font:700 15px "Segoe UI",sans-serif;fill:#e6edf3;animation:fi .5s ease-out both}
 .sb{font:600 9px "Segoe UI",sans-serif;fill:#6366f1;letter-spacing:2.2px;animation:fi .5s .1s ease-out both}
 .num{font:700 22px "Segoe UI",sans-serif;fill:#e6edf3}
 .lbl{font:600 8px "Segoe UI",sans-serif;fill:#7d8590;letter-spacing:1.3px}
 .ln{font:600 10px "Segoe UI",sans-serif;fill:#c9d1d9}
 .pc{font:600 9px "Segoe UI",sans-serif;fill:#7d8590}
 .bar{transform-origin:left center;animation:gw .9s cubic-bezier(.2,.8,.2,1) both}
 .st{animation:fi .55s ease-out both}
 .dot{animation:pu 2.4s ease-in-out infinite}
</style>''')
    p.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
             '<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#131a2e"/></linearGradient></defs>')
    p.append('<rect width="480" height="250" rx="10" fill="url(#bg)" stroke="#232b3d"/>')
    p.append('<rect x="0" y="0" width="3.5" height="250" rx="2" fill="#6366f1"/>')
    p.append('<circle class="dot" cx="454" cy="26" r="3.5" fill="#6366f1"/>')
    p.append('<text class="sb" x="26" y="26">SCOUTING REPORT</text>')
    p.append('<text class="hd" x="26" y="47">Shubham Sahu \u00b7 Striker No. 01</text>')
    p.append('<line x1="26" y1="60" x2="454" y2="60" stroke="#232b3d"/>')
    for i, (lb, v) in enumerate(stats):
        x = 26 + i * 109
        p.append('<g class="st" style="animation-delay:%.2fs">' % (.15 + i * .08))
        p.append('<text class="num" x="%d" y="90">%s</text>'
                 '<text class="lbl" x="%d" y="105">%s</text></g>' % (x, v, x, lb))
    p.append('<line x1="26" y1="122" x2="454" y2="122" stroke="#232b3d"/>')
    p.append('<text class="sb" x="26" y="141">WEAPON PROFICIENCY</text>')
    for i, l in enumerate(langs):
        y = 158 + i * 18
        w = max(3, round(l["pct"] / 100 * 250))
        p.append('<text class="ln" x="26" y="%d">%s</text>' % (y + 4, l["name"]))
        p.append('<rect x="140" y="%d" width="250" height="6" rx="3" fill="#1c2333"/>' % (y - 4))
        p.append('<rect class="bar" x="140" y="%d" width="%d" height="6" rx="3" fill="%s" '
                 'style="animation-delay:%.2fs"/>' % (y - 4, w, l["color"], .4 + i * .1))
        p.append('<text class="pc" x="400" y="%d">%s%%</text>' % (y + 4, l["pct"]))
    p.append('</svg>')
    return "\n".join(p)


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GH_TOKEN or GITHUB_TOKEN required")
    os.makedirs("assets", exist_ok=True)
    with open("assets/scouting-report.svg", "w", encoding="utf-8") as f:
        f.write(build(fetch()))
    print("wrote assets/scouting-report.svg")
