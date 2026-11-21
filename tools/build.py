#!/usr/bin/env python3
"""Build uticamidstream.com from content/*.json.

Usage: python3 tools/build.py   (the newest edition becomes the homepage)
Writes: index.html, archive/<date>.html, archive/index.html, method.html, privacy.html,
        feed.xml, sitemap.xml, robots.txt, llms.txt,
        social/<date>[-midday|-evening][-story].png, captions and social/today.json
"""
import json, glob, os, html, hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

editions = sorted(p for p in glob.glob("content/*.json") if os.path.basename(p)[:4].isdigit())
if not editions:
    raise SystemExit("no content files")
data = [json.load(open(p)) for p in editions]
latest = data[-1]
CFG = json.load(open("site.json")) if os.path.exists("site.json") else {}
_ga = "https://www.googletagmanager.com https://*.google-analytics.com https://*.analytics.google.com" if CFG.get("ga_id") else ""
CSP = (f"default-src 'self'; script-src 'self' {('https://www.googletagmanager.com' if _ga else '')}; style-src 'self' 'unsafe-inline'; "
       f"img-src 'self' data: {_ga}; font-src 'self'; connect-src 'self' {_ga}; object-src 'none'; "
       "base-uri 'self'; form-action 'self'; upgrade-insecure-requests").replace("  ", " ").replace(" ;", ";")
V = hashlib.md5("".join(open(f).read() for f in ["assets/style.css", "assets/ga.js"]).encode()).hexdigest()[:8]
os.makedirs("archive", exist_ok=True)
os.makedirs("social", exist_ok=True)

SITE = "https://uticamidstream.com/"
NAME = "Utica Midstream"
DESC = "A free daily read on oil and gas from wellhead to market: prices, stocks, pipelines, policy, projects and people, with every fact sourced and dated."
ORG = {"@type": "NewsMediaOrganization", "@id": SITE + "#org", "name": NAME, "url": SITE,
       "logo": {"@type": "ImageObject", "url": SITE + "brand/um-icon-512.png", "width": 512, "height": 512},
       "description": DESC, "sameAs": CFG.get("same_as", [])}

def published(d):
    return datetime.strptime(d["date"] + " " + CFG.get("publish_time", "05:47"), "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/Chicago")).isoformat()
def summary(d):
    t = d.get("social", {}).get("caption", "").split("\n")[0].strip() or d["lead"]["dek"]
    if len(t) > 300:
        t = t[:300].rsplit(". ", 1)[0] + "."
    return t
def page_url(d, archived):
    return SITE + (f"archive/{d['date']}.html" if archived else "")
def ld_for(d, archived):
    url = page_url(d, archived)
    art = {"@type": "NewsArticle", "@id": url + "#article", "headline": d["lead"]["headline"][:110],
           "description": summary(d), "url": url, "mainEntityOfPage": url,
           "image": [SITE + f"social/{d['date']}.png"], "datePublished": published(d), "dateModified": published(d),
           "inLanguage": "en-US", "isAccessibleForFree": True,
           "articleSection": [d["lead"]["kicker"]] + [b["segment"] for b in d.get("briefs", [])],
           "author": {"@id": SITE + "#org"}, "publisher": {"@id": SITE + "#org"}}
    graph = [ORG, art]
    if d.get("leader"):
        graph.append({"@type": "Person", "name": d["leader"]["name"], "jobTitle": d["leader"]["role"]})
    if not archived:
        graph.append({"@type": "WebSite", "@id": SITE + "#site", "name": NAME, "url": SITE, "publisher": {"@id": SITE + "#org"}, "inLanguage": "en-US"})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")

page = env.get_template("page.html.j2")
common = dict(v=V, cfg=CFG, csp=CSP)
open("index.html", "w").write(page.render(d=latest, root="", archived=False, url=SITE, published=published(latest), desc=summary(latest), ld=ld_for(latest, False), **common))
for d in data:
    open(f"archive/{d['date']}.html", "w").write(page.render(d=d, root="../", archived=True, url=page_url(d, True), published=published(d), desc=summary(d), ld=ld_for(d, True), **common))

def simple(title, desc, canonical, body, root=""):
    hdr = env.get_template("header.html.j2").render(root=root)
    ftr = env.get_template("footer.html.j2").render(root=root, cfg=CFG)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="{CSP}"><meta name="referrer" content="strict-origin-when-cross-origin">
