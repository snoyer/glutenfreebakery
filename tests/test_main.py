from pathlib import Path
from tempfile import TemporaryDirectory

from pytest import CaptureFixture, raises

from glutenfreebakery import __main__


def test_main_no_args(capsys: CaptureFixture[str]):
    with raises(SystemExit) as e:
        __main__.main([])
    assert e.value.code == 1

    captured = capsys.readouterr()
    assert_help(captured.out)


def test_main_help(capsys: CaptureFixture[str]):
    with raises(SystemExit) as e:
        __main__.main(["-h"])
    assert e.value.code == 0

    captured = capsys.readouterr()
    assert_help(captured.out)


def assert_help(out: str):
    assert "glutenfreebakery convert [-h] input output" in out
    assert "glutenfreebakery unpack [-h] in.glb out.json" in out


def test_main_convert_gltf_to_glb(capsys: CaptureFixture[str]):
    DIR = Path(__file__).parent
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        __main__.main(
            [
                "convert",
                str(DIR / "data/small/two-textured-quads.gltf"),
                str(tmp / "packed.glb"),
            ]
        )
        assert sorted(tmp.glob("**/*")) == [tmp / "packed.glb"]


def test_main_convert_glb_to_gltf(capsys: CaptureFixture[str]):
    DIR = Path(__file__).parent
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        __main__.main(
            [
                "convert",
                str(DIR / "data/small/two-textured-quads.glb"),
                str(tmp / "unpacked.gltf"),
            ]
        )
        assert sorted(tmp.glob("**/*")) == [
            tmp / "unpacked.buffer0.glbin",
            tmp / "unpacked.gltf",
            tmp / "unpacked.image0.png",
            tmp / "unpacked.image1.png",
        ]


def test_unpack():
    DIR = Path(__file__).parent
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        __main__.main(
            [
                "unpack",
                str(DIR / "data/small/two-textured-quads.glb"),
                str(tmp / "unpacked.json"),
            ]
        )
        assert sorted(tmp.glob("**/*")) == [
            tmp / "unpacked.bin",
            tmp / "unpacked.json",
        ]

        json = (tmp / "unpacked.json").read_text()
        assert json.startswith('{"asset":{"version":"2.0"},"scene":0,"accessors":[')
        assert json.endswith('[{"source":0,"sampler":0},{"source":1,"sampler":0}]} ')

        bin = (tmp / "unpacked.bin").read_bytes()
        assert bin.startswith(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert bin.endswith(b"\xb8\x96\x8aH\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00")
