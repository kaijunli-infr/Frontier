# Leaf helpers that never import upward.
from .base_poly_config import BasePolyConfig
from .base_fixed_config import BaseFixedConfig
from .precision_type import PrecisionType
from .utils import dataclass_to_dict, get_all_subclasses
from . import global_vars

# Re-export everything from config.py
from .config import *

# The quantization manager imports frontier.operators and frontier.attention,
# which sit above frontier.config in the layering. Resolve it on first access so
# that importing any config submodule never pulls those packages in eagerly.
_LAZY_QUANTIZATION_EXPORTS = frozenset({"QuantizationManager", "get_quantization_manager"})


def __getattr__(name):
    if name in _LAZY_QUANTIZATION_EXPORTS:
        from . import quantization_manager

        value = getattr(quantization_manager, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _LAZY_QUANTIZATION_EXPORTS)