<title>{html.escape(title)} | {NAME}</title><meta name="description" content="{html.escape(desc)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="index, follow"><meta name="theme-color" content="#13263A"><link rel="icon" type="image/svg+xml" href="{root}brand/um-icon.svg"><link rel="stylesheet" href="{root}assets/style.css?v={V}"></head>
<body>{hdr}<main id="main" class="page"><div class="wrap">{body}</div></main>{ftr}</body></html>"""

items = "\n".join(f'<li><a href="{d["date"]}.html">{html.escape(d["date_long"])}</a><br><span>{html.escape(d["lead"]["headline"])}</span></li>' for d in reversed(data))
open("archive/index.html", "w").write(simple("Past editions", "Every Utica Midstream edition, kept so readers can check what we reported against what happened.", SITE + "archive/",
    f'<h1>Past editions</h1><p class="intro">Every edition, kept so you can check what we reported against what happened next.</p><ul class="archive-list">{items}</ul>', root="../"))

open("method.html", "w").write(simple("How we work", "How Utica Midstream sources prices, news and the docket.", SITE + "method.html", """<div class="prose"><h1>How we work</h1>
<p>Utica Midstream is a free daily edition on oil and gas from wellhead to market. It covers upstream, midstream and downstream; onshore and offshore; conventional and unconventional; and the policy, capital and cross-industry work, such as carbon capture and produced water, that touches all of them.</p>
<h2>Prices</h2><p>The board shows the latest quotes available when the edition is built, with the time and the source on every row. Futures quotes move all day, so treat them as a snapshot. Spreads are calculated from the quotes shown and labeled as calculated.</p>
<h2>Markets and stocks</h2><p>Index levels are the prior session's close. Stocks appear when they are in the news; we show a price only when the source gives a dated close.</p>
<h2>Along the chain</h2><p>Every lead story is traced through upstream, midstream, downstream and the market, because a price move or a permit rarely stops at one link.</p>
<h2>The docket</h2><p>Decisions by regulators, governments and producer groups such as OPEC+, with the date, the status reported by the agency and a link to the filing or report.</p>
<h2>Leader of the week</h2><p>Once a week we profile a person whose decisions are moving the industry, from public statements and filings. Profiles are not endorsements.</p>
<h2>Standards</h2><p>Every fact is linked to a dated source. We paraphrase and quote sparingly. Outlook lines are our reading and are labeled. Corrections are made in the archive. This is general information, not investment, legal or tax advice.</p></div>"""))

_ga_text = ("""<h2>Analytics</h2><p>We use Google Analytics 4 to count visits and learn which pages are useful. It records pages viewed, the referring site, general location and device type, and uses cookies to tell new visitors from returning ones. You can block it with Google's <a href="https://tools.google.com/dlpage/gaoptout">opt-out add-on</a> or by blocking cookies; the site works the same.</p>"""
    if CFG.get("ga_id") else "<h2>Analytics</h2><p>We do not run analytics or tracking on this site. If we add visitor analytics, this page will say so first.</p>")
open("privacy.html", "w").write(simple("Privacy", "How Utica Midstream handles visitor data.", SITE + "privacy.html",
    f"""<div class="prose"><h1>Privacy</h1><p>Last updated {latest['date_long']}.</p><p>Utica Midstream is free to read. You do not need an account, and we do not sell, rent or share personal information.</p>{_ga_text}
<h2>Hosting</h2><p>The site is hosted on GitHub Pages, which keeps standard server logs, including IP addresses, for security. See <a href="https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages#data-collection">GitHub's note on data collection</a>.</p></div>"""))

def rfc822(ds):
    return datetime.strptime(ds, "%Y-%m-%d").replace(hour=11, minute=47).strftime("%a, %d %b %Y %H:%M:%S +0000")
