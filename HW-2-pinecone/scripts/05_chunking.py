# scripts/05_chunking.py
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

MODEL_NAME = "allenai/specter2_base"
VECTOR_DIM = 768
FIXED_INDEX = "arxiv-chunks-fixed"
SEM_INDEX = "arxiv-chunks-semantic"
BATCH_SIZE = 100
INPUT_PARQUET = DATA_DIR / "arxiv_subset.parquet"

if not INPUT_PARQUET.exists():
    raise FileNotFoundError(
        f"Не знайдено parquet-файл: {INPUT_PARQUET}\n"
        "Спочатку запусти scripts/01_prepare_data.py"
    )

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
print("Завантаження моделі може зайняти 1-3 хвилини при першому запуску...")
model = SentenceTransformer(MODEL_NAME)
df = pd.read_parquet(INPUT_PARQUET).reset_index(drop=True)

def ensure_index(name: str):
    if name not in pc.list_indexes().names():
        pc.create_index(
            name=name,
            dimension=VECTOR_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        while not pc.describe_index(name).status["ready"]:
            time.sleep(2)
    return pc.Index(name)

fixed_index = ensure_index(FIXED_INDEX)
sem_index = ensure_index(SEM_INDEX)

df["abstract_len_words"] = df["abstract"].fillna("").str.split().str.len()
top_df = df.sort_values("abstract_len_words", ascending=False).head(30).copy()

def fixed_size_chunk(text: str, chunk_size: int = 200, overlap: int = 30):
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks

def split_sentences(text: str):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return re.split(r'(?<=[.!?])\s+', text)

def semantic_chunk(text: str, max_words: int = 200):
    sentences = split_sentences(text)
    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        sent_words = sent.split()
        sent_len = len(sent_words)

        if current and current_len + sent_len > max_words:
            chunks.append(" ".join(current).strip())
            current = [sent]
            current_len = sent_len
        else:
            current.append(sent)
            current_len += sent_len

    if current:
        chunks.append(" ".join(current).strip())

    return chunks

def build_chunk_records(strategy_name: str):
    records = []
    for _, row in top_df.iterrows():
        if strategy_name == "fixed":
            chunks = fixed_size_chunk(row["abstract"], chunk_size=200, overlap=30)
        else:
            chunks = semantic_chunk(row["abstract"], max_words=200)

        for j, chunk in enumerate(chunks):
            records.append({
                "id": f"{strategy_name}_{row.name}_{j}",
                "text": f"{row['title']} [SEP] {chunk}",
                "metadata": {
                    "arxiv_id": str(row["id"]),
                    "title": str(row["title"])[:300],
                    "chunk_text": chunk[:1000],
                    "chunk_id": int(j),
                    "year": int(row["year"]),
                    "category": str(row["category"]),
                }
            })
    return records

fixed_records = build_chunk_records("fixed")
sem_records = build_chunk_records("semantic")

def upsert_chunks(index, records, desc):
    texts = [r["text"] for r in records]
    embs = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    for start in tqdm(range(0, len(records), BATCH_SIZE), desc=desc):
        end = min(start + BATCH_SIZE, len(records))
        batch = []
        for i in range(start, end):
            batch.append({
                "id": records[i]["id"],
                "values": embs[i].tolist(),
                "metadata": records[i]["metadata"],
            })
        index.upsert(vectors=batch)

upsert_chunks(fixed_index, fixed_records, "Fixed chunks -> Pinecone")
upsert_chunks(sem_index, sem_records, "Semantic chunks -> Pinecone")

def search_chunks(index, query: str, top_k: int = 5):
    q = model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0].tolist()
    res = index.query(vector=q, top_k=top_k, include_metadata=True)
    return res["matches"]

test_queries = [
    "graph neural networks for molecules",
    "black hole entropy in string theory",
    "learning visual representations from images"
]

for query in test_queries:
    print(f"\n\n######## QUERY: {query} ########")

    print("\n--- Fixed-size ---")
    for i, m in enumerate(search_chunks(fixed_index, query), 1):
        md = m["metadata"]
        print(f"{i}. {md['title']} | chunk={md['chunk_id']} | score={m['score']:.4f}")
        print(f"   {md['chunk_text'][:220]}...")

    print("\n--- Semantic ---")
    for i, m in enumerate(search_chunks(sem_index, query), 1):
        md = m["metadata"]
        print(f"{i}. {md['title']} | chunk={md['chunk_id']} | score={m['score']:.4f}")
        print(f"   {md['chunk_text'][:220]}...")