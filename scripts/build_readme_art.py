#!/usr/bin/env python3
"""Build the static README art: hero.svg, trophies.svg and loadout.svg.

Usage: python scripts/build_readme_art.py
Requires Pillow (sprites are cleaned and embedded so the SVGs stay self-contained).
"""
import base64, io, math, os
from xml.sax.saxutils import escape

from PIL import Image

OUT = "assets/readme"
BG, LINE, FG, MUTED, ACCENT, WHITE, INK = (
    "#090C14", "#1A2133", "#F2F4F8", "#8B93A7", "#6366F1", "#E8ECF4", "#0B0F18")
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
REDUCED = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def sprite(name):
    """Return (width, height, data URI) for a striker sprite with its green key fringe removed."""
    im = Image.open(f"assets/{name}.png").convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and g > r + 25 and g > b + 25:
                px[x, y] = (20, 22, 31, a)
    buf = io.BytesIO()
    im.quantize(colors=128, method=Image.Quantize.FASTOCTREE).save(buf, "PNG", optimize=True)
    return im.width, im.height, "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def ball(cx, cy, r):
    """A football drawn at (cx, cy)."""
    pts = []
    for i in range(5):
        a = math.radians(-90 + i * 72)
        pts.append(f"{cx + r * 0.42 * math.cos(a):.1f},{cy + r * 0.42 * math.sin(a):.1f}")
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{FG}" stroke="{INK}" stroke-width="1.5"/>'
            f'<polygon points="{" ".join(pts)}" fill="{INK}"/>')


def goal_frame(left, right, top, ground, step_x=30, step_y=27):
    net = []
    x = left + step_x
    while x < right:
        net.append(f"M{x} {top}V{ground}")
        x += step_x
    y = top + step_y
    while y < ground:
        net.append(f"M{left} {y}H{right}")
        y += step_y
    return (f'<path class="net" d="{"".join(net)}" stroke="#1F2840" stroke-width="2" fill="none"/>'
            f'<path d="M{left} {ground}V{top}H{right}V{ground}" stroke="{WHITE}" stroke-width="8" '
            f'fill="none" stroke-linejoin="round" stroke-linecap="round"/>')


def flight_keyframes(name, dx, dy, s0, start, end, ctrl=(0.15, 0.55)):
    """Ball flight from offset (dx, dy) at scale s0 to (0, 0) at scale 1, along a curve, ease-out."""
    frames = [f"0%, {start}% {{ transform: translate({dx}px, {dy}px) scale({s0}); opacity: 1; }}"]
    steps = 8
    for i in range(1, steps + 1):
        t = 1 - (1 - i / steps) ** 2            # ease-out spacing
        cx, cy = dx * ctrl[0], dy * ctrl[1]     # quadratic control point, bends the shot
        x = (1 - t) ** 2 * dx + 2 * (1 - t) * t * cx
        y = (1 - t) ** 2 * dy + 2 * (1 - t) * t * cy
        s = s0 + (1 - s0) * t
        pct = start + (end - start) * i / steps
        frames.append(f"{pct:.2f}% {{ transform: translate({x:.1f}px, {y:.1f}px) scale({s:.3f}); opacity: 1; }}")
    frames.append(f"88% {{ transform: translate(0px, 0px) scale(1); opacity: 1; }}")
    frames.append(f"92% {{ transform: translate(0px, 0px) scale(1); opacity: 0; }}")
    frames.append(f"94% {{ transform: translate({dx}px, {dy}px) scale({s0}); opacity: 0; }}")
    frames.append(f"97%, 100% {{ transform: translate({dx}px, {dy}px) scale({s0}); opacity: 1; }}")
    return f"@keyframes {name} {{ {' '.join(frames)} }}"


