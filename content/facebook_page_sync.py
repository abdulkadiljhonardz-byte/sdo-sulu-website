"""Official Meta Graph API sync for the configured SDO Sulu Facebook Page."""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timezone as dt_timezone
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User

from .facebook_import import FacebookImportError, download_facebook_image
from .models import News


MAX_API_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 100
MEMO_PATTERN = re.compile(
    r"(?:\bmemorandum\b|\bdivision\s+memo\b|\boffice\s+memo\b|"
    r"\bunnumbered\s+memo\b|\bdeped\s+memo\b|\bdm\s*(?:no\.?|number|#))",
    re.IGNORECASE,
)


class FacebookPageSyncError(Exception):
    """An administrator-safe Facebook Page synchronization error."""


@dataclass
class FacebookSyncSummary:
    imported: int = 0
    duplicates: int = 0
    excluded_memos: int = 0
    outside_date_range: int = 0
    incomplete: int = 0
    failed: int = 0
    scanned: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


def is_memorandum(text):
    return bool(MEMO_PATTERN.search(text or ""))


def _post_text(post):
    parts = [post.get("message", "")]
    attachments = ((post.get("attachments") or {}).get("data") or [])
    for attachment in attachments:
        parts.extend(
            [
                attachment.get("title", ""),
                attachment.get("description", ""),
            ]
        )
    return "\n".join(part for part in parts if part).strip()


def _title_from_caption(caption):
    lines = [" ".join(line.split()) for line in caption.splitlines() if line.strip()]
    candidate = lines[0] if lines else "SDO Sulu News Update"
    candidate = candidate.lstrip("# ")
    if len(candidate) < 18 and len(lines) > 1:
        candidate = f"{candidate} — {lines[1]}"
    if len(candidate) > 255:
        candidate = candidate[:252].rstrip() + "..."
    return candidate or "SDO Sulu News Update"


def _unique_slug(title):
    base = slugify(title)[:45] or "facebook-news"
    candidate = base
    index = 2
    while News.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _created_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise FacebookPageSyncError("Facebook returned an invalid post date.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


def _read_json(response):
    payload = response.read(MAX_API_RESPONSE_BYTES + 1)
    if len(payload) > MAX_API_RESPONSE_BYTES:
        raise FacebookPageSyncError("Facebook returned an unexpectedly large response.")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FacebookPageSyncError("Facebook returned an unreadable response.") from exc
    if "error" in data:
        error = data["error"] or {}
        message = error.get("message", "Facebook rejected the Page request.")
        raise FacebookPageSyncError(f"Facebook API error: {message}")
    return data


def _fetch_posts(start_date, end_date):
    token = settings.FACEBOOK_PAGE_ACCESS_TOKEN.strip()
    page_id = settings.FACEBOOK_PAGE_ID.strip()
    version = settings.FACEBOOK_GRAPH_API_VERSION.strip()
    if not token:
        raise FacebookPageSyncError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured. Add the official Page token to .env first."
        )
    if not page_id.isdigit():
        raise FacebookPageSyncError("FACEBOOK_PAGE_ID must be the configured numeric SDO Page ID.")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise FacebookPageSyncError("FACEBOOK_GRAPH_API_VERSION has an invalid format.")

    since = datetime.combine(start_date, time.min, tzinfo=dt_timezone.utc)
    until = datetime.combine(end_date, time.max, tzinfo=dt_timezone.utc)
    after = ""
    for _ in range(MAX_PAGES):
        params = {
            "fields": "id,message,created_time,permalink_url,full_picture,attachments{media_type,title,description,url}",
            "since": int(since.timestamp()),
            "until": int(until.timestamp()),
            "limit": 100,
        }
        if after:
            params["after"] = after
        endpoint = f"https://graph.facebook.com/{version}/{page_id}/posts?{urlencode(params)}"
        request = Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "SDOSuluPortal/1.0",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = _read_json(response)
        except HTTPError as exc:
            try:
                data = _read_json(exc)
            except FacebookPageSyncError as api_exc:
                raise api_exc from exc
            raise FacebookPageSyncError(f"Facebook request failed with HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise FacebookPageSyncError("The Facebook Page feed could not be reached.") from exc

        posts = data.get("data")
        if not isinstance(posts, list):
            raise FacebookPageSyncError("Facebook returned an invalid Page feed.")
        yield from posts
        after = (((data.get("paging") or {}).get("cursors") or {}).get("after") or "")
        if not after or not posts:
            break
    else:
        raise FacebookPageSyncError("Facebook pagination exceeded the safe synchronization limit.")


def sync_facebook_news(
    *, start_date=date(2026, 1, 1), end_date=date(2027, 12, 31), publish=True
):
    if start_date.year < 2026 or end_date.year > 2027 or end_date < start_date:
        raise FacebookPageSyncError("This sync is restricted to calendar years 2026 and 2027.")

    summary = FacebookSyncSummary()
    author = None
    author_username = settings.FACEBOOK_SYNC_AUTHOR.strip()
    if author_username:
        author = User.objects.filter(username=author_username, is_active=True).first()

    for post in _fetch_posts(start_date, end_date):
        summary.scanned += 1
        post_id = str(post.get("id") or "").strip()
        source_url = str(post.get("permalink_url") or "").strip()
        caption = _post_text(post)
        image_url = str(post.get("full_picture") or "").strip()
        try:
            created_at = _created_time(post.get("created_time"))
        except FacebookPageSyncError as exc:
            summary.failed += 1
            summary.errors.append(str(exc))
            continue
        if created_at.date() < start_date or created_at.date() > end_date:
            summary.outside_date_range += 1
            continue
        if is_memorandum(caption):
            summary.excluded_memos += 1
            continue
        if not post_id or not source_url or not caption or not image_url:
            summary.incomplete += 1
            continue
        if News.objects.filter(facebook_post_id=post_id).exists() or News.objects.filter(
            source_url=source_url
        ).exists():
            summary.duplicates += 1
            continue
        try:
            image_bytes, image_name, _ = download_facebook_image(image_url, source_url)
        except FacebookImportError as exc:
            summary.failed += 1
            if len(summary.errors) < 20:
                summary.errors.append(f"Post {post_id}: {exc}")
            continue

        title = _title_from_caption(caption)
        with transaction.atomic():
            news = News(
                title=title,
                slug=_unique_slug(title),
                body=caption,
                category="Facebook News",
                source_url=source_url,
                source_imported_at=timezone.now(),
                facebook_post_id=post_id,
                author=author,
                published_at=created_at,
                is_published=publish,
            )
            news.cover_image.save(image_name, ContentFile(image_bytes), save=False)
            news.save()
        summary.imported += 1

    return summary
