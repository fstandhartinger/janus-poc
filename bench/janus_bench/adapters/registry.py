"""Benchmark adapter registry."""

from __future__ import annotations

from typing import Callable

from ..models import BenchmarkName
from .base import BenchmarkAdapter

_ADAPTERS: dict[BenchmarkName, type[BenchmarkAdapter]] = {}


def register_adapter(
    name: BenchmarkName,
) -> Callable[[type[BenchmarkAdapter]], type[BenchmarkAdapter]]:
    """Register a benchmark adapter under the given name."""

    def decorator(adapter_cls: type[BenchmarkAdapter]) -> type[BenchmarkAdapter]:
        _ADAPTERS[name] = adapter_cls
        return adapter_cls

    return decorator


def get_adapter(name: BenchmarkName | str) -> BenchmarkAdapter:
    """Instantiate a registered adapter."""
    benchmark_name = BenchmarkName(name)
    adapter_cls = _ADAPTERS.get(benchmark_name)
    if adapter_cls is None:
        raise KeyError(f"Unknown benchmark adapter: {benchmark_name}")
    return adapter_cls()


def list_adapters() -> list[BenchmarkAdapter]:
    """Return instances for all registered adapters."""
    return [adapter_cls() for adapter_cls in _ADAPTERS.values()]
