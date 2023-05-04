from typing import List, Union

from equistore.core import TensorBlock, TensorMap

from . import _dispatch
from ._utils import _check_gradient_presence


def ones_like(
    tensor: TensorMap,
    gradients: Union[List[str], str] = None,
    requires_grad: bool = False,
) -> TensorMap:
    """Return a new :py:class:`TensorMap` with the same metadata as tensor,
    and all values equal to one.

    :param tensor:
        Input tensor from which the metadata is taken.

    :param gradients:
        Which gradients should be present in the output. If this is
        :py:obj:`None` (default) all gradient of ``tensor`` are present in the
        new :py:class:`TensorMap`. If this is an empty list ``[]``, no gradients
        information is copied.

    :param requires_grad:
        If autograd should record operations for the returned tensor. This
        option is only relevant for torch.

    >>> import numpy as np
    >>> import equistore
    >>> from equistore import TensorBlock, TensorMap, Labels
    >>> np.random.seed(1)

    First we create a :py:class:`TensorMap` with just one block with two
    gradients, named ``alpha`` and ``beta``, containing random data:

    >>> block = TensorBlock(
    ...     values=np.random.rand(4, 3),
    ...     samples=Labels.arange("sample", 4),
    ...     components=[],
    ...     properties=Labels.arange("property", 3),
    ... )
    >>> block.add_gradient(
    ...     parameter="alpha",
    ...     gradient=TensorBlock(
    ...         values=np.random.rand(2, 3, 3),
    ...         samples=Labels(["sample", "atom"], np.array([[0, 0], [0, 2]])),
    ...         components=[Labels.arange("component", 3)],
    ...         properties=block.properties,
    ...     ),
    ... )
    >>> block.add_gradient(
    ...     parameter="beta",
    ...     gradient=TensorBlock(
    ...         values=np.random.rand(1, 3),
    ...         samples=Labels(["sample"], np.array([[0]])),
    ...         components=[],
    ...         properties=block.properties,
    ...     ),
    ... )
    >>> keys = Labels(names=["key"], values=np.array([[0]]))
    >>> tensor = TensorMap(keys, [block])
    >>> print(tensor.block(0))
    TensorBlock
        samples (4): ['sample']
        components (): []
        properties (3): ['property']
        gradients: ['alpha', 'beta']

    Then we use ``ones_like`` to create a :py:class:`TensorMap` with the same
    metadata as ``tensor``, but with all values set to 1.

    >>> tensor_ones = equistore.ones_like(tensor)
    >>> print(tensor_ones.block(0))
    TensorBlock
        samples (4): ['sample']
        components (): []
        properties (3): ['property']
        gradients: ['alpha', 'beta']
    >>> print(tensor_ones.block(0).values)
    [[1. 1. 1.]
     [1. 1. 1.]
     [1. 1. 1.]
     [1. 1. 1.]]
    >>> print(tensor_ones.block(0).gradient("alpha").values)
    [[[1. 1. 1.]
      [1. 1. 1.]
      [1. 1. 1.]]
    <BLANKLINE>
     [[1. 1. 1.]
      [1. 1. 1.]
      [1. 1. 1.]]]

    Note that if we copy just the gradient ``alpha``, ``beta`` is no longer
    available.

    >>> tensor_ones = equistore.ones_like(tensor, gradients="alpha")
    >>> print(tensor_ones.block(0).gradients_list())
    ['alpha']
    """

    blocks = []
    for block in tensor.blocks():
        blocks.append(
            ones_like_block(
                block=block, gradients=gradients, requires_grad=requires_grad
            )
        )
    return TensorMap(tensor.keys, blocks)


def ones_like_block(
    block: TensorBlock,
    gradients: Union[List[str], str] = None,
    requires_grad: bool = False,
) -> TensorBlock:
    """Return a new :py:class:`TensorBlock` with the same metadata as block,
    and all values equal to one.

    :param block:
        Input block from which the metadata is taken.

    :param gradients:
        Which gradients should be present in the output. If this is
        :py:obj:`None` (default) all gradient of ``block`` are present in the
        new :py:class:`TensorBlock`. If this is an empty list ``[]``, no
        gradients information is copied.

    :param requires_grad:
        If autograd should record operations for the returned tensor. This
        option is only relevant for torch.
    """

    values = _dispatch.ones_like(block.values, requires_grad=requires_grad)
    result_block = TensorBlock(
        values=values,
        samples=block.samples,
        components=block.components,
        properties=block.properties,
    )

    if isinstance(gradients, str):
        gradients = [gradients]

    if gradients is None:
        gradients = block.gradients_list()
    else:
        _check_gradient_presence(block=block, parameters=gradients, fname="ones_like")

    for parameter in gradients:
        gradient = block.gradient(parameter)
        if len(gradient.gradients_list()) != 0:
            raise NotImplementedError("gradients of gradients are not supported")

        gradient_values = _dispatch.ones_like(gradient.values)

        result_block.add_gradient(
            parameter=parameter,
            gradient=TensorBlock(
                values=gradient_values,
                samples=gradient.samples,
                components=gradient.components,
                properties=gradient.properties,
            ),
        )

    return result_block