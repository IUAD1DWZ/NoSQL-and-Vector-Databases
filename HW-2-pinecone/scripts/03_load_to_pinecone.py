# scripts/03_load_to_pinecone.py
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

INPUT_PARQUET = DATA_DIR / "arxiv_subset.parquet"
INPUT_EMBEDDINGS = EMBEDDINGS_DIR / "embeddings.npy"
INDEX_NAME = "arxiv-papers"
VECTOR_DIM = 768
BATCH_SIZE = 200


pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=VECTOR_DIM,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",
        ),
    )
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(2)

index = pc.Index(INDEX_NAME)

df = pd.read_parquet(INPUT_PARQUET).reset_index(drop=True)
embeddings = np.load(INPUT_EMBEDDINGS)

assert len(df) == len(embeddings), "Кількість записів і ембеддингів не збігається"
assert embeddings.shape[1] == VECTOR_DIM, "Невірна розмірність ембеддингів"

for start in tqdm(range(0, len(df), BATCH_SIZE), desc="Завантаження в Pinecone"):
    end = min(start + BATCH_SIZE, len(df))
    batch_vectors = []

    for i in range(start, end):
        row = df.iloc[i]
        vector = {
            "id": f"paper_{i}",
            "values": embeddings[i].tolist(),
            "metadata": {
                "arxiv_id": str(row["id"]),
                "title": str(row["title"])[:300],
                "abstract": str(row["abstract"])[:500],
                "authors": str(row["authors"])[:200],
                "year": int(row["year"]),
                "category": str(row["category"]),
            },
        }
        batch_vectors.append(vector)

    index.upsert(vectors=batch_vectors)

stats = index.describe_index_stats()
print("Статистика індексу:")
print(stats)
print(f"Усього векторів: {stats['total_vector_count']}")