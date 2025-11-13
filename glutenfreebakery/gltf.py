from io import BufferedIOBase
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from .gltf_refactor import (
    embed_external_buffers,
    embed_external_images,
    embed_external_images_as_data_uri,
    extract_resources,
    merge_data_buffers,
)
from .schema import GltfRoot
from .schema_io import (
    load_gltf_dict,
    read_glb,
    read_gltf,
    to_gltf_dict,
    write_glb,
    write_gltf,
)


class Gltf2(GltfRoot):
    source: Path | None = None

    @classmethod
    def Read(cls, f: TextIO | BinaryIO | Path | str):
        instance = cls()
        if isinstance(f, (BinaryIO, BufferedIOBase)) or (
            isinstance(f, (Path, str)) and str(f).endswith(".glb")
        ):
            return read_glb(f, instance)
        else:
            read_gltf(f, instance)

        if isinstance(f, (Path, str)):
            instance.source = Path(f)

        return instance

    def write(self, f: TextIO | BinaryIO | Path | str):
        if isinstance(f, (BinaryIO, BufferedIOBase)) or (
            isinstance(f, (Path, str)) and str(f).endswith(".glb")
        ):
            return write_glb(self, f)
        else:
            return write_gltf(self, f, indent=2)

    @classmethod
    def Load(cls, data: dict[str, Any]):
        return load_gltf_dict(data, cls())

    def dump(self):
        return to_gltf_dict(self)

    def embed_images_as_data_uri(self, relative_to: Path | None = None):
        embed_external_images_as_data_uri(
            self, relative_to=relative_to or _source_dir(self)
        )

    def embed_resources(self, *, relative_to: Path | None = None, merge: bool = True):
        embed_external_buffers(self, relative_to=relative_to or _source_dir(self))
        embed_external_images(self, relative_to=relative_to or _source_dir(self))
        if merge:
            merge_data_buffers(self)

    def extract_resources(
        self,
        out_dir: Path,
        base_name: str | None = None,
        *,
        relative_to: Path | None = None,
    ):
        if base_name is None and (stem := _source_stem(self)):
            base_name = f"{stem}-"
        extract_resources(
            self,
            out_dir,
            relative_to or _source_dir(self),
            base_name=base_name or "",
        )


def _source_dir(gltf: Gltf2):
    if source := gltf.source:
        return source.parent if source.is_file() else source


def _source_stem(gltf: Gltf2):
    if (source := gltf.source) and source.is_file():
        return source.stem
