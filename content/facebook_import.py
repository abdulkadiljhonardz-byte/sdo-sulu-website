"""Safe, best-effort importer for public Facebook post metadata.

Facebook can require authentication or decline automated metadata requests.  The
portal therefore imports only metadata Facebook makes public and returns a clear
error instead of silently creating incomplete content.
"""

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
FACEBOOK_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
    "mbasic.facebook.com",
    "fb.watch",
    "www.fb.watch",
}
IMAGE_HOST_SUFFIXES = (".fbcdn.net", ".facebook.com", ".fbsbx.com")


class FacebookImportError(Exception):
    """A public, administrator-safe import error."""


@dataclass(frozen=True)
class ImportedFacebookPost:
    url: str
    title: str
    caption: str
    image_bytes: bytes
    image_name: str
    image_content_type: str


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
        self.page_title = ""
        self._inside_title = False

    def handle_starttag(self, tag, attrs):
        attributes = {key.lower(): value for key, value in attrs if value}
        if tag.lower() == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            value = attributes.get("content", "").strip()
            if key and value and key not in self.values:
                self.values[key] = value
        elif tag.lower() == "title":
            self._inside_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data):
        if self._inside_title:
            self.page_title += data


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, *, image=False):
        super().__init__()
        self.image = image

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _normalise_url(newurl, image=self.image)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _hostname_is_public(hostname):
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FacebookImportError("The Facebook address could not be reached.") from exc
    if not addresses:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            return False
    return True


def _normalise_url(value, *, image=False):
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except (AttributeError, ValueError) as exc:
        raise ValidationError("Enter a valid Facebook post link.") from exc
    hostname = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme.lower() != "https" or not hostname or parts.username or parts.password:
        raise ValidationError("Use a secure public Facebook link beginning with https://.")
    if port not in (None, 443):
        raise ValidationError("The Facebook link uses an unsupported network port.")
    if image:
        allowed = hostname in FACEBOOK_HOSTS or any(
            hostname.endswith(suffix) for suffix in IMAGE_HOST_SUFFIXES
        )
    else:
        allowed = hostname in FACEBOOK_HOSTS
    if not allowed:
        raise ValidationError("Only public facebook.com or fb.watch links are supported.")
    if not image:
        path = (parts.path or "/").lower()
        looks_like_post = hostname.endswith("fb.watch") and path != "/"
        looks_like_post = looks_like_post or any(
            marker in path
            for marker in (
                "/posts/",
                "/share/",
                "/photo",
                "/permalink",
                "/story.php",
                "/reel/",
                "/videos/",
                "/watch/",
            )
        )
        if not looks_like_post:
            raise ValidationError("Enter a direct link to a Facebook post, photo, reel, or video.")
    return urlunsplit(("https", parts.netloc, parts.path or "/", parts.query, ""))


def validate_facebook_url(value):
    return _normalise_url(value)


def _read_response(response, limit):
    declared = response.headers.get("Content-Length")
    if declared:
        try:
            if int(declared) > limit:
                raise FacebookImportError("The Facebook response is too large to import safely.")
        except ValueError:
            pass
    payload = response.read(limit + 1)
    if len(payload) > limit:
        raise FacebookImportError("The Facebook response is too large to import safely.")
    return payload


def _open(url, *, accept):
    hostname = urlsplit(url).hostname
    if not hostname or not _hostname_is_public(hostname):
        raise FacebookImportError("The link does not resolve to a public internet address.")
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "Mozilla/5.0 (compatible; SDOSuluPortal/1.0; +https://sulu.deped.gov.ph/)",
        },
    )
    try:
        return build_opener(
            _SafeRedirectHandler(image=accept.startswith("image/"))
        ).open(request, timeout=10)
    except ValidationError as exc:
        raise FacebookImportError(str(exc)) from exc
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise FacebookImportError(
            "Facebook did not allow this post to be imported. Confirm that the post is public, or upload the photo and caption manually."
        ) from exc


def _clean_text(value):
    return " ".join(unescape(value or "").replace("\u00a0", " ").split()).strip()


def _derive_title(title, caption):
    title = _clean_text(title)
    caption = _clean_text(caption)
    if not title or title.lower() in {"facebook", "log into facebook"}:
        title = caption
    for suffix in (" | Facebook", " - Facebook"):
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return (title or caption)[:255].strip(" -|")


def download_facebook_image(image_url, page_url="https://www.facebook.com/"):
    absolute_url = urljoin(page_url, image_url)
    try:
        safe_url = _normalise_url(absolute_url, image=True)
    except ValidationError as exc:
        raise FacebookImportError("Facebook returned an image from an unsupported host.") from exc
    with _open(safe_url, accept="image/jpeg,image/png") as response:
        content_type = response.headers.get_content_type().lower()
        if content_type not in {"image/jpeg", "image/png"}:
            raise FacebookImportError("Facebook did not return a supported JPG or PNG photo.")
        image_bytes = _read_response(response, MAX_IMAGE_BYTES)
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.width * image.height > 40_000_000:
                raise FacebookImportError("The Facebook photo dimensions are too large.")
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise FacebookImportError("The Facebook photo could not be verified as a safe image.") from exc
    if image_format not in {"JPEG", "PNG"}:
        raise FacebookImportError("Only JPG and PNG Facebook photos can be imported.")
    extension = "jpg" if image_format == "JPEG" else "png"
    return image_bytes, f"facebook-cover.{extension}", content_type


def import_facebook_post(value, *, require_text=True):
    """Return caption and cover image exposed by a public Facebook post."""
    try:
        safe_url = validate_facebook_url(value)
    except ValidationError as exc:
        raise FacebookImportError(" ".join(exc.messages)) from exc
    with _open(safe_url, accept="text/html,application/xhtml+xml") as response:
        if response.headers.get_content_type().lower() not in {"text/html", "application/xhtml+xml"}:
            raise FacebookImportError("The supplied link is not a Facebook post page.")
        html = _read_response(response, MAX_HTML_BYTES)
        charset = response.headers.get_content_charset() or "utf-8"
        final_url = response.geturl()
    parser = _MetadataParser()
    try:
        decoded_html = html.decode(charset, errors="replace")
    except LookupError:
        decoded_html = html.decode("utf-8", errors="replace")
    parser.feed(decoded_html)
    caption = _clean_text(
        parser.values.get("og:description") or parser.values.get("description")
    )
    title = _derive_title(parser.values.get("og:title") or parser.page_title, caption)
    image_url = parser.values.get("og:image")
    if require_text and (not title or not caption):
        raise FacebookImportError(
            "The post caption is not publicly available. Confirm that the post is Public, or copy the caption manually."
        )
    if not image_url:
        raise FacebookImportError(
            "No public photo was found in this Facebook post. Upload a cover photo manually instead."
        )
    image_bytes, image_name, image_content_type = download_facebook_image(image_url, final_url)
    return ImportedFacebookPost(
        url=safe_url,
        title=title,
        caption=caption,
        image_bytes=image_bytes,
        image_name=image_name,
        image_content_type=image_content_type,
    )