entries = "".join(f"""<item><title>{html.escape(d['lead']['headline'])}</title><link>{page_url(d, True)}</link><guid>{page_url(d, True)}</guid>
<pubDate>{rfc822(d['date'])}</pubDate><description>{html.escape(summary(d))}</description><enclosure url="{SITE}social/{d['date']}.png" type="image/png" length="0"/></item>""" for d in reversed(data[-30:]))
open("feed.xml", "w").write(f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{NAME}</title><link>{SITE}</link>
<description>{html.escape(DESC)}</description>{entries}</channel></rss>""")

urls = [(SITE, latest["date"], "daily", "1.0"), (SITE + "method.html", latest["date"], "monthly", "0.5"), (SITE + "archive/", latest["date"], "daily", "0.6")] \
    + [(page_url(d, True), d["date"], "monthly", "0.7") for d in reversed(data)] + [(SITE + "privacy.html", latest["date"], "yearly", "0.2")]
open("sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "\n".join(f"<url><loc>{u}</loc><lastmod>{m}</lastmod><changefreq>{c}</changefreq><priority>{p}</priority></url>" for u, m, c, p in urls) + "\n</urlset>\n")
bots = ["Googlebot", "Bingbot", "Applebot", "DuckDuckBot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
        "anthropic-ai", "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "meta-externalagent", "Meta-ExternalFetcher",
        "FacebookBot", "CCBot", "Amazonbot", "cohere-ai"]
open("robots.txt", "w").write("# Utica Midstream welcomes search engines and AI assistants.\n# Quote and link freely; please credit Utica Midstream and link to uticamidstream.com.\n\n"
    + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")
L = [f"# {NAME}", "", f"> {DESC} Each edition has a price board (crude, gas, products and calculated spreads), market and stock notes, a lead story traced through upstream, midstream, downstream and the market, briefs by segment, a regulatory docket, basin watch, a weekly leader profile and an events calendar. General information, not investment advice.", "",
     "## Today's edition", f"- [{latest['lead']['headline']}]({SITE}): {latest['date_long']}. {summary(latest)}"]
L += [f"- [{b['segment']}: {b['headline']}]({SITE}#{b['id']})" for b in latest.get("briefs", [])]
L += ["", "## About", f"- [How we work]({SITE}method.html)", f"- [Past editions]({SITE}archive/)", f"- [RSS feed]({SITE}feed.xml)", f"- [Sitemap]({SITE}sitemap.xml)", "", "## Recent editions"]
L += [f"- [{d['date_long']}: {d['lead']['headline']}]({page_url(d, True)})" for d in list(reversed(data))[:30]]
open("llms.txt", "w").write("\n".join(L) + "\n")

# Social graphics: three slot looks (flow, money, world), each with two layouts that
# alternate by date, so no two posts in a row share a template.
NAVY, NAVY2, PAPER, AMB, AMBINK, GAS, WATER = (19, 38, 58), (28, 53, 80), (245, 244, 239), (245, 176, 0), (143, 94, 0), (62, 142, 208), (46, 143, 214)
WHITE, MUTE, LINE, UP, DN, INK2 = (241, 245, 249), (159, 178, 196), (45, 75, 106), (91, 208, 143), (255, 138, 128), (84, 98, 112)
UPI, DNI = (22, 128, 70), (180, 40, 40)
def F(w, s): return ImageFont.truetype(f"tools/fonts/{w}.ttf", s)
HEAD, SANS, SANSM, SANSB, MONO = "BarlowSemiCondensed-Bold", "IBMPlexSans-Regular", "IBMPlexSans-Medium", "IBMPlexSans-SemiBold", "IBMPlexMono-SemiBold"
def _png(p):
    i = Image.open(p).convert("RGBA"); return i.crop(i.getbbox())
LOCK_W, LOCK_N, MARK_W, MARK_C = _png("brand/um-lockup-white-1200.png"), _png("brand/um-lockup-navy-1200.png"), _png("brand/um-mark-white-400.png"), _png("brand/um-mark-400.png")
M = 84

def wrap(dr, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return lines

def paste(im, src, x, y, w):
    s = src.resize((w, int(w * src.height / src.width)), Image.LANCZOS); im.paste(s, (x, y), s); return s.height

def headline(dr, text, x, y, width, sizes, fill, maxl=3):
    for sz in sizes:
        f = F(HEAD, sz); ls = wrap(dr, text, f, width)
        if len(ls) <= maxl: break
    for line in ls:
        dr.text((x, y), line, font=f, fill=fill); y += int(f.size * 1.02)
    return y

def stat_of(s):
    if s.get("stat"): return s["stat"]["value"], s["stat"].get("label", "")
    import re
    for pat in (r"[$€£]\d[\d,.]*\s?(?:B|M|K|bn|billion|million)?", r"\d[\d,.]*\s?(?:Bcf/d|MMcf/d|b/d|mtpa|%)"):
        for p in s["points"]:
            m = re.search(pat, p)
            if m: return m.group().strip(), p
    for p in s["points"]:
        m = re.search(r"[$€£]?\d[\d,.]*\s?(?:%|B|M|K|bn|billion|million|Bcf/d|MMcf/d|b/d|mtpa)?", p)
        if m and len(m.group().strip()) >= 2: return m.group().strip(), p
    return None, None

def price_strip(dr, d, x, y, W, dark):
    if not d.get("prices"): return y
    rows = {r["name"].split(" (")[0]: r for r in d["prices"]["rows"]}
    picks = [(n, rows.get(k)) for n, k in (("WTI", "WTI"), ("BRENT", "Brent"), ("HENRY HUB", "Henry Hub")) if rows.get(k)]
    if not picks: return y
    cw = W // len(picks)
    for i, (n, r) in enumerate(picks):
        x0 = x + i * cw
        dr.text((x0, y), n, font=F(HEAD, 26), fill=MUTE if dark else INK2)
        dr.text((x0, y + 32), r["value"], font=F(MONO, 44), fill=WHITE if dark else NAVY)
        pc = r.get("pct", "")
        dr.text((x0 + dr.textlength(r["value"], font=F(MONO, 44)) + 14, y + 46), pc, font=F(MONO, 28),
                fill=(DN if dark else DNI) if pc.startswith("-") else (UP if dark else UPI))
    return y + 100

def footer(im, dr, d, W, H, dark, mark_right=True):
    fy = H - M - 96
    dr.line((M, fy, W - M, fy), fill=LINE if dark else (214, 210, 198), width=2)
    dr.text((M, H - M - 70), d["date_long"], font=F(SANS, 28), fill=MUTE if dark else INK2)
    dr.text((M, H - M - 30), "uticamidstream.com", font=F(SANSB, 36), fill=WHITE if dark else NAVY)
    if mark_right: paste(im, MARK_W if dark else MARK_C, W - M - 112, H - M - 108, 112)
    return fy

def chain_on(d, s):
    return d["lead"].get("chain", []) if s is d.get("social") else ["midstream"]

# Morning A: chain bar and bullets (the original look)
def flow_a(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), NAVY); dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, W, 14), fill=AMB)
    y = M + paste(im, LOCK_W, M, M, 560) + 64 + pad
    dr.text((M, y), s["kicker"].upper(), font=F(HEAD, 38), fill=AMB); y += 70
    y = headline(dr, s["headline"], M, y, W - 2 * M, (104, 92, 78) if H > W * 1.5 else (92, 78), WHITE) + 40
    seg, on = (W - 2 * M) // 4, chain_on(d, s)
    for i, lab in enumerate(("UPSTREAM", "MIDSTREAM", "DOWNSTREAM", "MARKET")):
        x0 = M + i * seg
        dr.rectangle((x0, y, x0 + seg - (10 if i < 3 else 0), y + 10), fill=AMB if lab == "MIDSTREAM" else (GAS if lab.lower() in on else LINE))
        dr.text((x0, y + 20), lab, font=F(HEAD, 24), fill=MUTE)
    y += 84; pf = F(SANSM, 44)
    for p in s["points"]:
        dr.rectangle((M, y + 18, M + 18, y + 36), fill=AMB)
        for line in wrap(dr, p, pf, W - 2 * M - 50):
            dr.text((M + 46, y), line, font=pf, fill=WHITE); y += 58
        y += 22
    if s.get("watch"):
        y += 16; dr.text((M, y), "WHAT TO WATCH", font=F(HEAD, 32), fill=GAS); y += 46
        for line in wrap(dr, s["watch"], F(SANS, 38), W - 2 * M):
            dr.text((M, y), line, font=F(SANS, 38), fill=WHITE); y += 52
    fy = footer(im, dr, d, W, H, True)
    if fy - y > 150: price_strip(dr, d, M, fy - 120, W - 2 * M, True)
    return im, y

# Morning B: a pipeline schematic, headline up top, numbered steps along the pipe
def flow_b(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), NAVY2); dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, 14, H), fill=AMB)
    y = M + pad
    paste(im, MARK_W, M, y, 96)
    dr.text((M + 120, y + 8), "UTICA MIDSTREAM", font=F(HEAD, 34), fill=WHITE)
    dr.text((M + 120, y + 50), s["kicker"].upper(), font=F(HEAD, 30), fill=AMB)
    y += 160
    y = headline(dr, s["headline"], M, y, W - 2 * M, (112, 98, 84) if H > W * 1.5 else (100, 86, 76), WHITE) + 56
    # pipe with four valves
    on = chain_on(d, s); xs = [M + 40 + i * (W - 2 * M - 80) // 3 for i in range(4)]
    dr.rectangle((M, y + 26, W - M, y + 46), fill=LINE)
    for i, lab in enumerate(("UPSTREAM", "MIDSTREAM", "DOWNSTREAM", "MARKET")):
        lit = lab == "MIDSTREAM" or lab.lower() in on
        c = AMB if lab == "MIDSTREAM" else (GAS if lit else LINE)
        if i < 3 and lit and (("UPSTREAM", "MIDSTREAM", "DOWNSTREAM", "MARKET")[i + 1].lower() in on or i == 0 and "upstream" in on):
            dr.rectangle((xs[i], y + 26, xs[i + 1], y + 46), fill=GAS)
        dr.ellipse((xs[i] - 36, y, xs[i] + 36, y + 72), fill=c, outline=NAVY2, width=6)
        tw = dr.textlength(lab, font=F(HEAD, 24))
        dr.text((max(M, min(xs[i] - tw / 2, W - M - tw)), y + 86), lab, font=F(HEAD, 24), fill=WHITE if lit else MUTE)
    y += 150
    for n, p in enumerate(s["points"], 1):
        dr.text((M, y - 4), f"0{n}", font=F(MONO, 40), fill=AMB)
        for line in wrap(dr, p, F(SANSM, 44), W - 2 * M - 90):
            dr.text((M + 90, y), line, font=F(SANSM, 44), fill=WHITE); y += 58
        y += 14; dr.line((M + 90, y, W - M, y), fill=LINE, width=2); y += 24
    if s.get("watch"):
        y += 10
        for i, line in enumerate(wrap(dr, "Watch: " + s["watch"], F(SANS, 38), W - 2 * M)):
            dr.text((M, y), line, font=F(SANS, 38), fill=MUTE if i else WHITE); y += 52
    fy = footer(im, dr, d, W, H, True, mark_right=False)
    if fy - y > 150: price_strip(dr, d, M, fy - 120, W - 2 * M, True)
    return im, y

# Midday A: light paper card with a big number
def money_a(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), PAPER); dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, W, 14), fill=NAVY)
    y = M + paste(im, LOCK_N, M, M, 420) + 70 + pad
    dr.text((M, y), s["kicker"].upper(), font=F(HEAD, 36), fill=AMBINK); y += 72
    val, lab = stat_of(s)
    if val:
        vf = F(HEAD, 230 if dr.textlength(val, font=F(HEAD, 230)) < W - 2 * M else 160)
        dr.text((M - 6, y - 30), val, font=vf, fill=NAVY); y += int(vf.size * 0.95)
        dr.rectangle((M, y, M + 160, y + 12), fill=AMB); y += 34
        for line in wrap(dr, lab, F(SANSM, 36), W - 2 * M):
            dr.text((M, y), line, font=F(SANSM, 36), fill=INK2); y += 48
        y += 30
    y = headline(dr, s["headline"], M, y, W - 2 * M, (84, 74, 66), NAVY) + 30
    rest = [p for p in s["points"] if p != lab]
    for p in rest:
        for i, line in enumerate(wrap(dr, p, F(SANS, 40), W - 2 * M - 40)):
            if i == 0: dr.text((M, y), "+", font=F(SANSB, 40), fill=AMBINK)
            dr.text((M + 40, y), line, font=F(SANS, 40), fill=NAVY); y += 54
        y += 10
    if s.get("watch") and H > W * 1.5:
        y += 20
        for line in wrap(dr, "Next: " + s["watch"], F(SANS, 36), W - 2 * M):
            dr.text((M, y), line, font=F(SANS, 36), fill=INK2); y += 50
    footer(im, dr, d, W, H, False)
    return im, y

# Midday B: navy number block over paper, ticker style
def money_b(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), PAPER); dr = ImageDraw.Draw(im)
    val, lab = stat_of(s)
    bh = (600 if H > W * 1.5 else 530) + pad
    dr.rectangle((0, 0, W, bh), fill=NAVY)
    paste(im, LOCK_W, M, M, 360)
    dr.text((M, M + 128 + pad // 3), s["kicker"].upper(), font=F(HEAD, 34), fill=AMB)
    if val:
        vf = F(HEAD, 170 if dr.textlength(val, font=F(HEAD, 170)) < W - 2 * M else 120)
        dr.text((M - 4, bh - 104), val, font=vf, fill=AMB, anchor="ls")
        dr.text((M, bh - 80), (lab or "")[:60], font=F(SANSM, 32), fill=WHITE)
    dr.rectangle((0, bh, W, bh + 14), fill=AMB)
    y = bh + 70
    y = headline(dr, s["headline"], M, y, W - 2 * M, (92, 80, 70), NAVY) + 36
    for p in [p for p in s["points"] if p != lab]:
        dr.rectangle((M, y + 6, M + 8, y + 44), fill=NAVY)
        for line in wrap(dr, p, F(SANSM, 40), W - 2 * M - 36):
            dr.text((M + 34, y), line, font=F(SANSM, 40), fill=NAVY); y += 54
        y += 18
    if s.get("watch"):
        y += 10
        dr.text((M, y), "WHAT'S NEXT", font=F(HEAD, 30), fill=AMBINK); y += 42
        for line in wrap(dr, s["watch"], F(SANS, 36), W - 2 * M):
            dr.text((M, y), line, font=F(SANS, 36), fill=INK2); y += 50
    footer(im, dr, d, W, H, False)
    return im, y

# Evening A: blue world band, numbered dispatch
def world_a(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), NAVY); dr = ImageDraw.Draw(im)
    bh = 300 + pad
    dr.rectangle((0, 0, W, bh), fill=BAND)
    for k in range(1, 7):  # latitude lines
        yy = int(bh * k / 7); dr.line((0, yy, W, yy), fill=tuple(min(255, c + 26) for c in BAND), width=2)
    paste(im, LOCK_N if BAND == AMB else LOCK_W, M, M, 420)
    dr.text((M, bh - 74), s["kicker"].upper(), font=F(HEAD, 40), fill=NAVY)
    y = bh + 64
    y = headline(dr, s["headline"], M, y, W - 2 * M, (100, 88, 76), WHITE) + 44
    for n, p in enumerate(s["points"], 1):
        dr.ellipse((M, y + 2, M + 52, y + 54), outline=GAS, width=4)
        dr.text((M + 26, y + 28), str(n), font=F(HEAD, 32), fill=GAS, anchor="mm")
        for line in wrap(dr, p, F(SANSM, 42), W - 2 * M - 80):
            dr.text((M + 80, y + 2), line, font=F(SANSM, 42), fill=WHITE); y += 56
        y += 26
    if s.get("watch"):
        y += 10
        dr.text((M, y), "ON THE CALENDAR", font=F(HEAD, 30), fill=GAS); y += 44
        for line in wrap(dr, s["watch"], F(SANS, 38), W - 2 * M):
            dr.text((M, y), line, font=F(SANS, 38), fill=WHITE); y += 52
    footer(im, dr, d, W, H, True)
    return im, y

# Evening B: big quote-style headline, water blue rule, no lockup at top
def world_b(d, s, W, H, pad):
    im = Image.new("RGB", (W, H), NAVY2); dr = ImageDraw.Draw(im)
    for x in range(-H, W, 90):  # faint meridian hatching
        dr.line((x, 0, x + H // 3, H), fill=tuple(min(255, c + 6) for c in NAVY2), width=2)
    y = M + 20 + pad
    dr.text((M, y), s["kicker"].upper(), font=F(HEAD, 38), fill=WATER); y += 60
    dr.rectangle((M, y, M + 120, y + 10), fill=AMB); y += 50
    y = headline(dr, s["headline"], M, y, W - 2 * M, (128, 112, 96, 84) if H > W * 1.5 else (116, 100, 86, 76), WHITE, maxl=4) + 50
    pts = "  /  ".join(s["points"])
    for line in wrap(dr, pts, F(SANSM, 40), W - 2 * M):
        dr.text((M, y), line, font=F(SANSM, 40), fill=MUTE); y += 56
    if s.get("watch"):
        y += 36
        dr.rectangle((M, y, W - M, y + 2), fill=LINE); y += 30
        for i, line in enumerate(wrap(dr, "Next: " + s["watch"], F(SANS, 38), W - 2 * M)):
            dr.text((M, y), line, font=F(SANS, 38), fill=WHITE); y += 52
    fy = H - M - 96
    dr.text((M, H - M - 70), d["date_long"], font=F(SANS, 28), fill=MUTE)
    paste(im, LOCK_W, W - M - 380, H - M - 76, 380)
    dr.text((M, H - M - 30), "uticamidstream.com", font=F(SANSB, 36), fill=WHITE)
    return im, y

LAYOUTS = {"morning": (flow_a, flow_b), "midday": (money_a, money_b), "evening": (world_a, world_b)}

# Palettes (Raj, Nov 21, 2026: mix the colors daily). Each palette swaps the dark grounds, the paper and the
# evening band; brand amber stays the pipeline marker. Layout alternates by date and the palette shifts by date
# and slot: every slot changes color each day, a slot repeats its exact look only every eight days, and the
# three slots of a day never share a palette.
PALETTES = {
    "navy":      dict(NAVY=(19, 38, 58), NAVY2=(28, 53, 80), PAPER=(245, 244, 239), LINE=(45, 75, 106), BAND=(62, 142, 208)),
    "deepwater": dict(NAVY=(8, 46, 62), NAVY2=(12, 62, 80), PAPER=(232, 242, 246), LINE=(34, 88, 108), BAND=(46, 143, 214)),
    "steel":     dict(NAVY=(24, 30, 38), NAVY2=(36, 44, 54), PAPER=(238, 240, 242), LINE=(60, 72, 86), BAND=(245, 176, 0)),
    "crude":     dict(NAVY=(34, 29, 24), NAVY2=(48, 41, 33), PAPER=(248, 240, 225), LINE=(82, 70, 56), BAND=(245, 176, 0)),
}
PAL_ORDER = list(PALETTES)
BAND = PALETTES["navy"]["BAND"]
SLOT_K = {"morning": 0, "midday": 1, "evening": 2}

def card(d, s, slot, W, H, path, pad=0):
    n = datetime.strptime(d["date"], "%Y-%m-%d").toordinal()
    k = n % 2
    pal = s.get("design", {}).get("palette")
    pal = pal if pal in PALETTES else PAL_ORDER[(n + n // 4 + SLOT_K[slot]) % len(PAL_ORDER)]
    globals().update(PALETTES[pal])
    im, end = LAYOUTS[slot][k](d, s, W, H, pad)
    im.save(path, optimize=True)
    return end

def render_slot(d, s, base, slot="morning"):
    card(d, s, slot, 1080, 1350, f"social/{base}.png")
    end = card(d, s, slot, 1080, 1920, f"social/{base}-story.png")
    free = (1920 - 84 - 300) - end
    if free > 80:
        card(d, s, slot, 1080, 1920, f"social/{base}-story.png", pad=free // 2)

for d in data:
    if "social" not in d: continue
    if d is latest or not os.path.exists(f"social/{d['date']}.png"):
        render_slot(d, d["social"], d["date"])
        open(f"social/{d['date']}.txt", "w").write(d["social"]["caption"] + "\n")
        for slot, ss in d.get("social_slots", {}).items():
            render_slot(d, ss, f"{d['date']}-{slot}", slot)
            open(f"social/{d['date']}-{slot}.txt", "w").write(ss["caption"] + "\n")

slots = {"morning": {"image": f"{SITE}social/{latest['date']}.png", "story": f"{SITE}social/{latest['date']}-story.png", "caption": latest["social"]["caption"]}}
for slot, ss in latest.get("social_slots", {}).items():
    slots[slot] = {"image": f"{SITE}social/{latest['date']}-{slot}.png", "story": f"{SITE}social/{latest['date']}-{slot}-story.png", "caption": ss["caption"]}
json.dump({"date": latest["date"], "slots": slots}, open("social/today.json", "w"), indent=1)
Image.open(f"social/{latest['date']}.png").save("social/latest.png")
print("built", latest["date"], "editions:", len(data))
