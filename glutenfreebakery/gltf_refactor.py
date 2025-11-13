from pathlib import Path
from typing import Any, Callable

from .schema import Buffer, BufferView, DataBuffer, GltfRoot
from .util import encode_data_uri, guess_extension, read_uri_data


def embed_external_images_as_data_uri(gltf: GltfRoot, relative_to: Path | None = None):
    for image in gltf.images:
        if image.uri:
            image_data, mime_type = read_uri_data(image.uri, relative_to=relative_to)
            image.uri = encode_data_uri(image_data, image.mimeType or mime_type)


def extract_resources(
    gltf: GltfRoot,
    out_dir: Path,
    relative_to: Path | None = None,
    base_name: str = "",
    write_file: Callable[[Path, bytes], Any] = Path.write_bytes,
):
    for i, image in enumerate(gltf.images):
        if image.uri:
            data, mimetype = read_uri_data(image.uri, relative_to=relative_to)

            new_uri = f"{base_name}image{i}{guess_extension(mimetype)}"
            write_file(out_dir / new_uri, data)

            image.uri = new_uri

    def f(old_buffer: Buffer | DataBuffer):
        if isinstance(old_buffer, Buffer):
            data, mimetype = read_uri_data(old_buffer.uri, relative_to=relative_to)
        else:
            data = old_buffer.data
            mimetype = old_buffer.mimeType

        i = gltf.buffers.index(old_buffer)
        new_uri = f"{base_name}buffer{i}{guess_extension(mimetype)}"
        write_file(out_dir / new_uri, data)

        if isinstance(old_buffer, Buffer):
            old_buffer.uri = new_uri
        else:
            return Buffer(
                byteLength=len(data),
                uri=new_uri,
                extensions=old_buffer.extensions,
                extras=old_buffer.extras,
                name=old_buffer.name,
            )

    _replace_buffers(gltf, f)


def embed_external_images(gltf: GltfRoot, relative_to: Path | None = None):
    for image in gltf.images:
        if image.uri:
            image_data, mime_type = read_uri_data(image.uri, relative_to=relative_to)
            if image.mimeType:
                mime_type = image.mimeType
            image.bufferView = BufferView(
                DataBuffer(image_data, name=image.uri, mimeType=mime_type),
                byteLength=len(image_data),
            )
            image.uri = None
            image.mimeType = mime_type


def embed_external_buffers(gltf: GltfRoot, relative_to: Path | None = None):
    def f(old_buffer: Buffer | DataBuffer):
        if isinstance(old_buffer, Buffer) and old_buffer.uri:
            data, mime_type = read_uri_data(old_buffer.uri, relative_to=relative_to)
            return DataBuffer(
                data,
                mimeType=mime_type,
                extensions=old_buffer.extensions,
                extras=old_buffer.extras,
                name=old_buffer.name,
            )

    _replace_buffers(gltf, f)


def _replace_buffers(
    gltf: GltfRoot, f: Callable[[Buffer | DataBuffer], Buffer | DataBuffer | None]
):
    replacements_by_old_id: dict[int, Buffer | DataBuffer] = {
        id(old_buffer): new_buffer
        for old_buffer in gltf.buffers
        if (new_buffer := f(old_buffer))
    }

    for view in gltf.bufferViews:
        try:
            view.buffer = replacements_by_old_id[id(view.buffer)]
        except KeyError:
            pass

    gltf.buffers.explicit = [
        replacements_by_old_id.get(id(old_buffer), old_buffer)
        for old_buffer in gltf.buffers.explicit
    ]


def merge_data_buffers(gltf: GltfRoot):
    data_buffers = [buffer for buffer in gltf.buffers if isinstance(buffer, DataBuffer)]
    if data_buffers:
        combined_buffer = DataBuffer(name="merged")
        replacements_by_id: dict[int, tuple[Buffer | DataBuffer, int]] = {}
        for buffer in data_buffers:
            offset = len(combined_buffer.data)
            combined_buffer.data += buffer.data
            replacements_by_id[id(buffer)] = combined_buffer, offset

        for view in gltf.bufferViews:
            try:
                new_buffer, offset = replacements_by_id[id(view.buffer)]
                view.buffer = new_buffer
                view.byteOffset += offset
            except KeyError:
                pass

        gltf.buffers.explicit = [
            combined_buffer,
            *(b for b in gltf.buffers.explicit if id(b) not in replacements_by_id),
        ]
