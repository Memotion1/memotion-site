"""ME Motion website generator.

Reads the editable content in ./content (projects, settings, wedding prices),
copies ./assets and ./media, and writes the finished website to ./public.
Run:  python3 build.py
"""
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "public"
CONTENT = ROOT / "content"
ARTIFACT = os.environ.get("ARTIFACT") == "1"   # preview mode used while designing; not needed for hosting


def load(name, default):
    try:
        return json.loads((CONTENT / name).read_text(encoding="utf-8"))
    except Exception as err:  # missing or broken file: fall back so the site still builds
        print(f"note: could not read content/{name} ({err}); using defaults")
        return default


def e(v):
    return html.escape(str(v or ""), quote=True)


SETTINGS = load("settings.json", {})
BRAND = "ME Motion"
EMAIL = (SETTINGS.get("email") or "info@memotion.se").strip()
PHONE = (SETTINGS.get("phone") or "").strip()
PHONE_TEL = re.sub(r"[^\d+]", "", PHONE)
INSTAGRAM = (SETTINGS.get("instagram") or "https://www.instagram.com/").strip()
BUNNY = re.sub(r"^https?://", "", (SETTINGS.get("bunny_host") or "").strip()).strip("/")
SITE_URL = "https://memotion.se"

# Cal.com booking link from Site settings, e.g. "https://cal.com/memotion/introsamtal" -> "memotion/introsamtal"
BOOKING = re.sub(r"^https?://(app\.)?cal\.com/", "", (SETTINGS.get("booking") or "").strip()).strip("/")
CAL_LOADER = ('<script>(function (C, A, L) { var p = function (a, ar) { a.q.push(ar); }; var d = C.document; '
              'C.Cal = C.Cal || function () { var cal = C.Cal; var ar = arguments; if (!cal.loaded) { cal.ns = {}; cal.q = cal.q || []; '
              'd.head.appendChild(d.createElement("script")).src = A; cal.loaded = true; } if (ar[0] === L) { var api = function () { p(api, arguments); }; '
              'var namespace = ar[1]; api.q = api.q || []; if (typeof namespace === "string") { cal.ns[namespace] = cal.ns[namespace] || api; '
              'p(cal.ns[namespace], ar); p(cal, ["initNamespace", namespace]); } else p(cal, ar); return; } p(cal, ar); }; })'
              '(window, "https://app.cal.com/embed/embed.js", "init"); Cal("init", { origin: "https://cal.com" });</script>\n')

# version tag per file, so browsers fetch the new styles and script right after an update
ASSET_V = {n: hashlib.md5((ROOT / "assets" / n).read_bytes()).hexdigest()[:8] for n in ("styles.css", "site.js", "favicon.svg")}
# one id per version of the site; pages compare it with version.json and reload themselves if a newer version is out
_bh = hashlib.md5(pathlib.Path(__file__).read_bytes())
for _f in sorted([*(ROOT / "assets").rglob("*"), *(ROOT / "content").rglob("*")]):
    if _f.is_file():
        _bh.update(str(_f.relative_to(ROOT)).encode()); _bh.update(_f.read_bytes())
BUILD_ID = _bh.hexdigest()[:10]
# fresh output folder with the static assets and uploaded media
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in (ROOT / "assets").iterdir():
    if f.is_file():
        shutil.copy2(f, OUT / f.name)
if (ROOT / "media").is_dir():
    shutil.copytree(ROOT / "media", OUT / "media", ignore=shutil.ignore_patterns(".gitkeep"))


