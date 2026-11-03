#!/usr/bin/env python3
"""Explainer Reel builder.

Turns a JSON spec (script, footage, on-screen text, sound cues, brand) into a
1080x1920 short-form education video with an offline AI voice, animated
captions, motion-graphic overlays, a mixed and loudness-normalised soundtrack,
and a crop-safe cover image.

Usage:
    python3 reel.py SPEC.json                 # full render
    python3 reel.py SPEC.json --stills s.jpg  # contact sheet, one still per scene
    python3 reel.py SPEC.json --cover c.jpg   # cover + crop preview
    python3 reel.py SPEC.json --only s3,s4    # re-render some scenes, then assemble

Paths inside the spec are relative to the spec file.
Needs: ffmpeg, numpy, pillow, scipy, kokoro-onnx, soundfile (see setup_assets.sh).
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("spec")
ap.add_argument("--stills", help="write a contact sheet instead of rendering")
ap.add_argument("--only", help="comma-separated scene ids to re-render")
ap.add_argument("--cover", help="write a cover image instead of rendering")
ap.add_argument("--assets", default=os.environ.get("REEL_ASSETS", os.path.expanduser("~/.explainer-reel-assets")))
A = ap.parse_args()

SPEC = json.load(open(A.spec, encoding="utf-8"))
BASE = os.path.dirname(os.path.abspath(A.spec))
AS = A.assets
WORK = os.path.join(BASE, "build_" + SPEC["slug"])
os.makedirs(WORK, exist_ok=True)


def P(p):
    return p if os.path.isabs(p) else os.path.join(BASE, p)


# ---------------------------------------------------------------- brand
W, H, FPS, SR = 1080, 1920, 30, 48000
BRAND = SPEC.get("brand", {})


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


COL = {"bg": "#0D241B", "bg2": "#163628", "text": "#F4EEE2", "accent": "#CDAC70", "card": "#FAF7F0"}
COL.update(BRAND.get("colors", {}))
BG1, BG2, TEXT, ACCENT, CARD = (hexrgb(COL[k]) for k in ("bg", "bg2", "text", "accent", "card"))
SERIES = BRAND.get("series", "EXPLAINS").upper()
EPISODE = SPEC.get("episode")


def font_path(name):
    for d in (os.path.join(AS, "fonts"), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter"):
        for ext in (".ttf", ".otf"):
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
    sys.exit(f"Font {name} not found. Run setup_assets.sh first.")


FONTS = BRAND.get("fonts", {})
SER = P(FONTS["serif"]) if "serif" in FONTS else font_path("DMSerifDisplay-Regular")
SERI = P(FONTS["serif_italic"]) if "serif_italic" in FONTS else font_path("DMSerifDisplay-Italic")
SANS = {w: font_path(f"Inter-{w}") for w in ("Medium", "SemiBold")}

SC = SPEC["scenes"]
ORDER = [s["id"] for s in SC]
S = {s["id"]: s for s in SC}

# ---------------------------------------------------------------- 1. voice
VO_IN = 0.15  # seconds of silence before each scene's voice line
D = {}        # scene id -> voice duration in seconds


def voice():
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = None
    for s in SC:
        out = f"{WORK}/{s['id']}.wav"
        meta = out + ".txt"
        key = f"{SPEC.get('voice', 'af_heart')}|{SPEC.get('speed', 1.08)}|{s['vo']}"
        if not (os.path.exists(out) and open(meta, encoding="utf-8").read() == key):
            k = k or Kokoro(f"{AS}/kokoro/kokoro-v1.0.onnx", f"{AS}/kokoro/voices-v1.0.bin")
            a, sr = k.create(s["vo"], voice=SPEC.get("voice", "af_heart"), speed=SPEC.get("speed", 1.08), lang=SPEC.get("lang", "en-us"))
            sf.write(out, a, sr)
            open(meta, "w", encoding="utf-8").write(key)
        info = sf.info(out)
        D[s["id"]] = info.frames / info.samplerate


voice()
DUR = {k: round((D[k] + VO_IN + S[k].get("pad", 0.5)) * FPS) / FPS for k in ORDER}
START, t = {}, 0
for k in ORDER:
    START[k] = t
    t += DUR[k]
TOTAL = t

# ---------------------------------------------------------------- 2. picture helpers
_fc = {}


def F(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


def sans(w, s):
    return F(SANS[w], s)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(t):   # ease-out quart
    t = clamp(t)
    return 1 - (1 - t) ** 4


def eio(t):  # smoothstep
    t = clamp(t)
    return t * t * (3 - 2 * t)


# background: vertical gradient with vignette
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = (yy / H)[..., None]
base = np.array(BG2) * (1 - g) + np.array(BG1) * g
vig = 1 - 0.45 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)[..., None]
BG = Image.fromarray((base * vig).clip(0, 255).astype(np.uint8))
del yy, xx

rng = np.random.default_rng(1)
GRAIN = [rng.normal(0, 7, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]


def grain(im, i):
    a = np.asarray(im).astype(np.float32) + np.repeat(np.repeat(GRAIN[i % 6], 2, 0), 2, 1)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def load_logo():
    if not BRAND.get("logo"):
        return None
    im = Image.open(P(BRAND["logo"]))
    if im.mode in ("RGBA", "LA"):
        return im.convert("RGBA")
    # flat image: trim the white margin around the mark
    im = im.convert("RGB")
    arr = np.asarray(im).copy()
    arr[:8] = arr[-8:] = 255
    arr[:, :8] = arr[:, -8:] = 255
    ys, xs = np.where(arr.min(axis=2) < 200)
    if len(xs):
        im = im.crop((max(0, xs.min() - 10), max(0, ys.min() - 10), xs.max() + 10, ys.max() + 10))
    return im.convert("RGBA")


LOGO = load_logo()

# footage sits in a feathered band, leaving room for headline above and captions below
FY0, FH = 400, 1100
fm = np.ones((FH, W), np.float32)
fm[:160] *= np.linspace(0, 1, 160)[:, None] ** 1.5
fm[-260:] *= np.linspace(1, 0, 260)[:, None] ** 1.5
FMASK = Image.fromarray((fm * 255).astype(np.uint8))


def probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", f], capture_output=True, text=True)
    w, h = map(int, r.stdout.strip().split(",")[:2])
    return w, h


def read_frames(f, start, n):
    """Decode n frames at 30 fps from video or still image f, starting at `start` seconds."""
    w, h = probe(f)
    sw = 1280 if w >= h else 720
    sh = int(round(h * sw / w / 2)) * 2
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-i", f, "-frames:v", str(n),
                        "-vf", f"fps=30,scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, sh, sw, 3)
    if len(a) < n:  # stills and short clips: hold the last frame
        a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a


def grade(img, dim=0.0):
    """Gentle S-curve, slight desaturation and warm tint."""
    a = np.asarray(img).astype(np.float32) / 255
    a = a * a * (3 - 2 * a) * 0.35 + a * 0.65
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * 0.88
    a *= np.array(BRAND.get("tint", [1.03, 1.0, 0.94]))
    a *= (1 - dim)
    return Image.fromarray((a * 255).clip(0, 255).astype(np.uint8))


def footage(im, fr, t, dur, dim=0.0, fx=0.5, fit=False):
    img = Image.fromarray(fr)
    ih, iw = fr.shape[:2]
    z = 1.0 + 0.06 * (t / dur)  # slow push-in
    s = (FH / ih if fit else max(W / iw, FH / ih)) * z
    r = img.resize((int(iw * s), int(ih * s)), Image.BICUBIC)
    if r.width < W:  # fit mode: blurred fill behind the frame
        bg = r.resize((W, FH)).filter(ImageFilter.GaussianBlur(30))
        bg = Image.blend(bg, Image.new("RGB", (W, FH), BG1), 0.5)
        cy = (r.height - FH) // 2
        bg.paste(r.crop((0, cy, r.width, cy + FH)), ((W - r.width) // 2, 0))
        r = bg
    else:
        cx = int((r.width - W) * fx)
        cy = (r.height - FH) // 2
        r = r.crop((cx, cy, cx + W, cy + FH))
    if s > 1.4:
        r = r.filter(ImageFilter.UnsharpMask(2, 70, 2))
    im.paste(grade(r, dim), (0, FY0), FMASK)


def tw(d, s, f):
    return d.textlength(s, font=f)


def track_w(d, s, f, sp=6):
    return sum(d.textlength(c, font=f) + sp for c in s) - sp


def tracked(im, text, f, col, alpha, x, y, sp=5):
    """Letter-spaced text with alpha."""
    d = ImageDraw.Draw(im)
    w = track_w(d, text, f, sp)
    lay = Image.new("RGBA", (int(w) + 12, int(f.size * 1.5)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    cx = 0
    for ch in text:
        ld.text((cx, 0), ch, font=f, fill=col + (int(alpha),))
        cx += ld.textlength(ch, font=f) + sp
    im.paste(lay, (int(x), int(y)), lay)
    return w


def header(im, tg, label=None, lt=0):
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, int(W * tg / TOTAL), 4], fill=ACCENT + (255,))  # progress line
    tracked(im, SERIES, sans("Medium", 24), TEXT, 170, 72, 92)
    if EPISODE:
        s = f"No. {EPISODE}"
        fi = F(SERI, 36)
        d.text((W - 72 - tw(d, s, fi), 82), s, font=fi, fill=ACCENT)
    if label:
        a = eo((lt - 0.05) / 0.5)
        d.line([(72, 182), (72 + int(48 * a), 182)], fill=ACCENT, width=2)
        tracked(im, label.upper(), sans("SemiBold", 24), ACCENT, 255 * a, 136, 168)


def reveal_lines(im, t, lines, y=212, size=100, start=0.15, gap=0.14, center=False):
    """Masked line-by-line reveal. lines = [[text, italic_accent], ...]"""
    for i, (s, it) in enumerate(lines):
        p = eo((t - start - i * gap) / 0.6)
        if p <= 0:
            continue
        f = F(SERI if it else SER, size)
        h = int(size * 1.35)
        lay = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        x = (W - tw(ld, s, f)) / 2 if center else 72
        ld.text((x, int((1 - p) * h * 0.9)), s, font=f, fill=(ACCENT if it else TEXT) + (int(255 * min(1, p * 1.3)),))
        im.paste(lay, (0, int(y + i * size * 1.06)), lay)


# ---------------------------------------------------------------- captions
def chunks_for(k):
    """Estimate word timings from character weights and split into caption chunks."""
    words = S[k]["vo"].split()
    skip = S[k].get("caption_skip_words", 0)
    wts = [len(x) + (5 if x[-1] in ".,?!" else 0) + 2 for x in words]
    tot = sum(wts)
    span = D[k] - 0.2
    times, acc = [], 0
    for x in wts:
        times.append(VO_IN + span * acc / tot)
        acc += x
    ch, cur = [], []
    for i, x in enumerate(words):
        if i < skip:
            continue
        cur.append(i)
        if len(" ".join(words[j] for j in cur)) >= 30 or x[-1] in ".?!":
            ch.append(cur)
            cur = []
    if cur:
        ch.append(cur)
    return words, times, ch


CAPS = {k: chunks_for(k) for k in ORDER}


def captions(im, k, t, y=1580):
    words, times, ch = CAPS[k]
    cur = None
    for c in ch:
        if times[c[0]] - 0.05 <= t:
            cur = c
    if cur is None:
        return
    if ch.index(cur) == len(ch) - 1 and t > times[cur[-1]] + 1.4:
        return
    d = ImageDraw.Draw(im, "RGBA")
    f = sans("SemiBold", 50)
    sp = tw(d, " ", f)
    a = eo((t - times[cur[0]] + 0.05) / 0.3)
    lines = [[]]
    for i in cur:
        if tw(d, " ".join(words[j] for j in lines[-1] + [i]), f) > 900 and lines[-1]:
            lines.append([i])
        else:
            lines[-1].append(i)
    for li, ln in enumerate(lines):
        sw = sum(tw(d, words[i], f) for i in ln) + sp * (len(ln) - 1)
        x = (W - sw) / 2
        yl = y + li * 66 + (1 - a) * 14
        for i in ln:
            on = times[i] <= t + 0.03  # words brighten as they are spoken
            d.text((x + 2, yl + 3), words[i], font=f, fill=(0, 0, 0, int(90 * a)))
            d.text((x, yl), words[i], font=f, fill=TEXT + (int((255 if on else 95) * a),))
            x += tw(d, words[i], f) + sp


# ---------------------------------------------------------------- overlays
def ov_kicker(im, t, o):
    a = eo((t - o["start"]) / 0.5)
    if a <= 0:
        return
    d = ImageDraw.Draw(im, "RGBA")
    f = sans("SemiBold", 34)
    s = o["text"].upper()
    w = track_w(d, s, f, 8)
    x = (W - w) / 2
    y = o.get("y", 1600)
    L = int(110 * a)
    d.line([(x - 30 - L, y + 20), (x - 30, y + 20)], fill=ACCENT, width=2)
    d.line([(x + w + 30, y + 20), (x + w + 30 + L, y + 20)], fill=ACCENT, width=2)
    tracked(im, s, f, TEXT, 255 * a, x, y + (1 - a) * 12, 8)


def ov_bignumber(im, t, o):
    a = eo((t - o.get("start", 0.15)) / 0.9)
    if a <= 0:
        return
    d = ImageDraw.Draw(im)
    f = F(SER, int(o.get("size", 560) * (1.06 - 0.06 * a)))
    s = str(o["text"])
    w = tw(d, s, f)
    lay = Image.new("RGBA", (W, 700), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(((W - w) / 2, 0), s, font=f, fill=ACCENT + (int(255 * a),))
    im.paste(lay, (0, o.get("y", 430)), lay)


def ov_measure(im, t, o):
    """Dimension line that draws in while the number counts up."""
    a = eio((t - o.get("start", 1.0)) / 1.4)
    if a <= 0:
        return
    d = ImageDraw.Draw(im, "RGBA")
    y = o.get("y", 1340)
    x0 = 90
    x1 = x0 + int(900 * a)
    for seg in [((x0, y), (x1, y)), ((x0, y - 18), (x0, y + 18)), ((x1, y - 18), (x1, y + 18))]:
        d.line(seg, fill=ACCENT, width=3)
    s = f"{int(o['value'] * a):,}"
    f = F(SER, 84)
    u = sans("Medium", 38)
    unit = o.get("unit", "")
    wv = tw(d, s, f)
    x = (W - wv - 12 - tw(d, unit, u)) / 2
    d.text((x + 2, y - 118), s, font=f, fill=(0, 0, 0, 110))
    d.text((x, y - 120), s, font=f, fill=TEXT)
    d.text((x + wv + 12, y - 66), unit, font=u, fill=ACCENT)


def ov_bullets(im, t, o):
    items, starts = o["items"], o["starts"]
    y0 = o.get("y", 1230)
    shown = [i for i, s in enumerate(starts) if t > s]
    if not shown:
        return
    d = ImageDraw.Draw(im, "RGBA")
    a0 = eo((t - starts[0]) / 0.4)
    wmax = max(tw(d, s, sans("Medium", 38)) for s in items) + 140
    d.rounded_rectangle([60, y0 - 30, 60 + wmax, y0 + len(items) * 74], radius=22, fill=BG1 + (int(190 * a0),))
    for i in shown:
        a = eo((t - starts[i]) / 0.45)
        y = y0 + i * 74
        d.line([(92, y + 28), (92 + int(30 * a), y + 28)], fill=ACCENT, width=3)
        lay = Image.new("RGBA", (900, 60), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((0, 0), items[i], font=sans("Medium", 38), fill=TEXT + (int(255 * a),))
        im.paste(lay, (140 + int((1 - a) * 20), y + 4), lay)


def ov_tag(im, t, o):
    a = eo((t - o.get("start", 1.0)) / 0.5)
    if a <= 0:
        return
    d = ImageDraw.Draw(im)
    y = o.get("y", 1420)
    d.line([(72, y + 14), (72 + int(40 * a), y + 14)], fill=ACCENT, width=2)
    tracked(im, o["text"].upper(), sans("SemiBold", 26), TEXT, 230 * a, 128, y)


def ov_layers(im, t, o):
    """Isometric two-layer diagram (thick base + thin top) with callouts.
    Good for explaining any layered product: boards, mattresses, flooring, packaging."""
    d = ImageDraw.Draw(im, "RGBA")
    cx, base, w, dep = 540, 1080, 620, 230
    bc = hexrgb(o.get("base_color", "#CEB080"))
    tc = hexrgb(o.get("top_color", "#704A2C"))

    def shade(c, k, al):
        return tuple(int(v * k) for v in c) + (al,)

    def slab(y, th, col, al):
        pt = [(cx - w / 2, y), (cx + w / 2, y), (cx + w / 2 + dep * 0.55, y - dep * 0.45), (cx - w / 2 + dep * 0.55, y - dep * 0.45)]
        pf = [(cx - w / 2, y), (cx + w / 2, y), (cx + w / 2, y + th), (cx - w / 2, y + th)]
        ps = [(cx + w / 2, y), (cx + w / 2 + dep * 0.55, y - dep * 0.45), (cx + w / 2 + dep * 0.55, y - dep * 0.45 + th), (cx + w / 2, y + th)]
        d.polygon(pf, fill=shade(col, 0.86, al))
        d.polygon(ps, fill=shade(col, 0.73, al))
        d.polygon(pt, fill=shade(col, 1.0, al))
        return pt, pf

    a = eo((t - 0.2) / 0.8)
    off = (1 - a) * 60
    _, pf = slab(base + off, 110, bc, int(255 * a))
    r = np.random.default_rng(3)
    for _ in range(260):  # speckle texture on the core
        x = r.uniform(pf[0][0] + 8, pf[1][0] - 8)
        y = r.uniform(base + off + 8, base + off + 102)
        d.ellipse([x, y, x + r.uniform(3, 8), y + r.uniform(2, 4)], fill=shade(bc, 0.68, int(200 * a)))
    lt = o.get("layer_at", 2.4)
    b = eio((t - lt) / 0.8)
    top_y = 760 + (base + off - 14 - 760) * b
    if t > lt - 0.2:
        al = int(255 * clamp((t - lt + 0.2) / 0.3))
        pt, _ = slab(top_y, 14, tc, al)
        for kk in range(1, 10):
            fx = kk / 10
            d.line([(pt[0][0] + (pt[1][0] - pt[0][0]) * fx, pt[0][1]), (pt[3][0] + (pt[2][0] - pt[3][0]) * fx, pt[3][1])],
                   fill=shade(tc, 1.15, al), width=2)

    def callout(x0, y0, x1, y1, text, delay, col):
        c = eo((t - delay) / 0.5)
        if c <= 0:
            return
        d.line([(x0, y0), (x0 + (x1 - x0) * c, y0 + (y1 - y0) * c)], fill=ACCENT + (255,), width=2)
        d.ellipse([x0 - 6, y0 - 6, x0 + 6, y0 + 6], fill=ACCENT)
        if c > 0.6:
            d.text((x1 + 14, y1 - 30), text, font=F(SERI, 46), fill=col + (int(255 * (c - 0.6) / 0.4),))

    callout(cx - 180, base + off + 70, 180, base + 270, o.get("base_label", "Core"), o.get("base_at", 1.5), TEXT)
    if t > lt + 1.0:
        callout(cx + 80, top_y - 60, cx + 20, 620, o.get("top_label", "Surface"), lt + 1.1, ACCENT)


def chat_icon(d, cx, cy, r, col):
    """Generic chat bubble (deliberately not any messaging app's logo)."""
    w, h = r * 2.1, r * 1.55
    x0, y0 = cx - w / 2, cy - h / 2 - r * 0.12
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(h * 0.42), fill=col)
    d.polygon([(x0 + w * 0.22, y0 + h - 2), (x0 + w * 0.10, y0 + h + r * 0.42), (x0 + w * 0.42, y0 + h - 2)], fill=col)
    dr = r * 0.15
    for k in (-1, 0, 1):
        ex, ey = cx + k * r * 0.55, y0 + h / 2
        d.ellipse([ex - dr, ey - dr, ex + dr, ey + dr], fill=TEXT + (255,))


