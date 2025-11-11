import base64
import logging
import mimetypes
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def read_uri_data(uri: str, relative_to: Path | None = None):
    mimetype, _encoding = mimetypes.guess_type(uri)

    url = urllib.parse.urlparse(uri, "file")
    if url.scheme == "file":
        url = urllib.parse.urlparse(str(Path(relative_to or ".") / url.path), "file")
    url_to_read = url.geturl()

    logger.info("reading %s", url_to_read)
    return (
        urllib.request.urlopen(url_to_read).read(),
        mimetype or "application/octet-stream",
    )


def encode_data_uri(data: bytes, mime_type: str = "application/octet-stream"):
    return f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
