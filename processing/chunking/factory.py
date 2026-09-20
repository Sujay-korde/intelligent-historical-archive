import logging
from typing import Dict, Type

from processing.chunking.base import BaseChunker
from processing.chunking.page_chunker import PageChunker
from processing.chunking.text_chunker import TextChunker

logger = logging.getLogger(__name__)

CHUNKERS: Dict[str, Type[BaseChunker]] = {
    "paragraph": TextChunker,
    "text": TextChunker,
    "semantic": TextChunker,
    "page": PageChunker,
}


def register_chunking_strategy(name: str, chunker_cls: Type[BaseChunker]) -> None:
    """Register a new custom chunking strategy at runtime."""
    CHUNKERS[name.lower().strip()] = chunker_cls
    logger.info(f"Registered chunking strategy '{name}' with class {chunker_cls.__name__}.")


register_chunker = register_chunking_strategy


def list_chunkers() -> list[str]:
    """Return list of available chunking strategy names."""
    return list(CHUNKERS.keys())


list_available_chunkers = list_chunkers


def get_chunker(strategy: str = "paragraph") -> BaseChunker:
    """
    Factory function returning the configured chunker strategy.
    Enables chunking evolution without modifying database or ingestion layers.
    """
    clean_strategy = strategy.lower().strip()
    chunker_cls = CHUNKERS.get(clean_strategy, TextChunker)
    return chunker_cls()
