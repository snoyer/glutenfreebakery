import base64
import logging
import mimetypes
from urllib.error import URLError
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def read_uri_data(uri: str, relative_to: Path | None = None):
    mimetype, _encoding = mimetypes.guess_type(uri)
    mimetype = mimetype or "application/octet-stream"

    def uri_is_file():
        try:
            url = urllib.parse.urlparse(uri, "file")
            if url.scheme == "file":
                return url.path
        except URLError:  # can be caused by Windows drive letter
            return uri

    if path := uri_is_file():
        fixed_path = Path(relative_to or ".") / path
        try:
            return fixed_path.read_bytes(), mimetype
        except IOError as e:
            raise URLError(e.strerror or "unknown IO error", uri)
    else:
        logger.info("reading %s", uri)
        return urllib.request.urlopen(uri).read(), mimetype


def guess_extension(mime_type: str, default: str = ".bin"):
    if mime_type == "application/gltf-buffer":  # hardcoded because not cross-platform
        return ".glbin"
    return mimetypes.guess_extension(mime_type) or default


def encode_data_uri(data: bytes, mime_type: str = "application/octet-stream"):
    return f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
