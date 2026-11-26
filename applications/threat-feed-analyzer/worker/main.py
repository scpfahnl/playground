import json
import os
import time
import uuid

import boto3
from sqlalchemy import func

from shared.db import SessionLocal
from shared.models import Job

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]


def run_job(job_id: uuid.UUID):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None or job.status in ("completed", "failed"):
            return

        job.status = "running"
        db.commit()

        job.status = "completed"
        job.completed_at = func.now()
        db.commit()


def fail_job(job_id: uuid.UUID, error: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.status = "failed"
        job.error = error
        job.completed_at = func.now()
        db.commit()


def main():
    while True:
        try:
            resp = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20)
            for msg in resp.get("Messages", []):
                job_id = None
                try:
                    job_id = uuid.UUID(json.loads(msg["Body"])["job_id"])
                    run_job(job_id)
                except Exception as e:
                    if job_id:
                        fail_job(job_id, str(e))
                    # TODO: log bad message when job_id is None
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
        except Exception as e:
            # TODO: log worker error (exception as e, and job_id if set) when logging is added
            time.sleep(5)


if __name__ == "__main__":
    main()
