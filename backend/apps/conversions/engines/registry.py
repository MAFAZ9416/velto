"""
Engine Registry — maps (source_format, target_format) pairs to engine classes.

Usage
-----
Register an engine (typically in an app's ready() or a dedicated engines module):

    from apps.conversions.engines.registry import engine_registry
    from apps.conversions.engines.base import BaseConversionEngine

    class PdfToDocxEngine(BaseConversionEngine):
        source_format = "pdf"
        target_format = "docx"

        def convert(self, input_path, output_path):
            ...  # real implementation

    engine_registry.register(PdfToDocxEngine)

Look up an engine:

    engine_cls = engine_registry.get("pdf", "docx")
    if engine_cls is None:
        # No engine available — job stays pending
        ...
    else:
        engine = engine_cls()
        engine.convert(input_path, output_path)
"""

import logging
from typing import Optional, Type

from apps.conversions.engines.base import BaseConversionEngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    """
    Singleton registry mapping (source, target) → engine class.

    Thread safety: registration typically happens at startup (app ready()).
    Concurrent reads are safe; concurrent writes are not expected.
    """

    def __init__(self):
        self._registry: dict[tuple[str, str], Type[BaseConversionEngine]] = {}

    def register(self, engine_cls: Type[BaseConversionEngine]) -> None:
        """
        Register an engine class for its declared source/target pair.

        Raises
        ------
        TypeError
            If engine_cls is not a subclass of BaseConversionEngine.
        ValueError
            If another engine is already registered for the same pair.
        """
        if not (isinstance(engine_cls, type) and issubclass(engine_cls, BaseConversionEngine)):
            raise TypeError(f"{engine_cls!r} is not a subclass of BaseConversionEngine.")

        key = (engine_cls.source_format, engine_cls.target_format)
        if key in self._registry:
            existing = self._registry[key]
            raise ValueError(
                f"Engine already registered for {key}: {existing.__name__}. "
                f"Cannot register {engine_cls.__name__}."
            )

        self._registry[key] = engine_cls
        logger.info("Registered engine: %s for %s → %s", engine_cls.__name__, *key)

    def get(
        self, source_format: str, target_format: str
    ) -> Optional[Type[BaseConversionEngine]]:
        """
        Return the engine class for the given pair, or None if not registered.
        None means no engine is available yet — the job will stay pending.
        """
        return self._registry.get((source_format, target_format))

    def available_pairs(self) -> list[tuple[str, str]]:
        """Return all (source, target) pairs that have a registered engine."""
        return list(self._registry.keys())

    def __repr__(self) -> str:
        pairs = ", ".join(f"{s}→{t}" for s, t in self._registry)
        return f"<EngineRegistry [{pairs}]>"


# Module-level singleton — import this everywhere.
engine_registry = EngineRegistry()
