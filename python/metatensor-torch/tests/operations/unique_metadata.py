import torch
from packaging import version

import metatensor.torch

from .data import load_data


def check_operation(unique_metadata):
    tensor = load_data("qm7-power-spectrum.npz")

    unique_labels = unique_metadata(
        tensor,
        axis="samples",
        names=["structure"],
    )

    # check type
    assert isinstance(unique_labels, torch.ScriptObject)
    if version.parse(torch.__version__) >= version.parse("2.1"):
        assert unique_labels._type().name() == "Labels"

    # check label names
    assert unique_labels.names == ["structure"]

    # repeat with gradients
    unique_labels = unique_metadata(
        tensor,
        axis="samples",
        names=["atom"],
        gradient="positions",
    )

    assert isinstance(unique_labels, torch.ScriptObject)
    if version.parse(torch.__version__) >= version.parse("2.1"):
        assert unique_labels._type().name() == "Labels"

    assert unique_labels.names == ["atom"]


def check_operation_block(unique_metadata_block):
    tensor = load_data("qm7-power-spectrum.npz")
    block = tensor.block(0)

    unique_labels = unique_metadata_block(
        block,
        axis="samples",
        names=["structure"],
    )

    # check type
    assert isinstance(unique_labels, torch.ScriptObject)
    if version.parse(torch.__version__) >= version.parse("2.1"):
        assert unique_labels._type().name() == "Labels"

    # check label names
    assert unique_labels.names == ["structure"]

    # repeat with gradients
    unique_labels = unique_metadata_block(
        block,
        axis="samples",
        names=["atom"],
        gradient="positions",
    )

    assert isinstance(unique_labels, torch.ScriptObject)
    if version.parse(torch.__version__) >= version.parse("2.1"):
        assert unique_labels._type().name() == "Labels"

    assert unique_labels.names == ["atom"]


def test_operations_as_python():
    check_operation(metatensor.torch.unique_metadata)
    check_operation_block(metatensor.torch.unique_metadata_block)


def test_operations_as_torch_script():
    check_operation(torch.jit.script(metatensor.torch.unique_metadata))
    check_operation_block(torch.jit.script(metatensor.torch.unique_metadata_block))
