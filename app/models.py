from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator

class CameraKind(str, Enum):
    ELECTRO_OPTICAL = "electro-optical"
    THERMAL = "thermal"
    INFRARED = "infrared"

class NVR(BaseModel):
    serial_number: UUID = Field(default_factory=uuid4)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    maximum_input_channels: int = Field(gt=0)

    @field_validator("make", "model")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

class Camera(BaseModel):
    serial_number: UUID = Field(default_factory=uuid4)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    kind: CameraKind
    location: str = Field(min_length=1)
    nvr_uuid: UUID

    @field_validator("make", "model", "location")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v
