import ctypes
import pathlib
import warnings
from typing import BinaryIO, Callable, Union

import numpy as np

from ._c_api import c_uintptr_t, eqs_array_t, eqs_create_array_callback_t
from ._c_lib import _get_library
from .block import TensorBlock
from .data.array import ArrayWrapper, _is_numpy_array, _is_torch_array
from .labels import Labels
from .tensor import TensorMap
from .utils import catch_exceptions


@catch_exceptions
def create_numpy_array(shape_ptr, shape_count, array):
    """
    Callback function that can be used with
    :py:func:`equistore.core.io.load_custom_array` to load data in numpy arrays.
    """
    shape = []
    for i in range(shape_count):
        shape.append(shape_ptr[i])

    data = np.empty(shape, dtype=np.float64)
    wrapper = ArrayWrapper(data)
    array[0] = wrapper.into_eqs_array()


@catch_exceptions
def create_torch_array(shape_ptr, shape_count, array):
    """
    Callback function that can be used with
    :py:func:`equistore.core.io.load_custom_array` to load data in torch
    tensors. The resulting tensors are stored on CPU, and their dtype is
    ``torch.float64``.
    """
    import torch

    shape = []
    for i in range(shape_count):
        shape.append(shape_ptr[i])

    data = torch.empty(shape, dtype=torch.float64, device="cpu")
    wrapper = ArrayWrapper(data)
    array[0] = wrapper.into_eqs_array()


def load(file: Union[str, bytes, pathlib.Path, BinaryIO], use_numpy=False) -> TensorMap:
    """
    Load a previously saved :py:class:`TensorMap` from the given file.

    ``file`` can be a string or :py:class:`pathlib.Path` containing the path to the file
    to load, or a file-like object that should be opened in binary mode.

    :py:class:`TensorMap` are serialized using numpy's ``.npz`` format, i.e. a ZIP file
    without compression (storage method is ``STORED``), where each file is stored as a
    ``.npy`` array. See the C API documentation for more information on the format.

    :param file: file to load
    :param use_numpy: should we use numpy or the native implementation? Numpy should be
        able to process more dtypes than the native implementation, which is limited to
        float64, but the native implementation is usually faster than going through
        numpy.
    """
    if use_numpy:
        return _read_npz(file)
    else:
        if isinstance(file, str):
            file = file.encode("utf8")
        elif isinstance(file, pathlib.Path):
            file = bytes(file)

        if isinstance(file, bytes):
            return load_custom_array(file, create_numpy_array)
        else:
            # assume we have a file-like object
            buffer = file.read()
            assert isinstance(buffer, bytes)

            return load_buffer_custom_array(buffer, create_numpy_array)


CreateArrayCallback = Callable[
    [ctypes.POINTER(c_uintptr_t), c_uintptr_t, ctypes.POINTER(eqs_array_t)], None
]


def load_custom_array(path: bytes, create_array: CreateArrayCallback) -> TensorMap:
    """
    Load a previously saved :py:class:`TensorMap` from the given path using a
    custom array creation callback.

    This is an advanced functionality, which should not be needed by most users.

    This function allows to specify the kind of array to use when loading the
    data through the `create_array` callback. This callback should take three
    arguments: a pointer to the shape, the number of elements in the shape, and
    a pointer to the ``eqs_array_t`` to be filled.

    :py:func:`equistore.core.io.create_numpy_array` and
    :py:func:`equistore.core.io.create_torch_array` can be used to load data
    into numpy and torch arrays respectively.

    :param path: path of the file to load
    :param create_array: callback used to create arrays as needed
    """

    lib = _get_library()

    ptr = lib.eqs_tensormap_load(path, eqs_create_array_callback_t(create_array))

    return TensorMap._from_ptr(ptr)


def load_buffer_custom_array(
    buffer: bytes,
    create_array: CreateArrayCallback,
) -> TensorMap:
    """
    Load a previously saved :py:class:`TensorMap` from the given buffer using a
    custom array creation callback.

    This is an advanced functionality, which should not be needed by most users.

    This function allows to specify the kind of array to use when loading the
    data through the `create_array` callback. This callback should take three
    arguments: a pointer to the shape, the number of elements in the shape, and
    a pointer to the ``eqs_array_t`` to be filled.

    :py:func:`equistore.core.io.create_numpy_array` and
    :py:func:`equistore.core.io.create_torch_array` can be used to load data
    into numpy and torch arrays respectively.

    :param buffer: in-memory buffer containing a saved :py:class:`TensorMap`
    :param create_array: callback used to create arrays as needed
    """

    lib = _get_library()

    ptr = lib.eqs_tensormap_load_buffer(
        buffer,
        len(buffer),
        eqs_create_array_callback_t(create_array),
    )

    return TensorMap._from_ptr(ptr)


