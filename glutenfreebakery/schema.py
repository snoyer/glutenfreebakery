from __future__ import annotations

import logging
from enum import Enum, IntEnum
from itertools import chain
from typing import Any, Iterator, Literal, TypeVar

from attrs import Attribute, define, field, fields

from .schema_boilerplate import (
    PartiallyImplicitList,
    list_converter,
    optional_list_converter,
)

logger = logging.getLogger(__name__)


GltfDictValue = str | int | float | list["GltfDictValue"] | dict[str, "GltfDictValue"]
GltfDict = dict[str, GltfDictValue]

T = TypeVar("T")


@define(kw_only=True)
class GltfProperty:
    """glTF Property"""

    extensions: GltfDict = field(factory=dict)
    """JSON object with extension-specific objects."""
    extras: GltfDict = field(factory=dict)
    """Application-specific data.
    Although `extras` **MAY** have any type, it is common for applications to store and access custom data as key/value pairs. Therefore, `extras` **SHOULD** be a JSON object rather than a primitive value for best portability."""

    def __attrs_post_init__(self):
        for attr in fields(type(self)):
            value = getattr(self, attr.name)
            if isinstance(value, PartiallyImplicitList):
                value.parent = self


@define(kw_only=True)
class GltfChildOfRootProperty(GltfProperty):
    """glTF Child of Root Property"""

    name: str = ""
    """The user-defined name of this object.  This is not necessarily unique, e.g., an accessor and a buffer could have the same name, or two accessors could even have the same name."""


GltfPropertyT = TypeVar("GltfPropertyT", bound=GltfProperty)
GltfPropertyT2 = TypeVar("GltfPropertyT2", bound=GltfProperty)


class PropertyArray(PartiallyImplicitList[T, GltfPropertyT]):
    pass


def _fix_prop_array(
    instance: Any, attribute: Attribute[Any], value: Any
) -> PropertyArray[Any, Any]:
    converted = attribute.converter(value)  # type: ignore
    if isinstance(converted, PropertyArray):
        converted.parent = instance
    return converted


class GltfPropertyArray(PropertyArray[GltfPropertyT, GltfPropertyT2]):
    pass


GltfChildOfRootPropertyT = TypeVar(
    "GltfChildOfRootPropertyT", bound=GltfChildOfRootProperty
)


class GltfChildOfRootPropertyArray(
    GltfPropertyArray[GltfChildOfRootPropertyT, "GltfRoot"]
):
    pass


