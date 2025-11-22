from pathlib import Path
from tempfile import TemporaryDirectory

from pytest import CaptureFixture, raises

from glutenfreebakery import __main__


def test_main_no_args(capsys: CaptureFixture[str]):
    with raises(SystemExit) as e:
        __main__.main([])
    assert e.value.code == 1

    captured = capsys.readouterr()
    assert "glutenfreebakery convert [-h] input output" in captured.out


def test_main_help(capsys: CaptureFixture[str]):
    with raises(SystemExit) as e:
        __main__.main(["-h"])
    assert e.value.code == 0

    captured = capsys.readouterr()
    assert "glutenfreebakery convert [-h] input output" in captured.out


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
