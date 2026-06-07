#!/usr/bin/env python3
"""
convert.py - Конвертація MovieLens .dat файлів у CSV формат
Кодування вхідних файлів: Latin-1
Роздільник вхідних файлів: ::
Вихідне кодування: UTF-8
Вихідний роздільник: ,
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "import"

# Конвертація movies.dat
# Формат: MovieID::Title::Genres
print("Конвертація movies.dat -> movies.csv...")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
try:
    with open(INPUT_DIR / 'movies.dat', encoding='latin-1') as f_in, \
         open(INPUT_DIR / 'movies.csv', 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['movieId', 'title', 'genres'])
        for line in f_in:
            parts = line.strip().split('::')
            if len(parts) >= 3:
                writer.writerow(parts[:3])
except FileNotFoundError:
    print("  Помилка: файл movies.dat не знайдений")

# Конвертація ratings.dat
# Формат: UserID::MovieID::Rating::Timestamp
print("Конвертація ratings.dat -> ratings.csv...")
try:
    with open(INPUT_DIR / 'ratings.dat', encoding='latin-1') as f_in, \
         open(INPUT_DIR / 'ratings.csv', 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['userId', 'movieId', 'rating', 'timestamp'])
        for line in f_in:
            parts = line.strip().split('::')
            if len(parts) >= 4:
                writer.writerow(parts[:4])
except FileNotFoundError:
    print("  Помилка: файл ratings.dat не знайдений")

# Конвертація users.dat
# Формат: UserID::Gender::Age::Occupation::Zip
print("Конвертація users.dat -> users.csv...")
try:
    with open(INPUT_DIR / 'users.dat', encoding='latin-1') as f_in, \
         open(INPUT_DIR / 'users.csv', 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['userId', 'gender', 'age', 'occupation'])
        for line in f_in:
            parts = line.strip().split('::')
            if len(parts) >= 4:
                writer.writerow(parts[:4])
except FileNotFoundError:
    print("  Помилка: файл users.dat не знайдений")

print("Конвертація завершена!")
print("  - import/movies.csv")
print("  - import/ratings.csv")
print("  - import/users.csv")