"""Turns the plain-text story body an author types into safe HTML.

Authors write in a plain textarea, so this module is what lets them drop
things into the middle of a sentence:

* a bare link — ``https://example.com/report``
* a labelled link — ``[the full report](https://example.com/report)``
* a YouTube link on a line of its own, which becomes a playable embed

Everything is escaped first and links are rebuilt from a vetted scheme list,
so nothing an author pastes can inject markup into the page.
"""

import re
from urllib.parse import parse_qs, urlparse

from django.utils.html import escape
from django.utils.safestring import mark_safe

# Schemes we are willing to turn into a clickable <a>. Anything else
# (javascript:, data:, file: …) is left as plain text.
ALLOWED_SCHEMES = {"http", "https", "mailto"}

# Either [label](url) or a bare http(s):// / www. URL.
_TOKEN_RE = re.compile(
    r"\[(?P<label>[^\]\n]+)\]\(\s*(?P<md_url>[^\s)]+)\s*\)"
    r"|(?P<url>(?:https?://|www\.)[^\s<>\"']+)",
    re.IGNORECASE,
)

# Punctuation that is almost always sentence punctuation rather than part of
# the address when it trails a bare URL.
_TRAILING_PUNCTUATION = ".,;:!?'\""

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_YOUTUBE_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
_START_RE = re.compile(r"^(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?P<s>\d+)s?$")


def normalize_url(raw):
    """Return a safe absolute URL, or None if we should not link to it."""
    if not raw:
        return None
    url = raw.strip()
    if url.lower().startswith("www."):
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return None
    if parsed.scheme.lower() != "mailto" and not parsed.netloc:
        return None
    return url


def _start_seconds(value):
    """YouTube start offsets come as `90`, `90s` or `1h2m30s`."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return int(value)
    match = _START_RE.match(value)
    if not match:
        return None
    hours = int(match.group("h") or 0)
    minutes = int(match.group("m") or 0)
    seconds = int(match.group("s") or 0)
    total = hours * 3600 + minutes * 60 + seconds
    return total or None


def youtube_video(url):
    """Return ``(video_id, start_seconds)`` for a YouTube URL, else None."""
    safe = normalize_url(url)
    if not safe:
        return None
    parsed = urlparse(safe)
    host = parsed.netloc.lower()
    path = parsed.path or ""
    query = parse_qs(parsed.query)

    video_id = None
    if host in _YOUTUBE_SHORT_HOSTS:
        video_id = path.lstrip("/").split("/")[0]
    elif host in _YOUTUBE_HOSTS:
        if path == "/watch":
            video_id = (query.get("v") or [""])[0]
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "v", "live"}:
                video_id = parts[1]

    if not video_id or not _VIDEO_ID_RE.match(video_id):
        return None

    start = _start_seconds((query.get("t") or query.get("start") or [""])[0])
    return video_id, start


def embed_url(video_id, start=None):
    url = f"https://www.youtube-nocookie.com/embed/{video_id}"
    if start:
        url = f"{url}?start={start}"
    return url


def find_videos(text, limit=None):
    """Every YouTube video referenced in a body, in the order they appear."""
    found = []
    for match in _TOKEN_RE.finditer(text or ""):
        raw = match.group("md_url") or _strip_trailing_punctuation(match.group("url"))
        video = youtube_video(raw)
        if video and video[0] not in [v[0] for v in found]:
            found.append(video)
            if limit and len(found) >= limit:
                break
    return found


def _strip_trailing_punctuation(url):
    """`See https://example.com/report.` should not link the full stop."""
    while url and url[-1] in _TRAILING_PUNCTUATION:
        url = url[:-1]
    # Only drop a closing bracket when it is unbalanced.
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


def _anchor(url, label):
    return (
        f'<a class="story-link" href="{escape(url)}" target="_blank" '
        f'rel="noopener noreferrer nofollow">{escape(label)}</a>'
    )


def _render_inline(text, allow_links=True):
    """Escape a paragraph and turn its links into anchors."""
    out = []
    cursor = 0
    for match in _TOKEN_RE.finditer(text):
        out.append(escape(text[cursor:match.start()]))
        cursor = match.end()

        if match.group("md_url") is not None:
            label = match.group("label")
            url = normalize_url(match.group("md_url"))
            fallback = match.group(0)
        else:
            raw = _strip_trailing_punctuation(match.group("url"))
            # Anything we trimmed off is punctuation, not part of the link.
            cursor = match.start() + len(raw)
            label = raw
            url = normalize_url(raw)
            fallback = raw

        if url and allow_links:
            out.append(_anchor(url, label))
        else:
            out.append(escape(fallback))

    out.append(escape(text[cursor:]))
    return "".join(out)


def _lone_video(block):
    """If a paragraph is nothing but a YouTube link, return (video, caption)."""
    matches = list(_TOKEN_RE.finditer(block))
    if len(matches) != 1:
        return None
    match = matches[0]
    if match.group(0).strip() != block.strip():
        return None

    if match.group("md_url") is not None:
        video = youtube_video(match.group("md_url"))
        caption = match.group("label")
    else:
        video = youtube_video(_strip_trailing_punctuation(match.group("url")))
        caption = ""
    if not video:
        return None
    return video, caption


def _render_embed(video, caption):
    video_id, start = video
    caption_html = f"<figcaption>{escape(caption)}</figcaption>" if caption else ""
    return (
        '<figure class="video-embed">'
        '<div class="video-frame">'
        f'<iframe src="{escape(embed_url(video_id, start))}" '
        'title="YouTube video player" loading="lazy" allowfullscreen '
        'referrerpolicy="strict-origin-when-cross-origin" '
        'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; '
        'picture-in-picture; web-share"></iframe>'
        "</div>"
        f"{caption_html}"
        "</figure>"
    )


def render_body(text, allow_links=True, embed_videos=True):
    """Render a story body as HTML.

    ``allow_links`` and ``embed_videos`` are the author's per-story switches:
    with links off, addresses stay as plain text; with embedding off, a
    YouTube address is treated like any other link.
    """
    blocks = [block.strip() for block in (text or "").split("\n") if block.strip()]
    html = []
    for block in blocks:
        if embed_videos:
            lone = _lone_video(block)
            if lone:
                html.append(_render_embed(*lone))
                continue
        html.append(f"<p>{_render_inline(block, allow_links=allow_links)}</p>")
    return mark_safe("".join(html))
