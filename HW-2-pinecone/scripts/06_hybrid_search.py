# scripts/06_hybrid_search.py
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"
TOP_K = 10
INPUT_PARQUET = DATA_DIR / "arxiv_subset.parquet"

if not INPUT_PARQUET.exists():
    raise FileNotFoundError(
        f"Не знайдено parquet-файл: {INPUT_PARQUET}\n"
        "Спочатку запусти scripts/01_prepare_data.py"
    )

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(INDEX_NAME)
print("Завантаження моделі може зайняти 1-3 хвилини при першому запуску...")
model = SentenceTransformer(MODEL_NAME)
df = pd.read_parquet(INPUT_PARQUET).reset_index(drop=True)

corpus = (df["title"].fillna("") + " " + df["abstract"].fillna("")).tolist()
tokenized_corpus = [doc.lower().split() for doc in corpus]
bm25 = BM25Okapi(tokenized_corpus)

def encode_query(query: str):
    return model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]

def bm25_search(query: str, top_k: int = TOP_K):
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)
    idx = np.argsort(-scores)[:top_k]
    results = []
    for rank, i in enumerate(idx, 1):
        results.append({
            "doc_id": int(i),
            "rank": rank,
            "score": float(scores[i]),
            "title": df.iloc[i]["title"],
            "category": df.iloc[i]["category"],
            "year": int(df.iloc[i]["year"]),
        })
    return results

def vector_search(query: str, top_k: int = TOP_K):
    q = encode_query(query).tolist()
    res = index.query(vector=q, top_k=top_k, include_metadata=True)
    results = []
    for rank, m in enumerate(res["matches"], 1):
        doc_id = int(m["id"].replace("paper_", ""))
        results.append({
            "doc_id": doc_id,
            "rank": rank,
            "score": float(m["score"]),
            "title": m["metadata"]["title"],
            "category": m["metadata"]["category"],
            "year": int(m["metadata"]["year"]),
        })
    return results

def rrf_fusion(bm25_results, vector_results, k: int = 60, top_k: int = 5):
    fused = {}

    for result_set, source in [(bm25_results, "bm25"), (vector_results, "vector")]:
        for item in result_set:
            doc_id = item["doc_id"]
            if doc_id not in fused:
                fused[doc_id] = {
                    "doc_id": doc_id,
                    "title": item["title"],
                    "category": item["category"],
                    "year": item["year"],
                    "rrf_score": 0.0,
                    "sources": []
                }
            fused[doc_id]["rrf_score"] += 1.0 / (k + item["rank"])
            fused[doc_id]["sources"].append(f"{source}:{item['rank']}")

    ranked = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)
    return ranked[:top_k]

def print_results(label, results, use_rrf=False):
    print(f"\n=== {label} ===")
    for i, r in enumerate(results[:5], 1):
        if use_rrf:
            print(f"{i}. {r['title']}")
            print(f"   category={r['category']} | year={r['year']} | rrf={r['rrf_score']:.6f} | sources={', '.join(r['sources'])}")
        else:
            print(f"{i}. {r['title']}")
            print(f"   category={r['category']} | year={r['year']} | score={r['score']:.4f}")

queries = [
    "BERT fine-tuning",
    "Yann LeCun convolutional networks",
    "making computers understand human emotions from text",
]

for query in queries:
    print(f"\n\n############ QUERY: {query} ############")
    bm25_res = bm25_search(query)
    vec_res = vector_search(query)
    hybrid_res = rrf_fusion(bm25_res, vec_res, k=60, top_k=5)

    print_results("BM25", bm25_res)
    print_results("Vector", vec_res)
    print_results("Hybrid RRF", hybrid_res, use_rrf=True)