from io import BufferedIOBase
from pathlib import Path
from typing import Any, BinaryIO, TextIO

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
