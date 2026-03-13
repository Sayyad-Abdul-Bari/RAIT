"""
AdapterFactory — registry pattern for extensibility.
Adding Supplier D = register one new adapter class. Zero other changes.
"""
from typing import Dict, Type

from src.adapters.base import BaseAdapter
from src.adapters.supplier_a import SupplierAAdapter
from src.adapters.supplier_b import SupplierBAdapter
from src.adapters.supplier_c import SupplierCAdapter

_REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "supplier_a": SupplierAAdapter,
    "supplier_b": SupplierBAdapter,
    "supplier_c": SupplierCAdapter,
}


class AdapterFactory:
    """Instantiate the correct adapter for a given supplier_id."""

    @staticmethod
    def register(supplier_id: str, adapter_class: Type[BaseAdapter]) -> None:
        """Register a new supplier adapter at runtime."""
        _REGISTRY[supplier_id] = adapter_class

    @staticmethod
    def get(supplier_id: str) -> BaseAdapter:
        """Return an adapter instance for the given supplier_id."""
        cls = _REGISTRY.get(supplier_id)
        if cls is None:
            known = ", ".join(_REGISTRY)
            raise KeyError(
                f"No adapter registered for '{supplier_id}'. Known: {known}"
            )
        return cls()

    @staticmethod
    def list_suppliers() -> list[str]:
        return list(_REGISTRY.keys())
