# scripts/02_embed.py
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"
INPUT_FILE = DATA_DIR / "arxiv_subset.parquet"
OUTPUT_FILE = EMBEDDINGS_DIR / "embeddings.npy"
MODEL_NAME = "allenai/specter2_base"
BATCH_SIZE = 64

EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Не знайдено файл: {INPUT_FILE}\n"
        f"Спочатку запусти scripts/01_prepare_data.py"
    )

df = pd.read_parquet(INPUT_FILE)

texts = (df["title"].fillna("") + " [SEP] " + df["abstract"].fillna("")).tolist()

model = SentenceTransformer(MODEL_NAME)

embeddings = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    normalize_embeddings=True,
    convert_to_numpy=True,
)

print(f"Оброблено текстів: {len(texts)}")
print(f"Форма масиву ембеддингів: {embeddings.shape}")
print(f"Розмірність ембеддинга: {embeddings.shape[1]}")
print(f"Норма першого ембеддинга: {np.linalg.norm(embeddings[0]):.6f}")

np.save(OUTPUT_FILE, embeddings)
print(f"Ембеддинги збережено в {OUTPUT_FILE}")