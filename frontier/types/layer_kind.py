from enum import Enum


class LayerKind(Enum):
    """Typed FFN domain exposed by a model architecture profile."""

    DENSE = "dense"
    ROUTED = "routed"
    SHARED = "shared"
