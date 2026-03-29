import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Thread
from urllib.error import URLError

from pytest import LogCaptureFixture, mark, raises

from glutenfreebakery.gltf import Gltf2
from glutenfreebakery.schema import DataBuffer, GltfRoot
from glutenfreebakery.schema_io import (
    BIN_CHUNK_TYPE,
    JSON_CHUNK_TYPE,
    load_gltf_dict,
    normalize_json_dict,
    read_glb,
    write_glb_chunks,
)
from glutenfreebakery.util import encode_data_uri, read_uri_data


def test_load_gltf_unexpected_type():
    gltf = GltfRoot()
    with raises(ValueError) as e:
        load_gltf_dict({"samplers": [{"wrapT": "wrong type"}]}, gltf)
    assert "unexpected type for wrapT" in str(e)


def test_normalize_alpha_cutoff():
    data = {
        "materials": [
            {
                "alphaMode": "OPAQUE",
                "alphaCutoff": 0.8,
            }
        ]
    }
    normalize_json_dict(data)
    assert "alphaCutoff" not in repr(data)


def test_normalize_byteOffset():
    data = {
        "accessors": [
            {
                "byteOffset": 0,
                "sparse": {
                    "indices": {
                        "byteOffset": 0,
                    },
                    "values": {
                        "byteOffset": 0,
                    },
                },
            }
        ],
        "bufferViews": [
            {"byteOffset": 0},
            {"byteOffset": 0},
        ],
    }
    normalize_json_dict(data)
    assert "byteOffset" not in repr(data)


def test_normalize_extensionsRequired():
    data = {"extensionsRequired": ["foo", "bar"]}
    normalize_json_dict(data)
    assert data == {"extensionsRequired": ["bar", "foo"]}


def test_encode_data_uri():
    assert (
        encode_data_uri(bytes([1, 2, 3])) == "data:application/octet-stream;base64,AQID"
    )
    assert (
        encode_data_uri(bytes([1, 2, 3]), "application/gltf-buffer")
        == "data:application/gltf-buffer;base64,AQID"
    )


def test_read_data_uri():
    data, mime = read_uri_data("data:application/gltf-buffer;base64,AQID")
    assert data == bytes([1, 2, 3])
    assert mime == "application/gltf-buffer"


def test_read_url_uri():
    class HTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"lorem ipsum")
            self.wfile.close()

    httpd = HTTPServer(("", 0), HTTPRequestHandler)
    thread = Thread(target=httpd.serve_forever)
    thread.start()

    try:
        data, mime = read_uri_data(f"http://localhost:{httpd.server_port}/lorem.txt")
        assert data == b"lorem ipsum"
        assert mime == "text/plain"
    finally:
        httpd.shutdown()
        thread.join()


@mark.skipif(sys.platform == "win32", reason="getting Permission Error for some reason")
def test_read_abs_file_uri():
    with NamedTemporaryFile("w", suffix=".txt") as f:
        f.write("hello world")
        f.flush()
        uri = f.name

        assert Path(uri).is_absolute()
        data, mime = read_uri_data(uri)
        assert data == b"hello world"
        assert mime == "text/plain"


@mark.skipif(sys.platform == "win32", reason="getting Permission Error for some reason")
def test_read_rel_file_uri():
    with NamedTemporaryFile("w", suffix=".txt") as f:
        f.write("hello world")
        f.flush()
        uri = Path(f.name).name

        assert not Path(uri).is_absolute()
        with raises(URLError):
            data, mime = read_uri_data(uri)

        data, mime = read_uri_data(uri, relative_to=Path(f.name).parent)
        assert data == b"hello world"
        assert mime == "text/plain"


def test_write_glb_chunks():
    buf = BytesIO()
    write_glb_chunks(
        buf,
        (
            (JSON_CHUNK_TYPE, b'{"foo":"bar"}'),
            (BIN_CHUNK_TYPE, b"123"),
            (b"blah", b"abc"),
        ),
    )
    assert buf.getvalue() == (
        b'glTF\x02\x00\x00\x00;\x00\x00\x00\x10\x00\x00\x00JSON{"foo":"bar"}   '
        b"\x04\x00\x00\x00BIN\x00123\x00\x03\x00\x00\x00blahabc"
    )


def test_read_unknown_chunk(caplog: LogCaptureFixture):
    buf = BytesIO(
        b"glTF\x02\x00\x00\x00K\x00\x00\x00 \x00\x00\x00"
        b'JSON{"buffers":[{"byteLength":"4"}]}\x04\x00\x00\x00'
        b"BIN\x00123\x00\x03\x00\x00\x00blahabc"
    )
    with caplog.at_level(logging.WARNING):
        root = GltfRoot()
        read_glb(buf, root)
    assert "unknown chunk type b'blah'" in caplog.text


def test_write_glb_multiple_data_buffers():
    gltf = Gltf2()
    gltf.buffers += (DataBuffer(b"123"), DataBuffer(b"abc"))
    with raises(IOError) as e:
        gltf.write(BytesIO())
    assert "only the first buffer can be a data buffer" in str(e)


def test_implicit_properties_on_read():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.glb")

    assert "explicit" not in str(gltf.accessors)
    assert "explicit" not in str(gltf.buffers)
    assert "explicit" not in str(gltf.bufferViews)
    assert "explicit" not in str(gltf.meshes)
    assert "explicit" not in str(gltf.nodes)
