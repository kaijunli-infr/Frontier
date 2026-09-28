from enum import Enum


class TensorParallelMode(Enum):
    """How a predictor resolves the tensor-parallel key for an operator."""

    REPLICATED = "replicated"
    ATTENTION_TP = "attention_tp"
    FFN_TP = "ffn_tp"
    MOE_TP = "moe_tp"
