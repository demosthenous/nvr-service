from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class CameraKind(str, Enum):
    ELECTRO_OPTICAL = "electro-optical"
    THERMAL = "thermal"
    INFRARED = "infrared"

class NVR(BaseModel):
    serial_number: UUID = Field(default_factory=uuid4)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    maximum_input_channels: int = Field(gt=0)

class Camera(BaseModel):
    serial_number: UUID = Field(default_factory=uuid4)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    kind: CameraKind
    location: str = Field(min_length=1)
    nvr_uuid: UUID
    