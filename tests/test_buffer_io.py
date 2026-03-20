import operator
from functools import reduce
from struct import pack
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pytest import mark, raises

from glutenfreebakery.buffers import (
    BufferBuilder,
    array_from_accessor,
    get_bufferview_data,
)
from glutenfreebakery.gltf import Gltf2
from glutenfreebakery.schema import (
    Accessor,
    BufferView,
    DataBuffer,
    Mesh,
    MeshPrimitive,
    MeshPrimitiveAttributes,
    Node,
    Scene,
)


def sample_arrays():
    for dtype, expected_component_type in [
        (np.byte, Accessor.ComponentType.BYTE),
        (np.ubyte, Accessor.ComponentType.UNSIGNED_BYTE),
        (np.short, Accessor.ComponentType.SHORT),
        (np.ushort, Accessor.ComponentType.UNSIGNED_SHORT),
        (np.uint32, Accessor.ComponentType.UNSIGNED_INT),
        (np.uint64, Accessor.ComponentType.UNSIGNED_INT),
        (np.float32, Accessor.ComponentType.FLOAT),
        (np.float64, Accessor.ComponentType.FLOAT),
    ]:
        for shape, expected_type in [
            ((8,), Accessor.Type.SCALAR),
            ((8, 2), Accessor.Type.VEC2),
            ((8, 3), Accessor.Type.VEC3),
            ((8, 4), Accessor.Type.VEC4),
            ((8, 2, 2), Accessor.Type.MAT2),
            ((8, 3, 3), Accessor.Type.MAT3),
            ((8, 4, 4), Accessor.Type.MAT4),
        ]:
            array = np.array(list(range(reduce(operator.mul, shape))), dtype).reshape(
                shape
            )
            if dtype in (np.float32,):
                array /= 7
            yield array, expected_type, expected_component_type
            yield array, expected_type, expected_component_type


@mark.parametrize("array, expected_type, expected_component_type", sample_arrays())
def test_add_array(
    array: NDArray[Any],
    expected_type: Accessor.Type,
    expected_component_type: Accessor.ComponentType,
):
    builder = BufferBuilder()
    accessor = builder.add_array(array)

    assert accessor.type == expected_type
    assert accessor.componentType == expected_component_type
    assert np.all(array == array_from_accessor(accessor))


def test_add_indices_array():
    a = BufferBuilder().add_indices_array(np.array([1, 2, 3]))
    assert a.type == Accessor.Type.SCALAR
    assert a.componentType == Accessor.ComponentType.UNSIGNED_INT


def test_add_element_array():
    a = BufferBuilder().add_element_array(np.array([1, 2, 3]))
    assert (
        a.bufferView and a.bufferView.target == BufferView.Target.ELEMENT_ARRAY_BUFFER
    )
    assert a.componentType == Accessor.ComponentType.UNSIGNED_INT


def test_add_array_errors():
    with raises(ValueError) as e:
        BufferBuilder().add_array(np.array([[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]]))
    assert "could not guess accessor type" in str(e)

    with raises(ValueError) as e:
        BufferBuilder().add_array(np.array([1j, 2, 3j, 4, 5j], np.complex64))  # type: ignore[reportArgumentType]
    assert "could not guess component type" in str(e)


def test_trisrip_cube_buffer_builder():
    tristrip_cube = [
        (-1, +1, +1),
        (+1, +1, +1),
        (-1, -1, +1),
        (+1, -1, +1),
        (+1, -1, -1),
        (+1, +1, +1),
        (+1, +1, -1),
        (-1, +1, +1),
        (-1, +1, -1),
        (-1, -1, +1),
        (-1, -1, -1),
        (+1, -1, -1),
        (-1, +1, -1),
        (+1, +1, -1),
    ]
    b = BufferBuilder()

    gltf = Gltf2(
        scene=Scene(
            nodes=[
                Node(
                    mesh=Mesh(
                        primitives=[
                            MeshPrimitive(
                                MeshPrimitiveAttributes(
                                    POSITION=b.add_array(
                                        np.array(tristrip_cube, dtype=np.float32)
                                    )
                                ),
                                mode=MeshPrimitive.Mode.TRIANGLE_STRIP,
                            )
                        ]
                    ),
                    extras={"lorem": "ipsum"},
                )
            ]
        ),
        extras={"hello": "world"},
    )

    assert gltf.dump() == {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "extras": {"hello": "world"},
        "scene": 0,
        "accessors": [
            {
                "componentType": 5126,
                "count": 14,
                "type": "VEC3",
                "bufferView": 0,
                "min": [-1.0, -1.0, -1.0],
                "max": [1.0, 1.0, 1.0],
            }
        ],
        "buffers": [
            {
                "byteLength": 168,
                "uri": "data:application/gltf-buffer;base64,AACAvwAAgD8AAIA/AACAPwAAgD8AAIA/AACAvwAAgL8AAIA/AACAPwAAgL8AAIA/AACAPwAAgL8AAIC/AACAPwAAgD8AAIA/AACAPwAAgD8AAIC/AACAvwAAgD8AAIA/AACAvwAAgD8AAIC/AACAvwAAgL8AAIA/AACAvwAAgL8AAIC/AACAPwAAgL8AAIC/AACAvwAAgD8AAIC/AACAPwAAgD8AAIC/",
            }
        ],
        "bufferViews": [{"buffer": 0, "byteLength": 168, "target": 34962}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 5}]}],
        "nodes": [{"mesh": 0, "extras": {"lorem": "ipsum"}}],
        "scenes": [{"nodes": [0]}],
    }


