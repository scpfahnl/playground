import uuid

from pydantic import BaseModel


class SummarizeResponse(BaseModel):
    job_id: uuid.UUID