def optimise_photos(folder, max_side=2400):
    """Shrink very large uploads so pages load fast. Originals stay untouched in ./media."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("note: Pillow not installed, photos are published at their original size")
        return
    for f in folder.rglob("*"):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        try:
            with Image.open(f) as im:
                im = ImageOps.exif_transpose(im)
                if max(im.size) <= max_side and f.stat().st_size < 1_500_000:
                    continue
                im.thumbnail((max_side, max_side))
                fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[f.suffix.lower()]
                if fmt == "JPEG" and im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                opts = {"quality": 82, "optimize": True}
                if fmt == "JPEG":
                    opts["progressive"] = True
                if fmt == "PNG":
                    opts = {"optimize": True}
                im.save(f, fmt, **opts)
        except Exception as err:
            print(f"note: could not optimise {f.name} ({err})")


optimise_photos(OUT / "media")


def media_url(v):
    """Image value from the admin panel -> URL ('' if empty)."""
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("src") or v.get("path") or ""
    v = str(v or "").strip()
    if not v:
        return ""
    if v.startswith(("http://", "https://", "/")):
        return v
    return "/" + v


def media_list(v):
    if not v:
        return []
    if not isinstance(v, list):
        v = [v]
    return [u for u in (media_url(x) for x in v) if u]


def bunny_id(v):
    v = str(v or "").strip()
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", v, re.I)
    return m.group(1) if m else v


def vimeo_ref(v):
    """A Vimeo link (or just its number) -> (video number, private hash) or None."""
    v = str(v or "").strip()
    if re.fullmatch(r"\d{5,}", v):
        return v, ""
    m = re.search(r"vimeo\.com/(?:[^?#]*?/)?(\d{5,})(?:/([0-9a-f]{6,}))?", v, re.I)
    if not m:
        return None
    h = re.search(r"[?&]h=([0-9a-f]{6,})", v, re.I)
    return m.group(1), (h.group(1) if h else (m.group(2) or ""))


_VIMEO = {}


def vimeo_info(ref):
    """Title, size and thumbnail of a Vimeo video, looked up once while building."""
    if ref in _VIMEO:
        return _VIMEO[ref]
    vid, h = ref
    info = {}
    try:
        page_url = f"https://vimeo.com/{vid}" + (f"/{h}" if h else "")
        q = urllib.parse.urlencode({"url": page_url, "width": 1920})
        req = urllib.request.Request(f"https://vimeo.com/api/oembed.json?{q}", headers={"User-Agent": "memotion-site-build"})
        with urllib.request.urlopen(req, timeout=20) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception as err:
        print(f"note: could not look up Vimeo video {vid} ({err})")
    _VIMEO[ref] = info
    return info


def vimeo_ratio(ref):
    info = vimeo_info(ref)
    try:
        return max(0.5, min(4.0, float(info["width"]) / float(info["height"])))
    except Exception:
        return 16 / 9


def video_srcs(v, sizes=("1080p", "720p", "360p")):
    """Vimeo link, Bunny video ID or a direct .mp4 link -> list of sources, best first."""
    v = str(v or "").strip()
    if not v:
        return []
    if re.search(r"\.(mp4|webm|mov)(\?|$)", v, re.I):   # a direct video file link
        return [v]
    vr = vimeo_ref(v)
    if vr:
        return ["vimeo:" + vr[0] + (":" + vr[1] if vr[1] else "")]
    if not BUNNY:
        return []
    vid = bunny_id(v)   # accepts the plain ID or any Bunny link that contains it
    return [f"https://{BUNNY}/{vid}/play_{sz}.mp4" for sz in sizes]


def film_ratio(v):
    """Width / height of a Vimeo film (vertical films are below 1), so the player window fits it."""
    vr = vimeo_ref(str(v or "").strip())
    return round(vimeo_ratio(vr), 4) if vr else round(16 / 9, 4)


def video_thumb(v):
    v = str(v or "").strip()
    if not v or re.search(r"\.(mp4|webm|mov)(\?|$)", v, re.I):
        return ""
    vr = vimeo_ref(v)
    if vr:
        return str(vimeo_info(vr).get("thumbnail_url") or "")
    if not BUNNY:
        return ""
    return f"https://{BUNNY}/{bunny_id(v)}/thumbnail.jpg"


def frame(img, scene, seed, cls="", alt="", inner=""):
    """A picture box: the real image if there is one, otherwise the generated placeholder."""
    c = ("frame " + cls).strip()
    if img:
        return f'<div class="{c}"><img src="{e(img)}" alt="{e(alt)}" loading="lazy" decoding="async">{inner}</div>'
    return f'<div class="{c}" data-scene="{scene}" data-seed="{seed}">{inner}</div>'


FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,400..800&family=IBM+Plex+Mono:wght@400;500&display=swap">'

# Sets language and saved theme before paint. No saved theme = device setting decides.
BOOT = ('<script>(function(){var d=document.documentElement,l,t;try{l=localStorage.getItem("me-motion-lang");t=localStorage.getItem("me-motion-theme");}catch(e){}'
        'if(l!=="sv"&&l!=="en"){l=/^(sv|no|nb|nn|da|fi)/i.test(navigator.language||"sv")?"sv":"en";}'
        'd.setAttribute("data-lang",l);d.lang=l;var h=d.getAttribute("data-theme");if(h)d.setAttribute("data-host-theme",h);if(t==="light"||t==="dark")d.setAttribute("data-theme",t);try{if(localStorage.getItem("me-motion-nav")==="closed")d.setAttribute("data-nav","closed");}catch(e){}})();</script>')


# ---------------- EDITABLE TEXTS ----------------
# Every Swedish/English text on the site goes through T(). Texts changed in the admin panel
# ("Texts – ..." in Pages CMS, stored in content/texts/*.json) replace the originals here.
TEXT_DIR = CONTENT / "texts"
TEXT_PAGES = [("common", "Texts – Menu, footer & buttons"), ("home", "Texts – Home"), ("work", "Texts – Work"),
              ("services", "Texts – Services"), ("about", "Texts – About"), ("contact", "Texts – Contact")]
SECTION = ["common"]   # which page the texts below belong to (set further down)
SEEN = {}              # original Swedish text -> [page, Swedish, English], in order of appearance
TEXT_OVR = {}
for _f in sorted(TEXT_DIR.glob("*.json")) if TEXT_DIR.is_dir() else []:
    try:
        for _k, _v in json.loads(_f.read_text(encoding="utf-8")).items():
            if isinstance(_v, dict) and _v.get("orig"):
                _sv, _en = str(_v.get("sv") or "").strip(), str(_v.get("en") or "").strip()
                TEXT_OVR[_v["orig"]] = (_sv if _sv and _sv != _v["orig"] else None,
                                        _en if _en and _en != _v.get("orig_en") else None)
    except Exception as err:
        print(f"note: could not read {_f.name} ({err})")


def T(sv, en, tag="span", attrs="", edit=True):
    if edit:   # edit=False: text that comes from elsewhere (project titles, calculated prices)
        if sv not in SEEN:
            SEEN[sv] = [SECTION[0], sv, en]
        o = TEXT_OVR.get(sv)
        if o:
            sv, en = o[0] or sv, o[1] or en
    a = f" {attrs}" if attrs else ""
    return f'<{tag} data-l="sv" lang="sv"{a}>{sv}</{tag}><{tag} data-l="en" lang="en"{a}>{en}</{tag}>'


ARROW = ' <span class="arrow">→</span>'

NAV = [("./", "Hem", "Home", "home"), ("work.html", "Arbeten", "Work", "work"),
       ("services.html", "Tjänster", "Services", "services"), ("about.html", "Om", "About", "about"),
       ("contact.html", "Kontakt", "Contact", "contact")]


ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
    "work": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    "services": '<path d="M4 6h16M4 12h16M4 18h10"/>',
    "about": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    "contact": '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="m3 7 9 6 9-6"/>',
}


def icon(k):
    return f'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{ICONS[k]}</svg>'


def sidebar(active):
    links = "".join('<a href="%s"%s><span class="nav-label">%s</span></a>' % (
        h, ' aria-current="page"' if k == active else "", T(sv, en)) for h, sv, en, k in NAV)
    return f'''<aside class="sidebar">
  <div class="side-top">
    <a class="brand" href="./" aria-label="{BRAND} – Mikael Edström"><span class="logo logo-full" aria-hidden="true"></span><span class="logo logo-mark" aria-hidden="true"></span></a>
    <button class="side-toggle" type="button" aria-expanded="true" aria-label="Stäng meny / Close menu"><svg class="i-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg><svg class="i-burger" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
  </div>
  <nav class="nav" aria-label="Meny / Menu">{links}</nav>
  <div class="side-foot">
    <div class="side-controls">
      <div class="lang-switch" role="group" aria-label="Språk / Language"><button type="button" data-set-lang="sv" aria-pressed="true">SV</button><button type="button" data-set-lang="en" aria-pressed="false">EN</button></div>
      <div class="seg theme-seg" role="group" aria-label="Tema / Theme">
        <button type="button" data-set-theme="light" aria-pressed="false" aria-label="Ljust / Light"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><span class="lbl"></span></button>
        <button type="button" data-set-theme="dark" aria-pressed="false" aria-label="Mörkt / Dark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg><span class="lbl"></span></button>
      </div>
    </div>
    <div class="contact-mini stack" style="gap:4px"><span class="mono">{EMAIL}</span></div>
  </div>
</aside>'''


FOOTER = f'''<footer class="site-footer">
  <div class="wrap">
    <div class="stack" style="gap:10px">
      <span class="brand-foot">{BRAND}</span>
    </div>
    <nav aria-label="Sidor / Pages"><h4>{T("Sidor", "Pages")}</h4><ul>
      <li><a href="./">{T("Hem", "Home")}</a></li>
      <li><a href="work.html">{T("Arbeten", "Work")}</a></li>
      <li><a href="services.html">{T("Tjänster", "Services")}</a></li>
      <li><a href="about.html">{T("Om", "About")}</a></li>
      <li><a href="contact.html">{T("Kontakt", "Contact")}</a></li>
    </ul></nav>
    <div><h4>{T("Kontakt", "Contact")}</h4><ul>
      <li><a href="mailto:{EMAIL}">{EMAIL}</a></li>
      <li><a href="tel:{PHONE_TEL}">{PHONE}</a></li>
      <li><a href="{e(INSTAGRAM)}" target="_blank" rel="noopener">Instagram</a></li>
    </ul></div>
    <div class="legal" style="grid-column:1/-1"><span>© 2026 {BRAND}. {T("Alla rättigheter förbehållna.", "All rights reserved.")}</span><span>{T("Stockholm", "Stockholm")}</span></div>
  </div>
</footer>'''


DESC = {
    "index.html": ("ME Motion – film och foto i Stockholm för företag, evenemang och bröllop.",
                   "ME Motion – film and photography in Stockholm for companies, events and weddings."),
    "work.html": ("Utvalda filmer och bildserier från ME Motion.", "Selected films and photo series by ME Motion."),
    "services.html": ("Film och foto för företag, evenemang och bröllop. Bröllopspaket med fasta priser.",
                      "Film and photography for companies, events and weddings. Wedding packages with fixed prices."),
    "about.html": ("Om ME Motion och grundaren Mikael Edström.", "About ME Motion and its founder Mikael Edström."),
    "contact.html": ("Kontakta ME Motion för film och foto i Stockholm.", "Contact ME Motion for film and photography in Stockholm."),
}


def page(name, title_sv, title_en, active, body, full=True):
    full = not (ARTIFACT and name == "index.html")
    d_sv, d_en = DESC.get(name, DESC["index.html"])
    url = SITE_URL + ("/" if name == "index.html" else "/" + name)
    meta = (f'<meta name="description" content="{e(d_sv)}">\n'
            f'<link rel="icon" href="favicon.ico?v={ASSET_V["favicon.svg"]}" sizes="32x32">\n<link rel="icon" type="image/svg+xml" href="favicon.svg?v={ASSET_V["favicon.svg"]}">\n'
            f'<link rel="apple-touch-icon" href="apple-touch-icon.png?v={ASSET_V["favicon.svg"]}">\n'
            f'<link rel="canonical" href="{url}">\n'
            f'<meta property="og:type" content="website">\n<meta property="og:site_name" content="{BRAND}">\n'
            f'<meta property="og:title" content="{e(title_sv)}">\n<meta property="og:description" content="{e(d_sv)}">\n'
            f'<meta property="og:url" content="{url}">\n')
    head = f'<title>{title_sv}</title>\n{BOOT}\n{FONTS}\n<link rel="stylesheet" href="styles.css?v={ASSET_V["styles.css"]}">\n'
    shell = (f'<span id="page-title" data-sv="{title_sv}" data-en="{title_en}" hidden></span>\n'
             f'<div class="layout">\n{sidebar(active)}\n<div class="main">\n<main>\n{body}\n</main>\n{FOOTER}\n</div>\n</div>\n' + (CAL_LOADER if BOOKING else "") + f'<script src="site.js?v={ASSET_V["site.js"]}"></script>\n')
    if full:
        content = (f'<!doctype html>\n<html lang="sv" data-build="{BUILD_ID}">\n<head>\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                   + meta +
                   '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
                   + head + '</head>\n<body>\n' + shell + '</body>\n</html>\n')
    else:
        content = head + shell
    (OUT / name).write_text(content, encoding="utf-8")


def vf(meta="", info="", live=False):
    tc = '<span class="tc" data-timecode>00:00:12:04</span>' if live else ""
    return (f'<div class="vf" aria-hidden="true"><span class="c tl"></span><span class="c tr"></span><span class="c bl"></span><span class="c br"></span>'
            f'<span class="meta">{meta}</span><span class="info">{info}</span>{tc}</div>')


CTA = f'''<section class="cta-band">
  <div class="wrap">
    <div class="stack">
      {T("Nästa steg", "Next step", "span", 'class="eyebrow"')}
      {T("Berätta om ditt projekt", "Tell me about your project", "h2")}
      {T("Datum, plats och vad du har i tankarna.", "The date, the place and what you have in mind.", "p", 'class="lede"')}
    </div>
    <a class="btn primary" href="contact.html">{T("Kontakta mig", "Contact me")}{ARROW}</a>
  </div>
</section>'''

# ---------------- PROJECTS (from content/projects/*.json) ----------------
CATNAME = {"wedding": ("Bröllop", "Wedding"), "business": ("Företag", "Business"), "event": ("Evenemang", "Event"),
           "drone": ("Drönare", "Drone"), "stills": ("Övrigt", "Other")}
DEFAULT_SCENE = {"wedding": "wedding", "business": "interview", "event": "event", "drone": "aerial", "stills": "studio"}
MAIN_FILM = {"wedding": ("Highlightfilm", "Highlight film"), "business": ("Huvudfilm", "Main film"),
             "event": ("Sammanfattning", "Recap"), "drone": ("Film", "Film"), "stills": ("Film", "Film")}
SAMPLE = ["sample-film.mp4"]   # demo clip, only used by the example projects
DEMO_FILMS = {
    "wedding": [("Highlightfilm", "Highlight film", None), ("Hela vigseln", "The full ceremony", "ca 20 min"), ("Talen", "The speeches", "ca 30 min")],
    "business": [("Huvudfilm", "Main film", None), ("Version för sociala medier, 9:16", "Social media cut, 9:16", "0:30")],
    "event": [("Sammanfattning", "Recap", None), ("Klipp för sociala medier", "Social media edit", "0:45")],
    "drone": [("Film", "Film", None)],
}


def two(d, k):
    sv, en = str(d.get(k + "_sv") or "").strip(), str(d.get(k + "_en") or "").strip()
    return (sv or en, en or sv)


def load_projects():
    out = []
    folder = CONTENT / "projects"
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as err:
            print(f"note: skipped {f.name} ({err})")
            continue
        if d.get("hidden") or d.get("draft"):
            continue
        d["id"] = re.sub(r"[^a-z0-9-]+", "-", f.stem.lower()).strip("-") or "project"
        if d.get("category") not in CATNAME:
            d["category"] = "stills"
        d["type"] = "series" if d.get("type") == "series" else "film"
        d["video"] = str(d.get("video") or "").strip()
        d["image_urls"] = media_list(d.get("images"))
        d["cover_url"] = media_url(d.get("cover")) or video_thumb(d["video"]) or (d["image_urls"][0] if d["image_urls"] else "")
        d["scene"] = d.get("scene") or DEFAULT_SCENE[d["category"]]
        try:
            d["seed"] = int(d.get("seed") or (sum(map(ord, d["id"])) % 90 + 3))
        except (TypeError, ValueError):
            d["seed"] = 7
        d["demo"] = not (d["cover_url"] or d["video"] or d["image_urls"])
        try:
            d["_order"] = float(d.get("order") if d.get("order") not in (None, "") else 999)
        except (TypeError, ValueError):
            d["_order"] = 999
        out.append(d)
    out.sort(key=lambda d: (d["_order"], two(d, "title")[0].lower()))
    return out


PROJECTS = load_projects()


def p_length(p):
    ln = str(p.get("length") or "").strip()
    if not ln and p["type"] == "series" and p["image_urls"]:
        ln = str(len(p["image_urls"]))
    return ln


def preview_attr(p):
    """Film shown when the pointer rests on a project (Vimeo or a direct video file)."""
    srcs = video_srcs(p["video"], ("720p", "360p")) if p["video"] else []
    if not srcs and p["demo"] and p["type"] == "film":
        srcs = SAMPLE
    if not srcs:
        return ""
    ratio = vimeo_ratio(vimeo_ref(p["video"])) if p["video"] and vimeo_ref(p["video"]) else 16 / 9
    return f' data-preview="{e("|".join(srcs))}" data-preview-r="{ratio:.4f}"'


def clip(p):
    cat, series = p["category"], p["type"] == "series"
    wide = bool(p.get("wide"))
    ln = p_length(p)
    meta = T(*CATNAME[cat]) + (f" · {e(ln)}" + (T(" bilder", " images") if series else "") if ln else "")
    play = f'<span class="play{" plus" if series else ""}" aria-hidden="true"></span>'
    t = [e(x) for x in two(p, "title")]
    return f'''<a class="clip{" wide" if wide else ""}" href="#{p["id"]}" data-project="{p["id"]}" data-cat="{cat}"{preview_attr(p)}>
  {frame(p["cover_url"], p["scene"], p["seed"], "ratio-scope" if wide else "ratio-16x9", t[0], play)}
  <div class="clip-meta">{T(*t, "h3", edit=False)}<span class="mono">{meta}</span></div>
</a>'''


def project_json(p):
    cat = p["category"]
    o = {"id": p["id"], "type": p["type"], "cat": cat, "length": p_length(p), "fmt": str(p.get("format") or ""),
         "scene": p["scene"], "seed": p["seed"], "cover": p["cover_url"], "kind": {"sv": CATNAME[cat][0], "en": CATNAME[cat][1]}}
    for k in ("title", "client", "summary", "process"):
        sv, en = two(p, k)
        o[k] = {"sv": sv, "en": en}
    # pictures
    if p["image_urls"]:
        gallery = [{"img": u, "sv": f"Bild {i + 1}", "en": f"Image {i + 1}"} for i, u in enumerate(p["image_urls"])]
    elif p["demo"]:
        gallery = [{"scene": p["scene"], "seed": p["seed"] + k * 7, "sv": f"Bild {k}", "en": f"Image {k}"} for k in range(1, 10)]
    else:
        gallery = []
    # films
    films = []
    if p["video"]:
        n_sv, n_en = MAIN_FILM[cat]
        films.append({"sv": n_sv, "en": n_en, "length": p_length(p) if p["type"] == "film" else "",
                      "src": video_srcs(p["video"]), "img": video_thumb(p["video"]), "r": film_ratio(p["video"]), "scene": p["scene"], "seed": p["seed"]})
    for x in p.get("extra_films") or []:
        if not isinstance(x, dict) or not str(x.get("video") or "").strip():
            continue
        sv, en = two(x, "name")
        films.append({"sv": sv or "Film", "en": en or "Film", "length": str(x.get("length") or ""),
                      "src": video_srcs(x["video"]), "img": video_thumb(x["video"]), "r": film_ratio(x["video"]), "scene": p["scene"], "seed": p["seed"] + 5})
    if p["demo"] and p["type"] == "film":
        films = [{"sv": a, "en": b, "length": ln or p_length(p), "src": SAMPLE, "scene": p["scene"], "seed": p["seed"]}
                 for a, b, ln in DEMO_FILMS.get(cat, [])]
    films = [f for f in films if f.get("src")]
    o["films"] = films
    o["all"] = gallery
    # story: paragraphs with the project's pictures woven in between
    sv_t, en_t = two(p, "story")
    sv_p = [x.strip() for x in re.split(r"\n\s*\n", sv_t) if x.strip()]
    en_p = [x.strip() for x in re.split(r"\n\s*\n", en_t) if x.strip()]
    if sv_p or en_p:
        blocks, pics, n = [], list(gallery), max(len(sv_p), len(en_p))
        for i in range(n):
            a = sv_p[i] if i < len(sv_p) else (en_p[i] if i < len(en_p) else "")
            b = en_p[i] if i < len(en_p) else a
            blocks.append({"type": "text", "sv": a, "en": b})
            if i % 2 == 0 and pics:
                blocks.append({"type": "full", "img": pics.pop(0)})
            elif len(pics) >= 2:
                blocks.append({"type": "pair", "imgs": [pics.pop(0), pics.pop(0)]})
        o["story"] = {"blocks": blocks, "credits": []}
    return o


# ---------------- HOME ----------------
SECTION[0] = "home"
SHOWREEL = str(SETTINGS.get("showreel") or "").strip()
REEL = "|".join(video_srcs(SHOWREEL)) or "sample-film.mp4"
REEL_POSTER = video_thumb(SHOWREEL)
PORTRAIT = media_url(SETTINGS.get("portrait"))


def loop_video(srcs, preload="metadata"):
    if srcs.startswith("vimeo:"):   # Vimeo's background player: silent, looping, no controls
        vid, _, h = srcs[6:].partition("|")[0].partition(":")
        q = "background=1&dnt=1" + (f"&h={h}" if h else "")
        return (f'<iframe class="bg-loop vimeo-loop" src="https://player.vimeo.com/video/{e(vid)}?{q}" '
                f'data-ratio="{vimeo_ratio((vid, h)):.4f}" allow="autoplay; fullscreen; picture-in-picture" '
                f'tabindex="-1" aria-hidden="true" title="Showreel"></iframe>')
    return f'<video class="bg-loop" data-loop-src="{e(srcs)}" muted loop playsinline autoplay preload="{preload}" aria-hidden="true"></video>'


def lens_item(p):
    v = ""
    if p["video"] and BUNNY and not vimeo_ref(p["video"]):
        v = loop_video("|".join(video_srcs(p["video"], ("720p", "360p"))))
    elif p["demo"] and p.get("demo_loop"):
        v = loop_video("sample-film.mp4")
    t = two(p, "title")
    title = T(e(t[0]), e(t[1]), "span", 'class="tile-title"', edit=False)
    return (f'<a class="lens-item tall" href="work.html#{p["id"]}" data-cat="{p["category"]}" aria-label="{e(t[0])}"{"" if v else preview_attr(p)}>'
            f'{frame(p["cover_url"], p["scene"], p["seed"], "", t[0], v + title)}'
            f'<span class="lens-cat mono">{T(*CATNAME[p["category"]])}</span></a>')


# Behind-the-scenes pictures for the strip (admin panel: "Through the lens - BTS pictures"). Not projects:
# they open as a large picture and never appear on the Work page.
LENS_BTS = []
for _x in (load("lens.json", {}) or {}).get("pictures") or []:
    if isinstance(_x, dict) and media_url(_x.get("image")):
        LENS_BTS.append({"img": media_url(_x.get("image")), "sv": str(_x.get("caption_sv") or "").strip(), "en": str(_x.get("caption_en") or "").strip()})


def bts_item(b):
    sv, en = b["sv"] or b["en"], b["en"] or b["sv"]
    title = T(e(sv), e(en), "span", 'class="tile-title"', edit=False) if sv else ""
    return (f'<a class="lens-item tall lens-bts" href="{e(b["img"])}" data-photo="lens" data-cap-sv="{e(sv)}" data-cap-en="{e(en)}" '
            f'data-cat="stills" aria-label="{e(sv or "Bakom kulisserna")}">'
            f'{frame(b["img"], "studio", 7, "", sv, title)}<span class="lens-cat mono">{T("Bakom kulisserna", "Behind the scenes")}</span></a>')


# projects first, with a behind-the-scenes picture after every second one; any left over go at the end
_lens_p = [lens_item(p) for p in PROJECTS if p.get("show_on_home")]
_lens_b = [bts_item(b) for b in LENS_BTS]
_lens = []
for _k, _it in enumerate(_lens_p, 1):
    _lens.append(_it)
    if _k % 2 == 0 and _lens_b:
        _lens.append(_lens_b.pop(0))
LENS_HTML = "".join(_lens + _lens_b)


if BOOKING:
    BOOK_BTN = (f'<a class="btn primary hero-cta" href="https://cal.com/{e(BOOKING)}" data-cal-link="{e(BOOKING)}" '
                f'data-cal-config=\'{{"layout":"month_view"}}\' target="_blank" rel="noopener">{T("Boka ett samtal", "Book a call")}{ARROW}</a>')
else:
    BOOK_BTN = f'<a class="btn primary hero-cta" href="contact.html">{T("Boka ett samtal", "Book a call")}{ARROW}</a>'

# The showreel keeps its own shape (no cropping): its width/height ratio goes to the CSS
_vr = vimeo_ref(SHOWREEL)
REEL_RATIO = vimeo_ratio(_vr) if _vr else 16 / 9
# Pause / play button drawn from the logo mark: six strokes the script re-shapes into pause or play
_MARK = [[(342.8, 0), (215.7, 0), (0, 475.6), (130, 475.6)], [(575.1, 0), (448, 0), (232.3, 475.6), (362.3, 475.6)],
         [(795, 0), (667.8, 0), (452.2, 475.6), (582.1, 475.6)], [(840.2, 357.1), (710.9, 357.1), (657.2, 475.6), (787.1, 475.6)],
         [(1000, 0), (872.9, 0), (813.6, 130.7), (941.5, 130.7)], [(919, 181.1), (790.7, 181.1), (733.7, 306.7), (862.8, 306.7)]]
RT_ICON = ('<svg class="rt-icon" viewBox="0 0 1000 1000" aria-hidden="true">' +
           "".join('<polygon points="' + " ".join(f"{180 + x * 0.64:.1f},{348 + y * 0.64:.1f}" for x, y in q) + '"/>' for q in _MARK) + '</svg>')
HERO_REEL = frame(REEL_POSTER, "archipelago", 3, "ratio-scope hero-reel", "", loop_video(REEL, "auto"))[:-6].replace(
    'class="frame ratio-scope hero-reel"', f'class="frame ratio-scope hero-reel" style="--reel-r:{REEL_RATIO:.4f}"', 1)

home = f'''<section class="hero">
  <div class="wrap">
    {HERO_REEL}<span class="reel-big" aria-hidden="true">{RT_ICON}</span><button class="reel-toggle" type="button" aria-pressed="false">{RT_ICON}<span class="rt-label rt-l-pause">{T("Pausa", "Pause")}</span><span class="rt-label rt-l-play">{T("Spela", "Play")}</span></button></div>
    <div class="hero-copy">
      {T("Berättelser som rör sig", "Stories that move", "h1")}
      {BOOK_BTN}
    </div>
  </div>
</section>

<section class="behind">
  <div class="wrap behind-grid">
    {frame(PORTRAIT, "interview", 61, "ratio-4x5 behind-portrait", "Mikael Edström")}
    <div class="stack behind-copy">
      {T("Bakom kameran", "Behind the camera", "span", 'class="eyebrow"')}
      {T("Lugn på plats, noggrann i efterarbetet", "Calm on location, meticulous in post-production", "h2")}
      {T("Varje projekt börjar med en idé, långt innan kameran kommer fram. Först när känslan du är ute efter är tydlig börjar arbetet.", "Every project starts with an idea, long before the camera comes out. The work begins once the feeling you're after is clear.", "p", 'class="lede"')}
      <a class="btn behind-link" href="about.html">{T("Läs om ME Motion", "About ME Motion")}{ARROW}</a>
    </div>
  </div>
</section>

<section class="lens">
  <div class="wrap">
    <div class="section-head split">
      <div class="stack">{T("Utvalda projekt", "Selected work", "span", 'class="eyebrow"')}{T("Genom linsen", "Through the lens", "h2")}</div>
      <div class="lens-tools">
        <button class="icon-btn lens-prev" type="button" aria-label="Föregående / Previous">←</button>
        <button class="icon-btn lens-next" type="button" aria-label="Nästa / Next">→</button>
      </div>
    </div>
  </div>
  <div class="lens-track" tabindex="0" aria-label="Utvalt arbete / Selected work">{LENS_HTML}</div>
</section>

<section class="doing-sec">
  <div class="wrap doing">
    <div class="doing-intro">
      {T("Vad jag gör", "What I do", "span", 'class="eyebrow"')}
      {T("Stora som små uppdrag", "Projects big and small", "h2")}
      {T("Reklamfilm, intervjuer, en YouTube-serie, en match eller ett bröllop i skärgården. Uppdragen ser olika ut, men alla börjar med samma fråga: vad ska bilderna göra för dig?", "A commercial, interviews, a YouTube series, a match or a wedding in the archipelago. Every project looks different, but they all start with the same question: what should the footage do for you?", "p")}
      {T("Jag planerar, filmar och klipper själv. Det ger korta beslutsvägar och en film som håller ihop hela vägen från idé till leverans.", "I plan, film and edit everything myself. That means short decision paths and a film that holds together all the way from idea to delivery.", "p")}
    </div>
    <div class="doing-side">
      <ul class="doing-list">
        <li data-cat="business"><a href="services.html#business-panel"><span class="doing-num">01</span><span class="doing-text">{T("Företag", "Companies", "strong")}{T("Reklam- och varumärkesfilm, intervjuer, YouTube, klipp för sociala medier och produktbilder.", "Commercials and brand films, interviews, YouTube, social media clips and product photography.", "span")}</span><span class="doing-arrow" aria-hidden="true">→</span></a></li>
        <li data-cat="event"><a href="services.html#event-panel"><span class="doing-num">02</span><span class="doing-text">{T("Evenemang och idrott", "Events and sport", "strong")}{T("Konferenser, lanseringar, matcher och fester, fångade medan de pågår.", "Conferences, launches, matches and parties, captured as they happen.", "span")}</span><span class="doing-arrow" aria-hidden="true">→</span></a></li>
        <li data-cat="wedding"><a href="services.html#wedding-panel"><span class="doing-num">03</span><span class="doing-text">{T("Bröllop", "Weddings", "strong")}{T("Film och foto från vigseln till sista dansen.", "Film and photography from the ceremony to the last dance.", "span")}</span><span class="doing-arrow" aria-hidden="true">→</span></a></li>
        <li data-cat="drone"><a href="services.html#idea"><span class="doing-num">04</span><span class="doing-text">{T("Drönare", "Drone", "strong")}{T("Flygbilder över skärgård, fastigheter och evenemang, där det är tillåtet att flyga.", "Aerial footage of the archipelago, properties and events, wherever flying is permitted.", "span")}</span><span class="doing-arrow" aria-hidden="true">→</span></a></li>
      </ul>
      <p class="doing-note">{T("Något helt annat i tankarna?", "Something else entirely in mind?")} <a href="contact.html">{T("Berätta om det", "Tell me about it")}</a></p>
    </div>
  </div>
</section>







'''
page("index.html", BRAND, BRAND, "home", home, full=False)

# ---------------- WORK ----------------
SECTION[0] = "work"
grid = "\n".join(clip(p) for p in PROJECTS)
data = json.dumps([project_json(p) for p in PROJECTS], ensure_ascii=False).replace("</", "<\\/")
chips = [("all", "Alla", "All"), ("wedding", "Bröllop", "Weddings"), ("business", "Företag", "Companies"),
         ("event", "Evenemang", "Events"), ("drone", "Drönare", "Drone"), ("stills", "Övrigt", "Other")]
chip_html = "".join(f'<button class="chip" data-filter="{f}" aria-pressed="{"true" if f == "all" else "false"}">{T(sv, en)}</button>' for f, sv, en in chips)
work = f'''<div class="wrap page-hero">
  {T("Arbeten", "Work", "span", 'class="eyebrow"')}
  {T("Projekt", "Projects", "h1")}
  {T("Ett urval av projekt. Öppna ett för att se allt material och läsa berättelsen bakom.", "A selection of projects. Open one to see it in full and read the story behind it.", "p", 'class="lede"')}
</div>
<section style="padding-top: 0;">
  <div class="wrap">
    <div class="section-head">
      <div class="filters" role="group" aria-label="Filter">{chip_html}</div>
    </div>
    <div class="reel">
{grid}
    </div>
  </div>
</section>
<div class="modal" id="project-modal" role="dialog" aria-modal="true" aria-labelledby="pm-title" hidden>
  <div class="modal-backdrop" data-close></div>
  <div class="modal-panel" tabindex="-1">
    <div class="modal-bar">
      <div class="modal-nav"><button class="icon-btn" type="button" data-step="-1" aria-label="Föregående / Previous">←</button><button class="icon-btn" type="button" data-step="1" aria-label="Nästa / Next">→</button></div>
      <button class="icon-btn" type="button" data-close aria-label="Stäng / Close">✕</button>
    </div>
    <div class="modal-body" id="pm-body"></div>
  </div>
</div>
<script type="application/json" id="projects">{data}</script>
'''
page("work.html", f"Arbeten · {BRAND}", f"Work · {BRAND}", "work", work)




# ---------------- SERVICES ----------------
SECTION[0] = "services"
def svc_panel(pid, scene, seed, eb, title, intro, lis, btn):
    lis_html = "".join(f"<li>{T(sv, en)}</li>" for sv, en in lis)
    return f'''<article class="svc" id="{pid}-panel">
      <div class="frame" data-scene="{scene}" data-seed="{seed}"></div>
      <div class="wedding-body">
        {T(*eb, "span", 'class="eyebrow"')}
        {T(*title, "h2")}
        {T(*intro, "p", 'class="lede"')}
        <div class="w-panel"><ul>{lis_html}</ul></div>
        {T("Pris enligt offert, utifrån projektets omfattning.", "Price on request, shaped around the scope of the project.", "p", 'class="note"')}
        <div class="actions"><a class="btn primary" href="contact.html">{T(*btn)}{ARROW}</a></div>
      </div>
    </article>'''


biz_panel = svc_panel("business", "interview", 12, ("Företag", "Companies"), ("Ert företag i bild", "Your business on camera"),
    ("Film och bilder som visar vilka ni är, från en halvdag hos er till större produktioner.", "Film and photography that show who you are, from a half-day shoot on site to larger productions."), [
        ("Varumärkes- och reklamfilm", "Brand and commercial film"),
        ("YouTube och korta klipp för sociala medier", "YouTube and short clips for social media"),
        ("Intervjuer och rekryteringsfilm", "Interviews and recruitment film"),
        ("Porträtt och produktbilder för webb och press", "Portraits and product images for web and press")], ("Berätta om projektet", "Tell me about the project"))
evt_panel = svc_panel("event", "event", 23, ("Evenemang", "Events"), ("Ögonblicket", "The moment"),
    ("Lanseringar, konferenser, fester och sport, fångade medan de pågår.", "Launches, conferences, parties and sport, captured as they happen."), [
        ("En film som fångar stämningen", "A film that captures the atmosphere"),
        ("Ett kort klipp för sociala medier samma vecka", "A short social clip the same week"),
        ("Bilder redo att publicera dagen efter", "Images ready to post the next day"),
        ("Korta intervjuer med gäster och talare", "Short interviews with guests and speakers")], ("Fånga ögonblicket", "Capture the moment"))


# ---- Wedding builder: coverage x length, one card, no columns ----
COV = [("photo", "Bilder", "Images"), ("film", "Film", "Film"), ("both", "Båda", "Both")]
LEN = [("3", "3 h", "3 h"), ("6", "6 h", "6 h"), ("10", "Hela dagen", "Full day")]
TIER = {
    "3": ("Intim vigsel", "Intimate ceremony", "3 timmar", "3 hours", "Vigseln, parporträtt och familjebilder", "Ceremony, couple portraits and family photos"),
    "6": ("Halva dagen", "Half-day story", "6 timmar", "6 hours", "Vigseln, porträtt, mingel och middagens viktigaste stunder", "Ceremony, portraits, drinks reception and the key moments of dinner"),
    "10": ("Hela dagen", "The full day", "12+ timmar", "12+ hours", "Hela dagen, från förberedelserna till festen på kvällen", "The whole day, from getting ready to the party at night"),
}
WED = load("wedding.json", {})
_WED_DEFAULT = {"photo_3": "7 800", "photo_6": "13 500", "photo_full": "18 900", "film_3": "8 500", "film_6": "14 000",
                "film_full": "19 900", "both_3": "14 000", "both_6": "23 100", "both_full": "30 700"}


def _price(key):
    v = str(WED.get(key) or _WED_DEFAULT[key]).replace("kr", "").strip()
    digits = re.sub(r"\D", "", v)
    return f"{int(digits):,}".replace(",", " ") if digits else _WED_DEFAULT[key]


PRICE = {(c, l): _price(f"{c}_{'full' if l == '10' else l}") for c in ("photo", "film", "both") for l in ("3", "6", "10")}
IMG = {"3": "300+", "6": "500+", "10": "800+"}
FILM = {
    "3": [("Highlightfilm, 2–3 minuter", "Highlight film, 2–3 minutes"), ("Hela vigseln som egen film", "The full ceremony as its own film")],
    "6": [("Highlightfilm, 3–5 minuter", "Highlight film, 3–5 minutes"), ("Vigseln och talen i sin helhet", "Ceremony and speeches in full"), ("Kort version för sociala medier", "Short version for socials")],
    "10": [("Highlightfilm, 5–7 minuter", "Highlight film, 5–7 minutes"), ("Vigsel, tal och första dansen i sin helhet", "Ceremony, speeches and first dance in full"), ("Längre dokumentärfilm, 15–20 minuter", "Longer documentary film, 15–20 minutes"), ("Kort version för sociala medier", "Short version for socials")],
}
PHOTO_DAYS = {"3": "3", "6": "5", "10": "5"}
FILM_WEEKS = {"3": "4", "6": "6", "10": "6"}


def w_items(cov, ln):
    t = TIER[ln]
    items = [(t[4], t[5])]
    if cov in ("photo", "both"):
        items += [(f"{IMG[ln]} redigerade bilder", f"{IMG[ln]} edited images"),
                  ("Ett första smakprov inom 48 timmar", "A first sneak peek within 48 hours")]
    if cov in ("film", "both"):
        items += FILM[ln]
    if cov == "photo":
        items.append((f"Levereras inom {PHOTO_DAYS[ln]} veckor", f"Delivered within {PHOTO_DAYS[ln]} weeks"))
    elif cov == "film":
        items.append((f"Levereras inom {FILM_WEEKS[ln]} veckor", f"Delivered within {FILM_WEEKS[ln]} weeks"))
    else:
        items.append((f"Bilder inom {PHOTO_DAYS[ln]} veckor, film inom {FILM_WEEKS[ln]} veckor", f"Images within {PHOTO_DAYS[ln]} weeks, film within {FILM_WEEKS[ln]} weeks"))
    return items

def _kr(v):
    return int(v.replace(" ", ""))


def save_line(c, l):
    if c != "both":
        return ""
    diff = _kr(PRICE[("photo", l)]) + _kr(PRICE[("film", l)]) - _kr(PRICE[("both", l)])
    amt = f"{diff:,}".replace(",", " ")
    return f'<p class="w-save">{T(f"Du sparar {amt} kr jämfört med bilder och film var för sig.", f"You save {amt} kr compared with booking images and film separately.", edit=False)}</p>'


panels = []
for c, _, _ in COV:
    for l, _, _ in LEN:
        t = TIER[l]
        lis = "".join(f"<li>{T(a, b)}</li>" for a, b in w_items(c, l))
        hidden = "" if (c, l) == ("both", "10") else " hidden"
        panels.append(f'''<div class="w-panel" data-cov="{c}" data-len="{l}"{hidden}>
            <div class="w-head"><div>{T(t[0], t[1], "h3")}<span class="mono w-hours">{T(t[2], t[3])}</span></div><div class="amount">{PRICE[(c, l)]} kr<span class="vat">{T("inkl. moms", "incl. VAT")}</span></div></div>
            <ul>{lis}</ul>{save_line(c, l)}
          </div>''')


def seg(group, opts, default):
    return (f'<div class="seg pick-seg" role="group" data-group="{group}">' +
            "".join(f'<button type="button" data-val="{v}" aria-pressed="{"true" if v == default else "false"}">{T(sv, en)}</button>' for v, sv, en in opts) + '</div>')


wedding = f'''<article class="svc wedding" id="wedding-panel">
      <div class="frame" data-scene="wedding" data-seed="44"></div>
      <div class="wedding-body wedding-split">
        <div class="w-left">
          {T("Bröllop", "Weddings", "span", 'class="eyebrow"')}
          {T("Välj det som passar er dag", "Choose what fits your day", "h2")}
          <div class="pick">{T("Vad vill ni ha?", "What would you like?", "span", 'class="pick-label"')}{seg("cov", COV, "both")}</div>
          <div class="pick">{T("Hur länge?", "How long?", "span", 'class="pick-label"')}{seg("len", LEN, "10")}</div>
          {T("Alla paket har ett planeringsmöte och ett privat onlinegalleri. Priserna gäller i Stockholms län. En handpenning på 30 % säkrar datumet.", "Every package includes a planning meeting and a private online gallery. Prices apply within Stockholm county. A 30% deposit holds the date.", "p", 'class="note"')}
          <div class="actions"><a class="btn primary" href="contact.html">{T("Fråga om ert datum", "Ask about your date")}{ARROW}</a></div>
        </div>
        <div class="w-panels" aria-live="polite">
          {"".join(panels)}
        </div>
      </div>
    </article>'''


steps = [("01", "Samtalet", "The conversation", "Ett första samtal om idén, vilka som är med och vad du hoppas få ut av det.", "A first conversation about the idea, who's involved and what you hope to get out of it."),
         ("02", "Planeringen", "The plan", "Plats, schema och detaljer gås igenom tillsammans, så att planen utgår från det som är viktigast för dig.", "Location, schedule and details are worked out together, so the plan starts from what matters most to you."),
         ("03", "Dagen", "The day", "Du fokuserar på det som händer. Allt annat är redan ordnat.", "You focus on what's happening. Everything else is taken care of."),
         ("04", "Leveransen", "Delivery", "Ditt färdiga material, levererat i tid och redo att delas.", "Your finished work, delivered on time and ready to share.")]
steps_html = "\n      ".join(f'<li class="tl-step"><span class="tl-dot">{n}</span>{T(hs, he, "h3")}{T(ps, pe, "p")}</li>' for n, hs, he, ps, pe in steps)

addons = [("Resor", "Travel", "Ingår inom Stockholms län. Längre bilresor debiteras per mil, restid inräknad. Flyg och boende läggs till i offerten.", "Included within Stockholm county. Longer trips by car are charged per mil (10 km), travel time included. Flights and accommodation are added to the quote.", T("25 kr/mil", "25 kr/mil")),
          ("Drönare", "Drone", "Flygbilder där det är tillåtet att flyga", "Drone shots where flying is allowed", "2 500 kr"),
          ("Extra timme", "Extra hour", "Mer tid under dagen", "More time on the day", "1 200 kr"),
          ("Råmaterial", "Raw footage", "Alla användbara klipp, sorterade per scen", "All usable clips, sorted by scene", "1 500 kr"),
          ("Expressleverans", "Express delivery", "Leverans på halva den vanliga tiden", "Delivery in half the usual time", "+30 %"),
          ("Tryckta bilder", "Printed frames", "Tio favoriter tryckta på arkivbeständigt papper", "Ten favourites on archival paper", "1 900 kr")]
addon_html = "\n      ".join(f'<div class="addon"><div class="addon-top">{T(a, b, "h3")}<span class="addon-price">{p}</span></div>{T(c, d, "p")}</div>' for a, b, c, d, p in addons)

TABS = [("business", "Företag", "Companies"), ("event", "Evenemang", "Events"), ("wedding", "Bröllop", "Weddings")]
tabs_html = '<div class="seg svc-tabs" role="tablist">' + "".join(
    f'<button type="button" role="tab" data-tab="{k}" aria-selected="{"true" if k == "business" else "false"}" aria-pressed="{"true" if k == "business" else "false"}">{T(sv, en)}</button>' for k, sv, en in TABS) + '</div>'

services = f'''<div class="wrap page-hero">
  {T("Tjänster", "Services", "span", 'class="eyebrow"')}
  {T("Så går ett samarbete till", "Ways to work together", "h1")}
  {T("Allt görs i egen regi, och du är med i varje steg.", "Everything is made in-house, and you're involved in every step.", "p", 'class="lede"')}
</div>

<section style="padding-top: 0;">
  <div class="wrap svc-wrap">
    <div class="svc-grid">
      {biz_panel}
      {evt_panel}
      {wedding}
    </div>
    <div class="idea" id="idea">
      <div class="stack">
        {T("Har du en annan idé?", "Have a different idea?", "h2")}
        {T("Paketen är bara en utgångspunkt. Har du något annat i tankarna skräddarsys ett upplägg efter dig.", "The packages are only a starting point. If you have something else in mind, a setup is tailored to you.", "p", 'class="lede"')}
      </div>
      <a class="btn primary" href="contact.html">{T("Kontakta mig", "Contact me")}{ARROW}</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head">{T("Så går det till", "How it goes", "span", 'class="eyebrow"')}{T("Från första meddelandet till färdig produkt", "From first message to finished product", "h2")}{T("En tydlig process från första samtalet till leverans, där du är med i varje steg.", "A clear process from the first conversation to delivery, with you involved at every step.", "p", 'class="lede"')}</div>
    <ol class="timeline">
      {steps_html}
    </ol>
  </div>
</section>

<section id="addons" style="padding-top:0">
  <div class="wrap">
    <div class="section-head">{T("Tillval", "Add-ons", "span", 'class="eyebrow"')}{T("Tillval efter behov", "Extras as needed", "h2")}</div>
    <div class="addons">
      {addon_html}
    </div>
  </div>
</section>
'''
page("services.html", f"Tjänster · {BRAND}", f"Services · {BRAND}", "services", services)

# ---------------- ABOUT ----------------
SECTION[0] = "about"
# Behind-the-scenes photos for the About page (admin panel: Site settings). Placeholders until there are real ones.
ABOUT_IMGS = [u for u in (media_url(x) for x in (SETTINGS.get("about_images") or [])) if u]
_BTS = [("interview", 64, "4 / 5"), ("event", 27, "16 / 10"), ("aerial", 33, "1 / 1"), ("wedding", 18, "4 / 5"),
        ("studio", 45, "16 / 10"), ("archipelago", 52, "4 / 5"), ("event", 71, "1 / 1"), ("interview", 88, "16 / 10")]
if ABOUT_IMGS:
    BTS_HTML = "".join(f'<a class="bts-item" href="{e(u)}" data-photo="about"><img src="{e(u)}" alt="" loading="lazy" decoding="async"></a>' for u in ABOUT_IMGS)
else:
    BTS_HTML = "".join(f'<figure class="bts-item"><div class="frame" data-scene="{sc}" data-seed="{sd}" style="aspect-ratio: {ar}"></div></figure>'
                       for sc, sd, ar in _BTS)


def book_btn(cls="btn primary"):
    label = T("Boka ett samtal", "Book a call")
    if BOOKING:
        return (f'<a class="{cls}" href="https://cal.com/{e(BOOKING)}" data-cal-link="{e(BOOKING)}" '
                f'data-cal-config=\'{{"layout":"month_view"}}\' target="_blank" rel="noopener">{label}{ARROW}</a>')
    return f'<a class="{cls}" href="contact.html">{label}{ARROW}</a>'


IG_LINK = (f'<a href="{e(INSTAGRAM)}" target="_blank" rel="noopener">Instagram</a>' if INSTAGRAM else "")
about = f'''<section class="about-hero">
  <div class="wrap">
    {T("Om", "About", "span", 'class="eyebrow"')}
    {T("Det här är ME Motion", "This is ME Motion", "h1")}
    <div class="about-intro">
      {T("ME Motion är en studio för film och foto i Stockholm. Uppdragen kommer från företag, evenemang och brudpar, och varje bildruta får samma omsorg oavsett hur stort projektet är.", "ME Motion is a film and photography studio in Stockholm. The work comes from companies, events and couples, and every frame gets the same care however big the project is.", "p", 'class="about-lead"')}
      {T("Allt görs från början till slut av samma person. Samma öga som planerar inspelningen står bakom kameran och sitter sedan vid klippbordet. Det gör vägen kort mellan idé och färdig film, och resultatet håller ihop.", "Everything is made from start to finish by the same person. The eye that plans the shoot is behind the camera and then at the edit. That keeps the path from idea to finished film short, and the result holds together.", "p")}
      {T("Ingen produktion är för liten för att göras ordentligt, och ingen är så stor att den tappar det personliga.", "No production is too small to be done properly, and none is so big that it loses the personal touch.", "p")}
    </div>
  </div>
</section>

<section class="about-facts" aria-label="ME Motion">
  <div class="wrap">
    <dl class="facts-row">
      <div>{T("Bas", "Based in", "dt")}{T("Stockholm", "Stockholm", "dd")}</div>
      <div>{T("Arbetar", "Works", "dt")}{T("I hela Sverige och utomlands", "Across Sweden and abroad", "dd")}</div>
      <div>{T("Gör", "Makes", "dt")}{T("Film, foto och drönarbilder", "Film, photography and aerial footage", "dd")}</div>
      <div>{T("Levererar", "Delivers", "dt")}{T("I de format du behöver", "In the formats you need", "dd")}</div>
    </dl>
  </div>
</section>

<section style="padding-top: 0;">
  <div class="wrap founder-grid">
    {frame(PORTRAIT, "interview", 61, "ratio-4x5", "Mikael Edström", "" if PORTRAIT else vf(meta="4:5"))}
    <div class="stack founder-copy">
      {T("Grundaren", "The founder", "span", 'class="eyebrow"')}
      {T("Mikael Edström", "Mikael Edström", "h2")}
      {T("ME Motion är en studio för visuellt berättande i Stockholm, grundad av Mikael Edström. Uppdragen spänner från företagsfilm och evenemang till bröllop, med samma krav på hantverk oavsett vad det gäller.", "ME Motion is a visual storytelling studio in Stockholm, founded by Mikael Edström. The work spans company films, events and weddings, held to the same standard whatever the assignment.", "p", 'class="lede"')}
      {T("Mikael kombinerar tekniskt kunnande med ett öga för detaljer. Planering och efterarbete får lika mycket omsorg som inspelningen, och målet är bilder som håller även när man ser dem en andra gång.", "Mikael combines technical precision with an eye for detail. Planning and post-production get as much care as the shoot, with the aim of images that still hold up on a second watch.", "p", 'class="lede"')}
    </div>
  </div>
</section>

<section class="approach-sec">
  <div class="wrap">
    <div class="section-head">{T("Om arbetet", "About the work", "span", 'class="eyebrow"')}{T("Arbetssätt", "The approach", "h2")}</div>
    <ol class="approach">
      <li><span class="approach-num">01</span>{T('Varje uppdrag får sin egen ton', 'Every project finds its own tone', "h3")}{T('Inget uppdrag är det andra likt. Uttrycket formas efter det som ska berättas, inte tvärtom.', 'No two projects are alike. The look is shaped by what needs to be told, not the other way around.', "p")}</li>
      <li><span class="approach-num">02</span>{T('Rätt format från början', 'The right format from the start', "h3")}{T('Materialet levereras i de format det ska användas i, från bred film till stående klipp för sociala medier.', 'Everything is delivered in the formats it will be used in, from widescreen film to vertical clips for social media.', "p")}</li>
      <li><span class="approach-num">03</span>{T('Detaljerna gör helheten', 'The details make the whole', "h3")}{T('Ljus, ljud och klipp får samma omsorg som själva inspelningen.', 'Light, sound and cut get the same care as the shoot itself.', "p")}</li>
    </ol>
  </div>
</section>

<section class="bts-sec">
  <div class="wrap">
    <div class="section-head">{T("Bakom kulisserna", "Behind the scenes", "span", 'class="eyebrow"')}{T("På plats", "On location", "h2")}</div>
  </div>
  <div class="bts">{BTS_HTML}</div>
</section>

<section class="about-contact">
  <div class="wrap">
    {T("Kontakt", "Contact", "span", 'class="eyebrow"')}
    {T("Har du ett projekt på gång?", "Got a project in mind?", "h2")}
    <div class="about-contact-grid">
      <div class="about-contact-lines">
        <a class="big-link" href="mailto:{e(EMAIL)}">{e(EMAIL)}</a>
        {f'<a class="big-link" href="tel:{e(PHONE_TEL)}">{e(PHONE)}</a>' if PHONE else ""}
        <p class="mono about-place">{T("Stockholm, Sverige", "Stockholm, Sweden")}{(" · " + IG_LINK) if IG_LINK else ""}</p>
      </div>
      <div class="actions">
        {book_btn()}
        <a class="btn" href="contact.html">{T("Skicka ett meddelande", "Send a message")}{ARROW}</a>
      </div>
    </div>
  </div>
</section>
'''
page("about.html", f"Om · {BRAND}", f"About · {BRAND}", "about", about)


# ---------------- CONTACT ----------------
SECTION[0] = "contact"
def fseg(group, opts, mode):
    cls = "seg form-seg" if mode == "single" else "chips-multi"
    return (f'<div class="{cls}" role="group" data-group="{group}" data-mode="{mode}">' +
            "".join(f'<button type="button" data-val="{v}" data-sv="{sv}" data-en="{en}" aria-pressed="false">{T(sv, en)}</button>' for v, sv, en in opts) + '</div>')


def opt(sv, en):
    return f'<option data-sv="{sv}" data-en="{en}">{sv}</option>'


faq = [("Hur långt i förväg behöver jag boka?", "How far in advance do I need to book?",
        "Vanligtvis rekommenderas att boka 6–9 månader i förväg. Men även med kort varsel går det ofta att lösa, så hör av dig ändå.",
        "It's usually recommended to book 6–9 months ahead. But even at short notice it can often be arranged, so get in touch anyway."),
       ("Hur hittar ni berättelsen?", "How do you find the story?",
        "Genom att lyssna först. Innan kameran kommer fram pratar man igenom vad och vilka som är viktiga, och vad du vill känna när du ser resultatet. Berättelsen finns oftast redan där. Uppgiften är att se den.",
        "By listening first. Before the camera comes out, the conversation covers what matters, who matters and what you want to feel when you look back on it. The story is usually already there. The job is to notice it."),
       ("Hur mycket behöver jag planera själv?", "How much of the planning do I need to do?",
        "Väldigt lite. Berätta vad som känns viktigt för dig, så tar ME Motion hand om upplägget, tiderna och detaljerna.",
        "Very little. Share whatever feels important to you, and ME Motion takes care of the plan, the timing and the details."),
       ("Jobbar ni utanför Stockholm?", "Do you work outside Stockholm?",
        "Ja, både i Sverige och utomlands. Resekostnaden beror på avstånd och färdsätt och finns alltid med i offerten.",
        "Yes, both in Sweden and abroad. Travel costs depend on the distance and the way of travel, and they're always part of your quote."),
       ("Vad får jag när allt är klart?", "What do I get in the end?",
        "Färdigt material, redo att använda. Film i de format du behöver, från bred film till stående klipp, och bilder i full upplösning för webb och tryck. Allt levereras via en privat länk, på det datum som bestämts från start.",
        "Finished material, ready to use. Film in the formats you need, from widescreen to vertical clips, and images in full resolution for web and print. Everything is delivered via a private link, on the date agreed from the start.")]
faq_html = "\n          ".join(
    f'<details{" open" if i == 0 else ""}><summary>{T(qs, qe)}</summary>{T(as_, ae, "p")}</details>'
    for i, (qs, qe, as_, ae) in enumerate(faq))

contact = f'''<div class="wrap page-hero">
  {T("Kontakt", "Contact", "span", 'class="eyebrow"')}
  {T("Kontakta mig", "Contact me", "h1")}
  {T("Berätta lite om vad du planerar. Datumet får gärna vara ungefärligt. Alla meddelanden läses och besvaras personligen.", "Share a little about what you're planning. The date can be rough. Every message is read and answered personally.", "p", 'class="lede"')}
</div>
<section style="padding-top: 0;">
  <div class="wrap two-col">
    <div class="stack">
      <form class="form" id="enquiry" novalidate data-send="https://formsubmit.co/ajax/{e(EMAIL)}">
        <input type="text" name="_honey" id="hp-field" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0">
        <div class="row">
          <div class="field"><label for="name">{T("Namn", "Name")}</label><input id="name" autocomplete="name"><span class="err" id="name-err" hidden>{T("Skriv ditt namn.", "Add your name.")}</span></div>
          <div class="field"><label for="email">{T("E-post", "Email")}</label><input id="email" type="email" autocomplete="email"><span class="err" id="email-err" hidden>{T("Skriv en e-postadress, t.ex. namn@exempel.se.", "Add an email address like name@example.se.")}</span></div>
        </div>
        <div class="field" id="occasion">
          {T("Vad gäller det?", "What's it about?", "span", 'class="flabel"')}
          {fseg("type", [("business", "Företag", "Company"), ("event", "Evenemang", "Event"), ("wedding", "Bröllop", "Wedding"), ("other", "Något annat", "Something else")], "single")}
          <div class="sub" data-for="wedding" hidden>
            {fseg("wcov", COV, "single")}
            {fseg("wlen", LEN, "single")}
          </div>
        </div>
        <div class="row">
          <div class="field"><label for="phone">{T("Telefon (valfritt)", "Phone (optional)")}</label><input id="phone" type="tel" autocomplete="tel"></div>
          <div class="field"><label for="date">{T("Datum", "Date")}</label><input id="date" type="date"></div>
        </div>
        <div class="field"><label for="location">{T("Plats", "Location")}</label><input id="location" data-sv-placeholder="t.ex. Grand Hôtel, Stockholm" data-en-placeholder="e.g. Grand Hôtel, Stockholm" placeholder="t.ex. Grand Hôtel, Stockholm"></div>
        <div class="field"><label for="message">{T("Berätta mer", "The details")}</label><textarea id="message" data-sv-placeholder="Kort om projektet: vad det gäller, ungefär hur stort det är och annat som är bra att veta." data-en-placeholder="A few lines about the project: what it is, roughly how big, and anything else that's good to know." placeholder="Kort om projektet: vad det gäller, ungefär hur stort det är och annat som är bra att veta."></textarea><span class="err" id="message-err" hidden>{T("Skriv några rader om vad du planerar.", "Write a few lines about what you're planning.")}</span></div>
        <div><button class="btn primary" type="submit">{T("Skicka meddelande", "Send message")}{ARROW}</button></div>
      </form>
      <div class="result sent" id="enquiry-sent" hidden tabindex="-1" aria-live="polite">
        {T("Tack! Meddelandet är skickat.", "Thank you! Your message has been sent.", "strong")}
        {T("Svaret kommer till e-postadressen du angav.", "The reply will come to the email address you entered.", "p", 'class="note"')}
      </div>
      <div class="result send-error" id="enquiry-error" hidden tabindex="-1" aria-live="assertive">
        {T("Meddelandet kunde inte skickas.", "The message couldn't be sent.", "strong")}
        {T("Kontrollera internetanslutningen och försök igen om en stund. Det går också bra att skriva direkt till", "Check your internet connection and try again in a moment. You can also write directly to", "p", 'class="note"')}
        <p class="note"><span class="mono">{EMAIL}</span></p>
      </div>
    </div>
    <div class="stack" style="gap:32px">
      <div class="stack">
        {T("Kontaktuppgifter", "Contact details", "span", 'class="eyebrow"')}
        <p class="contact-line"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
        <p class="contact-line"><a href="tel:{PHONE_TEL}">{PHONE}</a></p>
      </div>
      <div class="stack">
        {T("FAQ", "FAQ", "span", 'class="eyebrow faq-eyebrow"')}
        <div class="faq">
          {faq_html}
        </div>
      </div>
    </div>
  </div>
</section>'''
page("contact.html", f"Kontakt · {BRAND}", f"Contact · {BRAND}", "contact", contact)


# ---------------- KEEP THE ADMIN PANEL'S TEXT LIST UP TO DATE ----------------
TEXTS_MARK = "# ===== Website texts: made automatically by build.py. Edit the texts in the admin panel, not here. ====="


def sync_texts():
    """Write content/texts/*.json and the matching 'Texts – ...' sections of .pages.yml.
    Texts already edited in the admin panel are kept."""
    old = {}
    for f in TEXT_DIR.glob("*.json") if TEXT_DIR.is_dir() else []:
        try:
            for v in json.loads(f.read_text(encoding="utf-8")).values():
                if isinstance(v, dict) and v.get("orig"):
                    old[v["orig"]] = v
        except Exception:
            pass
    TEXT_DIR.mkdir(exist_ok=True)
    yml = [TEXTS_MARK]
    for sec, label in TEXT_PAGES:
        rows = [(orig, en) for orig, (s, _sv, en) in SEEN.items() if s == sec and re.search(r"[A-Za-zÅÄÖåäö]", orig)]
        data = {}
        fields = []
        for i, (orig, en) in enumerate(rows, 1):
            key = f"{sec}_{i:03d}"
            o = old.get(orig, {})
            sv_cur = str(o.get("sv") or "").strip() or orig
            en_cur = str(o.get("en") or "").strip()
            if not en_cur or en_cur == o.get("orig_en"):
                en_cur = en   # not edited: follow the website's own English
            data[key] = {"orig": orig, "orig_en": en, "sv": sv_cur, "en": en_cur}
            name = re.sub(r"<[^>]+>", "", html.unescape(orig))
            name = (name[:70] + "…") if len(name) > 72 else name
            fields.append(f"  - name: {key}\n    label: {json.dumps(name, ensure_ascii=False)}\n    type: object\n    fields:\n"
                          "    - {name: orig, type: string, hidden: true}\n    - {name: orig_en, type: string, hidden: true}\n"
                          "    - {name: sv, label: Svenska, type: text}\n    - {name: en, label: English, type: text}")
        (TEXT_DIR / f"{sec}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        yml.append(f"- name: texts_{sec}\n  label: {json.dumps(label, ensure_ascii=False)}\n  type: file\n"
                   f"  path: content/texts/{sec}.json\n  format: json\n  fields:\n" + "\n".join(fields))
    cfg = ROOT / ".pages.yml"
    base = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    base = base.split(TEXTS_MARK)[0].rstrip() + "\n\n"
    cfg.write_text(base + "\n".join(yml) + "\n", encoding="utf-8")
    print(f"texts: {sum(1 for s in SEEN.values() if s[0])} texts written to content/texts and .pages.yml")


(OUT / "version.json").write_text(json.dumps({"build": BUILD_ID}) + "\n", encoding="utf-8")
if os.environ.get("SYNC_TEXTS") == "1":
    sync_texts()
print("ok")
