"""
One-time script: embed data/kb_documents.json and load into Supabase's
healthguard_kb table (pgvector).

Requires in .env:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY   (service role key — bypasses RLS, needed for inserts)

Usage:
    python scripts/index_kb.py

Safe to re-run: it clears existing rows in healthguard_kb before inserting,
so re-running after an edit to kb_documents.json doesn't create duplicates.
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 384-dim, matches schema
EXPECTED_DIM = 384
KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "kb_documents.json")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        fail(
            "SUPABASE_URL and/or SUPABASE_SERVICE_KEY not set. "
            "Add them to your .env (get both from Supabase Dashboard -> Settings -> API) "
            "and re-run."
        )

    if not os.path.exists(KB_PATH):
        fail(f"Knowledge base file not found at {KB_PATH}")

    with open(KB_PATH, encoding="utf-8") as f:
        docs = json.load(f)

    required_fields = {"title", "category", "content_urdu", "source_url", "is_direct_urdu_source"}
    for i, doc in enumerate(docs):
        missing = required_fields - doc.keys()
        if missing:
            fail(f"Document {i} ('{doc.get('title', '?')}') is missing fields: {missing}")

    print(f"Loaded {len(docs)} documents from {KB_PATH}")

    print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}' (this downloads the model on first run)...")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        fail("sentence-transformers not installed. Run: pip install -r requirements.txt")

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    actual_dim = model.get_sentence_embedding_dimension()
    if actual_dim != EXPECTED_DIM:
        fail(
            f"Model produces {actual_dim}-dim embeddings, but the Supabase schema expects "
            f"vector({EXPECTED_DIM}). Either change the model or run: "
            f"'alter table healthguard_kb alter column embedding type vector({actual_dim});' "
            f"in Supabase SQL Editor first."
        )
    print(f"Model loaded. Embedding dimension: {actual_dim} (matches schema).")

    try:
        from supabase import create_client
    except ImportError:
        fail("supabase package not installed. Run: pip install -r requirements.txt")

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print("Clearing existing rows in healthguard_kb (safe re-run, avoids duplicates)...")
    try:
        supabase.table("healthguard_kb").delete().neq("id", 0).execute()
    except Exception as e:
        fail(f"Could not clear existing rows — check SUPABASE_URL/SERVICE_KEY are correct. Details: {e}")

    print("Embedding and inserting documents...")
    inserted = 0
    failed = []
    for i, doc in enumerate(docs):
        try:
            embedding = model.encode(doc["content_urdu"]).tolist()
            row = {
                "title": doc["title"],
                "category": doc["category"],
                "content_urdu": doc["content_urdu"],
                "source_url": doc["source_url"],
                "is_direct_urdu_source": doc["is_direct_urdu_source"],
                "embedding": embedding,
            }
            supabase.table("healthguard_kb").insert(row).execute()
            inserted += 1
            print(f"  [{i + 1}/{len(docs)}] Inserted: {doc['title'][:40]}...")
        except Exception as e:
            failed.append((doc.get("title", f"doc {i}"), str(e)))
            print(f"  [{i + 1}/{len(docs)}] FAILED: {doc.get('title', '?')[:40]}... — {e}")

    print()
    print(f"Done. Inserted {inserted}/{len(docs)} documents.")
    if failed:
        print(f"{len(failed)} document(s) failed:")
        for title, error in failed:
            print(f"  - {title}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
