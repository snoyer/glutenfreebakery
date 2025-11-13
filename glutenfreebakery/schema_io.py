import json
import logging
from contextlib import contextmanager
from enum import Enum
from functools import lru_cache
from inspect import isclass
from pathlib import Path
from struct import pack, unpack
from types import GenericAlias, UnionType
from typing import (
    Any,
    BinaryIO,
    Iterable,
    Iterator,
    Mapping,
    TextIO,
    Type,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from attrs import Attribute, Factory, fields

from .schema import (
    Accessor,
    Animation,
    AnimationChannel,
    AnimationChannels,
    AnimationSampler,
    AnimationSamplers,
    Asset,
    Buffer,
    BufferView,
    Camera,
    DataBuffer,
    GltfDict,
    GltfDictValue,
    GltfProperty,
    GltfPropertyArray,
    GltfPropertyT,
    GltfRoot,
    Image,
    Material,
    Mesh,
    Mode,
    Node,
    Primitive,
    Sampler,
    Scene,
    Skin,
    SparseIndices,
    SparseValues,
    Texture,
    TextureInfo,
    Wrap,
)
from .util import encode_data_uri

logger = logging.getLogger(__name__)

GltfRootT = TypeVar("GltfRootT", bound=GltfRoot)

JSON_CHUNK_TYPE = b"JSON"
BIN_CHUNK_TYPE = b"BIN\0"


def read_gltf(src: TextIO | Path | str, root: GltfRootT) -> GltfRootT:
    f = open(src, "r") if isinstance(src, (Path, str)) else src
    return load_gltf_dict(json.load(f), root)


def read_glb(src: BinaryIO | Path | str, root: GltfRootT) -> GltfRootT:
    f = open(src, "rb") if isinstance(src, (Path, str)) else src

    for chunk_type, chunk_data in read_glb_chunks(f):
        if chunk_type == JSON_CHUNK_TYPE:
            load_gltf_dict(json.loads(chunk_data), root)
        elif chunk_type == BIN_CHUNK_TYPE:
            if chunk_data:
                empty_data_buffer = next(
                    buffer
                    for buffer in root.buffers
                    if isinstance(buffer, Buffer) and buffer.uri == ""
                )
                new_data_buffer = DataBuffer(chunk_data)
                root.buffers.remove(empty_data_buffer)
                for bufferView in root.bufferViews:
                    if bufferView.buffer == empty_data_buffer:
                        bufferView.buffer = new_data_buffer
        else:
            logger.warning("unknown chunk type %r", chunk_type)

    return root


def write_glb(gltf: GltfRoot, dst: BinaryIO | Path | str):
    f = open(dst, "wb") if isinstance(dst, (Path | str)) else dst
    return GlbWriter.write(gltf, f)


def write_gltf(gltf: GltfRoot, dst: TextIO | Path | str, indent: int | None = None):
    f = open(dst, "w") if isinstance(dst, (Path | str)) else dst
    return GltfWriter.write(gltf, f, indent=indent)


################################################################################


def read_glb_chunks(f: BinaryIO) -> Iterator[tuple[bytes, bytes]]:
    magic, version, total_len = unpack("4sII", f.read(4 + 4 + 4))
    assert magic == b"glTF"
    assert version == 2
    assert total_len > 0

    while f.tell() < total_len:
        chunk_len, chunk_type = unpack("I4s", f.read(4 + 4))
        chunk_data = f.read(chunk_len)
        assert len(chunk_data) == chunk_len
        yield chunk_type, chunk_data


def write_glb_chunks(
    f: BinaryIO, chunks: Iterable[tuple[bytes, bytes]], version: int = 2
):
    def fix_chunks():
        for chunk_type, chunk_data in chunks:
            if not chunk_data:
                continue

            if chunk_type == JSON_CHUNK_TYPE:
                if r := len(chunk_data) % 4:
                    chunk_data += b" " * (4 - r)
            elif chunk_type == BIN_CHUNK_TYPE:
                if r := len(chunk_data) % 4:
                    chunk_data += b"\0" * (4 - r)

            yield chunk_type, chunk_data

    chunks = list(fix_chunks())

    total_len = 12 + sum(8 + len(data) for _, data in chunks)

    f.write(pack("4sII", b"glTF", version, total_len))

    for chunk_type, chunk_data in chunks:
        f.write(pack("I4s", len(chunk_data), chunk_type))
        f.write(chunk_data)


################################################################################


PROP_LISTS = [
    ("buffers", Buffer),
    ("bufferViews", BufferView),
    ("accessors", Accessor),
    ("images", Image),
    ("samplers", Sampler),
    ("textures", Texture),
    ("materials", Material),
    ("meshes", Mesh),
    ("cameras", Camera),
    ("nodes", Node),
    ("skins", Skin),
    ("animations", Animation),
    ("scenes", Scene),
]


def load_gltf_dict(data: Any, gltf: GltfRootT) -> GltfRootT:

    with ignore_key_error():
        gltf.asset = _load_class(Asset, data["asset"])

    for name, cls in PROP_LISTS:
        with ignore_key_error():
            data[name] = [_load_class(cls, x) for x in data[name]]

    for name, cls in PROP_LISTS:
        for x in data.get(name, []):
            _fix_prop(x, data)

    with ignore_key_error():
        data["scene"] = data["scenes"][data["scene"]]

    for name, cls in PROP_LISTS:
        with ignore_key_error():
            setattr(gltf, name, data[name])

    with ignore_key_error():
        gltf.scene = data["scene"]

    gltf.extensionsUsed = data.get("extensionsUsed", [])
    gltf.extensionsRequired = data.get("extensionsRequired", [])

    with ignore_key_error():
        gltf.extensions = data["extensions"]
    with ignore_key_error():
        gltf.extras = data["extras"]

    return gltf


@contextmanager
def ignore_key_error():
    try:
        yield
    except KeyError:
        pass


def _fix_prop(o: GltfProperty, data: Any):

    if isinstance(o, BufferView):
        if isinstance(o.buffer, int):
            o.buffer = data["buffers"][o.buffer]

    elif isinstance(o, Accessor):
        if isinstance(o.bufferView, int):
            o.bufferView = data["bufferViews"][o.bufferView]
        if sparse := o.sparse:
            _fix_prop(sparse.indices, data)
            _fix_prop(sparse.values, data)

    elif isinstance(o, (SparseIndices, SparseValues, Image)):
        if isinstance(o.bufferView, int):
            o.bufferView = data["bufferViews"][o.bufferView]

    elif isinstance(o, Texture):
        if isinstance(o.sampler, int):
            o.sampler = data["samplers"][o.sampler]
        if isinstance(o.source, int):
            o.source = data["images"][o.source]

    elif isinstance(o, Material):

        def texinfos():
            yield o.normalTexture
            yield o.occlusionTexture
            yield o.emissiveTexture
            if pbr := o.pbrMetallicRoughness:
                yield pbr.baseColorTexture
                yield pbr.metallicRoughnessTexture

        for texinfo in texinfos():
            if texinfo and isinstance(texinfo.texture, int):
                texinfo.texture = data["textures"][texinfo.texture]

    elif isinstance(o, Mesh):
        for primitive in o.primitives:
            if isinstance(primitive.indices, int):
                primitive.indices = data["accessors"][primitive.indices]
            if isinstance(primitive.material, int):
                primitive.material = data["materials"][primitive.material]
            primitive.attributes = {
                k: data["accessors"][v] if isinstance(v, int) else v
                for k, v in primitive.attributes.items()
            }

    elif isinstance(o, Node):
        if isinstance(o.camera, int):
            o.camera = data["cameras"][o.camera]
        if isinstance(o.mesh, int):
            o.mesh = data["meshes"][o.mesh]
        if isinstance(o.skin, int):
            o.skin = data["skins"][o.skin]
        if o.children:
            o.children[:] = [
                data["nodes"][v] if isinstance(v, int) else v for v in o.children
            ]

    elif isinstance(o, Skin):
        if isinstance(o.inverseBindMatrices, int):
            o.inverseBindMatrices = data["accessors"][o.inverseBindMatrices]
        o.joints[:] = [data["nodes"][v] if isinstance(v, int) else v for v in o.joints]
        if isinstance(o.skeleton, int):
            o.skeleton = data["accessors"][o.skeleton]

    elif isinstance(o, Scene):
        o.nodes = [data["nodes"][n] if isinstance(n, int) else n for n in o.nodes]

    return o


def _load_class(cls: Type[GltfPropertyT], data: Any) -> GltfPropertyT:
    if issubclass(cls, TextureInfo):
        data["texture"] = data.pop("index")
        return _prop_from_dict(cls, data)
    if issubclass(cls, Mesh):
        return _prop_from_dict(
            cls,
            data,
            primitives=[_load_class(Primitive, v) for v in data.get("primitives", [])],
        )
    if issubclass(cls, Animation):
        samplers = [_load_class(AnimationSampler, v) for v in data["samplers"]]
        channels = [
            _prop_from_dict(AnimationChannel, v, sampler=samplers[v["sampler"]])
            for v in data["channels"]
        ]
        return _prop_from_dict(
            cls,
            data,
            samplers=AnimationSamplers(samplers),
            channels=AnimationChannels(channels),
        )
    else:
        return _prop_from_dict(cls, data)


def _prop_from_dict(
    cls: Type[GltfPropertyT],
    data: GltfDict,
    **preloaded: Any,
) -> GltfPropertyT:
    def f(
        prop_ts: list[Type[GltfProperty]],
        any_ts: list[Type[Any]],
        data_val: Any,
        name: str,
    ):
        if prop_ts:
            if isinstance(data_val, int):
                return data_val
            else:
                return _load_class(prop_ts[0], data_val)
        else:
            for t in any_ts:
                try:
                    return t(data_val)
                except (ValueError, TypeError):
                    pass
            if any_ts:
                raise ValueError(f"unexpected type for {name}={data_val!r}")
            else:
                return data_val

    kwargs = preloaded | {
        name: f(prop_ts, any_ts, data[name], name)
        for name, prop_ts, any_ts in _fields_and_types(cls)
        if name not in preloaded and name in data
    }
    return cls(**kwargs)


@lru_cache
def _fields_and_types(cls: Type[Any]):
    return tuple(_iter_fields_and_types(cls))


def _iter_fields_and_types(cls: Type[Any]):
    hints = get_type_hints(cls)
    for attr in fields(cls):
        yield attr.name, *_types_from_hint(hints.get(attr.name))


@lru_cache
def _types_from_hint(hint: Any):

    def types() -> Iterator[Type[Any]]:
        if isinstance(hint, UnionType):
            yield from map(_arg_type, get_args(hint))
        elif isclass(hint):
            yield _arg_type(hint)

    prop_ts: list[type[GltfProperty]] = []
    any_ts: list[type[Any]] = []
    for t in types():
        (prop_ts if isclass(t) and issubclass(t, GltfProperty) else any_ts).append(t)
    return prop_ts, any_ts


def _arg_type(arg: Any) -> Type[Any]:
    return get_origin(arg) if isinstance(arg, GenericAlias) else arg


################################################################################


def to_gltf_dict(gltf: GltfRoot):
    return GltfWriter.to_json_dict(gltf)


class Writer:

    @classmethod
    def to_json_dict(cls, gltf: GltfRoot):
        return cls.root_to_dict(gltf)

    @classmethod
    def buffer_to_dict(cls, buffer: Buffer | DataBuffer) -> dict[str, Any]: ...

    @classmethod
    def root_to_dict(cls, root: GltfRoot):
        return normalize_json_dict(cls.prop_to_dict(root))

    @classmethod
    def prop_to_dict(cls, o: GltfProperty, parents: tuple[Any, ...] = ()) -> GltfDict:
        def items():
            for name, default_value in _fields_and_defaults(type(o)):
                value = getattr(o, name)
                if not isinstance(value, GltfProperty) and value == default_value:
                    continue

                if isinstance(o, TextureInfo) and name == "texture":
                    name = "index"

                yield name, cls.value_to_dict(value, (*parents, o))

        return dict(items())

    @classmethod
    def value_to_dict(cls, o: Any, parents: tuple[Any, ...]) -> GltfDictValue:
        def check_parents(*classes: type[Any]):
            try:
                for x, y in zip(parents, classes, strict=True):
                    if not isinstance(x, y):
                        return False
                return True
            except ValueError:
                return False

        if isinstance(o, Enum):
            return o.value
        if isinstance(o, (str, int, float)):
            return o

        if (
            isinstance(o, GltfProperty)
            and not check_parents(GltfRoot, GltfPropertyArray)
            and isinstance(parents[0], GltfRoot)
        ):
            try:
                return getattr(parents[0], INDEXING[type(o)], []).index(o)  # type: ignore
            except KeyError:
                for prop_cls, array_name in INDEXING.items():
                    if isinstance(o, prop_cls):
                        return getattr(parents[0], array_name, []).index(o)

        if isinstance(o, Buffer | DataBuffer):
            return cls.buffer_to_dict(o)

        if isinstance(o, AnimationSampler):
            if any(isinstance(p, AnimationChannels) for p in parents):
                for parent in reversed(parents):
                    if isinstance(parent, Animation):
                        return parent.samplers.index(o)
            else:
                return cls.prop_to_dict(o, parents)

        if isinstance(o, GltfProperty):
            return cls.prop_to_dict(o, parents)

        if isinstance(o, Mapping):
            kvs = cast(Mapping[Any, Any], o)
            return {k: cls.value_to_dict(v, (*parents, kvs)) for k, v in kvs.items()}
        if isinstance(o, bytes):
            raise ValueError("cannot encode bytes")
        if isinstance(o, Iterable):
            xs = cast(Iterable[Any], o)
            return [cls.value_to_dict(x, (*parents, xs)) for x in xs]

        raise ValueError(o)


INDEXING = {
    Buffer: "buffers",
    DataBuffer: "buffers",
    BufferView: "bufferViews",
    Accessor: "accessors",
    Image: "images",
    Sampler: "samplers",
    Texture: "textures",
    Material: "materials",
    Mesh: "meshes",
    Camera: "cameras",
    Node: "nodes",
    Skin: "skins",
    Animation: "animations",
    Scene: "scenes",
}


class GltfWriter(Writer):
    @classmethod
    def write(cls, gltf: GltfRoot, f: TextIO, indent: int | None = None):
        json.dump(cls.to_json_dict(gltf), f, indent=indent)

    @classmethod
    def buffer_to_dict(cls, buffer: Buffer | DataBuffer):
        if isinstance(buffer, DataBuffer):
            uri_buffer = Buffer(
                uri=encode_data_uri(
                    buffer.data, mime_type=buffer.mimeType or "application/gltf-buffer"
                ),
                byteLength=len(buffer.data),
                name=buffer.name,
                extensions=buffer.extensions,
                extras=buffer.extras,
            )
        else:
            uri_buffer = buffer
        return cls.prop_to_dict(uri_buffer, ())


class GlbWriter(Writer):
    @classmethod
    def write(cls, gltf: GltfRoot, f: BinaryIO):

        bin_data = b""
        if gltf.buffers:
            first_buffer, *other_buffers = gltf.buffers
            if isinstance(first_buffer, DataBuffer):
                logger.debug("writing data buffer to BIN chunk")
                bin_data = first_buffer.data
            if any(isinstance(buffer, DataBuffer) for buffer in other_buffers):
                raise IOError("only the first buffer can be a data buffer")

        json_data = json.dumps(cls.to_json_dict(gltf), separators=(",", ":")).encode()

        write_glb_chunks(f, ((JSON_CHUNK_TYPE, json_data), (BIN_CHUNK_TYPE, bin_data)))

    @classmethod
    def buffer_to_dict(cls, buffer: Buffer | DataBuffer):
        if isinstance(buffer, DataBuffer):
            uri_buffer = Buffer(
                uri="",
                byteLength=len(buffer.data),
                name=buffer.name,
                extensions=buffer.extensions,
                extras=buffer.extras,
            )
        else:
            uri_buffer = buffer
        return cls.prop_to_dict(uri_buffer, ())


def normalize_json_dict(data: dict[str, Any]):
    def pop_if(o: dict[str, Any], k: str, pred: Any):
        if o.get(k) == pred:
            o.pop(k)

    def normalize_textures(o: dict[str, Any], *tex_ks: str):
        for tex_k in tex_ks:
            if tex := o.get(tex_k):
                pop_if(tex, "texCoord", 0)
                pop_if(tex, "scale", 1)
                pop_if(tex, "strength", 1)

    for accessor in data.get("accessors", []):
        pop_if(accessor, "byteOffset", 0)

        if sparse := accessor.get("sparse"):
            if indices := sparse.get("indices"):
                pop_if(indices, "byteOffset", 0)
            if values := sparse.get("values"):
                pop_if(values, "byteOffset", 0)

    for bufferView in data.get("bufferViews", []):
        pop_if(bufferView, "byteOffset", 0)

    for meshes in data.get("meshes", []):
        for primitive in meshes.get("primitives", []):
            pop_if(primitive, "mode", Mode.TRIANGLES)

    for material in data.get("materials", []):
        pop_if(material, "doubleSided", False)
        pop_if(material, "alphaMode", "OPAQUE")
        pop_if(material, "alphaCutoff", 0.5)
        pop_if(material, "emissiveFactor", [0, 0, 0])
        normalize_textures(
            material, "emissiveTexture", "normalTexture", "occlusionTexture"
        )
        if material.get("alphaMode") != "MASK" and "alphaCutoff" in material:
            material.pop("alphaCutoff")

        if pbr := material.get("pbrMetallicRoughness"):
            pop_if(pbr, "metallicFactor", 1)
            pop_if(pbr, "roughnessFactor", 1)
            pop_if(pbr, "baseColorFactor", [1, 1, 1, 1])
            normalize_textures(pbr, "baseColorTexture", "metallicRoughnessTexture")

    for sampler in data.get("samplers", []):
        pop_if(sampler, "wrapS", Wrap.REPEAT)
        pop_if(sampler, "wrapT", Wrap.REPEAT)

    for k in ("extensionsUsed", "extensionsRequired"):
        if k in data:
            data[k] = sorted(data[k])

    q = [data]
    while q:
        o = q.pop()
        pop_if(o, "extensions", {})

        for child in o.values():
            if isinstance(child, dict):
                q.append(child)  # type: ignore
            elif isinstance(child, list):
                q += (child2 for child2 in child if isinstance(child2, dict))

    return data


@lru_cache
def _fields_and_defaults(cls: Type[Any]):
    return list(_iter_fields_and_defaults(cls))


def _iter_fields_and_defaults(cls: Type[Any]) -> Iterator[tuple[str, Any]]:
    for field in fields(cls):
        if isinstance(field, Attribute):
            if isinstance(field.default, Factory):  # type: ignore
                yield field.name, field.default.factory()  # type: ignore
            else:
                yield field.name, field.default
