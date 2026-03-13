"""Base adapter interface — every supplier implements this."""
from abc import ABC, abstractmethod
from src.schema.canonical import DataBatch


class BaseAdapter(ABC):
    """Transform raw supplier data into a canonical DataBatch."""

    @abstractmethod
    def ingest(self, source: str) -> DataBatch:
        """
        Load data from `source` (file path, URL, etc.)
        and return a validated DataBatch.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
