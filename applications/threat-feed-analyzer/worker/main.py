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
EMBEDDING_URL = os.environ["EMBEDDING_URL"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
CHAT_URL = os.environ["CHAT_URL"]
CHAT_MODEL = os.environ["CHAT_MODEL"]
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
TOP_STORIES_PROMPT = (
    "You are a security news analyst. You are given news stories from different sites about the same security event. "
    "Write a short headline and a 2-3 sentence summary of the event."
)
TOP_STORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["title", "summary"],
}
SIMILARITY_SCORE = 0.875

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


def index_stories(stories: list[dict]) -> list[dict]:
    docs = []
    texts = []
    for s in stories:
        if "failed" not in s:
            docs.append({"_index": f"stories-{s['published'][:4]}","_id": hashlib.sha256(s["link"].encode()).hexdigest(), "_source": dict(s)})
            texts.append(s["title"] + "\n" + s["summary"])

    resp = requests.post(f"{EMBEDDING_URL}/embeddings", json={"model": EMBEDDING_MODEL, "input": texts}, timeout=120)
    resp.raise_for_status()
    data = resp.json()["data"]
    for i in range(len(docs)):
        docs[i]["_source"]["embedding"] = data[i]["embedding"]
    helpers.bulk(opensearch, docs, refresh=True)
    return docs


def group_stories(docs: list[dict]) -> list[dict]:
    top_stories = []
    seen = set()
    for doc in docs:
        if doc["_id"] in seen:
            continue
        hits = opensearch.search(index="stories-*", body={
            "min_score": SIMILARITY_SCORE,
            "query": {"knn": {"embedding": {"vector": doc["_source"]["embedding"], "k": 20, "filter": {"range": {"published": {"gte": "now-24h"}}}}}},
        })["hits"]["hits"]
        top_story = {"sources": [], "titles": [], "stories": [], "links": []}
        for hit in hits:
            if hit["_id"] not in seen:
                seen.add(hit["_id"])
                top_story["sources"].append(hit["_source"]["source"])
                top_story["titles"].append(hit["_source"]["title"])
                top_story["stories"].append(hit["_source"]["title"] + "\n" + hit["_source"]["summary"])
                top_story["links"].append(hit["_source"]["link"])
        if len(set(top_story["sources"])) > 1:
            top_stories.append(top_story)
    top_stories.sort(key=lambda top_story: len(set(top_story["sources"])), reverse=True)
    return top_stories[:5]


def summarize_group(top_story: dict) -> dict:
    resp = requests.post(f"{CHAT_URL}/chat/completions", json={
        "model": CHAT_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": TOP_STORIES_PROMPT},
            {"role": "user", "content": "\n\n".join(top_story["stories"])},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "top_story", "schema": TOP_STORIES_SCHEMA}},
    }, timeout=120)
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def run_job(job_id: uuid.UUID):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None or job.status in ("completed", "failed"):
            return

        job.status = "running"
        db.commit()

        docs = index_stories(fetch_stories())
        top_stories = group_stories(docs)
        for top_story in top_stories:
            top_story.update(summarize_group(top_story))

        job.result = {"top_stories": top_stories}
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
