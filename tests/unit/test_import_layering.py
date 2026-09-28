"""Import layering guards for the core package.

Two checks protect the cycle fix from design issue #37:

1. Every core module imports cleanly when it is the *first* frontier import in a
   fresh interpreter. Import order used to decide whether
   ``frontier.operators.families`` succeeded.
2. Leaf packages never import upward at module level. The contracts below are
   the module-level edges the target layering forbids; deferred (function-level)
   imports are not covered, so lifting one to the top of a module is checked
   here automatically.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "frontier"

FIRST_IMPORT_MODULES = [
    "frontier.types",
    "frontier.types.parallel_semantics",
    "frontier.operators",
    "frontier.operators.spec",
    "frontier.operators.families",
    "frontier.operators.binding",
    "frontier.operators.typed_contracts",
    "frontier.attention.families",
    "frontier.model_architectures",
    "frontier.moe_ep_workload",
    "frontier.config",
    "frontier.config.config",
    "frontier.config.model_config",
    "frontier.config.parallel_semantics",
    "frontier.config.quantization_manager",
    "frontier.entities",
    "frontier.execution_time_predictor",
    "frontier.cc_backend",
    "frontier.kv_cache_transfer",
    "frontier.m2n_transfer",
    "frontier.spec_decode",
    "frontier.scheduler",
    "frontier.events",
    "frontier.metrics",
    "frontier.simulator",
    "frontier.main",
    "frontier.training",
]

UPPER_LAYERS = (
    "frontier.config",
    "frontier.entities",
    "frontier.execution_time_predictor",
    "frontier.cc_backend",
    "frontier.kv_cache_transfer",
    "frontier.m2n_transfer",
    "frontier.spec_decode",
    "frontier.scheduler",
    "frontier.events",
    "frontier.metrics",
    "frontier.simulator",
    "frontier.main",
    "frontier.training",
    "frontier.profiling",
)

# package or module -> module prefixes it must not import at module level.
FORBIDDEN_MODULE_LEVEL_IMPORTS = {
    "frontier.types": ("frontier.",),  # only frontier.types itself, handled below
    "frontier.operators": UPPER_LAYERS + ("frontier.model_architectures",),
    "frontier.attention": UPPER_LAYERS + ("frontier.model_architectures",),
    "frontier.moe_ep_workload": UPPER_LAYERS + ("frontier.model_architectures",),
    "frontier.model_architectures": UPPER_LAYERS,
}
SELF_ALLOWED = {"frontier.types": ("frontier.types",)}


def _module_name(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_paths(dotted: str) -> list[Path]:
    base = PACKAGE_ROOT / Path(*dotted.split(".")[1:])
    if base.is_dir():
        return sorted(base.rglob("*.py"))
    return [base.with_suffix(".py")]


def _module_level_imports(path: Path, module: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
                package = ".".join(package.split(".")[: len(package.split(".")) - node.level + 1])
                target = f"{package}.{node.module}" if node.module else package
            else:
                target = node.module or ""
            yield node.lineno, target


@pytest.mark.parametrize("module", FIRST_IMPORT_MODULES)
def test_module_imports_first_in_fresh_interpreter(module: str) -> None:
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "WANDB_DISABLED": "true",
        "VIDUR_DISABLE_WANDB": "1",
    }
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False, timeout=120,
    )
    assert result.returncode == 0, (
        f"`import {module}` fails as the first frontier import:\n{result.stderr[-2000:]}"
    )


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_MODULE_LEVEL_IMPORTS))
def test_leaf_layer_has_no_upward_module_level_imports(layer: str) -> None:
    forbidden = FORBIDDEN_MODULE_LEVEL_IMPORTS[layer]
    allowed = SELF_ALLOWED.get(layer, ())
    violations = []
    for path in _module_paths(layer):
        module = _module_name(path)
        for lineno, target in _module_level_imports(path, module):
            if allowed and target.startswith(allowed):
                continue
            if target.startswith(forbidden):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{lineno} imports {target}")
    assert not violations, "\n".join(violations)