def hero():
    w8, h8, focus = sprite("striker-pose8")
    w7, h7, cheer = sprite("striker-pose7")
    bx, by, br = 838, 104, 13          # where the ball settles: top-left corner of the net
    sx, sy, s0 = 970, 372, 2.0         # penalty spot, seen close up
    css = f"""
  .meta {{ font: 600 18px {MONO}; fill: {MUTED}; letter-spacing: 3px; }}
  .name {{ font: 800 66px {SANS}; fill: {FG}; }}
  .l1 {{ font: 600 24px {SANS}; fill: {FG}; }}
  .l2 {{ font: 400 22px {SANS}; fill: {MUTED}; }}
  .team {{ font: 800 19px {SANS}; fill: {FG}; letter-spacing: 1px; }}
  .score {{ font: 800 26px {MONO}; fill: {FG}; }}
  .goal {{ font: 900 64px {SANS}; fill: {ACCENT}; letter-spacing: 8px; }}
  .ball, .net, .goal, .s0, .s1, .focus, .cheer {{
    animation-duration: 6s; animation-iteration-count: infinite; animation-timing-function: linear;
  }}
  .ball {{ transform-box: fill-box; transform-origin: center; animation-name: shot; }}
  .net {{ transform-box: fill-box; transform-origin: 8% 8%; animation-name: bulge; animation-timing-function: ease-out; }}
  .goal {{ animation-name: on; }}
  .s1 {{ animation-name: on; }}
  .s0 {{ opacity: 0; animation-name: off; }}
  .cheer {{ animation-name: on; }}
  .focus {{ opacity: 0; animation-name: off; }}
  {flight_keyframes("shot", sx - bx, sy - by, s0, 12, 28)}
  @keyframes bulge {{ 0%, 28% {{ transform: scale(1); }} 30% {{ transform: scale(1.025); }} 36%, 100% {{ transform: scale(1); }} }}
  @keyframes on {{ 0%, 28.9% {{ opacity: 0; }} 29%, 88% {{ opacity: 1; }} 92%, 100% {{ opacity: 0; }} }}
  @keyframes off {{ 0%, 28.9% {{ opacity: 1; }} 29%, 93.9% {{ opacity: 0; }} 94%, 100% {{ opacity: 1; }} }}
  {REDUCED}
"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400" viewBox="0 0 1200 400" role="img" aria-labelledby="t d">
<title id="t">Shubham Sahu, founder of NO SUS</title>
<desc id="d">Shubham Sahu, Striker No. 01 from Mumbai. Founder of NO SUS and co-founder of Aurigen. A chibi striker watches a shot fly into the top corner and the scoreboard reads NO SUS 1, LEAKS 0.</desc>
<style>{css}</style>
<rect width="1200" height="400" rx="24" fill="{BG}"/>
<g id="pitch" stroke="{LINE}" stroke-width="2" fill="none">
  <path d="M700 250H1180"/>
  <path d="M850 250L822 300H1118L1090 250"/>
</g>
<ellipse cx="{sx}" cy="{sy - 18}" rx="8" ry="3" fill="#2A3350"/>
{goal_frame(790, 1150, 60, 250)}
<text class="goal" x="970" y="196" text-anchor="middle">GOAL</text>
<g class="ball">{ball(bx, by, br)}</g>
<g id="player">
  <image class="focus" x="56" y="122" width="{w8}" height="{h8}" href="{focus}"/>
  <image class="cheer" x="56" y="122" width="{w7}" height="{h7}" href="{cheer}"/>
</g>
<g id="title">
  <text class="meta" x="196" y="128">STRIKER NO. 01 · MUMBAI</text>
  <text class="name" x="193" y="200">Shubham Sahu</text>
  <text class="l1" x="196" y="246">Founder of NO SUS. Co-founder of Aurigen.</text>
  <text class="l2" x="196" y="282">I build rovers, firmware and apps that ship.</text>
</g>
<g id="scoreboard">
  <rect x="196" y="310" width="340" height="50" rx="12" fill="#0E1322" stroke="#262F45" stroke-width="2"/>
  <text class="team" x="216" y="342">NO SUS</text>
  <text class="score s1" x="352" y="344" text-anchor="middle">1</text>
  <text class="score s0" x="352" y="344" text-anchor="middle">0</text>
  <text class="score" x="378" y="344" text-anchor="middle">:</text>
  <text class="score" x="404" y="344" text-anchor="middle">0</text>
  <text class="team" x="516" y="342" text-anchor="end" fill="{MUTED}" style="fill:{MUTED}">LEAKS</text>
</g>
</svg>
"""


TROPHIES = [
    # (date, event, project line, result, style)
    ("MAR 2026", "Lovable × Anthropic Buildathon", "CareProof: verified credit for unpaid caregiving", "WINNER", "fill"),
    ("SEP 2026", "Monad Blitz Mumbai V4", "NO SUS Canary: leak tracing with Solana receipts", "2ND PLACE", "outline"),
    ("", "M-Indicator AI Hackathon", "M-Indicator 2.0: a mobile-first redesign for Mumbai commuters", "TOP 10", "outline"),
    ("JUL 2026", "Automation Expo", "Niva: smart insole with explainable gait analytics", "SHOWCASED", "muted"),
    ("2026", "India Innovates", "New Delhi", "PRESENTED", "muted"),
]


