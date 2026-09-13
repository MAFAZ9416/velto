"""
Abstract base class for VELTO conversion engines.

Every real conversion engine (e.g., LibreOffice, pdf2docx, Pillow, etc.)
must subclass BaseConversionEngine and implement the `convert` method.

Engines are never instantiated here; they are registered in the EngineRegistry
and invoked by ConversionService.
"""

import abc
import logging

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """
    Raised by an engine when a conversion fails due to a known, recoverable
    condition (e.g., corrupt file, unsupported feature inside the format).

    The message will be stored in ConversionJob.error_message.
    """


class BaseConversionEngine(abc.ABC):
    """
    Abstract interface that all conversion engines must implement.

    Attributes
    ----------
    source_format : str
        The format this engine reads from (e.g., "pdf").
    target_format : str
        The format this engine writes to (e.g., "docx").
    """

    #: Subclasses must declare these class-level attributes.
    source_format: str
    target_format: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Enforce that subclasses declare source_format and target_format.
        if not (hasattr(cls, "source_format") and hasattr(cls, "target_format")):
            raise TypeError(
                f"Engine {cls.__name__} must define class attributes "
                "'source_format' and 'target_format'."
            )

    @abc.abstractmethod
    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Perform the conversion.

        Parameters
        ----------
        input_path : str
            Absolute path to the uploaded source file (temporary).
        output_path : str
            Absolute path where the converted file should be written.

        Returns
        -------
        str | None
            The actual output file path if it differs from output_path
            (e.g., when multi-page output is packaged into a .zip file),
            or None if output_path was used directly.

        Raises
        ------
        ConversionError
            If the conversion fails for a known reason.
        Exception
            Any other exception is treated as an unexpected error by
            ConversionService and stored as error_message.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"{self.source_format}→{self.target_format}>"
        )
