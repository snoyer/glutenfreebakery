import base64
import logging
import mimetypes
import urllib.request
from pathlib import Path
from urllib.error import URLError

logger = logging.getLogger(__name__)


def read_uri_data(uri: str, relative_to: Path | None = None):
    mimetype, _encoding = mimetypes.guess_type(uri)
    mimetype = mimetype or "application/octet-stream"

    if not uri.startswith("data:"):
        logger.info("reading %r", uri)

    try:
        return urllib.request.urlopen(uri).read(), mimetype
    except ValueError:
        fixed_path = Path(relative_to or ".") / uri
        try:
            return fixed_path.read_bytes(), mimetype
        except IOError as e:
            raise URLError(e.strerror or "unknown IO error", uri)


def guess_extension(mime_type: str, default: str = ".bin"):
    if mime_type == "application/gltf-buffer":  # hardcoded because not cross-platform
        return ".glbin"
    return mimetypes.guess_extension(mime_type) or default


def encode_data_uri(data: bytes, mime_type: str = "application/octet-stream"):
    return f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
