# uticamidstream.com: Utica Midstream

Static site on GitHub Pages (repo fiopoin/uticamidstream-site, branch main, custom domain uticamidstream.com via GoDaddy DNS). Same process as fiopoin.com and carbonenergynexus.com.

## Build
- One JSON file per edition in `content/YYYY-MM-DD.json` (America/Chicago date); the newest becomes the homepage. Copy the latest file and replace every field.
- `python3 tools/build.py` writes index.html, archive/, method.html, privacy.html, feed.xml, sitemap.xml, robots.txt, llms.txt and the social graphics (social/<date>.png, -story.png, -midday, -evening, captions, social/today.json). Never hand edit generated files; never block crawlers.
- Needs jinja2 and Pillow. Fonts in tools/fonts (Barlow Semi Condensed, IBM Plex Sans, IBM Plex Mono, all OFL). `tools/render_brand.py` re-renders brand PNGs (Playwright) only when brand SVGs change.

## Content schema
date, date_long, edition,
prices{asof, rows[]{group Crude|Gas|Products, name, value, unit, change, pct, note?, source{name,url}}, spreads[]{name, value, note}},
markets{asof, indexes[]{name,value,change,pct}, index_source, read, read_source, stocks[]{ticker,name,segment,price?,pct?,note,source}},
lead{kicker, chain[] of upstream|midstream|downstream|market that the story touches, headline (under 110 chars), dek, body[3], flow{upstream,midstream,downstream,market}, use[4]{who,text}, sources[]},
briefs[4 to 6]{id, segment Upstream|Midstream|Downstream|Gas and LNG|Cross-industry|Regulation, setting (Onshore, Offshore, Refining, CCUS, Global...), region, headline, text, why, sources[]},
docket[]{agency, action, date, status, means, source}, basins[]{name, setting, line, source},
leader{week_of, name, role, summary, path, why, sources[]}, events[]{when, name, where, note, url},
social{kicker "Morning: the flow", headline, points[3], watch, caption}, social_slots{midday{kicker "Midday: the money",...}, evening{kicker "Evening: the world",...}}.
Brief ids "money" and "world" must exist.

## Daily rules
- Coverage: oil and gas across upstream, midstream (including midstream water), downstream; onshore and offshore; conventional and unconventional; LNG; commodity prices; equity indexes and major oil and gas stocks; regulation (DOE, FERC, PHMSA, EPA, BOEM, BLM, Texas RRC, state agencies, OPEC+, foreign governments); cross-industry (CCUS, hydrogen, power and data centers, produced water, critical minerals). Global, with a US industry reader in mind.
- Prices: take the latest quotes available at build time from a page that shows them with a time (OilPrice.com price charts works); write the time in prices.asof and mark stale rows in note. Spreads are calculated from the quotes shown and labeled "Calculated". Never invent or estimate a number.
- Stocks: show price and pct only when the source shows a dated close for the last trading day; otherwise leave them out and keep the news line. Indexes are the prior session's close (AP "How major US stock indexes fared" is reliable).
- Leader of the week: change it on Mondays (or the first edition of a week); keep it unchanged the rest of the week. Profile from public, sourced facts; paraphrase; no photos of people.
- Events: keep upcoming industry events in date order, drop past ones, add new ones when announced (official site first). Keep Produced Water Society events listed.
- Docket: keep items until a week after they pass; add new decisions with status as reported.
- Every fact sourced, dated and linked. Paraphrase; at most one short quote per source. No em or en dashes as punctuation. Plain, direct, human prose. Politically neutral. General information, not investment advice.
- Social headline under 60 chars, points under 40, caption under 600 with 4 to 6 hashtags; caption first paragraph is the page description (under 300 chars). Morning post is written for a US reader; midday and evening for a global reader.

## Brand
Navy #13263A, navy2 #1C3550, pipeline marker amber #F5B000 (amber ink #8F5E00 on light), gas blue #3E8ED0, water blue #2E8FD6, paper #F5F4EF. Mark (chosen by Raj, Nov 18, 2026): a pipe rack seen end on, three pipes on a support beam: crude (navy, white on dark), gas (amber, raised in the middle) and water (blue). Wordmark: UTICA (Barlow Semi Condensed Bold) over spaced MIDSTREAM in amber. Files in brand/, social kit in brand/social/.

## Schedule (America/Chicago)
- Daily edition: 05:47.
- Social: morning "the flow" 07:23 (US), midday "the money" 12:23, evening "the world" 16:53.
- Keep at least 30 minutes from fiopoin posts (06:42, 11:42, 17:42 Chicago) and Carbon Energy Nexus posts (05:37, 08:17, 11:07 Chicago in winter); never post two brands at the same minute.

## Publish and verify
Commit as user "fiopoin" (noreply@fiopoin.com) and push to main. Verify the live site (desktop and phone) after every update before reporting done.
