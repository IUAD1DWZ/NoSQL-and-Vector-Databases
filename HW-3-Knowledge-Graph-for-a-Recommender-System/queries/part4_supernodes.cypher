// =====================================================
// PART 4. SUPERNODES ANALYSIS
// =====================================================

// -----------------------------------------------------
// 4.1. Користувачі з найбільшою кількістю оцінок
// -----------------------------------------------------
MATCH (u:User)-[r:RATED]->()
WITH u, count(r) AS degree
RETURN
    u.userId AS userId,
    degree
ORDER BY degree DESC
LIMIT 20;

// -----------------------------------------------------
// 4.2. Фільми з найбільшою кількістю оцінок
// -----------------------------------------------------
MATCH (m:Movie)<-[r:RATED]-()
WITH m, count(r) AS degree
RETURN
    m.movieId AS movieId,
    m.title AS title,
    degree
ORDER BY degree DESC
LIMIT 20;

// -----------------------------------------------------
// 4.3. Жанри з найбільшою кількістю фільмів
// -----------------------------------------------------
MATCH (g:Genre)<-[r:HAS_GENRE]-()
WITH g, count(r) AS degree
RETURN
    g.name AS genre,
    degree
ORDER BY degree DESC
LIMIT 20;

// -----------------------------------------------------
// 4.4. Загальний пошук вузлів з дуже великим degree
// -----------------------------------------------------
MATCH (n)
WITH labels(n) AS nodeLabels, n, count { (n)--() } AS degree
WHERE degree > 100
RETURN
    nodeLabels,
    coalesce(toString(n.userId), toString(n.movieId), n.name, n.title) AS identifier,
    degree
ORDER BY degree DESC
LIMIT 50;

// -----------------------------------------------------
// 4.5. Порівняння "звичайних" і "великих" вузлів Movie
// -----------------------------------------------------
MATCH (m:Movie)<-[r:RATED]-()
WITH m, count(r) AS ratingCount
WHERE ratingCount >= 20 AND ratingCount <= 30
RETURN
    m.movieId AS movieId,
    m.title AS title,
    ratingCount
ORDER BY ratingCount DESC
LIMIT 20;

// -----------------------------------------------------
// 4.6. Перевірка типів зв'язків у графі
// -----------------------------------------------------
MATCH ()-[r]->()
RETURN
    type(r) AS relationshipType,
    count(*) AS relationshipCount
ORDER BY relationshipCount DESC;