from typing import Any

from pytest import mark, raises

from glutenfreebakery import Gltf2
from glutenfreebakery.schema import (
    Accessor,
    Animation,
    Attributes,
    BufferView,
    Camera,
    DataBuffer,
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
    Texture,
    UriBuffer,
)


def test_init_default_scene():
    gltf = Gltf2(scene=Scene(nodes=[Node(mesh=Mesh())]))

    assert check_GltfRoot_internals(gltf)

    assert gltf.dump() == {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "meshes": [{}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }


def test_init_scenes():
    scene1 = Scene(nodes=[Node(mesh=Mesh())])
    scene2 = Scene(nodes=[Node(children=[Node(mesh=Mesh())])])
    gltf = Gltf2(scenes=[scene1, scene2], scene=scene2)

    assert check_GltfRoot_internals(gltf)

    assert gltf.dump() == {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "meshes": [{}, {}],
        "nodes": [{"mesh": 0}, {"children": [2]}, {"mesh": 1}],
        "scenes": [{"nodes": [0]}, {"nodes": [1]}],
        "scene": 1,
    }


def test_iadd_scenes():
    scene1 = Scene(nodes=[Node(mesh=Mesh())])
    scene2 = Scene(nodes=[Node(children=[Node(mesh=Mesh())])])
    gltf = Gltf2()
    gltf.scenes += [scene1, scene2]
    gltf.scene = scene2

    assert check_GltfRoot_internals(gltf)

    assert gltf.dump() == {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "meshes": [{}, {}],
        "nodes": [{"mesh": 0}, {"children": [2]}, {"mesh": 1}],
        "scenes": [{"nodes": [0]}, {"nodes": [1]}],
        "scene": 1,
    }


def test_set_scenes():
    scene1 = Scene(nodes=[Node(mesh=Mesh())])
    scene2 = Scene(nodes=[Node(children=[Node(mesh=Mesh())])])
    gltf = Gltf2()
    gltf.scenes = [scene1, scene2]
    gltf.scene = scene2

    assert check_GltfRoot_internals(gltf)

    assert gltf.dump() == {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "meshes": [{}, {}],
        "nodes": [{"mesh": 0}, {"children": [2]}, {"mesh": 1}],
        "scenes": [{"nodes": [0]}, {"nodes": [1]}],
        "scene": 1,
    }


def test_scene_nodes_field_converter():
    scene = Scene((Node(), Node()))  # init as tuple
    assert isinstance(scene.nodes, list)
    assert len(scene.nodes) == 2


def test_Attributes_is_MutableMapping():
    POSITION, NORMAL, TANGENT, TEXCOORD_0, TEXCOORD_1, COLOR_0, JOINTS_0, WEIGHTS_0 = (
        Accessor(Accessor.ComponentType.BYTE, 2, Accessor.Type.SCALAR) for _ in range(8)
    )
    attrs = Attributes(
        POSITION=POSITION,
        NORMAL=NORMAL,
        TANGENT=TANGENT,
        TEXCOORD_0=TEXCOORD_0,
        TEXCOORD_1=TEXCOORD_1,
        COLOR_0=COLOR_0,
        JOINTS_0=JOINTS_0,
        WEIGHTS_0=WEIGHTS_0,
    )

    assert attrs["POSITION"] is POSITION
    assert attrs["NORMAL"] is NORMAL
    assert attrs["TANGENT"] is TANGENT
    assert attrs["TEXCOORD_0"] is TEXCOORD_0
    assert attrs["TEXCOORD_1"] is TEXCOORD_1
    assert attrs["COLOR_0"] is COLOR_0
    assert attrs["JOINTS_0"] is JOINTS_0
    assert attrs["WEIGHTS_0"] is WEIGHTS_0

    del attrs["WEIGHTS_0"]
    assert attrs.WEIGHTS_0 is None

    attrs["TEXCOORD_1"] = attrs["TEXCOORD_0"]
    assert attrs["TEXCOORD_1"] is attrs["TEXCOORD_0"]


def test_Attributes_properties():
    POSITION, NORMAL, TANGENT, TEXCOORD_0, TEXCOORD_1, COLOR_0, JOINTS_0, WEIGHTS_0 = (
        Accessor(Accessor.ComponentType.BYTE, 2, Accessor.Type.SCALAR) for _ in range(8)
    )
    attrs = Attributes()

    attrs.POSITION = POSITION
    attrs.NORMAL = NORMAL
    attrs.TANGENT = TANGENT
    attrs.TEXCOORD_0 = TEXCOORD_0
    attrs.TEXCOORD_1 = TEXCOORD_1
    attrs.COLOR_0 = COLOR_0
    attrs.JOINTS_0 = JOINTS_0
    attrs.WEIGHTS_0 = WEIGHTS_0

    assert attrs.POSITION is POSITION
    assert attrs.NORMAL is NORMAL
    assert attrs.TANGENT is TANGENT
    assert attrs.TEXCOORD_0 is TEXCOORD_0
    assert attrs.TEXCOORD_1 is TEXCOORD_1
    assert attrs.COLOR_0 is COLOR_0
    assert attrs.JOINTS_0 is JOINTS_0
    assert attrs.WEIGHTS_0 is WEIGHTS_0

    attrs.POSITION = None
    attrs.NORMAL = None
    attrs.TANGENT = None
    attrs.TEXCOORD_0 = None
    attrs.TEXCOORD_1 = None
    attrs.COLOR_0 = None
    attrs.JOINTS_0 = None
    attrs.WEIGHTS_0 = None

    assert attrs.POSITION is None
    assert attrs.NORMAL is None
    assert attrs.TANGENT is None
    assert attrs.TEXCOORD_0 is None
    assert attrs.TEXCOORD_1 is None
    assert attrs.COLOR_0 is None
    assert attrs.JOINTS_0 is None
    assert attrs.WEIGHTS_0 is None


def test_load():
    data: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "glutenfreebakery"},
        "meshes": [{}, {}],
        "nodes": [{"mesh": 0}, {"children": [2]}, {"mesh": 1}],
        "scenes": [{"nodes": [0]}, {"nodes": [1]}],
        "scene": 1,
    }

    gltf = Gltf2.Load(data)
    assert check_GltfRoot_internals(gltf)


