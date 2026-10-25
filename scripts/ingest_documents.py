from __future__ import annotations
import json
from app.database import init_state_db
from app.rag.ingestion import ingest_all_documents
from app.sql.demo_database import init_business_db

if __name__ == "__main__":
    init_state_db()
    init_business_db()
    print(json.dumps(ingest_all_documents(), indent=2, ensure_ascii=False))
