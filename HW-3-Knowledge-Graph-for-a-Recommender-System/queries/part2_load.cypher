// =====================================================
// PART 2. DATA LOADING
// MovieLens 1M -> Neo4j 5.x
// =====================================================

/*
Перед запуском:
1. Виконано convert.py
2. У папці ./import вже є:
   - movies.csv
   - users.csv
   - ratings.csv

У Docker volume змонтовано так:
./import -> /var/lib/neo4j/import

Тому Neo4j читає файли як:
file:///movies.csv
file:///users.csv
file:///ratings.csv
*/

// =====================================================
// 1. ІНДЕКСИ
// =====================================================

CREATE INDEX user_userId_index IF NOT EXISTS
FOR (u:User)
ON (u.userId);

CREATE INDEX movie_movieId_index IF NOT EXISTS
FOR (m:Movie)
ON (m.movieId);

CREATE INDEX genre_name_index IF NOT EXISTS
FOR (g:Genre)
ON (g.name);

// Опціонально: перевірка
SHOW INDEXES;

// =====================================================
// 2. ЗАВАНТАЖЕННЯ КОРИСТУВАЧІВ
// =====================================================

LOAD CSV WITH HEADERS FROM 'file:///users.csv' AS row
WITH row
WHERE row.userId IS NOT NULL
MERGE (u:User {userId: toInteger(row.userId)})
SET u.gender = row.gender,
    u.age = toInteger(row.age),
    u.occupation = toInteger(row.occupation);

// Перевірка
MATCH (u:User)
RETURN count(u) AS users_count;

// =====================================================
// 3. ЗАВАНТАЖЕННЯ ФІЛЬМІВ
// =====================================================

LOAD CSV WITH HEADERS FROM 'file:///movies.csv' AS row
WITH row
WHERE row.movieId IS NOT NULL
MERGE (m:Movie {movieId: toInteger(row.movieId)})
SET m.title = row.title;

// Перевірка
MATCH (m:Movie)
RETURN count(m) AS movies_count;

// =====================================================
// 4. СТВОРЕННЯ ЖАНРІВ
// =====================================================

LOAD CSV WITH HEADERS FROM 'file:///movies.csv' AS row
WITH row
WHERE row.genres IS NOT NULL
UNWIND split(row.genres, '|') AS genreName
WITH trim(genreName) AS genreName
MERGE (:Genre {name: genreName});

// Перевірка
MATCH (g:Genre)
RETURN count(g) AS genres_count, collect(g.name) AS genres;

// =====================================================
// 5. ЗВ'ЯЗКИ MOVIE -> GENRE
// =====================================================

LOAD CSV WITH HEADERS FROM 'file:///movies.csv' AS row
WITH row
WHERE row.movieId IS NOT NULL AND row.genres IS NOT NULL
MATCH (m:Movie {movieId: toInteger(row.movieId)})
UNWIND split(row.genres, '|') AS genreName
WITH m, trim(genreName) AS genreName
MATCH (g:Genre {name: genreName})
MERGE (m)-[:HAS_GENRE]->(g);

// Перевірка
MATCH ()-[r:HAS_GENRE]->()
RETURN count(r) AS has_genre_count;

// =====================================================
// 6. ЗАВАНТАЖЕННЯ ОЦІНОК BATCH-АМИ
// =====================================================

CALL apoc.periodic.iterate(
  "
  LOAD CSV WITH HEADERS FROM 'file:///ratings.csv' AS row
  WITH row
  WHERE row.userId IS NOT NULL AND row.movieId IS NOT NULL
  RETURN row
  ",
  "
  MATCH (u:User {userId: toInteger(row.userId)})
  MATCH (m:Movie {movieId: toInteger(row.movieId)})
  MERGE (u)-[r:RATED]->(m)
  SET r.rating = toInteger(row.rating),
      r.timestamp = toInteger(row.timestamp)
  ",
  {
    batchSize: 10000,
    parallel: false,
    iterateList: true
  }
)
YIELD batches, total, timeTaken, committedOperations, failedOperations, failedBatches
RETURN batches, total, timeTaken, committedOperations, failedOperations, failedBatches;

// =====================================================
// 7. ФІНАЛЬНА ПЕРЕВІРКА
// =====================================================

MATCH (u:User)
RETURN count(u) AS users;

MATCH (m:Movie)
RETURN count(m) AS movies;

MATCH (g:Genre)
RETURN count(g) AS genres;

MATCH ()-[r:RATED]->()
RETURN count(r) AS ratings;

MATCH ()-[r:HAS_GENRE]->()
RETURN count(r) AS has_genre;