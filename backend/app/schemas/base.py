from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Common base schema for API models."""

    model_config = ConfigDict(from_attributes=True)