def trophies():
    row_h, top = 72, 24
    height = top * 2 + row_h * len(TROPHIES)
    rows, frames, classes = [], [], []
    for i, (date, event, project, result, style) in enumerate(TROPHIES):
        y = top + i * row_h
        start, end = 6 + i * 12, 34 + i * 12
        frames.append(f"@keyframes r{i} {{ 0%, {start}% {{ opacity: 0; transform: translateX(-18px); }} "
                      f"{end}%, 100% {{ opacity: 1; transform: translateX(0px); }} }}")
        classes.append(f".r{i} {{ animation: r{i} 1.6s ease-out 1 both; }}")
        if style == "fill":
            chip = (f'<rect x="968" y="{y + 16}" width="184" height="40" rx="20" fill="{ACCENT}"/>'
                    f'<text class="chip" x="1060" y="{y + 42}" text-anchor="middle" style="fill:{BG}">{result}</text>')
        elif style == "outline":
            chip = (f'<rect x="969" y="{y + 17}" width="182" height="38" rx="19" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
                    f'<text class="chip" x="1060" y="{y + 42}" text-anchor="middle" style="fill:{ACCENT}">{result}</text>')
        else:
            chip = (f'<rect x="969" y="{y + 17}" width="182" height="38" rx="19" fill="none" stroke="#2A3350" stroke-width="2"/>'
                    f'<text class="chip" x="1060" y="{y + 42}" text-anchor="middle" style="fill:{MUTED}">{result}</text>')
        rule = "" if i == 0 else f'<path d="M48 {y}H1152" stroke="{LINE}" stroke-width="2"/>'
        rows.append(f"""{rule}<g class="r{i}">
  <text class="date" x="48" y="{y + 44}">{escape(date)}</text>
  <text class="event" x="210" y="{y + 32}">{escape(event)}</text>
  <text class="proj" x="210" y="{y + 58}">{escape(project)}</text>
  {chip}
</g>""")
    alt = "; ".join(f"{r[3].title()}, {r[1]}{', ' + r[0].title() if r[0] else ''}: {r[2]}" for r in TROPHIES)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="t d">
<title id="t">Match record</title>
<desc id="d">{escape(alt)}</desc>
<style>
  .date {{ font: 600 18px {MONO}; fill: {MUTED}; letter-spacing: 2px; }}
  .event {{ font: 700 26px {SANS}; fill: {FG}; }}
  .proj {{ font: 400 20px {SANS}; fill: {MUTED}; }}
  .chip {{ font: 800 17px {MONO}; letter-spacing: 2px; }}
  {" ".join(classes)}
  {" ".join(frames)}
  {REDUCED}
</style>
<rect width="1200" height="{height}" rx="24" fill="{BG}"/>
{"".join(rows)}
</svg>
"""


LOADOUT = [
    ("Hardware", ["ESP32", "Arduino", "C / C++", "CAD"]),
    ("Apps", ["Flutter + Dart", "TypeScript", "React"]),
    ("Backend + AI", ["Python", "Supabase", "Cloudflare", "Ollama"]),
    ("Video in code", ["HyperFrames", "GSAP"]),
]


def loadout():
    col_w, x0 = 276, 48
    parts = []
    for c, (title, items) in enumerate(LOADOUT):
        x = x0 + c * col_w
        parts.append(f'<path d="M{x} 40H{x + 36}" stroke="{ACCENT}" stroke-width="4" stroke-linecap="round"/>')
        parts.append(f'<text class="h" x="{x}" y="78">{escape(title)}</text>')
        for i, item in enumerate(items):
            y = 100 + i * 50
            w = round(len(item) * 10.6 + 36)
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="38" rx="10" fill="#0E1322" stroke="#262F45" stroke-width="2"/>'
                         f'<text class="i" x="{x + 18}" y="{y + 25}">{escape(item)}</text>')
    alt = ". ".join(f"{t}: {', '.join(i)}" for t, i in LOADOUT)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="320" viewBox="0 0 1200 320" role="img" aria-labelledby="t d">
<title id="t">Loadout</title>
<desc id="d">{escape(alt)}</desc>
<style>
  .h {{ font: 700 24px {SANS}; fill: {FG}; }}
  .i {{ font: 600 18px {MONO}; fill: #C9D1E3; }}
</style>
<rect width="1200" height="320" rx="24" fill="{BG}"/>
{"".join(parts)}
</svg>
"""


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, build in (("hero", hero), ("trophies", trophies), ("loadout", loadout)):
        path = f"{OUT}/{name}.svg"
        with open(path, "w", encoding="utf-8") as f:
            f.write(build())
        print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")
