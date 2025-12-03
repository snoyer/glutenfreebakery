from pathlib import Path
from typing import Any, Callable, Iterable

from .buffers import get_buffer_data, get_bufferview_data
from .schema import Buffer, BufferView, DataBuffer, GltfRoot, UriBuffer
from .util import encode_data_uri, guess_extension, read_uri_data


def embed_external_images_as_data_uri(gltf: GltfRoot, relative_to: Path | None = None):
    for image in gltf.images:
        if image.uri:
            image_data, mime_type = read_uri_data(image.uri, relative_to=relative_to)
            image.uri = encode_data_uri(image_data, image.mimeType or mime_type)


def trim_data_buffer(
    gltf: GltfRoot,
    buffer: DataBuffer,
    ranges_to_remove: Iterable[tuple[int, int]],
    ranges_to_keep: Iterable[tuple[int, int]] = (),
):
    views = [view for view in gltf.bufferViews if view.buffer is buffer]

    ranges_in_use = set(
        (view.byteOffset, view.byteOffset + view.byteLength) for view in views
    )

    final_ranges_to_remove = list(
        intervals_difference(ranges_to_remove, set(ranges_to_keep) | ranges_in_use)
    )

    data = get_buffer_data(buffer)
    for lo, hi in sorted(final_ranges_to_remove, reverse=True):
        data = data[:lo] + data[hi:]
        for view in views:
            if view.byteOffset >= lo:
                view.byteOffset -= hi - lo
    buffer.data = data


def extract_resources(
    gltf: GltfRoot,
    out_dir: Path,
    relative_to: Path | None = None,
    base_name: str = "",
    write_file: Callable[[Path, bytes], Any] = Path.write_bytes,
):
    intervals_to_remove: dict[int, tuple[DataBuffer, dict[int, tuple[int, int]]]] = {}

    for i, image in enumerate(gltf.images):
        if image.uri:
            data, mimetype = read_uri_data(image.uri, relative_to=relative_to)

            new_uri = f"{base_name}image{i}{guess_extension(mimetype)}"
            write_file(out_dir / new_uri, data)

            image.uri = new_uri
        elif view := image.bufferView:
            mimetype = image.mimeType

            new_uri = f"{base_name}image{i}{guess_extension(mimetype)}"
            data = get_bufferview_data(view)
            write_file(out_dir / new_uri, data)

            image.uri = new_uri
            image.bufferView = None
            if isinstance(view.buffer, DataBuffer):
                buffer = view.buffer
                _, intervals = intervals_to_remove.setdefault(id(buffer), (buffer, {}))
                intervals[id(view)] = view.byteOffset, view.byteOffset + view.byteLength

    view_ids_to_remove = set(
        id for _k, v in intervals_to_remove.values() for id in v.keys()
    )
    gltf.bufferViews.explicit = [
        view for view in gltf.bufferViews.explicit if id(view) not in view_ids_to_remove
    ]

    for buffer, ranges_to_remove in intervals_to_remove.values():
        trim_data_buffer(gltf, buffer, ranges_to_remove.values())

    def f(old_buffer: Buffer):
        if isinstance(old_buffer, UriBuffer):
            data, mimetype = read_uri_data(old_buffer.uri, relative_to=relative_to)
        else:
            data = old_buffer.data
            mimetype = old_buffer.mimeType

        i = gltf.buffers.index(old_buffer)
        new_uri = f"{base_name}buffer{i}{guess_extension(mimetype)}"
        write_file(out_dir / new_uri, data)

        if isinstance(old_buffer, UriBuffer):
            old_buffer.uri = new_uri
        else:
            return UriBuffer(
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
    def f(old_buffer: Buffer):
        if isinstance(old_buffer, UriBuffer) and old_buffer.uri:
            data, mime_type = read_uri_data(old_buffer.uri, relative_to=relative_to)
            return DataBuffer(
                data,
                mimeType=mime_type,
                extensions=old_buffer.extensions,
                extras=old_buffer.extras,
                name=old_buffer.name,
            )

    _replace_buffers(gltf, f)


def _replace_buffers(gltf: GltfRoot, f: Callable[[Buffer], Buffer | None]):
    replacements_by_old_id: dict[int, Buffer] = {
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
        replacements_by_id: dict[int, tuple[Buffer, int]] = {}
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


def intervals_union(xs: Iterable[tuple[int, int]]):
    it = iter(sorted(xs))
    try:
        lo, hi = next(it)
        while it:
            try:
                lo2, hi2 = next(it)
                if lo <= lo2 <= hi + 1:
                    hi = max(hi, hi2)
                else:
                    yield lo, hi
                    lo, hi = lo2, hi2
            except StopIteration:
                break
        yield lo, hi
    except StopIteration:
        pass


def intervals_difference(xs: Iterable[tuple[int, int]], ys: Iterable[tuple[int, int]]):

    def diff1(xs: Iterable[tuple[int, int]], y: tuple[int, int]):
        lo0, hi0 = y
        for lo, hi in xs:
            if lo <= lo0 <= hi and lo <= hi0 <= hi:
                if lo0 > lo:
                    yield lo, lo0
                if hi > hi0:
                    yield hi0, hi
            elif lo < lo0 or hi > hi0:
                if lo <= lo0 <= hi:
                    hi = lo0
                if lo <= hi0 <= hi:
                    lo = hi0
                yield lo, hi

    xs = tuple(intervals_union(xs))
    for y in intervals_union(ys):
        xs = tuple(diff1(xs, y))
    return xs
