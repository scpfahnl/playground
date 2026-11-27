import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SummarizeResponse(BaseModel):
    job_id: uuid.UUID


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    status: str
    result: dict | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class SearchResult(BaseModel):
    score: float
    source: str
    title: str
    link: str
    summary: str
    published: datetime
