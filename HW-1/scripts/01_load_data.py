import os
from pathlib import Path

import kagglehub
import pandas as pd
from pymongo import MongoClient
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "spotify"
LOCAL_CSV_PATH = Path("dataset.csv")
DATASET_SLUG = "maharshipandya/-spotify-tracks-dataset"
BATCH_SIZE = 1000


def resolve_csv_path() -> Path:
    """
    Priority:
    1. Use local dataset.csv if it exists.
    2. Otherwise download dataset via kagglehub and find a CSV inside.
    """
    if LOCAL_CSV_PATH.exists():
        print(f"Using local CSV: {LOCAL_CSV_PATH.resolve()}")
        return LOCAL_CSV_PATH

    print(f"Local file {LOCAL_CSV_PATH} not found.")
    print(f"Downloading dataset from Kaggle: {DATASET_SLUG}")

    dataset_dir = Path(kagglehub.dataset_download(DATASET_SLUG))
    print(f"Path to dataset files: {dataset_dir}")

    csv_files = list(dataset_dir.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in downloaded dataset directory: {dataset_dir}"
        )

    # Prefer likely main dataset names, otherwise use the largest CSV
    preferred = None
    priority_keywords = ["dataset", "spotify", "tracks", "data"]

    for csv_file in csv_files:
        lower_name = csv_file.name.lower()
        if any(keyword in lower_name for keyword in priority_keywords):
            preferred = csv_file
            break

    if preferred is None:
        preferred = max(csv_files, key=lambda p: p.stat().st_size)

    print(f"Selected CSV: {preferred}")
    return preferred


def main():
    csv_path = resolve_csv_path()

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Drop for idempotent reruns
    db["tracks_raw"].drop()

    df = pd.read_csv(csv_path)
    print(f"Loading {len(df)} rows into {DB_NAME}.tracks_raw ...")

    # Boolean
    if "explicit" in df.columns:
        df["explicit"] = df["explicit"].astype(bool)

    # Integers
    int_cols = ["popularity", "duration_ms", "key", "mode", "time_signature"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Floats
    float_cols = [
        "danceability", "energy", "loudness", "speechiness",
        "acousticness", "instrumentalness", "liveness",
        "valence", "tempo"
    ]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    # Remove unusable rows
    required_cols = ["artists", "track_name"]
    existing_required_cols = [col for col in required_cols if col in df.columns]
    if existing_required_cols:
        df = df.dropna(subset=existing_required_cols)

    records = df.to_dict("records")

    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="Inserting batches"):
        batch = records[i:i + BATCH_SIZE]
        if batch:
            db["tracks_raw"].insert_many(batch)

    print(f"Inserted documents: {db['tracks_raw'].count_documents({})}")
    print("Sample document:")
    print(db["tracks_raw"].find_one())

    client.close()


if __name__ == "__main__":
    main()