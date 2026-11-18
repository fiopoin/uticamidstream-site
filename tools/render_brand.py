#!/usr/bin/env python3
"""Render brand SVGs to PNG with headless Chromium (run once after changing brand/*.svg).

Usage: python3 tools/render_brand.py
Writes: brand/um-icon-{32,180,512}.png, brand/um-mark-white-400.png, brand/um-mark-400.png,
        brand/um-lockup-white-1200.png, brand/um-lockup-navy-1200.png, brand/um-og.png and social kit images in brand/social/.
"""
import os, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
B = ROOT / "brand"
FONTS = (ROOT / "assets" / "fonts").as_uri()
CSS = f"""<style>
@font-face{{font-family:'Barlow Semi Condensed';font-weight:700;src:url({FONTS}/barlow-semi-condensed-latin-700-normal.woff2)}}
@font-face{{font-family:'Barlow Semi Condensed';font-weight:600;src:url({FONTS}/barlow-semi-condensed-latin-600-normal.woff2)}}
@font-face{{font-family:'IBM Plex Sans';font-weight:500;src:url({FONTS}/ibm-plex-sans-latin-500-normal.woff2)}}
html,body{{margin:0;padding:0;background:transparent}} svg{{display:block}}</style>"""

def shot(page, html, w, h, out, transparent=True):
    page.set_viewport_size({"width": w, "height": h})
    tmp = ROOT / "brand" / "_render.html"
    tmp.write_text(f"<!DOCTYPE html><html><head>{CSS}</head><body>{html}</body></html>")
    page.goto(tmp.as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(150)
    page.screenshot(path=str(out), omit_background=transparent, clip={"x": 0, "y": 0, "width": w, "height": h})

def svg(name, w, h):
    s = (B / name).read_text()
    return s.replace("<svg ", f'<svg width="{w}" height="{h}" ', 1)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page()
    for n in (32, 180, 512):
        shot(pg, svg("um-icon.svg", n, n), n, n, B / f"um-icon-{n}.png")
    shot(pg, svg("um-mark-white.svg", 400, 400), 400, 400, B / "um-mark-white-400.png")
    shot(pg, svg("um-mark.svg", 400, 400), 400, 400, B / "um-mark-400.png")
    shot(pg, svg("um-lockup-dark.svg", 1200, 240), 1200, 240, B / "um-lockup-white-1200.png")
    shot(pg, svg("um-lockup-light.svg", 1200, 240), 1200, 240, B / "um-lockup-navy-1200.png")
    # Social kit
    os.makedirs(B / "social", exist_ok=True)
    for name, bg in (("profile-navy", "#13263A"), ("profile-light", "#F5F4EF"), ("profile-white", "#FFFFFF")):
        mk = "um-mark-white.svg" if bg == "#13263A" else "um-mark.svg"
        shot(pg, f'<div style="width:800px;height:800px;background:{bg};display:flex;align-items:center;justify-content:center">{svg(mk, 560, 560)}</div>', 800, 800, B / "social" / f"{name}-800.png", False)
    def cover(w, h, lw, name, pad_left=None, tagline=True):
        left = pad_left if pad_left is not None else int(w * 0.06)
        tg = (f'<div style="font:500 {int(lw*0.055)}px \'IBM Plex Sans\';color:#C9D4DE;margin-top:{int(lw*0.03)}px;letter-spacing:.02em">'
              'Wellhead to market. Every day.</div>') if tagline else ""
        html = (f'<div style="width:{w}px;height:{h}px;background:#13263A;position:relative;overflow:hidden">'
                f'<svg width="{w}" height="{h}" style="position:absolute;left:0;top:0" viewBox="0 0 {w} {h}"><g stroke="#1F3A57" stroke-width="{max(2,h//60)}" fill="none">'
                f'<path d="M0 {h*0.78} H{w*0.55} q{h*0.12} 0 {h*0.12} -{h*0.12} V{h*0.30} q0 -{h*0.12} {h*0.12} -{h*0.12} H{w}"/>'
                f'<path d="M0 {h*0.90} H{w*0.62} q{h*0.12} 0 {h*0.12} -{h*0.12} V{h*0.42} q0 -{h*0.12} {h*0.12} -{h*0.12} H{w}"/></g>'
                f'<rect x="{w*0.55+h*0.02}" y="{h*0.74}" width="{h*0.05}" height="{h*0.08}" fill="#F5B000"/></svg>'
                f'<div style="position:absolute;left:{left}px;top:50%;transform:translateY(-50%)">{svg("um-lockup-dark.svg", lw, int(lw*0.2))}{tg}</div></div>')
        shot(pg, html, w, h, B / "social" / f"{name}.png", False)
    cover(1500, 500, 760, "x-header-1500x500")
    cover(1640, 624, 820, "facebook-cover-1640x624")
    cover(2256, 382, 900, "linkedin-cover-1128x191@2x", pad_left=760, tagline=False)
    cover(2560, 1440, 1200, "youtube-banner-2560x1440", pad_left=int((2560 - 1200) / 2), tagline=True)
    cover(1200, 630, 720, "og-1200x630")
    br.close()
os.replace(B / "social" / "og-1200x630.png", B / "um-og.png")
(B / "_render.html").unlink(missing_ok=True)
print("brand rendered")
