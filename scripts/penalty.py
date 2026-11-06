#!/usr/bin/env python3
"""Penalty shootout for the profile README.

A visitor opens an issue titled "penalty|left", "penalty|center" or "penalty|right".
`play` takes every open penalty issue, rolls the keeper, and rewrites the board, the
data file and the README section. `reply` (run after the push) comments and closes
the issues. `render` only rebuilds the board and README section from the data file.

Usage: GH_TOKEN=... GITHUB_REPOSITORY=owner/repo python scripts/penalty.py play|reply|render
Requires only the standard library.
"""
import datetime, json, os, random, re, sys, urllib.request
from xml.sax.saxutils import escape

DATA = "data/penalty.json"
BOARD = "assets/readme/penalty.svg"
README = "README.md"
REPLIES = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "penalty-replies.json")
REPO = os.environ.get("GITHUB_REPOSITORY", "https-shubhamsahu/https-shubhamsahu")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
TITLE = re.compile(r"^\s*penalty\s*\|\s*(left|center|centre|right)\s*$", re.I)
SIDES = ("left", "center", "right")

BG, LINE, FG, MUTED, ACCENT, WHITE, INK = (
    "#090C14", "#1A2133", "#F2F4F8", "#8B93A7", "#6366F1", "#E8ECF4", "#0B0F18")
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r) if r.status != 204 else None


def load():
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    return {"totals": {"shots": 0, "goals": 0, "saves": 0}, "scorers": {}, "last_day": {}, "recent": []}


def play():
    data, replies = load(), []
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    issues = api("GET", f"/repos/{REPO}/issues?state=open&per_page=100&sort=created&direction=asc")
    for issue in issues:
        if "pull_request" in issue or not issue["title"].lower().lstrip().startswith("penalty"):
            continue
        login, number = issue["user"]["login"], issue["number"]
        match = TITLE.match(issue["title"])
        if not match:
            replies.append((number, "not_planned", "That title isn't a shot. Use one of the shoot links on the profile."))
            continue
        if data["last_day"].get(login) == today:
            replies.append((number, "not_planned", "You already took today's penalty. Come back tomorrow (UTC)."))
            continue
        side = "center" if match.group(1).lower() == "centre" else match.group(1).lower()
        keeper = random.SystemRandom().choice(SIDES)
        goal = keeper != side
        data["last_day"][login] = today
        data["totals"]["shots"] += 1
        data["totals"]["goals" if goal else "saves"] += 1
        if goal:
            data["scorers"][login] = data["scorers"].get(login, 0) + 1
        data["recent"] = ([{"by": login, "side": side, "keeper": keeper, "goal": goal, "issue": number}]
                          + data["recent"])[:10]
        verdict = "GOAL!" if goal else "Saved."
        replies.append((number, "completed",
                        f"{verdict} You went {side}, the keeper went {keeper}. "
                        f"Your shot is on the board: https://github.com/{REPO.split('/')[0]}"))
    # Keep only today's entries so the file doesn't grow forever.
    data["last_day"] = {k: v for k, v in data["last_day"].items() if v == today}
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    with open(REPLIES, "w", encoding="utf-8") as f:
        json.dump(replies, f)
    render(data)
    print(f"processed {len(replies)} issue(s)")


def reply():
    if not os.path.exists(REPLIES):
        return
    with open(REPLIES, encoding="utf-8") as f:
        for number, reason, text in json.load(f):
            api("POST", f"/repos/{REPO}/issues/{number}/comments", {"body": text})
            api("PATCH", f"/repos/{REPO}/issues/{number}", {"state": "closed", "state_reason": reason})


def keeper_pose(side):
    # Rotate about the keeper's centre (370, 225) so the gloves land on the shot target.
    return {"left": "translate(-81px, -15px) rotate(-60deg)",
            "right": "translate(81px, -15px) rotate(60deg)",
            "center": "translate(0px, 0px) rotate(0deg)"}[side]


TARGET_X = {"left": 220, "center": 370, "right": 520}


