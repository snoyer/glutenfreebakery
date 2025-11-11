import json
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import gettempdir
from typing import Iterator

import pytest
from test_schema import check_GltfRoot_internals

from glutenfreebakery import Gltf2
from glutenfreebakery.schema_io import normalize_json_dict

KHRONOS_SAMPLES_DIR = Path(gettempdir()) / "glTF-Sample-Assets"
SAMPLES_DIRS = {
    "tests-data": Path(__file__).parent / "data",
    "Khronos": KHRONOS_SAMPLES_DIR / "Models",
}


def expand_sample_fn(fn_template: str):
    for k, dir_path in SAMPLES_DIRS.items():
        prefix = f"{{{k}}}/"
        if fn_template.startswith(prefix):
            return dir_path / fn_template.removeprefix(prefix)
    raise ValueError()  # pragma: no cover


def find_gltf_samples(gltf: bool = True, glb: bool = True):
    def glob(dir: Path) -> Iterator[Path]:
        if gltf:
            yield from dir.glob("**/*.gltf")
        if glb:
            yield from dir.glob("**/*.glb")

    for k, dir_path in SAMPLES_DIRS.items():
        for path in sorted(glob(dir_path)):
            if path.name not in ("NodePerformanceTest.glb",):
                yield f"{{{k}}}/{path.relative_to(dir_path)}"


@pytest.mark.parametrize("fn_template", find_gltf_samples(glb=False))
def test_glb_rewrite_json(fn_template: str):
    fn = expand_sample_fn(fn_template)
    gltf = Gltf2.Read(fn)

    assert check_GltfRoot_internals(gltf)

    buf = StringIO()
    gltf.write(buf)
    buf.seek(0)

    data_src = normalize_json_dict(json.load(open(fn)))
    data_rewrite = json.load(buf)

    assert data_rewrite == data_src


@pytest.mark.parametrize("fn_template", find_gltf_samples(glb=False))
def test_gltf_reread_gltf(fn_template: str):
    fn = expand_sample_fn(fn_template)
    gltf = Gltf2.Read(fn)

    rewrite_buf = StringIO()
    gltf.write(rewrite_buf)
    rewrite_buf.seek(0)
    gltf_reread = Gltf2.Read(rewrite_buf)

    assert gltf_reread == gltf


@pytest.mark.parametrize("fn_template", find_gltf_samples(glb=False))
def test_gltf_reread_glb(fn_template: str):
    fn = expand_sample_fn(fn_template)
    gltf = Gltf2.Read(fn)

    rewrite_buf = BytesIO()
    gltf.write(rewrite_buf)
    rewrite_buf.seek(0)
    gltf_reread = Gltf2.Read(rewrite_buf)

    assert gltf_reread == gltf


@pytest.mark.parametrize("fn_template", find_gltf_samples(gltf=False))
def test_glb_reread_glb(fn_template: str):
    fn = expand_sample_fn(fn_template)
    gltf = Gltf2.Read(fn)

    rewrite_buf = BytesIO()
    gltf.write(rewrite_buf)
    rewrite_buf.seek(0)
    gltf_reread = Gltf2.Read(rewrite_buf)

    assert gltf_reread == gltf
