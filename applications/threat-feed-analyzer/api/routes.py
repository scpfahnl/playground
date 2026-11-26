import json
import os

import boto3
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.models import Job
from schemas import SummarizeResponse

router = APIRouter()
sqs = boto3.client("sqs")


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(db: Session = Depends(get_db)):
    job = Job()
    try:
        db.add(job)
        db.commit()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        sqs.send_message(QueueUrl=os.environ["QUEUE_URL"], MessageBody=json.dumps({"job_id": str(job.job_id)}))
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.completed_at = func.now()
        db.commit()
        raise HTTPException(status_code=503, detail="Failed to queue job")

    return SummarizeResponse(job_id=job.job_id)
