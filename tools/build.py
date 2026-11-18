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
    ftr = env.get_template("footer.html.j2").render(root=root)
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

# Social graphics
NAVY, PAPER, AMB, GAS, MUTE, LINE, UP, DN = (19, 38, 58), (241, 245, 249), (245, 176, 0), (62, 142, 208), (159, 178, 196), (45, 75, 106), (91, 208, 143), (255, 138, 128)
def F(w, s): return ImageFont.truetype(f"tools/fonts/{w}.ttf", s)
HEAD, SANS, SANSM, SANSB, MONO = "BarlowSemiCondensed-Bold", "IBMPlexSans-Regular", "IBMPlexSans-Medium", "IBMPlexSans-SemiBold", "IBMPlexMono-SemiBold"
lock = Image.open("brand/um-lockup-white-1200.png").convert("RGBA")
lock = lock.crop(lock.getbbox())
mark = Image.open("brand/um-mark-white-400.png").convert("RGBA")

def wrap(dr, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return lines

def card(d, s, W, H, path, pad=0, prices=True):
    im = Image.new("RGB", (W, H), NAVY); dr = ImageDraw.Draw(im); M = 84
    dr.rectangle((0, 0, W, 14), fill=AMB)
    lg = lock.resize((560, int(560 * lock.height / lock.width)), Image.LANCZOS); im.paste(lg, (M, M), lg)
    y = M + lg.height + 64 + pad
    dr.text((M, y), s["kicker"].upper(), font=F(HEAD, 38), fill=AMB); y += 70
    hf = F(HEAD, 104 if H > W * 1.5 else 92)
    if H <= W * 1.5 and len(wrap(dr, s["headline"], hf, W - 2 * M)) > 2:
        hf = F(HEAD, 78)
    for line in wrap(dr, s["headline"], hf, W - 2 * M):
        dr.text((M, y), line, font=hf, fill=PAPER); y += int(hf.size * 1.02)
    y += 40
    # value chain bar
    seg = (W - 2 * M) // 4
    for i, lab in enumerate(("UPSTREAM", "MIDSTREAM", "DOWNSTREAM", "MARKET")):
        x0 = M + i * seg
        on = lab.lower() in d["lead"].get("chain", []) if s is d.get("social") else lab == "MIDSTREAM"
        dr.rectangle((x0, y, x0 + seg - (10 if i < 3 else 0), y + 10), fill=AMB if lab == "MIDSTREAM" else (GAS if on else LINE))
        dr.text((x0, y + 20), lab, font=F(HEAD, 24), fill=MUTE)
    y += 84
    pf = F(SANSM, 44)
    for p in s["points"]:
        dr.rectangle((M, y + 18, M + 18, y + 36), fill=AMB)
        for line in wrap(dr, p, pf, W - 2 * M - 50):
            dr.text((M + 46, y), line, font=pf, fill=PAPER); y += 58
        y += 22
    if s.get("watch"):
        y += 16
        dr.text((M, y), "WHAT TO WATCH", font=F(HEAD, 32), fill=GAS); y += 46
        wf = F(SANS, 38)
        for line in wrap(dr, s["watch"], wf, W - 2 * M):
            dr.text((M, y), line, font=wf, fill=PAPER); y += 52
    end = y
    foot = H - M - 96
    if prices and d.get("prices"):
        rows = {r["name"].split(" (")[0]: r for r in d["prices"]["rows"]}
        picks = [("WTI", rows.get("WTI")), ("BRENT", rows.get("Brent")), ("HENRY HUB", rows.get("Henry Hub"))]
        picks = [(n, r) for n, r in picks if r]
        if picks and foot - end > 150:
            py = foot - 120
            cw = (W - 2 * M) // len(picks)
            for i, (n, r) in enumerate(picks):
                x0 = M + i * cw
                dr.text((x0, py), n, font=F(HEAD, 26), fill=MUTE)
                dr.text((x0, py + 32), r["value"], font=F(MONO, 44), fill=PAPER)
                pc = r.get("pct", "")
                dr.text((x0 + dr.textlength(r["value"], font=F(MONO, 44)) + 14, py + 46), pc, font=F(MONO, 28), fill=DN if pc.startswith("-") else UP)
    dr.line((M, foot, W - M, foot), fill=LINE, width=2)
    dr.text((M, H - M - 70), d["date_long"], font=F(SANS, 28), fill=MUTE)
    dr.text((M, H - M - 30), "uticamidstream.com", font=F(SANSB, 36), fill=PAPER)
    mk = mark.resize((112, 112), Image.LANCZOS); im.paste(mk, (W - M - 112, H - M - 108), mk)
    im.save(path, optimize=True)
    return end

def render_slot(d, s, base):
    card(d, s, 1080, 1350, f"social/{base}.png")
    end = card(d, s, 1080, 1920, f"social/{base}-story.png")
    free = (1920 - 84 - 300) - end
    if free > 80:
        card(d, s, 1080, 1920, f"social/{base}-story.png", pad=free // 2)

for d in data:
    if "social" not in d: continue
    if d is latest or not os.path.exists(f"social/{d['date']}.png"):
        render_slot(d, d["social"], d["date"])
        open(f"social/{d['date']}.txt", "w").write(d["social"]["caption"] + "\n")
        for slot, ss in d.get("social_slots", {}).items():
            render_slot(d, ss, f"{d['date']}-{slot}")
            open(f"social/{d['date']}-{slot}.txt", "w").write(ss["caption"] + "\n")

slots = {"morning": {"image": f"{SITE}social/{latest['date']}.png", "story": f"{SITE}social/{latest['date']}-story.png", "caption": latest["social"]["caption"]}}
for slot, ss in latest.get("social_slots", {}).items():
    slots[slot] = {"image": f"{SITE}social/{latest['date']}-{slot}.png", "story": f"{SITE}social/{latest['date']}-{slot}-story.png", "caption": ss["caption"]}
json.dump({"date": latest["date"], "slots": slots}, open("social/today.json", "w"), indent=1)
Image.open(f"social/{latest['date']}.png").save("social/latest.png")
print("built", latest["date"], "editions:", len(data))
