from typing import List, Optional
from pydantic import BaseModel, Field


class Capability(BaseModel):
    """Represents a single capability of a camera.

    Attributes:
        media_type (str): The media type of the capability (e.g., 'image/jpeg').
        format (Optional[str]): The format of the media (e.g., 'NV12').
        width (int): The width of the video frame.
        height (int): The height of the video frame.
        framerate (str): The framerate as a fraction (e.g., '30/1').
    """
    media_type: str
    format: Optional[str] = None
    width: int
    height: int
    framerate: str

    def to_gstreamer_capability(self) -> str:
        """Convert the capability to a GStreamer capability string.

        Returns:
            str: The GStreamer capability string.
        """
        if self.format:
            return f"{self.media_type},format={self.format},width={self.width},height={self.height},framerate={self.framerate}"
        return f"{self.media_type},width={self.width},height={self.height},framerate={self.framerate}"


class Camera(BaseModel):
    """Represents a camera device.

    Attributes:
        id (int): The unique identifier for the camera.
        name (str): The name of the camera.
        capabilities (List[Capability]): A list of supported capabilities for
            the camera.
    """
    id: int
    name: str
    capabilities: List[Capability] = Field(default_factory=list, alias="caps")
