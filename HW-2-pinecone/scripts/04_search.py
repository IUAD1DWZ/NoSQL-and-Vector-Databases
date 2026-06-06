# scripts/04_search.py
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"
TOP_K = 5

INPUT_PARQUET = DATA_DIR / "arxiv_subset.parquet"
INPUT_EMBEDDINGS = EMBEDDINGS_DIR / "embeddings.npy"

if not INPUT_PARQUET.exists():
    raise FileNotFoundError(
        f"Не знайдено parquet-файл: {INPUT_PARQUET}\n"
        "Спочатку запусти scripts/01_prepare_data.py"
    )

if not INPUT_EMBEDDINGS.exists():
    raise FileNotFoundError(
        f"Не знайдено файл ембеддингів: {INPUT_EMBEDDINGS}\n"
        "Спочатку запусти scripts/02_embed.py"
    )

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(INDEX_NAME)
print("Завантаження моделі може зайняти 1-3 хвилини при першому запуску...")
model = SentenceTransformer(MODEL_NAME)
df = pd.read_parquet(INPUT_PARQUET).reset_index(drop=True)
embeddings = np.load(INPUT_EMBEDDINGS)

texts = (df["title"].fillna("") + " [SEP] " + df["abstract"].fillna("")).tolist()

def encode_query(query: str) -> np.ndarray:
    emb = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    )[0]
    return emb

def pretty_print_matches(matches, header):
    print(f"\n=== {header} ===")
    for rank, match in enumerate(matches, 1):
        md = match["metadata"]
        print(f"{rank}. {md['title']}")
        print(f"   category={md['category']} | year={md['year']} | score={match['score']:.4f}")
        print(f"   abstract={md['abstract'][:180]}...")
        print()

def pinecone_search(query: str, top_k: int = TOP_K, filt: Optional[dict] = None):
    q = encode_query(query).tolist()
    res = index.query(
        vector=q,
        top_k=top_k,
        include_metadata=True,
        filter=filt
    )
    return res["matches"]

query = "teaching machines to recognize objects in pictures"
matches = pinecone_search(query)
pretty_print_matches(matches, f"Семантичний пошук: {query}")

current_year = 2026
filter_a = {
    "$and": [
        {"year": {"$gte": current_year - 5}},
        {"category": {"$eq": "cs.LG"}}
    ]
}
matches_a = pinecone_search("reinforcement learning", filt=filter_a)
pretty_print_matches(matches_a, "Фільтр A: RL, останні 5 років, cs.LG")

filter_b = {"year": {"$lte": 2015}}
matches_b = pinecone_search("reinforcement learning", filt=filter_b)
pretty_print_matches(matches_b, "Фільтр B: RL, до 2015 року, будь-яка категорія")

def top_local(query: str, metric: str, top_k: int = TOP_K):
    q = encode_query(query)

    if metric == "cosine":
        scores = embeddings @ q
        idx = np.argsort(-scores)[:top_k]
    elif metric == "dot":
        scores = embeddings @ q
        idx = np.argsort(-scores)[:top_k]
    elif metric == "l2":
        distances = np.linalg.norm(embeddings - q, axis=1)
        idx = np.argsort(distances)[:top_k]
        scores = -distances
    else:
        raise ValueError("Unknown metric")

    print(f"\n=== Локальна метрика: {metric} ===")
    for rank, i in enumerate(idx, 1):
        row = df.iloc[i]
        print(f"{rank}. {row['title']}")
        print(f"   category={row['category']} | year={row['year']} | score={scores[i]:.4f}")
        print(f"   abstract={row['abstract'][:180]}...")
        print()

for metric in ["cosine", "dot", "l2"]:
    top_local(query, metric)