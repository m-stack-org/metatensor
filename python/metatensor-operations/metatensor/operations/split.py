from typing import List, Union

from ._classes import Labels, TensorBlock, TensorMap
from .slice import _slice_block


def split(
    tensor: TensorMap,
    axis: str,
    grouped_labels: List[Labels],
) -> List[TensorMap]:
    """Split a :py:class:`TensorMap` into multiple :py:class:`TensorMap`.

    The operation is based on some specified groups of indices, along either the
    "samples" or "properties" ``axis``. The number of returned :py:class:`TensorMap`s is
    equal to the number of :py:class:`Labels` objects passed in ``grouped_labels``. Each
    returned :py:class`TensorMap` will have the same keys and number of blocks at the
    input ``tensor``, but with the dimensions of the blocks reduced to only contain the
    specified indices for the corresponding group.

    For example, to split a tensor along the "samples" axis, according to the
    "structure" index, where structures 0, 6, and 7 are in the first returned
    :py:class`TensorMap`; 2, 3, and 4 in the second; and 1, 5, 8, 9, and 10 in the
    third:

    .. code-block:: python

        import metatensor

        tensor_splitted = metatensor.split(
            tensor,
            axis="samples",
            grouped_labels=[
                Labels(names=["structure"], values=np.array([[0], [6], [7]])),
                Labels(names=["structure"], values=np.array([[2], [3], [4]])),
                Labels(names=["structure"], values=np.array([[1], [5], [8], [10]])),
            ],
        )

    :param tensor: a :py:class:`TensorMap` to be split
    :param axis: a str, either "samples" or "properties", that indicates the
        :py:class:`TensorBlock` axis along which the named index (or indices) in
        ``grouped_labels`` belongs. Each :py:class:`TensorBlock` in each returned
        :py:class:`TensorMap` could have a reduced dimension along this axis, but the
        other axes will remain the same size.
    :param grouped_labels: a list of :py:class:`Labels` containing the names and values
        of the indices along the specified ``axis`` which should be in each respective
        output :py:class:`TensorMap`.

    :return: a list of:py:class:`TensorMap` that corresponds to the split input
        ``tensor``. Each tensor in the returned list contains only the named indices in
        the respective py:class:`Labels` object of ``grouped_labels``.
    """
    # Check input args
    if not isinstance(tensor, TensorMap):
        raise TypeError(f"tensor should be a 'TensorMap', not {type(tensor)}")
    _check_args(tensor, axis, grouped_labels)

    all_new_blocks = {group_i: [] for group_i in range(len(grouped_labels))}
    for key in tensor.keys:
        new_blocks = _split_block(tensor[key], axis, grouped_labels)

        for group_i, new_block in enumerate(new_blocks):
            all_new_blocks[group_i].append(new_block)

    return [
        TensorMap(keys=tensor.keys, blocks=all_new_blocks[group_i])
        for group_i in range(len(grouped_labels))
    ]


def split_block(
    block: TensorBlock,
    axis: str,
    grouped_labels: List[Labels],
) -> List[TensorBlock]:
    """
    Splits an input :py:class:`TensorBlock` into multiple :py:class:`TensorBlock`
    objects based on some specified ``grouped_labels``, along either the "samples" or
    "properties" ``axis``. The number of returned :py:class:`TensorBlock`s is equal to
    the number of :py:class:`Labels` objects passed in ``grouped_labels``. Each returned
    :py:class`TensorBlock` will have the same keys and number of blocks at the input
    ``tensor``, but with the dimensions of the blocks reduced to only contain the
    specified indices for the corresponding group.

    For example, to split a block along the "samples" axis, according to the "structure"
    index, where structures 0, 6, and 7 are in the first returned :py:class`TensorMap`;
    2, 3, and 4 in the second; and 1, 5, 8, 9, and 10 in the third:

    .. code-block:: python

        import metatensor

        block_splitted = metatensor.split_block(
            block,
            axis="samples",
            grouped_labels=[
                Labels(names=["structure"], values=np.array([[0], [6]])),
                Labels(names=["structure"], values=np.array([[2], [3]])),
                Labels(names=["structure"], values=np.array([[1], [5], [10]])),
            ],
        )

    :param block: a :py:class:`TensorBlock` to be split
    :param axis: a str, either "samples" or "properties", that indicates the
        :py:class:`TensorBlock` axis along which the named index (or indices) in
        ``grouped_labels`` belongs. Each :py:class:`TensorBlock` returned could have a
        reduced dimension along this axis, but the other axes will remain the same size.
    :param grouped_labels: a list of :py:class:`Labels` containing the names and values
        of the indices along the specified ``axis`` which should be in each respective
        output :py:class:`TensorBlock`.

    :return: a list of:py:class:`TensorBlock` that corresponds to the split input
        ``block``. Each block in the returned list contains only the named indices in
        the respective py:class:`Labels` object of ``grouped_labels``.
    """
    # Check input args
    if not isinstance(block, TensorBlock):
        raise TypeError(f"block should be a 'TensorBlock', not {type(block)}")
    _check_args(block, axis, grouped_labels)

    return _split_block(block, axis, grouped_labels)


def _split_block(
    block: TensorBlock,
    axis: str,
    grouped_labels: List[Labels],
) -> List[TensorBlock]:
    """
    Splits a TensorBlock into mutliple blocks, as in the public function
    :py:func:`split_block` but with no input checks. Note that the block is
    currently split into N new blocks by performing N number of slice
    operations. There may be a more efficient way of doing it, but this is not
    yet implemented.
    """
    new_blocks = []
    for indices in grouped_labels:
        # perform the slice either along the samples or properties axis
        new_block = _slice_block(block, axis=axis, labels=indices)
        new_blocks.append(new_block)

    return new_blocks


def _check_args(
    tensor: Union[TensorMap, TensorBlock], axis: str, grouped_labels: List[Labels]
):
    """
    Checks the arguments passed to :py:func:`split` and :py:func:`split_block`.
    """
    # Check types
    if not isinstance(axis, str):
        raise TypeError(f"axis should be a 'str', not {type(axis)}")
    if axis not in ["samples", "properties"]:
        raise ValueError("axis mut be either 'samples' or 'properties'")
    if not isinstance(grouped_labels, list):
        raise TypeError(
            f"grouped_labels must be a list of 'Labels', not {type(grouped_labels)}"
        )

    # If passed as an empty list, return now
    if len(grouped_labels) == 0:
        return

    for labels in grouped_labels:
        if not isinstance(labels, Labels):
            raise TypeError(
                f"each element in grouped_labels must be 'Labels', not {type(labels)}"
            )

    # Check the Labels names are equivalent for all Labels in grouped_labels
    reference_names = grouped_labels[0].names
    if len(grouped_labels) > 1:
        for labels in grouped_labels[1:]:
            if labels.names != reference_names:
                raise ValueError(
                    "the names of all 'Labels' in grouped_labels"
                    f" must be the same, got {reference_names} and {labels.names}"
                )

    # Get a single block
    block = tensor.block(0) if isinstance(tensor, TensorMap) else tensor

    # Check the names in grouped_labels Labels are contained within the names for
    # the block
    names = block.samples.names if axis == "samples" else block.properties.names
    for name in reference_names:
        if name not in names:
            raise ValueError(
                f"the name '{name}' in grouped_labels is not part of "
                f"the {axis} names of the input tensor"
            )