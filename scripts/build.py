#!/usr/bin/env python3
"""
Static site generator for ercindedeoglu.github.io.

Single source of truth lives in data/:
  - data/site.json      identity, nav, social links, sameAs, stats  (ALL links live here)
  - data/projects.json  project / proof cards
  - data/writing.json   external article feed (refresh from https://ercin.info/api/writing)

Every .html file in the repo is a BUILD ARTIFACT. Do not hand-edit links in pages —
edit the data, then rebuild. No article text is hosted here; writing links out to source.

    python3 scripts/build.py            # rebuild all pages from data/
    python3 scripts/build.py --fetch    # refresh data/writing.json from the API first
"""
import json
import os
import sys
import html
import datetime
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
API = "https://ercin.info/api/writing"


# ---------- data ----------
def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def fetch_writing():
    req = urllib.request.Request(API, headers={
        "Accept": "application/json",
        "User-Agent": "ercindedeoglu.github.io build bot (+https://ercindedeoglu.github.io)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
    json.loads(raw)
    with open(os.path.join(DATA, "writing.json"), "w") as f:
        f.write(raw)
    print(f"fetched {API} -> data/writing.json")


def writing_items():
    d = load("writing.json")
    items = d.get("items", d if isinstance(d, list) else [])
    items.sort(key=lambda i: i.get("date", ""), reverse=True)
    return items


# ---------- helpers ----------
def e(s):
    return html.escape(s or "", quote=True)


def fmt_date(iso):
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%-d %b %Y")
    except Exception:
        return (iso or "")[:10]


def iso_date(iso):
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return (iso or "")[:10]


def same_as(cfg):
    urls = [s["url"] for s in cfg["socials"]]
    urls += cfg.get("sameas_extra", [])
    urls.append(cfg["canonical_profile"])
    return urls


def nav_html(cfg, current):
    links = "\n".join(
        f'            <a href="{e(n["path"])}"'
        + (' aria-current="page"' if n["path"] == current else "")
        + f'>{e(n["label"])}</a>'
        for n in cfg["nav"]
    )
    return f"""<header class="site-header">
    <div class="container">
        <div class="brand-mark">
            <a href="/">{e(cfg["name"])}</a>
            <span class="tag">{e(cfg["tagline"])}</span>
        </div>
        <nav class="nav" aria-label="Primary">
{links}
        </nav>
    </div>
</header>"""


def footer_html(cfg):
    social = "\n".join(
        f'            <li><a href="{e(s["url"])}" rel="me noopener" aria-label="{e(s["label"])}">'
        f'<i class="fab {e(s["icon"])}" aria-hidden="true"></i></a></li>'
        for s in cfg["socials"]
    )
    return f"""<footer class="site-footer">
    <div class="container">
        <div>
            <strong>{e(cfg["name"])}</strong> — {e(cfg["role"])}, {e(cfg["location"])}<br/>
            <span class="foot-note">Canonical profile: <a href="{e(cfg["canonical_profile"])}" rel="me">{e(cfg["canonical_profile"].split("//")[-1])}</a> · &copy; 2026 {e(cfg["name"])}</span>
        </div>
        <ul class="social">
{social}
        </ul>
    </div>
</footer>"""


def jsonld_block(nodes):
    if not nodes:
        return ""
    payload = {"@context": "https://schema.org", "@graph": nodes} if len(nodes) > 1 else {
        "@context": "https://schema.org", **nodes[0]
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    body = "\n".join("    " + l for l in body.splitlines())
    return f'    <script type="application/ld+json">\n{body}\n    </script>\n'


def person_node(cfg):
    return {
        "@type": "Person",
        "@id": cfg["person_id"],
        "name": cfg["name"],
        "givenName": cfg["given_name"],
        "familyName": cfg["family_name"],
        "jobTitle": cfg["role"],
        "description": f'{cfg["role"]} in {cfg["location"]} building enterprise LLM, RAG and agentic systems for regulated banking on sovereign cloud.',
        "worksFor": {"@type": "Organization", "name": cfg["works_for"]["name"], "url": cfg["works_for"]["url"]},
        "address": {"@type": "PostalAddress", "addressLocality": cfg["address"]["locality"], "addressCountry": cfg["address"]["country"]},
        "url": cfg["canonical_profile"],
        "mainEntityOfPage": cfg["site_url"] + "/",
        "knowsAbout": cfg["knows_about"],
        "sameAs": same_as(cfg),
    }


def render_page(cfg, *, path, title, description, body, nodes, og_title=None, og_desc=None, og_type="website"):
    url = cfg["site_url"] + path
    og_title = og_title or title
    og_desc = og_desc or description
    img = cfg["site_url"] + cfg["og_image"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>

    <title>{e(title)}</title>
    <meta name="description" content="{e(description)}"/>
    <meta name="author" content="{e(cfg["name"])}"/>
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1"/>
    <link rel="canonical" href="{url}"/>
    <meta name="theme-color" content="{e(cfg["theme_color"])}"/>

    <meta property="og:type" content="{og_type}"/>
    <meta property="og:site_name" content="{e(cfg["name"])}"/>
    <meta property="og:title" content="{e(og_title)}"/>
    <meta property="og:description" content="{e(og_desc)}"/>
    <meta property="og:url" content="{url}"/>
    <meta property="og:image" content="{img}"/>
    <meta property="og:image:width" content="1200"/>
    <meta property="og:image:height" content="630"/>
    <meta property="og:image:alt" content="{e(cfg["name"])} — {e(cfg["role"])} in {e(cfg["location"])}"/>
    <meta property="og:locale" content="en_US"/>

    <meta name="twitter:card" content="summary_large_image"/>
    <meta name="twitter:site" content="{e(cfg["twitter_handle"])}"/>
    <meta name="twitter:creator" content="{e(cfg["twitter_handle"])}"/>
    <meta name="twitter:title" content="{e(og_title)}"/>
    <meta name="twitter:description" content="{e(og_desc)}"/>
    <meta name="twitter:image" content="{img}"/>

    <link rel="icon" href="/favicon.ico" sizes="any"/>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg"/>
    <link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
    <link rel="manifest" href="/site.webmanifest"/>

    <link rel="stylesheet" href="/assets/css/site.css"/>
    <link rel="stylesheet" href="/assets/css/fontawesome-all.min.css"/>

{jsonld_block(nodes)}</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
{nav_html(cfg, path)}

<main id="main">
{body}
</main>

{footer_html(cfg)}
</body>
</html>
"""


# ---------- page bodies ----------
def writing_cards(items, n=3):
    out = []
    for it in items[:n]:
        out.append(f"""                <article class="card">
                    <span class="kicker">{e(it.get("source",""))}</span>
                    <h3><a href="{e(it["url"])}" rel="noopener" target="_blank">{e(it["title"])}</a></h3>
                    <p>{e(it.get("summary",""))}</p>
                    <div class="meta">{fmt_date(it.get("date",""))} · {e(it.get("source",""))} ↗</div>
                </article>""")
    return "\n".join(out)


def home_body(cfg, items):
    stats = "\n".join(
        f'                <div class="stat"><div class="num">{e(s["num"])}</div><div class="lbl">{e(s["lbl"])}</div></div>'
        for s in cfg["stats"]
    )
    profile = cfg["canonical_profile"]
    return f"""    <section class="hero">
        <div class="container">
            <span class="eyebrow">{e(cfg["tagline"])}</span>
            <h1>I design enterprise AI that <span class="grad">regulated banks can actually ship</span>.</h1>
            <p class="lead">
                I build production <strong>LLM</strong>, <strong>RAG</strong> and <strong>agentic</strong> systems for
                <strong>regulated banking</strong> on <strong>sovereign cloud</strong> — model-agnostic, auditable,
                and engineered to survive compliance review. This is where I publish my writing and show the proof.
            </p>
            <div class="actions">
                <a class="btn btn-primary" href="/writing/">Read the writing</a>
                <a class="btn btn-ghost" href="/projects/">See the work</a>
            </div>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <div class="section-head">
                <div>
                    <h2>Latest writing</h2>
                    <p class="section-sub">Practitioner notes on LLM, RAG, agents and AI security — published on Medium, LinkedIn &amp; dev.to.</p>
                </div>
                <a class="read" href="/writing/">All articles →</a>
            </div>
            <div class="card-grid">
{writing_cards(items)}
            </div>
        </div>
    </section>

    <section class="section alt">
        <div class="container">
            <h2>Proof, not adjectives</h2>
            <p class="section-sub">Two decades of shipping systems under real load — now pointed at enterprise AI.</p>
            <div class="stats">
{stats}
            </div>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <div class="prose">
                <h2>Where to find the rest of me</h2>
                <p>
                    This site is my writing and proof hub. My full profile — bio, background and the canonical
                    record of who I am — lives at <a href="{e(profile)}" rel="me">{e(profile.split("//")[-1])}</a>.
                    If you are evaluating me as an <strong>{e(cfg["role"])}</strong> for <strong>regulated banking</strong>,
                    start with the <a href="/writing/">writing</a> and the <a href="/projects/">case studies</a>.
                </p>
            </div>
        </div>
    </section>"""


def writing_body(cfg, items):
    rows = "\n".join(
        f"""                <li><a class="row" href="{e(it["url"])}" rel="noopener" target="_blank">
                    <span class="row-title">{e(it["title"])} ↗</span>
                    <span class="row-meta">{fmt_date(it.get("date",""))} · {e(it.get("source",""))}</span>
                    <span class="row-desc">{e(it.get("summary",""))}</span>
                </a></li>"""
        for it in items
    )
    profile = cfg["canonical_profile"]
    return f"""    <section class="article-hero">
        <div class="container">
            <span class="kicker">Writing</span>
            <h1>Notes on building AI that ships</h1>
            <p class="byline">LLM, RAG, agents, sovereign banking AI and AI security — {len(items)} pieces, newest first. Each links to its source on Medium, LinkedIn or dev.to.</p>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <ul class="post-list">
{rows}
            </ul>
            <p class="section-sub" style="margin-top:28px">
                Aggregated from <a href="{e(profile)}" rel="me">{e(profile.split("//")[-1])}</a>. My full profile lives there.
            </p>
        </div>
    </section>"""


def projects_body(cfg, projects):
    cards = []
    for p in projects:
        title = p["title"]
        if p.get("url"):
            title = f'<a href="{e(p["url"])}" rel="noopener" target="_blank">{e(p["title"])}</a>'
        else:
            title = e(p["title"])
        cards.append(f"""                <article class="card">
                    <span class="kicker">{e(p.get("kicker",""))}</span>
                    <h3>{title}</h3>
                    <p>{p.get("body","")}</p>
                    <div class="meta">{e(p.get("meta",""))}</div>
                </article>""")
    cards_html = "\n".join(cards)
    profile = cfg["canonical_profile"]
    return f"""    <section class="article-hero">
        <div class="container">
            <span class="kicker">Projects</span>
            <h1>Selected work &amp; proof</h1>
            <p class="byline">What I build as an {e(cfg["role"])} in {e(cfg["location"])} — enterprise LLM, RAG and agentic systems for regulated banking on sovereign cloud, on top of two decades of high-load engineering.</p>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <div class="card-grid">
{cards_html}
            </div>
            <div class="callout">
                <p style="margin:0">
                    Want specifics — architecture, numbers, constraints — for a particular build?
                    The write-ups live in my <a href="/writing/">writing</a>, and the canonical profile is at
                    <a href="{e(profile)}" rel="me">{e(profile.split("//")[-1])}</a>. For anything confidential, reach me via the links below.
                </p>
            </div>
        </div>
    </section>"""


def about_body(cfg):
    profile = cfg["canonical_profile"]
    return f"""    <section class="article-hero">
        <div class="container">
            <span class="kicker">About</span>
            <h1>{e(cfg["name"])} — {e(cfg["role"])} in {e(cfg["location"])}</h1>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <div class="prose">
                <p>
                    I am an <strong>{e(cfg["role"])}</strong> based in <strong>{e(cfg["location"])}</strong>, building enterprise
                    <strong>LLM</strong>, <strong>RAG</strong> and <strong>agentic</strong> systems for <strong>regulated banking</strong>
                    on <strong>sovereign cloud</strong>. My focus is the unglamorous part that decides whether AI ships in a bank:
                    data residency, auditability, model-agnostic gateways, and guardrails that survive a regulator's review.
                </p>
                <p>
                    That work sits on top of 18+ years of high-load software architecture — backend, frontend and database systems
                    designed to stay up under real production pressure, including a backend that sustained 2.5M concurrent connections.
                </p>
                <div class="callout">
                    <p style="margin:0">
                        This is my writing and proof hub. My full profile and the canonical record of who I am live at
                        <a href="{e(profile)}" rel="me"><strong>{e(profile.split("//")[-1])}</strong></a> — start there for the complete picture,
                        or browse my <a href="/writing/">writing</a> and <a href="/projects/">projects</a> here.
                    </p>
                </div>
                <p>Find me on the platforms linked in the footer below, or reach out through <a href="{e(profile)}" rel="me">{e(profile.split("//")[-1])}</a>.</p>
            </div>
        </div>
    </section>"""


# ---------- sitemap ----------
def render_sitemap(cfg, items):
    site = cfg["site_url"]
    newest = max((iso_date(i.get("date", "")) for i in items), default="2026-06-20")
    rows = []
    for n in cfg["nav"]:
        rows.append((n["path"], newest if n["path"] == "/writing/" else "2026-06-20",
                     "weekly" if n["path"] == "/writing/" else "monthly", "0.8"))
    rows.insert(0, ("/", newest, "weekly", "1.0"))
    out = []
    for path, lastmod, freq, prio in rows:
        extra = ""
        if path == "/":
            extra = (f"\n    <image:image>\n      <image:loc>{site}{cfg['og_image']}</image:loc>"
                     f"\n      <image:title>{e(cfg['name'])} — {e(cfg['role'])} in {e(cfg['location'])}</image:title>\n    </image:image>")
        out.append(f"  <url>\n    <loc>{site}{path}</loc>\n    <lastmod>{lastmod}</lastmod>"
                   f"\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>{extra}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            + "\n".join(out) + "\n</urlset>\n")


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w") as f:
        f.write(content)


# ---------- main ----------
def main():
    if "--fetch" in sys.argv:
        fetch_writing()
    cfg = load("site.json")
    projects = load("projects.json")["items"]
    items = writing_items()

    website = {
        "@type": "WebSite",
        "@id": cfg["site_url"] + "/#website",
        "url": cfg["site_url"] + "/",
        "name": f'{cfg["name"]} — Writing & Proof Hub',
        "description": "Articles and case studies on enterprise AI, LLM, RAG and sovereign banking systems by Ercin Dedeoglu.",
        "inLanguage": "en",
        "about": {"@id": cfg["person_id"]},
        "publisher": {"@id": cfg["person_id"]},
    }

    writing_list = {
        "@type": "ItemList",
        "name": "Writing by " + cfg["name"],
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": n, "url": it["url"],
             "item": {"@type": "BlogPosting", "headline": it["title"], "url": it["url"],
                      "datePublished": iso_date(it.get("date", "")), "description": it.get("summary", ""),
                      "author": {"@id": cfg["person_id"]},
                      "publisher": {"@type": "Organization", "name": it.get("source", "")}}}
            for n, it in enumerate(items, 1)
        ],
    }

    # Home
    write("index.html", render_page(
        cfg, path="/",
        title=f'{cfg["name"]} — {cfg["role"]} in {cfg["location"]} | LLM, RAG & Sovereign Banking AI',
        description=f'Writing and case studies by {cfg["name"]}, an {cfg["role"]} in {cfg["location"]} building enterprise LLM, RAG and agentic systems for regulated banking on sovereign cloud.',
        og_title=f'{cfg["name"]} — {cfg["role"]} in {cfg["location"]}',
        og_desc="Writing and case studies on enterprise LLM, RAG and agentic systems for regulated banking on sovereign cloud.",
        body=home_body(cfg, items), nodes=[person_node(cfg), website]))

    # Writing
    write("writing/index.html", render_page(
        cfg, path="/writing/",
        title=f'Writing — {cfg["name"]}, {cfg["role"]} | LLM, RAG, Agents & AI Security',
        description=f'Articles by {cfg["name"]}, {cfg["role"]} in {cfg["location"]} — practitioner notes on LLM, RAG, AI agents, sovereign banking AI and AI security. {len(items)} pieces across Medium, LinkedIn and dev.to.',
        og_title=f'Writing — {cfg["name"]}',
        og_desc="Practitioner notes on LLM, RAG, AI agents, sovereign banking AI and AI security.",
        body=writing_body(cfg, items), nodes=[writing_list]))

    # Projects
    write("projects/index.html", render_page(
        cfg, path="/projects/",
        title=f'Projects — {cfg["name"]}, {cfg["role"]} in {cfg["location"]} | Sovereign LLM Gateway & RAG',
        description=f'Selected work by {cfg["name"]}, {cfg["role"]} in {cfg["location"]}: a sovereign model-agnostic LLM gateway, RAG for core banking, LLM token optimization, and high-load backend systems.',
        og_title=f'Projects — {cfg["name"]}',
        og_desc="Sovereign LLM gateway, RAG for core banking, LLM token optimization, and high-load systems.",
        body=projects_body(cfg, projects),
        nodes=[{"@type": "CollectionPage", "@id": cfg["site_url"] + "/projects/",
                "name": f'Projects — {cfg["name"]}', "inLanguage": "en",
                "about": {"@id": cfg["person_id"]}, "author": {"@id": cfg["person_id"]}}]))

    # About
    write("about/index.html", render_page(
        cfg, path="/about/", og_type="profile",
        title=f'About — {cfg["name"]} | {cfg["role"]} in {cfg["location"]}',
        description=f'{cfg["name"]} is an {cfg["role"]} in {cfg["location"]} building enterprise LLM, RAG and agentic systems for regulated banking on sovereign cloud. Full profile at {cfg["canonical_profile"]}.',
        og_title=f'About — {cfg["name"]}',
        body=about_body(cfg), nodes=[{"@type": "ProfilePage", "@id": cfg["site_url"] + "/about/",
                                      "inLanguage": "en", "mainEntity": {"@id": cfg["person_id"]}}]))

    # Sitemap
    write("sitemap.xml", render_sitemap(cfg, items))

    print(f"built: index.html, writing/ ({len(items)}), projects/ ({len(projects)}), about/, sitemap.xml")


if __name__ == "__main__":
    main()