def save(path: str, tensor: TensorMap, use_numpy=False):
    """Save the given :py:class:`TensorMap` to a file at ``path``.

    :py:class:`TensorMap` are serialized using numpy's ``.npz`` format, i.e. a
    ZIP file without compression (storage method is ``STORED``), where each file
    is stored as a ``.npy`` array. See the C API documentation for more
    information on the format.

    :param path: path of the file where to save the data
    :param tensor: tensor to save
    :param use_numpy: should we use numpy or the native implementation? Numpy
        should be able to process more dtypes than the native implementation,
        which is limited to float64, but the native implementation is usually
        faster than going through numpy.
    """
    if not isinstance(tensor, TensorMap):
        raise TypeError(f"tensor should be a 'TensorMap', not {type(tensor)}")

    if not path.endswith(".npz"):
        path += ".npz"
        warnings.warn(
            message=f"adding '.npz' extension, the file will be saved at '{path}'",
            stacklevel=1,
        )

    if use_numpy:
        all_entries = _tensor_map_to_dict(tensor)
        np.savez(path, **all_entries)
    else:
        lib = _get_library()
        lib.eqs_tensormap_save(path.encode("utf8"), tensor._ptr)


def _array_to_numpy(array):
    if _is_numpy_array(array):
        return array
    elif _is_torch_array(array):
        return array.cpu().numpy()
    else:
        raise ValueError("unknown array type passed to `equistore.save`")


def _tensor_map_to_dict(tensor_map):
    result = {
        "keys": _labels_to_npz(tensor_map.keys),
    }

    for block_i, block in enumerate(tensor_map.blocks()):
        prefix = f"blocks/{block_i}"

        result.update(_block_to_dict(block, prefix))
        result[f"{prefix}/properties"] = _labels_to_npz(block.properties)

    return result


def _block_to_dict(block, prefix):
    result = {}
    result[f"{prefix}/values"] = _array_to_numpy(block.values)
    result[f"{prefix}/samples"] = _labels_to_npz(block.samples)
    for i, component in enumerate(block.components):
        result[f"{prefix}/components/{i}"] = _labels_to_npz(component)

    for parameter, gradient in block.gradients():
        result.update(_block_to_dict(gradient, f"{prefix}/gradients/{parameter}"))

    return result


def _labels_from_npz(data):
    names = data.dtype.names
    return Labels(names=names, values=data.view(dtype=np.int32).reshape(-1, len(names)))


def _labels_to_npz(labels):
    dtype = [(name, np.int32) for name in labels.names]
    return labels.values.view(dtype=dtype).reshape((labels.values.shape[0],))


def _read_npz(file):
    dictionary = np.load(file)

    keys = _labels_from_npz(dictionary["keys"])
    blocks = []

    for block_i in range(len(keys)):
        prefix = f"blocks/{block_i}"
        properties = _labels_from_npz(dictionary[f"{prefix}/properties"])

        block = _read_block(prefix, dictionary, properties)
        blocks.append(block)

    return TensorMap(keys, blocks)


def _read_block(prefix, dictionary, properties):
    values = dictionary[f"{prefix}/values"]

    samples = _labels_from_npz(dictionary[f"{prefix}/samples"])
    components = []
    for i in range(len(values.shape) - 2):
        components.append(_labels_from_npz(dictionary[f"{prefix}/components/{i}"]))

    block = TensorBlock(values, samples, components, properties)

    parameters = set()
    gradient_prefix = f"{prefix}/gradients/"
    for name in dictionary.keys():
        if name.startswith(gradient_prefix) and name.endswith("/values"):
            parameter = name[len(gradient_prefix) :]
            parameter = parameter.split("/")[0]
            parameters.add(parameter)

    for parameter in parameters:
        gradient = _read_block(
            f"{prefix}/gradients/{parameter}",
            dictionary,
            properties,
        )
        block.add_gradient(parameter, gradient)

    return block
