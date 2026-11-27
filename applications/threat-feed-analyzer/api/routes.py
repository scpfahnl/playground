import json
import os
import uuid

import boto3
import requests
from fastapi import APIRouter, Depends, HTTPException
from opensearchpy import OpenSearch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.models import Job
from schemas import JobResponse, SearchResult, SummarizeResponse

router = APIRouter()
sqs = boto3.client("sqs")
opensearch = OpenSearch(os.environ["OPENSEARCH_URL"])
EMBEDDING_URL = os.environ["EMBEDDING_URL"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
SEARCH_INSTRUCT = "Given a search query, retrieve relevant security news stories"


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


@router.get("/jobs/latest", response_model=JobResponse)
def get_latest_job(db: Session = Depends(get_db)):
    job = db.scalars(select(Job).where(Job.status == "completed").order_by(Job.completed_at.desc()).limit(1)).first()
    if job is None:
        raise HTTPException(status_code=404, detail="No completed jobs")
    return job


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/search", response_model=list[SearchResult])
def search(q: str):
    resp = requests.post(f"{EMBEDDING_URL}/embeddings", json={
        "model": EMBEDDING_MODEL,
        "input": f"Instruct: {SEARCH_INSTRUCT}\nQuery: {q}",
    }, timeout=30)
    resp.raise_for_status()
    embedding = resp.json()["data"][0]["embedding"]

    hits = opensearch.search(index="stories-*", body={
        "size": 5,
        "_source": {"excludes": ["embedding"]},
        "query": {"knn": {"embedding": {"vector": embedding, "k": 5}}},
    })["hits"]["hits"]

    results = []
    for hit in hits:
        story = hit["_source"]
        results.append(SearchResult(score=hit["_score"], source=story["source"], title=story["title"], link=story["link"], summary=story["summary"], published=story["published"]))
    return results