def board(data):
    last = data["recent"][0] if data["recent"] else {"by": None, "side": "left", "keeper": "right", "goal": True}
    side, keeper, goal = last["side"], last["keeper"], last["goal"]
    tx, ty, r = TARGET_X[side], 170, 12
    sx, sy, s0 = 370, 420, 2.0
    if last["by"]:
        who = "@" + last["by"][:20]
        line = f"went {side} · keeper went {keeper}"
    else:
        who, line = "No shots yet", "Demo: shot left, keeper went right"
    result, rcolor = ("GOAL", ACCENT) if goal else ("SAVED", FG)
    t = data["totals"]
    top = sorted(data["scorers"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    scorers = "".join(
        f'<text class="row" x="760" y="{388 + i * 30}">{i + 1}  @{escape(n[:20])}</text>'
        f'<text class="row" x="1150" y="{388 + i * 30}" text-anchor="end">{g}</text>'
        for i, (n, g) in enumerate(top)) or f'<text class="row" x="760" y="388" style="fill:{MUTED}">Nobody has scored yet</text>'
    net = "".join(f"M{x} 70V300" for x in range(150, 600, 30)) + "".join(f"M120 {y}H620" for y in range(96, 300, 26))
    frames = []
    steps = 8
    for i in range(1, steps + 1):
        k = 1 - (1 - i / steps) ** 2
        x = (1 - k) ** 2 * (sx - tx) + 2 * (1 - k) * k * (sx - tx) * 0.2
        y = (1 - k) ** 2 * (sy - ty) + 2 * (1 - k) * k * (sy - ty) * 0.5
        frames.append(f"{15 + 18 * i / steps:.2f}% {{ transform: translate({x:.1f}px, {y:.1f}px) scale({s0 + (1 - s0) * k:.3f}); opacity: 1; }}")
    start = f"translate({sx - tx}px, {sy - ty}px) scale({s0})"
    alt = (f"Penalty board. Last shot: {who} went {side}, the keeper went {keeper}: {result.lower()}. "
           f"{t['shots']} shots, {t['goals']} goals, {t['saves']} saves.") if last["by"] else \
          "Penalty board. No shots yet. Demo: a shot to the left beats a keeper diving right."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="480" viewBox="0 0 1200 480" role="img" aria-labelledby="t d">
<title id="t">Penalty shootout</title>
<desc id="d">{escape(alt)}</desc>
<style>
  .lbl {{ font: 600 17px {MONO}; fill: {MUTED}; letter-spacing: 3px; }}
  .who {{ font: 800 32px {SANS}; fill: {FG}; }}
  .sub {{ font: 400 21px {SANS}; fill: {MUTED}; }}
  .res {{ font: 900 60px {SANS}; letter-spacing: 6px; }}
  .num {{ font: 800 36px {SANS}; fill: {FG}; }}
  .row {{ font: 600 20px {MONO}; fill: {FG}; }}
  .zone {{ font: 700 16px {MONO}; fill: #3A4463; letter-spacing: 3px; }}
  .ball, .keeper, .res, .net {{ animation-duration: 5s; animation-iteration-count: infinite; animation-timing-function: linear; }}
  .ball {{ transform-box: fill-box; transform-origin: center; animation-name: shot; }}
  .keeper {{ transform-box: view-box; transform-origin: 370px 225px; transform: {keeper_pose(keeper)}; animation-name: dive; animation-timing-function: ease-out; }}
  .res {{ animation-name: res; }}
  .net {{ transform-box: fill-box; transform-origin: {(tx - 120) / 5:.0f}% 40%; animation-name: {"bulge" if goal else "none"}; }}
  @keyframes shot {{ 0%, 15% {{ transform: {start}; opacity: 1; }} {" ".join(frames)}
    88% {{ transform: translate(0px, 0px) scale(1); opacity: 1; }} 92% {{ transform: translate(0px, 0px) scale(1); opacity: 0; }}
    94% {{ transform: {start}; opacity: 0; }} 97%, 100% {{ transform: {start}; opacity: 1; }} }}
  @keyframes dive {{ 0%, 17% {{ transform: translate(0px, 0px) rotate(0deg); }} 31%, 88% {{ transform: {keeper_pose(keeper)}; }}
    96%, 100% {{ transform: translate(0px, 0px) rotate(0deg); }} }}
  @keyframes res {{ 0%, 33.9% {{ opacity: 0; }} 34%, 88% {{ opacity: 1; }} 92%, 100% {{ opacity: 0; }} }}
  @keyframes bulge {{ 0%, 33% {{ transform: scale(1); }} 35% {{ transform: scale(1.03); }} 41%, 100% {{ transform: scale(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<rect width="1200" height="480" rx="24" fill="{BG}"/>
<path d="M60 300H680M150 300L118 360H622L590 300" stroke="{LINE}" stroke-width="2" fill="none"/>
<path class="net" d="{net}" stroke="#1F2840" stroke-width="2" fill="none"/>
<text class="zone" x="220" y="338" text-anchor="middle">LEFT</text>
<text class="zone" x="370" y="338" text-anchor="middle">CENTER</text>
<text class="zone" x="520" y="338" text-anchor="middle">RIGHT</text>
<path d="M120 300V70H620V300" stroke="{WHITE}" stroke-width="8" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
<g class="ball"><circle cx="{tx}" cy="{ty}" r="{r}" fill="{FG}" stroke="{INK}" stroke-width="1.5"/><circle cx="{tx}" cy="{ty}" r="4.5" fill="{INK}"/></g>
<g class="keeper">
  <rect x="356" y="262" width="11" height="38" rx="5" fill="#2D3352"/><rect x="373" y="262" width="11" height="38" rx="5" fill="#2D3352"/>
  <rect x="350" y="200" width="40" height="68" rx="14" fill="{ACCENT}"/>
  <path d="M356 210L340 160M384 210L400 160" stroke="{ACCENT}" stroke-width="10" stroke-linecap="round"/>
  <circle cx="338" cy="152" r="11" fill="{WHITE}"/><circle cx="402" cy="152" r="11" fill="{WHITE}"/>
  <circle cx="370" cy="184" r="16" fill="#2D3352"/>
</g>
<text class="lbl" x="760" y="76">LAST SHOT</text>
<text class="who" x="760" y="116">{escape(who)}</text>
<text class="sub" x="760" y="150">{escape(line)}</text>
<text class="res" x="756" y="224" style="fill:{rcolor}">{result}</text>
<path d="M760 252H1150" stroke="{LINE}" stroke-width="2"/>
<text class="num" x="760" y="300">{t['shots']}</text><text class="lbl" x="760" y="326">SHOTS</text>
<text class="num" x="900" y="300">{t['goals']}</text><text class="lbl" x="900" y="326">GOALS</text>
<text class="num" x="1040" y="300">{t['saves']}</text><text class="lbl" x="1040" y="326">SAVES</text>
<text class="lbl" x="760" y="362" style="font-size:15px">TOP SCORERS</text>
{scorers}
</svg>
"""


def section(data):
    t = data["totals"]
    lines = [f"**{t['goals']} goals and {t['saves']} saves from {t['shots']} shots.**"]
    if data["recent"]:
        last = data["recent"][0]
        lines.append(f"Last shot: [{last['by']}](https://github.com/{last['by']}) went {last['side']}, "
                     f"the keeper went {last['keeper']}. {'Goal.' if last['goal'] else 'Saved.'}")
    top = sorted(data["scorers"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top:
        lines.append("Top scorers: " + " · ".join(f"[{n}](https://github.com/{n}) ({g})" for n, g in top))
    return "\n\n".join(lines)


def render(data=None):
    data = data or load()
    os.makedirs(os.path.dirname(BOARD), exist_ok=True)
    with open(BOARD, "w", encoding="utf-8") as f:
        f.write(board(data))
    with open(README, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"(<!-- penalty:start -->\n).*?(<!-- penalty:end -->)",
                  lambda m: m.group(1) + section(data) + "\n" + m.group(2), text, flags=re.S)
    with open(README, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd in ("play", "reply") and not TOKEN:
        sys.exit("GH_TOKEN or GITHUB_TOKEN required")
    {"play": play, "reply": reply, "render": render}[cmd]()
