import hashlib
import html
import json
import os
import re
import signal
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import boto3
import feedparser
import requests
from opensearchpy import OpenSearch, helpers
from sqlalchemy import func

from shared.db import SessionLocal
from shared.models import Job

sqs = boto3.client("sqs")
opensearch = OpenSearch(os.environ["OPENSEARCH_URL"])
QUEUE_URL = os.environ["QUEUE_URL"]
running = True
FEEDS = {
    "bleepingcomputer": "https://www.bleepingcomputer.com/feed/",
    "thehackernews": "https://feeds.feedburner.com/TheHackersNews",
    "securityweek": "https://www.securityweek.com/feed/",
    "darkreading": "https://www.darkreading.com/rss.xml",
    "therecord": "https://therecord.media/feed",
    "krebsonsecurity": "https://krebsonsecurity.com/feed/",
    "infosecurity-magazine": "https://www.infosecurity-magazine.com/rss/news/",
    "cyberscoop": "https://cyberscoop.com/feed/",
    "helpnetsecurity": "https://www.helpnetsecurity.com/feed/",
    "securityaffairs": "https://securityaffairs.com/feed",
    "cybersecuritydive": "https://www.cybersecuritydive.com/feeds/news/",
    "theregister": "https://www.theregister.com/security/headlines.atom",
    "arstechnica": "https://arstechnica.com/security/feed/",
    "techcrunch": "https://techcrunch.com/category/security/feed/",
    "zdnet": "https://www.zdnet.com/topic/security/rss.xml",
    "wired": "https://www.wired.com/feed/category/security/latest/rss",
    "hackread": "https://hackread.com/feed/",
    "databreaches": "https://databreaches.net/feed/",
    "theverge-security": "https://www.theverge.com/rss/cyber-security/index.xml",
    "schneier": "https://www.schneier.com/feed/atom/",
    "grahamcluley": "https://grahamcluley.com/feed/",
    "siliconangle": "https://siliconangle.com/category/security/feed/",
    "industrialcyber": "https://industrialcyber.co/feed/",
}

def stop(signum, frame):
    global running
    running = False
    
def fetch_feed(source: str, url: str) -> list[dict]:
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "threat-feed-analyzer/0.1"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"invalid feed: {feed.bozo_exception}")
    except Exception as err:
        return [{"source": source, "failed": str(err)}]

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stories = []
    for e in feed.entries:
        if not e.get("published_parsed") or not e.get("title") or not e.get("link"):
            continue
        published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        if published < cutoff:
            continue
        stories.append({
            "source": source,
            "id": e.get("id", e.link),
            "title": e.title,
            "link": e.link,
            "summary": " ".join(html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<p>The post .*? appeared first on .*?</p>", "", e.get("summary", "")))).split()),
            "published": published.isoformat(),
            "tags": [t.term for t in e.get("tags", [])],
        })
    return stories


def fetch_stories() -> list[dict]:
    stories = []
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as pool:
        for result in pool.map(fetch_feed, FEEDS.keys(), FEEDS.values()):
            stories.extend(result)

    failed = len([s for s in stories if "failed" in s])
    if failed == len(FEEDS):
        raise RuntimeError(f"all feeds failed: {stories}")
    return stories


def run_job(job_id: uuid.UUID):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None or job.status in ("completed", "failed"):
            return

        job.status = "running"
        db.commit()

        stories = fetch_stories()
        docs = []
        for s in stories:
            if "failed" not in s:
                docs.append({"_index": f"stories-{s['published'][:4]}","_id": hashlib.sha256(s["link"].encode()).hexdigest(), "_source": s})
        # TODO: embed later when embedding model is running
        helpers.bulk(opensearch, docs)

        job.result = {"stories": stories} # TEMP, will be vLLM results not raw DB.
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
    signal.signal(signal.SIGTERM, stop)
    while running:
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
                    else:
                        # TODO: replace print with logging when logging is added
                        print(f"bad message: {msg['Body']}", flush=True)
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
        except Exception as e:
            # TODO: replace print with logging when logging is added
            print(f"worker error: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
