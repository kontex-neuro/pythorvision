from typing import List, Optional
from pydantic import BaseModel, Field


class Capability(BaseModel):
    media_type: str
    format: Optional[str] = None
    width: int
    height: int
    framerate: str

    def to_string(self) -> str:
        if self.format:
            return f"{self.media_type},format={self.format},width={self.width},height={self.height},framerate={self.framerate}"
        return f"{self.media_type},width={self.width},height={self.height},framerate={self.framerate}"


class Camera(BaseModel):
    id: int
    name: str
    caps: List[Capability] = Field(default_factory=list)
