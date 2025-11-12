__version__ = "0.3.0"

from .camera import Camera, Capability
from .client import ThorVisionClient
from .video import extract_metadata, frame_metadata_dtype, FrameMetadata
import logging

# Set up a logger for the package
logging.getLogger(__name__).addHandler(logging.NullHandler())


def enable_logging(level: str = "INFO"):
    """
    Enable logging for ThorVision.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    
    Example:
        >>> import pythorvision
        >>> pythorvision.enable_logging("DEBUG")
    """
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logger = logging.getLogger('pythorvision')
    logger.setLevel(getattr(logging, level.upper()))

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(handler)


__all__ = [
    'ThorVisionClient', 'Camera', 'Capability', 'enable_logging', '__version__', 'extract_metadata',
    'frame_metadata_dtype', 'FrameMetadata'
]