def brand_card(cw, ch, alpha):
    """Rounded light card carrying the logo, or the brand name if there is no logo."""
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, fill=CARD + (int(255 * alpha),))
    if LOGO is not None:
        lg = LOGO.copy()
        lg.thumbnail((cw - 120, ch - 80))
        if alpha < 1:
            lg.putalpha(Image.fromarray((np.asarray(lg.getchannel("A")) * alpha).astype(np.uint8)))
        card.paste(lg, ((cw - lg.width) // 2, (ch - lg.height) // 2), lg)
    else:
        name = BRAND.get("name", SERIES)
        f = F(SER, int(ch * 0.36))
        cd.text(((cw - cd.textlength(name, font=f)) / 2, ch * 0.28), name, font=f, fill=BG1 + (int(255 * alpha),))
    return card


def endcard(im, t, o):
    d = ImageDraw.Draw(im, "RGBA")
    a = eo((t - 0.3) / 0.8)
    if a > 0:
        cw, ch = int(700 + 20 * (1 - a)), 230
        card = brand_card(cw, ch, a)
        im.paste(card, ((W - cw) // 2, 380 + int((1 - a) * 20)), card)
    reveal_lines(im, t, [tuple(x) for x in o["headline"]], y=700, size=96, start=0.9)
    c = eo((t - 1.4) / 0.6)
    if c > 0 and o.get("button"):
        bw, bh = 860, 128
        x0 = (W - bw) // 2
        y0 = 1010 + int((1 - c) * 20)
        glow = 0.5 + 0.5 * math.sin((t - 1.4) * 3.2) if t > 2 else 0
        d.rounded_rectangle([x0 - 6, y0 - 6, x0 + bw + 6, y0 + bh + 6], radius=70, outline=ACCENT + (int(120 * glow * c),), width=3)
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=64, fill=TEXT + (int(255 * c),))
        f = sans("SemiBold", 40)
        s = o["button"]
        w = tw(d, s, f)
        if o.get("chat_icon", True):
            chat_icon(d, x0 + 80, y0 + bh // 2, 26, BG1 + (int(255 * c),))
        d.text((x0 + 130 + (bw - 150 - w) / 2, y0 + bh / 2 - 26), s, font=f, fill=BG1 + (int(255 * c),))
    e = eo((t - 1.9) / 0.6)
    if e > 0:
        if o.get("contact"):
            f = F(SER, 84)
            s = o["contact"]
            d.text(((W - tw(d, s, f)) / 2, 1200 + (1 - e) * 14), s, font=f, fill=ACCENT + (int(255 * e),))
        if o.get("sub"):
            f2 = sans("Medium", 30)
            s2 = o["sub"].upper()
            w2 = track_w(d, s2, f2, 4)
            tracked(im, s2, f2, TEXT, 200 * e, (W - w2) / 2, 1330, 4)


OV = {"kicker": ov_kicker, "bignumber": ov_bignumber, "measure": ov_measure,
      "bullets": ov_bullets, "tag": ov_tag, "layers": ov_layers}


def frame(k, t, fr, idx):
    s = S[k]
    im = BG.copy().convert("RGBA")
    if fr is not None:
        footage(im, fr, t, DUR[k], s.get("dim", 0.0), s.get("focus_x", 0.5), s.get("fit", False))
    header(im, START[k] + t, s.get("label"), t)
    if s.get("end"):
        endcard(im, t, s["end"])
    if s.get("headline"):
        reveal_lines(im, t, [tuple(x) for x in s["headline"]], y=s.get("headline_y", 212), start=s.get("headline_at", 0.15))
    for o in s.get("overlays", []):
        OV[o["type"]](im, t, o)
    if s.get("captions", True) and not s.get("end"):
        captions(im, k, t)
    out = im.convert("RGB")
    n = t * FPS
    if n < 6:  # short fade in from the background colour
        out = Image.blend(Image.new("RGB", (W, H), BG1), out, eio(n / 6))
    return grain(out, idx)


def scene_frames(k, n):
    fl = S[k].get("footage")
    if not fl:
        return None
    parts, rem = [], n
    for i, (f, st, p) in enumerate(fl):
        m = rem if i == len(fl) - 1 else int(round(n * p))
        rem -= m
        parts.append(read_frames(P(f), st, m))
    return np.concatenate(parts)


def render(k):
    n = int(round(DUR[k] * FPS))
    frames = scene_frames(k, n)
    tmp = f"{WORK}/{k}.tmp.mp4"
    pr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", tmp],
                          stdin=subprocess.PIPE)
    for i in range(n):
        pr.stdin.write(frame(k, i / FPS, None if frames is None else frames[i], i).tobytes())
    pr.stdin.close()
    assert pr.wait() == 0
    os.replace(tmp, f"{WORK}/{k}.mp4")


# ---------------------------------------------------------------- 3. sound
# HIT = offset of the transient inside each effect file, so the hit lands on the cue time
HIT = {"whoosh": 0.27, "impact": 0.01, "pop": 0.005, "click": 0.005, "tick": 0.005, "thud": 0.005,
       "riser": 1.825, "swipe": 0.09, "ding": 0.01, "msg": 0.005}
GAIN = {"whoosh": 0.4, "impact": 0.55, "pop": 0.5, "click": 0.5, "tick": 0.45, "thud": 0.6,
        "riser": 0.5, "swipe": 0.45, "ding": 0.7, "msg": 0.5}
HIT.update(SPEC.get("sfx_hit", {}))
GAIN.update(SPEC.get("sfx_gain", {}))


def pcm(f, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + (["-t", str(t)] if t else []) + \
          ["-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def hp(x, f):
    return sosfilt(butter(2, f, btype="high", fs=SR, output="sos"), x)


def norm(x, p=1.0):
    return x / (np.abs(x).max() + 1e-9) * p


def mixdown():
    """Voice on top, music ducked under voice, footage ambience low, effects subtle.
    Mastered to -14 LUFS integrated, -1.5 dBTP."""
    N = int(TOTAL * SR) + SR
    vo, sfx, amb = np.zeros(N), np.zeros(N), np.zeros(N)

    def add(buf, x, t0, g=1.0):
        i = int(t0 * SR)
        if i < 0:
            x = x[-i:]
            i = 0
        j = min(len(buf), i + len(x))
        buf[i:j] += g * x[:j - i]

    lib, missing = {}, set()
    for k in ORDER:
        add(vo, pcm(f"{WORK}/{k}.wav"), START[k] + VO_IN)
        for et, name in S[k].get("sfx", []):
            path = f"{AS}/sounds/{name}.wav"
            if name not in lib:
                if not os.path.exists(path):
                    missing.add(name)
                    continue
                lib[name] = pcm(path)
            add(sfx, lib[name], START[k] + et - HIT.get(name, 0.0), GAIN.get(name, 0.5))
        acc = 0
        fl = S[k].get("footage") or []
        for i, (f, st, p) in enumerate(fl):
            seg = DUR[k] * p if i < len(fl) - 1 else DUR[k] - acc
            try:
                a = pcm(P(f), st, seg)
            except Exception:
                a = np.zeros(1)  # stills and silent clips
            if len(a) > 10 and np.abs(a).max() > 1e-4:
                a = norm(hp(a, 120), 0.12)
                fade = np.minimum(1, np.minimum(np.arange(len(a)), len(a) - np.arange(len(a))) / (0.08 * SR))
                add(amb, a * fade, START[k] + acc)
            acc += seg
    if missing:
        print("warning: missing sound effects skipped:", ", ".join(sorted(missing)))

    env = np.convolve(np.abs(vo), np.ones(int(0.05 * SR)) / (0.05 * SR), "same")
    env = np.clip(env / 0.05, 0, 1)
    duck = 1 - 0.55 * np.convolve(env, np.ones(int(0.2 * SR)) / (0.2 * SR), "same")
    mix = norm(vo, 0.9) + sfx * 0.8 + amb * duck

    m = SPEC.get("music")
    if m:
        mp = P(m["file"]) if os.path.exists(P(m["file"])) else f"{AS}/sounds/{m['file']}"
        trk = pcm(mp)
        ls, le = (int(x * SR) for x in m.get("loop", [0, len(trk) / SR]))
        mus, tot = [trk[:le]], le
        while tot < N:
            mus.append(trk[ls:le])
            tot += le - ls
        mix += norm(np.concatenate(mus)[:N]) * m.get("gain", 0.3) * duck

    end = int(TOTAL * SR)
    fo = int(1.2 * SR)
    mix = mix[:end]
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = np.tanh(mix * 1.1) * 0.95  # soft clip
    open(f"{WORK}/mix.f32", "wb").write(np.stack([mix, mix], 1).astype(np.float32).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", f"{WORK}/mix.f32",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", f"{WORK}/mix.m4a"], check=True)


# ---------------------------------------------------------------- 4. cover
def make_cover(path):
    """1080x1920 cover. Key text sits in the centre band (y 560-1360) so it survives
    the 4:5 feed crop (y 285-1635) and the 1:1 grid crop (y 420-1500)."""
    c = SPEC.get("cover", {})
    im = BG.copy().convert("RGBA")
    src = c.get("frame") or next((S[k]["footage"][0][:2] for k in ORDER if S[k].get("footage")), None)
    if src:
        f, st = src
        fr = read_frames(P(f), st, 1)[0]
        img = Image.fromarray(fr)
        ih, iw = fr.shape[:2]
        sc = max(W / iw, H / ih)
        r = img.resize((int(iw * sc), int(ih * sc)), Image.BICUBIC)
        cx = int((r.width - W) * c.get("focus_x", 0.5))
        r = r.crop((cx, (r.height - H) // 2, cx + W, (r.height - H) // 2 + H))
        im = grade(r.filter(ImageFilter.UnsharpMask(2, 60, 2))).convert("RGBA")
        yv = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
        a = np.clip(np.clip(1 - np.abs(yv - 0.5) / 0.32, 0, 1) * 0.78 + 0.28, 0, 0.9)
        shade = Image.new("RGBA", (W, H), BG1 + (0,))
        shade.putalpha(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)))
        im.alpha_composite(shade)
    d = ImageDraw.Draw(im, "RGBA")
    k = c.get("kicker", SERIES)
    fk = sans("SemiBold", 30)
    kw = track_w(d, k.upper(), fk, 7)
    tracked(im, k.upper(), fk, ACCENT, 255, (W - kw) / 2, 600, 7)
    d.line([(W / 2 - 60, 660), (W / 2 + 60, 660)], fill=ACCENT, width=2)
    lines = c.get("lines", [[SPEC.get("title", ""), False]])
    size = c.get("size", 150)
    for i, (t_, it) in enumerate(lines):
        fnt = F(SERI if it else SER, size)
        tw_ = tw(d, t_, fnt)
        y = 700 + i * int(size * 1.02)
        d.text(((W - tw_) / 2 + 3, y + 4), t_, font=fnt, fill=(0, 0, 0, 120))
        d.text(((W - tw_) / 2, y), t_, font=fnt, fill=ACCENT if it else TEXT)
    yb = 700 + len(lines) * int(size * 1.02) + 40
    if c.get("sub"):
        fs = sans("Medium", 40)
        d.text(((W - tw(d, c["sub"], fs)) / 2, yb), c["sub"], font=fs, fill=TEXT + (230,))
        yb += 80
    if EPISODE:
        ep = f"No. {EPISODE}"
        fe = F(SERI, 48)
        d.text(((W - tw(d, ep, fe)) / 2, yb + 10), ep, font=fe, fill=ACCENT)
    card = brand_card(450, 150, 1.0)
    im.alpha_composite(card, ((W - 450) // 2, 1500))
    out = grain(im.convert("RGB"), 0)
    out.save(path, quality=92)
    # side-by-side preview: full, 4:5 feed crop, 1:1 grid crop
    prev = Image.new("RGB", (1080 * 3 + 80, 1920), "white")
    prev.paste(out, (0, 0))
    prev.paste(out.crop((0, 285, 1080, 1635)), (1120, 285))
    prev.paste(out.crop((0, 420, 1080, 1500)), (2240, 420))
    prev.resize((prev.width // 4, prev.height // 4)).save(path.rsplit(".", 1)[0] + "_crops.jpg", quality=85)
    print("cover", path)


# ---------------------------------------------------------------- main
if A.cover:
    make_cover(A.cover)
    sys.exit()

if A.stills:
    out = []
    for k in ORDER:
        t = min(DUR[k] - 0.1, S[k].get("still_at", DUR[k] * 0.8))
        fr = None
        if S[k].get("footage"):
            f, st, p = S[k]["footage"][0]
            fr = read_frames(P(f), st + t, 1)[0]
        out.append(frame(k, t, fr, 0).resize((360, 640)))
    cols = 4
    rows = (len(out) + cols - 1) // cols
    sh = Image.new("RGB", (360 * cols, 640 * rows), "white")
    for i, im in enumerate(out):
        sh.paste(im, ((i % cols) * 360, (i // cols) * 640))
    sh.save(A.stills, quality=88)
    print("stills", A.stills, "total", round(TOTAL, 1))
    sys.exit()

for k in (A.only.split(",") if A.only else ORDER):
    render(k)
    print("scene", k, flush=True)
mixdown()
open(f"{WORK}/list.txt", "w").write("".join(f"file '{k}.mp4'\n" for k in ORDER))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt", "-i", f"{WORK}/mix.m4a",
                "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-maxrate", "5M", "-bufsize", "10M",
                "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", P(SPEC["output"])], check=True)
print("done", P(SPEC["output"]), round(TOTAL, 1))
