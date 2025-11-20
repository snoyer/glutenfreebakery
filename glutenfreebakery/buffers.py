import logging
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .schema import (
    Accessor,
    AccessorType,
    Buffer,
    BufferView,
    ComponentType,
    DataBuffer,
    IndicesComponentType,
    Target,
)
from .util import read_uri_data

logger = logging.getLogger(__name__)


NP_TYPES = (
    np.byte
    | np.ubyte
    | np.short
    | np.ushort
    | np.integer
    | np.unsignedinteger
    | np.floating
)

COMPONENT_TYPE_TO_DTYPE = {
    ComponentType.BYTE: np.byte,
    ComponentType.UNSIGNED_BYTE: np.ubyte,
    ComponentType.SHORT: np.short,
    ComponentType.UNSIGNED_SHORT: np.ushort,
    ComponentType.UNSIGNED_INT: np.uint32,
    ComponentType.FLOAT: np.float32,
}

INDICES_COMPONENT_TYPE_TO_DTYPE = {
    IndicesComponentType.UNSIGNED_BYTE: np.ubyte,
    IndicesComponentType.UNSIGNED_INT: np.uint32,
    IndicesComponentType.UNSIGNED_SHORT: np.ushort,
}

DTYPELIKE_TO_COMPONENT_TYPE = {
    np.byte: ComponentType.BYTE,
    np.ubyte: ComponentType.UNSIGNED_BYTE,
    np.short: ComponentType.SHORT,
    np.ushort: ComponentType.UNSIGNED_SHORT,
    np.floating: ComponentType.FLOAT,
    np.unsignedinteger: ComponentType.UNSIGNED_INT,
    np.integer: ComponentType.UNSIGNED_INT,
}

SHAPE_TO_ACCESSOR_TYPE: dict[tuple[int, ...], AccessorType] = {
    (): AccessorType.SCALAR,
    (2,): AccessorType.VEC2,
    (3,): AccessorType.VEC3,
    (4,): AccessorType.VEC4,
    (2, 2): AccessorType.MAT2,
    (3, 3): AccessorType.MAT3,
    (4, 4): AccessorType.MAT4,
}
ACCESSOR_TYPE_TO_SHAPE = {v: k for k, v in SHAPE_TO_ACCESSOR_TYPE.items()}


class BufferBuilder:
    def __init__(self, buffer: DataBuffer | None = None) -> None:
        self.buffer = DataBuffer() if buffer is None else buffer

    def add_array(
        self,
        array: NDArray[NP_TYPES],
        accessorType: AccessorType | None = None,
        componentType: ComponentType | None = None,
        target: Target | None = Target.ARRAY_BUFFER,
    ):
        return self.add(array, accessorType, componentType, target=target)

    def add_indices_array(
        self,
        array: NDArray[NP_TYPES],
    ):
        return self.add_element_array(array.flatten(), accessorType=AccessorType.SCALAR)

    def add_element_array(
        self,
        array: NDArray[NP_TYPES],
        accessorType: AccessorType | None = None,
        componentType: ComponentType | None = None,
    ):
        return self.add(array, accessorType, componentType, Target.ELEMENT_ARRAY_BUFFER)

    def add(
        self,
        array: NDArray[NP_TYPES],
        accessorType: AccessorType | None = None,
        componentType: ComponentType | None = None,
        target: Target | None = None,
    ):
        if componentType is None:
            componentType = guess_component_type(array)
            logger.debug(
                "guessed component type %s from dtype=%s",
                componentType.name,
                array.dtype,
            )

        dst_type = COMPONENT_TYPE_TO_DTYPE[componentType]
        if dst_type != array.dtype.type:
            logger.info(
                "converting array from %s to %s for component type %s",
                array.dtype,
                dst_type.__name__,
                componentType.name,
            )
            array = array.astype(dst_type)

        if accessorType is None:
            try:
                accessorType = SHAPE_TO_ACCESSOR_TYPE[array.shape[1:]]
                logger.debug(
                    "guessed accessor type %s from shape=%s",
                    accessorType.name,
                    array.shape,
                )
            except KeyError:
                raise ValueError(
                    f"could not guess accessor type for shape {array.shape}"
                )

        data_bytes = array.flatten().tobytes()

        offset = len(self.buffer.data)
        self.buffer.data += data_bytes

        view = BufferView(
            buffer=self.buffer,
            byteOffset=offset,
            byteLength=len(data_bytes),
            target=target,
        )

        return Accessor(
            bufferView=view,
            byteOffset=0,
            componentType=componentType,
            type=accessorType,
            count=array.shape[0],
            min=np.min(array, axis=0, keepdims=True).reshape(-1).tolist(),
            max=np.max(array, axis=0, keepdims=True).reshape(-1).tolist(),
        )


def guess_component_type(array: NDArray[Any]):
    for dtype_like, component_type in DTYPELIKE_TO_COMPONENT_TYPE.items():
        if np.issubdtype(array.dtype, dtype_like):
            return component_type
    raise ValueError("could not guess component type for %s", array.dtype)


def array_from_accessor(accessor: Accessor, relative_to: Path | None = None):
    dst_shape = ACCESSOR_TYPE_TO_SHAPE[accessor.type]
    dst_dtype = COMPONENT_TYPE_TO_DTYPE[accessor.componentType]
    dst_item_size = np.dtype(dst_dtype).itemsize

    if view := accessor.bufferView:
        buffer_data = get_buffer_data(view.buffer, relative_to=relative_to)
        if view.byteStride:
            byte_buffer = np.frombuffer(
                buffer_data,
                np.ubyte,
                offset=view.byteOffset,
                count=view.byteStride * accessor.count,
            )
            flat = np.frombuffer(
                np.lib.stride_tricks.sliding_window_view(
                    byte_buffer, dst_item_size * (dst_shape or [1])[-1]
                )[accessor.byteOffset :: view.byteStride].tobytes(),
                dst_dtype,
            )
        else:
            flat = np.frombuffer(
                buffer_data,
                dst_dtype,
                offset=view.byteOffset + accessor.byteOffset,
                count=view.byteLength // dst_item_size,
            )

        reshaped = flat.reshape((-1, *dst_shape), copy=accessor.sparse is not None)
    else:
        reshaped = np.zeros((accessor.count, *dst_shape), dst_dtype)

    if sparse := accessor.sparse:
        indices_view = sparse.indices.bufferView
        indices = np.frombuffer(
            get_buffer_data(indices_view.buffer, relative_to=relative_to),
            INDICES_COMPONENT_TYPE_TO_DTYPE[sparse.indices.componentType],
            offset=indices_view.byteOffset + sparse.indices.byteOffset,
            count=sparse.count,
        )

        values_view = sparse.values.bufferView
        values = np.frombuffer(
            get_buffer_data(values_view.buffer, relative_to=relative_to),
            dst_dtype,
            offset=values_view.byteOffset + sparse.values.byteOffset,
            count=values_view.byteLength // dst_item_size,
        ).reshape((-1, *dst_shape))

        reshaped[indices] = values

    return reshaped


def get_bufferview_data(view: BufferView, relative_to: Path | None = None):
    buffer_data = get_buffer_data(view.buffer, relative_to=relative_to)
    if view.byteStride:
        raise ValueError("cannot get raw data from buffer view with byteStride and no accessor")
    else:
        return buffer_data[view.byteOffset : view.byteOffset + view.byteLength]


def get_buffer_data(buffer: Buffer | DataBuffer, relative_to: Path | None = None):
    if isinstance(buffer, DataBuffer):
        return buffer.data
    else:
        data, _mimetype = read_uri_data(buffer.uri, relative_to)
        return data
