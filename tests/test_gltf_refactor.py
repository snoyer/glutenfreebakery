from pathlib import Path
from tempfile import TemporaryDirectory

from glutenfreebakery.gltf import Gltf2
from glutenfreebakery.gltf_refactor import (
    embed_external_buffers,
    embed_external_images,
    extract_resources,
    merge_data_buffers,
)
from glutenfreebakery.schema import Buffer, BufferView, DataBuffer
from glutenfreebakery.util import encode_data_uri


def test_embed_images_as_base64():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    assert gltf.images[0].uri == "two-textured-quads-tex1.png"
    assert gltf.images[1].uri == "two-textured-quads-tex2.png"

    gltf.embed_images_as_data_uri()

    assert gltf.images[0].uri == encode_data_uri(
        (DIR / "two-textured-quads-tex1.png").read_bytes(), "image/png"
    )
    assert gltf.images[1].uri == encode_data_uri(
        (DIR / "two-textured-quads-tex2.png").read_bytes(), "image/png"
    )


def test_embed_external_images():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    assert gltf.images[0].uri == "two-textured-quads-tex1.png"
    assert gltf.images[1].uri == "two-textured-quads-tex2.png"

    embed_external_images(gltf, relative_to=DIR)

    assert gltf.images[0].uri is None
    assert gltf.images[1].uri is None


def test_embed_external_images_b64():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    gltf.images[1].uri = encode_data_uri(
        (DIR / "two-textured-quads-tex2.png").read_bytes(), "image/png"
    )
    gltf.images[1].mimeType = "image/png"

    embed_external_images(gltf, relative_to=DIR)

    assert gltf.images[0].uri is None
    assert gltf.images[1].uri is None


def test_embed_external_buffers():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    assert gltf.images[0].uri == "two-textured-quads-tex1.png"
    assert gltf.images[1].uri == "two-textured-quads-tex2.png"

    assert len(gltf.buffers) == 1
    buffer = gltf.buffers[0]
    assert isinstance(buffer, Buffer) and buffer.uri.startswith("data:")

    embed_external_buffers(gltf, relative_to=DIR)

    assert gltf.images[0].uri == "two-textured-quads-tex1.png"
    assert gltf.images[1].uri == "two-textured-quads-tex2.png"

    assert len(gltf.buffers) == 1
    assert isinstance(gltf.buffers[0], DataBuffer)


def test_embed_resources():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    gltf.embed_resources()

    assert not gltf.images[0].uri
    assert not gltf.images[1].uri

    assert len(gltf.buffers) == 1
    assert isinstance(gltf.buffers[0], DataBuffer)


def test_embed_resources_no_merge():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    gltf.embed_resources(merge=False)

    assert not gltf.images[0].uri
    assert not gltf.images[1].uri

    assert len(gltf.buffers) == 3
    assert isinstance(gltf.buffers[0], DataBuffer)
    assert isinstance(gltf.buffers[1], DataBuffer)
    assert isinstance(gltf.buffers[2], DataBuffer)


def test_extract_resources():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gltf.extract_resources(tmp)

        buffer_fns = ("two-textured-quads-buffer0.glbin",)
        for buffer, fn in zip(gltf.buffers, buffer_fns, strict=True):
            assert isinstance(buffer, Buffer) and buffer.uri == fn
            assert (tmp / fn).is_file()

        image_fns = "two-textured-quads-image0.png", "two-textured-quads-image1.png"
        for image, fn in zip(gltf.images, image_fns, strict=True):
            assert image.uri == fn
            assert (tmp / fn).is_file()


def test_extract_resources_check_data():
    DIR = Path(__file__).parent / "data/small/"
    gltf = Gltf2.Read(DIR / "two-textured-quads.gltf")

    gltf.buffers += (DataBuffer(b"123"),)

    written: dict[Path, bytes] = {}
    extract_resources(
        gltf,
        relative_to=DIR,
        out_dir=Path("/tmp"),
        base_name="hello-",
        write_file=written.__setitem__,
    )

    assert written == {
        Path("/tmp/hello-image0.png"): (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08"
            b"\x08\x04\x00\x00\x00n\x06v\x00\x00\x00\x00\x01sRGB\x00\xae\xce"
            b"\x1c\xe9\x00\x00\x00%IDAT\x08\x99c\xfc\xff\x9f\x01\x050\xc1\x18\x8c\xa8\x02"
            b"\x8c\xa8*\x18\xd1\xb5\xfcG\x17\xc00\x94\x11\xc9\x1c\x16t-\x00\\"
            b"\xf2\x04\x13\x85\xa7\xba{\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        Path("/tmp/hello-image1.png"): (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08"
            b"\x08\x04\x00\x00\x00n\x06v\x00\x00\x00\x00\x01sRGB\x00\xae\xce"
            b"\x1c\xe9\x00\x00\x004IDAT\x08\x99U\xcbA\x12\x00!\x0c\x02\xc1\x8e\xeb\xff"
            b"\xbf\x1c\x0fR\xae\xe6@\x8a\x01\xaa\xdbsc\xbfO\x05L(}t \xf6\x99Tp\xc0oO"
            b"\x83\xcah\xbaRX\x8a\xb1\x08\x17\xb8\x96\x8aH\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        Path("/tmp/hello-buffer0.glbin"): (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x80?\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?"
            b"\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00"
        ),
        Path("/tmp/hello-buffer1.glbin"): b"123",
    }


def test_merge_all_data_buffers():
    data1 = bytes(i for i in range(20))
    data2 = bytes(i * 2 for i in range(30))
    data3 = bytes(i * 3 for i in range(10))

    gltf = Gltf2(
        bufferViews=[
            BufferView(Buffer(0, ""), byteLength=0),
            BufferView(DataBuffer(data1), byteLength=len(data1)),
            BufferView(Buffer(0, ""), byteLength=0),
            BufferView(DataBuffer(data2), byteLength=len(data2)),
            BufferView(DataBuffer(data3), byteLength=len(data3)),
        ]
    )

    assert len(gltf.buffers) == 5

    merge_data_buffers(gltf)

    assert len(gltf.buffers) == 3

    buffer = gltf.buffers[0]
    assert isinstance(buffer, DataBuffer) and buffer.data == data1 + data2 + data3

    views = [view for view in gltf.bufferViews if view.buffer == buffer]
    assert len(views) == 3
    assert views[0].byteOffset == 0
    assert views[1].byteOffset == 20
    assert views[2].byteOffset == 50