class ComponentType(IntEnum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126


class AccessorType(Enum):
    SCALAR = "SCALAR"
    VEC2 = "VEC2"
    VEC3 = "VEC3"
    VEC4 = "VEC4"
    MAT2 = "MAT2"
    MAT3 = "MAT3"
    MAT4 = "MAT4"


@define
class Accessor(GltfChildOfRootProperty):
    """A typed view into a buffer view that contains raw binary data."""

    componentType: ComponentType
    """The datatype of the accessor's components.  UNSIGNED_INT type **MUST NOT** be used for any accessor that is not referenced by `mesh.primitive.indices`."""
    count: int
    """The number of elements referenced by this accessor, not to be confused with the number of bytes or number of components."""
    type: AccessorType
    """Specifies if the accessor's elements are scalars, vectors, or matrices."""
    bufferView: BufferView | None = None
    """The ~~index of the~~ buffer view. When undefined, the accessor **MUST** be initialized with zeros; `sparse` property or extensions **MAY** override zeros with actual values."""
    byteOffset: int = 0
    """The offset relative to the start of the buffer view in bytes."""
    normalized: bool = False
    """Specifies whether integer data values are normalized (`true`) to [0, 1] (for unsigned types) or to [-1, 1] (for signed types) when they are accessed. This property **MUST NOT** be set to `true` for accessors with `FLOAT` or `UNSIGNED_INT` component type."""
    min: list[float] | None = None
    """Minimum value of each component in this accessor.  Array elements **MUST** be treated as having the same data type as accessor's `componentType`. Both `min` and `max` arrays have the same length.  The length is determined by the value of the `type` property; it can be 1, 2, 3, 4, 9, or 16.\n\n`normalized` property has no effect on array values: they always correspond to the actual values stored in the buffer. When the accessor is sparse, this property **MUST** contain minimum values of accessor data with sparse substitution applied."""
    max: list[float] | None = None
    """Maximum value of each component in this accessor.  Array elements **MUST** be treated as having the same data type as accessor's `componentType`. Both `min` and `max` arrays have the same length.  The length is determined by the value of the `type` property; it can be 1, 2, 3, 4, 9, or 16.\n\n`normalized` property has no effect on array values: they always correspond to the actual values stored in the buffer. When the accessor is sparse, this property **MUST** contain maximum values of accessor data with sparse substitution applied."""
    sparse: Sparse | None = None
    """Sparse storage of elements that deviate from their initialization value."""


@define
class Sparse(GltfProperty):
    """Sparse storage of accessor values that deviate from their initialization value."""

    count: int
    """Number of deviating accessor values stored in the sparse array."""
    indices: SparseIndices
    """An object pointing to a buffer view containing the indices of deviating accessor values. The number of indices is equal to `count`. Indices **MUST** strictly increase."""
    values: SparseValues
    """An object pointing to a buffer view containing the deviating accessor values."""


class IndicesComponentType(IntEnum):
    UNSIGNED_BYTE = 5121
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125


@define
class SparseIndices(GltfProperty):
    """An object pointing to a buffer view containing the indices of deviating accessor values. The number of indices is equal to `accessor.sparse.count`. Indices **MUST** strictly increase."""

    bufferView: BufferView
    """The ~~index of the~~ buffer view with sparse indices. The referenced buffer view **MUST NOT** have its `target` or `byteStride` properties defined. The buffer view and the optional `byteOffset` **MUST** be aligned to the `componentType` byte length."""
    componentType: IndicesComponentType
    """The indices data type."""
    byteOffset: int = 0
    """The offset relative to the start of the bufferView in bytes."""


@define
class SparseValues(GltfProperty):
    """An object pointing to a buffer view containing the deviating accessor values. The number of elements is equal to `accessor.sparse.count` times number of components. The elements have the same component type as the base accessor. The elements are tightly packed. Data **MUST** be aligned following the same rules as the base accessor."""

    bufferView: BufferView
    """The ~~index of the~~ bufferView with sparse values. The referenced buffer view **MUST NOT** have its `target` or `byteStride` properties defined."""
    byteOffset: int = 0
    """The offset relative to the start of the bufferView in bytes."""


@define
class Asset(GltfProperty):
    """Metadata about the glTF asset."""

    version: str
    """glTF version in the form of `<major>.<minor>` that this asset targets."""
    copyright: str | None = None
    """A copyright message suitable for display to credit the content creator."""
    generator: str | None = None
    """Tool that generated this glTF model.  Useful for debugging."""
    minVersion: str | None = None
    """Minimum glTF version in the form of `<major>.<minor>` that this asset targets.
    This property **MUST NOT** be greater than the asset version."""


@define
class UriBuffer(GltfChildOfRootProperty):
    """A buffer points to binary geometry, animation, or skins."""

    byteLength: int
    """The length of the buffer in bytes."""
    uri: str = ""
    """The URI (or IRI) of the buffer.  Relative paths are relative to the current glTF asset.  Instead of referencing an external file, this field **MAY** contain a `data:`-URI."""


@define
class DataBuffer(GltfChildOfRootProperty):
    """A buffer points to binary geometry, animation, or skins."""

    data: bytes = b""
    mimeType: str = "application/gltf-buffer"


Buffer = UriBuffer | DataBuffer


class Target(IntEnum):
    ARRAY_BUFFER = 34962
    ELEMENT_ARRAY_BUFFER = 34963


@define
class BufferView(GltfChildOfRootProperty):
    """A view into a buffer generally representing a subset of the buffer."""

    buffer: Buffer
    """The ~~index of the~~ buffer."""
    byteLength: int
    """The length of the bufferView in bytes."""
    byteOffset: int = 0
    """The offset into the buffer in bytes."""
    byteStride: int = 0
    """The stride, in bytes."""
    target: Target | None = None
    """The hint representing the intended GPU buffer type to use with this buffer view."""


class Attributes(dict[str, Accessor]):
    def __init__(
        self,
        *,
        POSITION: Accessor | None = None,
        COLOR_0: Accessor | None = None,
        TEXCOORD_0: Accessor | None = None,
        TEXCOORD_1: Accessor | None = None,
        NORMAL: Accessor | None = None,
        TANGENT: Accessor | None = None,
        JOINTS_0: Accessor | None = None,
        WEIGHTS_0: Accessor | None = None,
        **kwargs: Accessor,
    ) -> None:
        d = dict(
            POSITION=POSITION,
            NORMAL=NORMAL,
            TANGENT=TANGENT,
            TEXCOORD_0=TEXCOORD_0,
            TEXCOORD_1=TEXCOORD_1,
            COLOR_0=COLOR_0,
            JOINTS_0=JOINTS_0,
            WEIGHTS_0=WEIGHTS_0,
            **kwargs,
        )
        super().__init__(
            **{k: v for k, v in d.items() if v is not None},
        )


class MagFilter(IntEnum):
    NEAREST = 9728
    LINEAR = 9729


class MinFilter(IntEnum):
    NEAREST = 9728
    LINEAR = 9729
    NEAREST_MIPMAP_NEAREST = 9984
    LINEAR_MIPMAP_NEAREST = 9985
    NEAREST_MIPMAP_LINEAR = 9986
    LINEAR_MIPMAP_LINEAR = 9987


class Wrap(IntEnum):
    CLAMP_TO_EDGE = 33071
    MIRRORED_REPEAT = 33648
    REPEAT = 10497


@define
class Sampler(GltfChildOfRootProperty):
    """Texture sampler properties for filtering and wrapping modes."""

    magFilter: MagFilter | None = None
    """"Magnification filter."""
    minFilter: MinFilter | None = None
    """Minification filter."""
    wrapS: Wrap = Wrap.REPEAT
    """S (U) wrapping mode.  All valid values correspond to WebGL enums."""
    wrapT: Wrap = Wrap.REPEAT
    """T (V) wrapping mode."""


@define
class Image(GltfChildOfRootProperty):
    """Image data used to create a texture. Image **MAY** be referenced by an URI (or IRI) or a buffer view index."""

    uri: str | None = None
    """The URI (or IRI) of the image.  Relative paths are relative to the current glTF asset.  Instead of referencing an external file, this field **MAY** contain a `data:`-URI. This field **MUST NOT** be defined when `bufferView` is defined."""
    mimeType: Literal["image/jpeg", "image/png"] | str = ""
    "The image's media type. This field **MUST** be defined when `bufferView` is defined."
    bufferView: BufferView | None = None
    """The ~~index of the~~ bufferView that contains the image. This field **MUST NOT** be defined when `uri` is defined."""


@define
class Texture(GltfChildOfRootProperty):
    """A texture and its sampler."""

    source: Image | None = None
    """The ~~index of the~~ image used by this texture. When undefined, an extension or other mechanism **SHOULD** supply an alternate texture source, otherwise behavior is undefined."""
    sampler: Sampler | None = None
    """The ~~index of the~~ sampler used by this texture. When undefined, a sampler with repeat wrapping and auto filtering **SHOULD** be used."""


@define
class TextureInfo(GltfProperty):
    """Reference to a texture."""

    texture: Texture
    """The ~~index of the~~ texture."""
    texCoord: int = 0
    """This integer value is used to construct a string in the format `TEXCOORD_<set index>` which is a reference to a key in `mesh.primitives.attributes` (e.g. a value of `0` corresponds to `TEXCOORD_0`). A mesh primitive **MUST** have the corresponding texture coordinate attributes for the material to be applicable to it."""


@define
class PbrMetallicRoughness(GltfProperty):
    """A set of parameter values that are used to define the metallic-roughness material model from Physically-Based Rendering (PBR) methodology."""

    baseColorFactor: tuple[float, float, float, float] = (1, 1, 1, 1)
    """The factors for the base color of the material. This value defines linear multipliers for the sampled texels of the base color texture."""
    baseColorTexture: TextureInfo | None = None
    """The base color texture. The first three components (RGB) **MUST** be encoded with the sRGB transfer function. They specify the base color of the material. If the fourth component (A) is present, it represents the linear alpha coverage of the material. Otherwise, the alpha coverage is equal to `1.0`. The `material.alphaMode` property specifies how alpha is interpreted. The stored texels **MUST NOT** be premultiplied. When undefined, the texture **MUST** be sampled as having `1.0` in all components."""
    metallicFactor: float = 1
    """The factor for the metalness of the material. This value defines a linear multiplier for the sampled metalness values of the metallic-roughness texture."""
    roughnessFactor: float = 1
    """The factor for the roughness of the material. This value defines a linear multiplier for the sampled roughness values of the metallic-roughness texture."""
    metallicRoughnessTexture: TextureInfo | None = None
    """The metallic-roughness texture. The metalness values are sampled from the B channel. The roughness values are sampled from the G channel. These values **MUST** be encoded with a linear transfer function. If other channels are present (R or A), they **MUST** be ignored for metallic-roughness calculations. When undefined, the texture **MUST** be sampled as having `1.0` in G and B components."""


class AlphaMode(Enum):
    OPAQUE = "OPAQUE"
    """The alpha value is ignored, and the rendered output is fully opaque."""
    MASK = "MASK"
    """The rendered output is either fully opaque or fully transparent depending on the alpha value and the specified `alphaCutoff` value; the exact appearance of the edges **MAY** be subject to implementation-specific techniques such as \"`Alpha-to-Coverage`\"."""
    BLEND = "BLEND"
    """The alpha value is used to composite the source and destination areas. The rendered output is combined with the background using the normal painting operation (i.e. the Porter and Duff over operator)."""


@define
class OcclusionTextureInfo(TextureInfo):
    """Material Occlusion Texture Info"""

    strength: float = 1
    """A scalar parameter controlling the amount of occlusion applied. A value of `0.0` means no occlusion. A value of `1.0` means full occlusion. This value affects the final occlusion value as: `1.0 + strength * (<sampled occlusion texture value> - 1.0)`."""


@define
class NormalTextureInfo(TextureInfo):
    """Material Normal Texture Info"""

    scale: float = 1
    """The scalar parameter applied to each normal vector of the texture. This value scales the normal vector in X and Y directions using the formula: `scaledNormal =  normalize((<sampled normal texture value> * 2.0 - 1.0) * vec3(<normal scale>, <normal scale>, 1.0))`."""


@define
class Material(GltfChildOfRootProperty):
    pbrMetallicRoughness: PbrMetallicRoughness | None = None
    """A set of parameter values that are used to define the metallic-roughness material model from Physically Based Rendering (PBR) methodology. When undefined, all the default values of `pbrMetallicRoughness` **MUST** apply."""
    normalTexture: NormalTextureInfo | None = None
    """The tangent space normal texture. The texture encodes RGB components with linear transfer function. Each texel represents the XYZ components of a normal vector in tangent space. The normal vectors use the convention +X is right and +Y is up. +Z points toward the viewer. If a fourth component (A) is present, it **MUST** be ignored. When undefined, the material does not have a tangent space normal texture."""
    occlusionTexture: OcclusionTextureInfo | None = None
    """The occlusion texture. The occlusion values are linearly sampled from the R channel. Higher values indicate areas that receive full indirect lighting and lower values indicate no indirect lighting. If other channels are present (GBA), they **MUST** be ignored for occlusion calculations. When undefined, the material does not have an occlusion texture."""
    emissiveTexture: TextureInfo | None = None
    """The emissive texture. It controls the color and intensity of the light being emitted by the material. This texture contains RGB components encoded with the sRGB transfer function. If a fourth component (A) is present, it **MUST** be ignored. When undefined, the texture **MUST** be sampled as having `1.0` in RGB components."""
    emissiveFactor: tuple[float, float, float] = (0, 0, 0)
    """The factors for the emissive color of the material. This value defines linear multipliers for the sampled texels of the emissive texture."""
    alphaMode: AlphaMode = AlphaMode.OPAQUE
    """The material's alpha rendering mode enumeration specifying the interpretation of the alpha value of the base color."""
    alphaCutoff: float = 0.5
    """Specifies the cutoff threshold when in `MASK` alpha mode. If the alpha value is greater than or equal to this value then it is rendered as fully opaque, otherwise, it is rendered as fully transparent. A value greater than `1.0` will render the entire material as fully transparent. This value **MUST** be ignored for other alpha modes. When `alphaMode` is not defined, this value **MUST NOT** be defined."""
    doubleSided: bool = False
    """Specifies whether the material is double sided. When this value is false, back-face culling is enabled. When this value is true, back-face culling is disabled and double-sided lighting is enabled. The back-face **MUST** have its normals reversed before the lighting equation is evaluated."""


class Mode(IntEnum):
    POINTS = 0
    LINES = 1
    LINE_LOOP = 2
    LINE_STRIP = 3
    TRIANGLES = 4
    TRIANGLE_STRIP = 5
    TRIANGLE_FAN = 6


@define
class Primitive(GltfProperty):
    """Geometry to be rendered with the given material."""

    attributes: dict[str, Accessor]
    """A plain JSON object, where each key corresponds to a mesh attribute semantic and each value is the ~~index of the~~ accessor containing attribute's data."""
    indices: Accessor | None = None
    """The ~~index of the~~ accessor that contains the vertex indices.  When this is undefined, the primitive defines non-indexed geometry.  When defined, the accessor **MUST** have `SCALAR` type and an unsigned integer component type."""
    material: Material | None = None
    """The ~~index of the~~ material to apply to this primitive when rendering."""
    mode: Mode = Mode.TRIANGLES
    """The topology type of primitives to render."""
    targets: list[dict[Literal["POSITION", "NORMAL", "TANGENT"], Accessor]] = field(
        factory=list
    )
    """An array of morph targets.

    A plain JSON object specifying attributes displacements in a morph target, where each key corresponds to one of the three supported attribute semantic (`POSITION`, `NORMAL`, or `TANGENT`) and each value is the ~~index of the~~ accessor containing the attribute displacements' data."""


@define
class Mesh(GltfChildOfRootProperty):
    primitives: list[Primitive] = field(factory=list, converter=list_converter)
    """An array of primitives, each defining geometry to be rendered."""
    weights: list[float] | None = None
    """Array of weights to be applied to the morph targets. The number of array elements **MUST** match the number of morph targets."""


@define
class Camera(GltfChildOfRootProperty):
    """A camera's projection.  A node **MAY** reference a camera to apply a transform to place the camera in the scene."""

    type: CameraType
    """Specifies if the camera uses a perspective or orthographic projection.  Based on this, either the camera's `perspective` or `orthographic` property **MUST** be defined."""
    orthographic: CameraOrthographic | None = None
    """An orthographic camera containing properties to create an orthographic projection matrix. This property **MUST NOT** be defined when `perspective` is defined."""
    perspective: CameraPerspective | None = None
    """A perspective camera containing properties to create a perspective projection matrix. This property **MUST NOT** be defined when `orthographic` is defined."""


@define
class CameraOrthographic(GltfProperty):
    """An orthographic camera containing properties to create an orthographic projection matrix."""

    xmag: float
    "The floating-point horizontal magnification of the view. This value **MUST NOT** be equal to zero. This value **SHOULD NOT** be negative."
    ymag: float
    """The floating-point vertical magnification of the view. This value **MUST NOT** be equal to zero. This value **SHOULD NOT** be negative."""
    zfar: float
    """The floating-point distance to the far clipping plane. This value **MUST NOT** be equal to zero. `zfar` **MUST** be greater than `znear`."""
    znear: float
    """The floating-point distance to the near clipping plane."""


@define
class CameraPerspective(GltfProperty):
    """A perspective camera containing properties to create a perspective projection matrix."""

    yfov: float
    """The floating-point vertical field of view in radians. This value **SHOULD** be less than π."""
    znear: float
    """The floating-point distance to the near clipping plane."""
    zfar: float | None = None
    """The floating-point distance to the far clipping plane. When defined, `zfar` **MUST** be greater than `znear`. If `zfar` is undefined, client implementations **SHOULD** use infinite projection matrix."""
    aspectRatio: float | None = None
    """The floating-point aspect ratio of the field of view. When undefined, the aspect ratio of the rendering viewport **MUST** be used."""


class CameraType(Enum):
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class AnimationChannels(GltfPropertyArray["AnimationChannel", "Animation"]):
    pass


class AnimationSamplers(GltfPropertyArray["AnimationSampler", "Animation"]):
    def _from_parent(self, parent: Animation):
        for channel in parent.channels:
            yield channel.sampler


@define
class Animation(GltfChildOfRootProperty):
    """A keyframe animation."""

    channels: AnimationChannels = field(
        factory=AnimationChannels,
        converter=AnimationChannels,
        on_setattr=_fix_prop_array,
    )
    """An array of animation channels. An animation channel combines an animation sampler with a target property being animated. Different channels of the same animation **MUST NOT** have the same targets."""
    samplers: AnimationSamplers = field(
        factory=AnimationSamplers,
        converter=AnimationSamplers,
        on_setattr=_fix_prop_array,
    )
    """An array of animation samplers. An animation sampler combines timestamps with a sequence of output values and defines an interpolation algorithm."""


@define
class AnimationChannel(GltfProperty):
    """An animation channel combines an animation sampler with a target property being animated."""

    sampler: AnimationSampler
    """The ~~index of a~~ sampler in this animation used to compute the value for the target, e.g., a node's translation, rotation, or scale (TRS)."""
    target: AnimationChannelTarget
    """The descriptor of the animated property."""


@define
class AnimationChannelTarget(GltfProperty):
    path: Literal["translation", "rotation", "scale", "weights"] | str
    """The name of the node's TRS property to animate, or the `\"weights\"` of the Morph Targets it instantiates. For the `\"translation\"` property, the values that are provided by the sampler are the translation along the X, Y, and Z axes. For the `\"rotation\"` property, the values are a quaternion in the order (x, y, z, w), where w is the scalar. For the `\"scale\"` property, the values are the scaling factors along the X, Y, and Z axes."""
    node: Node | None = None
    """The ~~index of the~~ node to animate. When undefined, the animated object **MAY** be defined by an extension."""


@define
class AnimationSampler(GltfProperty):
    """An animation sampler combines timestamps with a sequence of output values and defines an interpolation algorithm."""

    input: Accessor
    """The ~~index of an~~ accessor containing keyframe timestamps. The accessor **MUST** be of scalar type with floating-point components. The values represent time in seconds with `time[0] >= 0.0`, and strictly increasing values, i.e., `time[n + 1] > time[n]`."""
    output: Accessor
    """The ~~index of an~~ accessor, containing keyframe output values."""
    interpolation: AnimationSamplerIterpolation | None = None
    """Interpolation algorithm."""


class AnimationSamplerIterpolation(Enum):
    LINEAR = "LINEAR"
    """The animated values are linearly interpolated between keyframes. When targeting a rotation, spherical linear interpolation (slerp) **SHOULD** be used to interpolate quaternions. The number of output elements **MUST** equal the number of input elements."""
    STEP = "STEP"
    """The animated values remain constant to the output of the first keyframe, until the next keyframe. The number of output elements **MUST** equal the number of input elements."""
    CUBICSPLINE = "CUBICSPLINE"
    """The animation's interpolation is computed using a cubic spline with specified tangents. The number of output elements **MUST** equal three times the number of input elements. For each input element, the output stores three elements, an in-tangent, a spline vertex, and an out-tangent. There **MUST** be at least two keyframes when using this interpolation."""


@define
class Skin(GltfChildOfRootProperty):
    """Joints and matrices defining a skin."""

    joints: list[Node] = field(converter=list_converter)
    """~~Indices of~~ skeleton nodes, used as joints in this skin."""
    inverseBindMatrices: Accessor | None = None
    """The ~~index of the~~ accessor containing the floating-point 4x4 inverse-bind matrices. Its `accessor.count` property **MUST** be greater than or equal to the number of elements of the `joints` array. When undefined, each matrix is a 4x4 identity matrix."""
    skeleton: Node | None = None
    """The ~~index of the~~ node used as a skeleton root. The node **MUST** be the closest common root of the joints hierarchy or a direct or indirect parent node of the closest common root."""


@define
class Node(GltfChildOfRootProperty):
    camera: Camera | None = None
    """The ~~index of the~~ camera referenced by this node."""
    skin: Skin | None = None
    """"The ~~index of the~~ skin referenced by this node. When a skin is referenced by a node within a scene, all joints used by the skin **MUST** belong to the same scene. When defined, `mesh` **MUST** also be defined."""
    mesh: Mesh | None = None
    """The ~~index of the~~ mesh in this node."""
    children: list[Node] | None = field(default=None, converter=optional_list_converter)
    """The ~~indices of this~~ node's children."""
    # fmt: off
    matrix: tuple[
        float, float, float, float,
        float, float, float, float,
        float, float, float, float,
        float, float, float, float,
    ] | None = None
    # fmt: on
    """A floating-point 4x4 transformation matrix stored in column-major order."""
    rotation: tuple[float, float, float, float] | None = None
    """The node's unit quaternion rotation in the order (x, y, z, w), where w is the scalar."""
    scale: tuple[float, float, float] | None = None
    """The node's non-uniform scale, given as the scaling factors along the x, y, and z axes."""
    translation: tuple[float, float, float] | None = None
    """The node's translation along the x, y, and z axes."""
    weights: list[float] | None = None
    """The weights of the instantiated morph target. The number of array elements **MUST** match the number of morph targets of the referenced mesh. When defined, `mesh` **MUST** also be defined."""


@define
class Scene(GltfChildOfRootProperty):
    nodes: list[Node] = field(factory=list, converter=list_converter)


# ################################################################################


class Cameras(GltfChildOfRootPropertyArray[Camera]):
    pass


class Animations(GltfChildOfRootPropertyArray[Animation]):
    pass


class Accessors(GltfChildOfRootPropertyArray[Accessor]):
    def _from_parent(self, parent: GltfRoot) -> Iterator[Accessor | None]:
        for mesh in parent.meshes:
            for primitive in mesh.primitives:
                yield primitive.indices
                yield from primitive.attributes.values()
        for skin in parent.skins:
            yield skin.inverseBindMatrices
        for animation in parent.animations:
            for sampler in chain(
                animation.samplers, (channel.sampler for channel in animation.channels)
            ):
                yield sampler.input
                yield sampler.output


class BufferViews(GltfChildOfRootPropertyArray[BufferView]):
    def _from_parent(self, parent: GltfRoot):
        for accessor in parent.accessors:
            yield accessor.bufferView
        for image in parent.images:
            yield image.bufferView


class Buffers(GltfChildOfRootPropertyArray[Buffer]):
    def _from_parent(self, parent: GltfRoot):
        for view in parent.bufferViews:
            yield view.buffer


class Materials(GltfChildOfRootPropertyArray[Material]):
    def _from_parent(self, parent: GltfRoot):
        for mesh in parent.meshes:
            for prim in mesh.primitives:
                yield prim.material


class Meshes(GltfChildOfRootPropertyArray[Mesh]):
    def _from_parent(self, parent: GltfRoot):
        return (node.mesh for node in parent.nodes if node.mesh)


class Nodes(GltfChildOfRootPropertyArray[Node]):
    def _from_parent(self, parent: GltfRoot) -> Iterator[Node | None]:
        seen = set()
        for scene in parent.scenes:
            q = list(scene.nodes)
            while q:
                node = q.pop()
                if id(node) not in seen:
                    seen.add(id(node))
                    yield node
                    if children := node.children:
                        q = children + q


class Textures(GltfChildOfRootPropertyArray[Texture]):
    def _from_parent(self, parent: GltfRoot) -> Iterator[Texture]:
        def text_infos():
            for material in parent.materials:
                yield material.emissiveTexture
                yield material.normalTexture
                yield material.occlusionTexture
                if pbr := material.pbrMetallicRoughness:
                    yield pbr.baseColorTexture
                    yield pbr.metallicRoughnessTexture

        return (info.texture for info in text_infos() if info)


class Samplers(GltfChildOfRootPropertyArray[Sampler]):
    def _from_parent(self, parent: GltfRoot):
        for texture in parent.textures:
            yield texture.sampler


class Images(GltfChildOfRootPropertyArray[Image]):
    def _from_parent(self, parent: GltfRoot):
        for texture in parent.textures:
            yield texture.source


class Scenes(GltfChildOfRootPropertyArray[Scene]):
    def _from_parent(self, parent: GltfRoot):
        yield parent.scene


class Skins(GltfChildOfRootPropertyArray[Skin]):
    def _from_parent(self, parent: GltfRoot):
        for node in parent.nodes:
            yield node.skin


class ExtensionsUsed(PropertyArray[str, "GltfRoot"]):
    def _from_parent(self, parent: GltfRoot) -> Iterator[str]:
        for prop in _iter_props(parent):
            yield from prop.extensions

    def __iter__(self):
        return iter(sorted(list(super().__iter__())))


class ExtensionsRequired(PropertyArray[str, "GltfRoot"]):
    def __iter__(self):
        return iter(sorted(list(super().__iter__())))


@define(kw_only=True)
class GltfRoot(GltfProperty):
    asset: Asset = field(factory=lambda: Asset("2.0", generator="glutenfreebakery"))
    scene: Scene | None = None

    # fmt: off
    accessors  : Accessors   = field(factory=Accessors  , converter=Accessors  , on_setattr=_fix_prop_array)
    animations : Animations  = field(factory=Animations , converter=Animations , on_setattr=_fix_prop_array)
    buffers    : Buffers     = field(factory=Buffers    , converter=Buffers    , on_setattr=_fix_prop_array)
    bufferViews: BufferViews = field(factory=BufferViews, converter=BufferViews, on_setattr=_fix_prop_array)
    cameras    : Cameras     = field(factory=Cameras    , converter=Cameras    , on_setattr=_fix_prop_array)
    images     : Images      = field(factory=Images     , converter=Images     , on_setattr=_fix_prop_array)
    materials  : Materials   = field(factory=Materials  , converter=Materials  , on_setattr=_fix_prop_array)
    meshes     : Meshes      = field(factory=Meshes     , converter=Meshes     , on_setattr=_fix_prop_array)
    nodes      : Nodes       = field(factory=Nodes      , converter=Nodes      , on_setattr=_fix_prop_array)
    samplers   : Samplers    = field(factory=Samplers   , converter=Samplers   , on_setattr=_fix_prop_array)
    scenes     : Scenes      = field(factory=Scenes     , converter=Scenes     , on_setattr=_fix_prop_array)
    skins      : Skins       = field(factory=Skins      , converter=Skins      , on_setattr=_fix_prop_array)
    textures   : Textures    = field(factory=Textures   , converter=Textures   , on_setattr=_fix_prop_array)

    extensionsUsed    : ExtensionsUsed     = field(factory=ExtensionsUsed    , converter=ExtensionsUsed)
    extensionsRequired: ExtensionsRequired = field(factory=ExtensionsRequired, converter=ExtensionsRequired)
    # fmt: on


def _iter_props(prop: GltfProperty) -> Iterator[GltfProperty]:
    for f in fields(type(prop)):
        value = getattr(prop, f.name)
        if isinstance(value, (GltfPropertyArray, list)):
            for child in value:
                if isinstance(child, GltfProperty):
                    yield child
                    yield from _iter_props(child)
        elif isinstance(value, GltfProperty):
            yield value
            yield from _iter_props(value)