def test_interleaving():
    data = b"lorem"
    for i in range(1, 3):
        data += pack("<fffffb", i + 0.1, i + 0.2, i + 0.3, i + 0.4, i + 0.5, i)
    data += b"ipsum"

    bufferView = BufferView(
        buffer=DataBuffer(data),
        byteLength=len(data),
        byteOffset=5,
        byteStride=3 * 4 + 2 * 4 + 1,
    )
    accessor1 = Accessor(
        componentType=Accessor.ComponentType.FLOAT,
        count=2,
        type=Accessor.Type.VEC3,
        bufferView=bufferView,
        byteOffset=0,
    )
    accessor2 = Accessor(
        componentType=Accessor.ComponentType.FLOAT,
        count=2,
        type=Accessor.Type.VEC2,
        bufferView=bufferView,
        byteOffset=3 * 4,
    )
    accessor3 = Accessor(
        componentType=Accessor.ComponentType.BYTE,
        count=2,
        type=Accessor.Type.SCALAR,
        bufferView=bufferView,
        byteOffset=3 * 4 + 2 * 4,
    )

    expected1 = np.array([[1.1, 1.2, 1.3], [2.1, 2.2, 2.3]], np.float32)
    expected2 = np.array([[1.4, 1.5], [2.4, 2.5]], np.float32)
    expected3 = np.array([1, 2], np.byte)

    assert np.all(array_from_accessor(accessor1) == expected1)
    assert np.all(array_from_accessor(accessor2) == expected2)
    assert np.all(array_from_accessor(accessor3) == expected3)


def test_read_sparse_accessor():
    expected = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [2, 0, 0],
            [3, 0, 0],
            [4, 0, 0],
            [5, 0, 0],
            [6, 0, 0],
            [0, 1, 0],
            [1, 2, 0],
            [2, 1, 0],
            [3, 3, 0],
            [4, 1, 0],
            [5, 4, 0],
            [6, 1, 0],
        ],
        np.float32,
    )
    gltf = gltfTutorial_005_BuffersBufferViewsAccessors()
    assert np.all(array_from_accessor(gltf.accessors[1]) == expected)


def test_read_sparse_accessor_no_view():
    expected = np.array(
        [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [1, 2, 0],
            [0, 0, 0],
            [3, 3, 0],
            [0, 0, 0],
            [5, 4, 0],
            [0, 0, 0],
        ],
        np.float32,
    )
    gltf = gltfTutorial_005_BuffersBufferViewsAccessors()
    gltf.accessors[1].bufferView = None
    assert np.all(array_from_accessor(gltf.accessors[1]) == expected)


def gltfTutorial_005_BuffersBufferViewsAccessors():
    """from https://github.com/KhronosGroup/glTF-Tutorials/blob/main/gltfTutorial/gltfTutorial_005_BuffersBufferViewsAccessors.md#sparse-accessors"""
    data = {
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}],
        "buffers": [
            {
                "uri": "data:application/gltf-buffer;base64,"
                "AAAIAAcAAAABAAgAAQAJAAgAAQACAAkAAgAKAAkAAgADAAoAAwALAAoAAwAEAAsABAAMAA"
                "sABAAFAAwABQANAAwABQAGAA0AAAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAQAAAAAAA"
                "AAAAAABAQAAAAAAAAAAAAACAQAAAAAAAAAAAAACgQAAAAAAAAAAAAADAQAAAAAAAAAAAAA"
                "AAAAAAgD8AAAAAAACAPwAAgD8AAAAAAAAAQAAAgD8AAAAAAABAQAAAgD8AAAAAAACAQAAA"
                "gD8AAAAAAACgQAAAgD8AAAAAAADAQAAAgD8AAAAACAAKAAwAAAAAAIA/AAAAQAAAAAAAAE"
                "BAAABAQAAAAAAAAKBAAACAQAAAAAA=",
                "byteLength": 284,
            }
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 72, "target": 34963},
            {"buffer": 0, "byteOffset": 72, "byteLength": 168},
            {"buffer": 0, "byteOffset": 240, "byteLength": 6},
            {"buffer": 0, "byteOffset": 248, "byteLength": 36},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5123,
                "count": 36,
                "type": "SCALAR",
                "max": [13],
                "min": [0],
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,
                "count": 14,
                "type": "VEC3",
                "max": [6.0, 4.0, 0.0],
                "min": [0.0, 0.0, 0.0],
                "sparse": {
                    "count": 3,
                    "indices": {
                        "bufferView": 2,
                        "byteOffset": 0,
                        "componentType": 5123,
                    },
                    "values": {"bufferView": 3, "byteOffset": 0},
                },
            },
        ],
        "asset": {"version": "2.0"},
    }
    return Gltf2.Load(data)


def test_get_bufferview_data():
    view = BufferView(DataBuffer(b"123456"), byteLength=3)
    assert get_bufferview_data(view) == b"123"

    view = BufferView(DataBuffer(b"123456"), byteLength=3, byteStride=2)
    with raises(ValueError) as e:
        get_bufferview_data(view)
    assert "byteStride and no accessor" in str(e)
