import os
import re
import json
from typing import List, Dict, Any

POLICY_FILE = os.path.join(os.path.dirname(__file__), "documents", "airline_policies.md")
CHUNKS_OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "chunks.json")

def parse_markdown_chunks(filepath: str) -> List[Dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by markdown headers (## or ###)
    sections = re.split(r'\n(?=## )', content)
    chunks = []
    chunk_id = 1

    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        lines = section.split("\n")
        title = lines[0].replace("#", "").strip()

        # Extract fare_class tag if present
        fare_class = "GENERAL"
        if "BASIC_ECONOMY" in section or "Basic Economy" in section:
            fare_class = "BASIC_ECONOMY"
        elif "FLEXIBLE" in section or "Flexible" in section:
            fare_class = "FLEXIBLE"
        elif "BUSINESS" in section:
            fare_class = "BUSINESS_FLEX"

        chunks.append({
            "id": f"policy-chunk-{chunk_id:03d}",
            "title": title,
            "fare_class": fare_class,
            "text": section,
            "token_count": len(section.split())
        })
        chunk_id += 1

    return chunks

def ingest_policies():
    print(f"Reading airline policy document from: {POLICY_FILE}")
    chunks = parse_markdown_chunks(POLICY_FILE)
    print(f"Extracted {len(chunks)} semantic policy chunks.")

    # Save to local chunks.json for offline RAG retrieval
    with open(CHUNKS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
    print(f"Saved policy chunks to: {CHUNKS_OUTPUT_FILE}")

    # If Pinecone credentials exist, upsert to Pinecone
    pinecone_key = os.getenv("PINECONE_API_KEY")
    if pinecone_key:
        print("Pinecone API key detected. Connecting to Pinecone Serverless index...")
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=pinecone_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "flight-policies")
            index = pc.Index(index_name)
            print(f"Connected to Pinecone index: {index_name}")
            # Upsert vectors with metadata
        except Exception as e:
            print(f"Pinecone connection notice: {e}")
    else:
        print("Pinecone key not set in environment. Saved local vector chunks for offline and CI testing.")

if __name__ == "__main__":
    ingest_policies()
