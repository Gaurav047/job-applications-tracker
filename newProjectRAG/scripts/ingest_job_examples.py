#!/usr/bin/env python3
"""Bulk-loads a JSONL file of example job postings into the vector store,
so tailoring runs have realistic role phrasing/keywords to retrieve from.

Each line: {"source": "...", "title": "...", "text": "..."}

    python scripts/ingest_job_examples.py data/job_examples.sample.jsonl
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import _pathlink  # noqa: F401,E402
from app.core.db import SessionLocal  # noqa: E402
from rag.ingest import ingest_job_example  # noqa: E402


def main(path: str):
    db = SessionLocal()
    total = 0
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                total += ingest_job_example(db, row["source"], row["title"], row["text"])
    finally:
        db.close()
    print(f"Ingested {total} chunks.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/ingest_job_examples.py <path.jsonl>")
    main(sys.argv[1])
