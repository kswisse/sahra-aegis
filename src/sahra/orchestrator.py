"""Public entry point. The cycle itself is composed in ``kernel.py``:
deterministic control plane: sense -> assess -> plan -> gate -> act -> log.
No LLM participates in any of these transitions."""

from .kernel import run_cycle

__all__ = ["run_cycle"]
