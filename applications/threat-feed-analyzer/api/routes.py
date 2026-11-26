import json
import os

import boto3
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models import Job
from schemas import SummarizeResponse

router = APIRouter()
sqs = boto3.client("sqs")


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(db: Session = Depends(get_db)):
    job = Job()
    db.add(job)
    db.commit()

    sqs.send_message(QueueUrl=os.environ["QUEUE_URL"], MessageBody=json.dumps({"job_id": str(job.job_id)}))
    return SummarizeResponse(job_id=job.job_id)
