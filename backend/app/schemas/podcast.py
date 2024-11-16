from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class PodcastBase(BaseModel):
    """Base podcast schema."""
    title: str = Field(..., description="Title of the podcast")
    content: str = Field(..., description="Content to convert to podcast")
    word_count: int = Field(default=500, description="Target word count for the podcast")

class PodcastCreate(PodcastBase):
    """Schema for creating a podcast."""
    pass

class PodcastUpdate(BaseModel):
    """Schema for updating a podcast."""
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    is_completed: Optional[bool] = None

class PodcastInDB(PodcastBase):
    """Schema for podcast in database."""
    id: int
    search_space_id: int
    file_location: Optional[str] = None
    status: str
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PodcastResponse(BaseModel):
    """Schema for podcast response."""
    id: int
    title: str
    status: str
    is_completed: bool
    file_location: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