@mark.parametrize(
    "buffer",
    [
        UriBuffer(
            byteLength=168,
            uri="data:application/gltf-buffer;base64,"
            "AACAvwAAgD8AAIA/AACAPwAAgD8AAIA/AACAvwAAgL8AAIA/AACAPwAAgL8AAIA/AACAPwAAgL8AAIC/"
            "AACAPwAAgD8AAIA/AACAPwAAgD8AAIC/AACAvwAAgD8AAIA/AACAvwAAgD8AAIC/AACAvwAAgL8AAIA/"
            "AACAvwAAgL8AAIC/AACAPwAAgL8AAIC/AACAvwAAgD8AAIC/AACAPwAAgD8AAIC/",
        ),
        DataBuffer(
            b"\x00\x00\x80\xbf\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?"
            b"\x00\x00\x80?\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80?\x00\x00\x80?"
            b"\x00\x00\x80\xbf\x00\x00\x80?\x00\x00\x80?\x00\x00\x80\xbf\x00\x00\x80\xbf"
            b"\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?\x00\x00\x80?"
            b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80?\x00\x00\x80?\x00\x00\x80\xbf"
            b"\x00\x00\x80?\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80?"
            b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80?"
            b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80?"
            b"\x00\x00\x80\xbf\x00\x00\x80?\x00\x00\x80?\x00\x00\x80\xbf"
        ),
    ],
)
def test_trisrip_cube(buffer: UriBuffer):
    accessor = Accessor(
        componentType=Accessor.ComponentType.FLOAT,
        count=14,
        type=Accessor.Type.VEC3,
        bufferView=BufferView(
            buffer=buffer, byteLength=168, target=BufferView.Target.ARRAY_BUFFER
        ),
        min=[-1.0, -1.0, -1.0],
        max=[1.0, 1.0, 1.0],
    )
    gltf = Gltf2(
        scene=Scene(
            nodes=[
                Node(
                    mesh=Mesh(
                        primitives=[
                            Primitive(
                                Attributes(POSITION=accessor), mode=Mode.TRIANGLE_STRIP
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
                "uri": "data:application/gltf-buffer;base64,"
                "AACAvwAAgD8AAIA/AACAPwAAgD8AAIA/AACAvwAAgL8AAIA/AACAPwAAgL8AAIA/AACAPwAAgL8AAIC/"
                "AACAPwAAgD8AAIA/AACAPwAAgD8AAIC/AACAvwAAgD8AAIA/AACAvwAAgD8AAIC/AACAvwAAgL8AAIA/"
                "AACAvwAAgL8AAIC/AACAPwAAgL8AAIC/AACAvwAAgD8AAIC/AACAPwAAgD8AAIC/",
            }
        ],
        "bufferViews": [{"buffer": 0, "byteLength": 168, "target": 34962}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 5}]}],
        "nodes": [{"mesh": 0, "extras": {"lorem": "ipsum"}}],
        "scenes": [{"nodes": [0]}],
    }


def test_prop_arrays():
    gltf = Gltf2()
    scene0 = Scene()
    scene1 = Scene()
    scene2 = Scene()
    scene3 = Scene()
    gltf.scenes = [scene0, scene1, scene2]
    gltf.scene = scene3

    assert gltf.scenes.index(scene0) == 0
    assert gltf.scenes.index(scene1) == 1
    assert gltf.scenes.index(scene2) == 2
    assert gltf.scenes.index(scene3) == 3
    with raises(IndexError):
        gltf.scenes.index(Scene())

    with raises(IndexError):
        gltf.scenes[4]
    assert gltf.scenes[1:3] == [scene1, scene2]
    assert gltf.scenes[2:] == [scene2, scene3]


def check_GltfRoot_internals(root: GltfRoot):
    for name, cls in [
        ("buffers", (UriBuffer, DataBuffer)),
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
    ]:
        props = getattr(root, name)
        assert props.parent == root
        assert all(isinstance(x, cls) for x in props)

    assert isinstance(root.scene, Scene) or root.scene is None

    return True


def test_replace_buffers():
    buffer1 = DataBuffer(b"1111")
    buffer2 = DataBuffer(b"2222")
    buffer3 = DataBuffer(b"3333")

    view1 = BufferView(buffer1, buffer1.byteLength)
    view2 = BufferView(buffer2, buffer2.byteLength)
    view3a = BufferView(buffer3, buffer3.byteLength)
    view3b = BufferView(buffer3, buffer3.byteLength)

    gltf = Gltf2(bufferViews=[view1, view2, view3a, view3b])

    buffer3_new = DataBuffer(b"xxxx")
    gltf.buffers.replace(lambda b: buffer3_new if b is buffer3 else b)

    assert buffer3_new in gltf.buffers
    assert buffer3 not in gltf.buffers

    assert view1.buffer is buffer1
    assert view2.buffer is buffer2
    assert view3a.buffer is buffer3_new
    assert view3b.buffer is buffer3_new


def test_replace_buffers_error():
    buffer1 = DataBuffer(b"1111")

    view1 = BufferView(buffer1, buffer1.byteLength)

    gltf = Gltf2(bufferViews=[view1])

    with raises(ValueError) as e:
        gltf.buffers.replace(lambda b: None)

    assert "cannot replace" in str(e)
