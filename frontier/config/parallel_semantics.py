"""Compatibility facade; the implementation lives in ``frontier.types.parallel_semantics``.

The module moved into the dependency-free ``frontier.types`` package so that
``frontier.operators.families`` no longer imports through ``frontier.config``,
which closed the config -> model_config -> model_architectures -> operators
import cycle. Import from ``frontier.types.parallel_semantics`` in new code.
"""

from frontier.types.parallel_semantics import (  # noqa: F401
    CollectiveSimParallelLayout,
    CollectiveSimPhysicalTopology,
    FrontierParallelismMapping,
    build_collective_sim_layout,
    build_collective_sim_physical_topology,
    resolve_collective_sim_physical_topology,
    resolve_frontier_parallelism_mapping,
    resolve_shared_expert_tensor_parallel_mode,
    resolve_shared_expert_tensor_parallel_size,
    validate_frontier_shared_parallel_domains,
)

__all__ = [
    "CollectiveSimParallelLayout",
    "CollectiveSimPhysicalTopology",
    "FrontierParallelismMapping",
    "build_collective_sim_layout",
    "build_collective_sim_physical_topology",
    "resolve_collective_sim_physical_topology",
    "resolve_frontier_parallelism_mapping",
    "resolve_shared_expert_tensor_parallel_mode",
    "resolve_shared_expert_tensor_parallel_size",
    "validate_frontier_shared_parallel_domains",
]
