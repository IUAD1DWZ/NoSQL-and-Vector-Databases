// =====================================================
// PART 3. CYPHER QUERIES
// =====================================================

// -----------------------------------------------------
// Query 1
// Усі фільми жанру Thriller із середнім рейтингом > 4.0
// -----------------------------------------------------
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Thriller'})
MATCH (m)<-[r:RATED]-(:User)
WITH m, avg(r.rating) AS avgRating, count(r) AS ratingsCount
WHERE avgRating > 4.0
RETURN
    m.movieId AS movieId,
    m.title AS title,
    round(avgRating * 100) / 100.0 AS avgRating,
    ratingsCount
ORDER BY avgRating DESC, ratingsCount DESC, title ASC;

// -----------------------------------------------------
// Query 2
// Користувачі, які поставили оцінку 5 більш ніж 50 фільмам
// -----------------------------------------------------
MATCH (u:User)-[r:RATED]->(m:Movie)
WHERE r.rating = 5
WITH u, count(r) AS fiveStarCount
WHERE fiveStarCount > 50
RETURN
    u.userId AS userId,
    u.gender AS gender,
    u.age AS age,
    u.occupation AS occupation,
    fiveStarCount
ORDER BY fiveStarCount DESC, userId ASC;

// -----------------------------------------------------
// Query 3
// Фільми, які користувачі 1 і 2 обидва оцінили високо (>= 4)
// -----------------------------------------------------
MATCH (u1:User {userId: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User {userId: 2})
WHERE r1.rating >= 4 AND r2.rating >= 4
RETURN
    m.movieId AS movieId,
    m.title AS title,
    r1.rating AS ratingUser1,
    r2.rating AS ratingUser2
ORDER BY m.title ASC;

// -----------------------------------------------------
// Query 4
// Жанри, чиї фільми стабільно отримують високі оцінки
// -----------------------------------------------------
MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie)<-[r:RATED]-(:User)
WITH
    g.name AS genre,
    avg(r.rating) AS avgRating,
    count(r) AS ratingsCount
WHERE ratingsCount >= 1000
RETURN
    genre,
    round(avgRating * 100) / 100.0 AS avgRating,
    ratingsCount
ORDER BY avgRating DESC, ratingsCount DESC;

// -----------------------------------------------------
// Query 5
// Рекомендація: "користувачі зі схожими смаками також дивилися"
// Для прикладу: target userId = 1
// -----------------------------------------------------
MATCH (target:User {userId: 1})-[tr:RATED]->(common:Movie)<-[or:RATED]-(other:User)
WHERE tr.rating >= 4 AND or.rating >= 4 AND target <> other
WITH target, other, count(common) AS overlap, avg(abs(tr.rating - or.rating)) AS avgDiff
WHERE overlap >= 3 AND avgDiff <= 1.0
MATCH (other)-[r2:RATED]->(rec:Movie)
WHERE r2.rating >= 4
  AND NOT (target)-[:RATED]->(rec)
WITH rec, count(DISTINCT other) AS similarUsersCount, avg(r2.rating) AS avgRecommendedRating
RETURN
    rec.movieId AS movieId,
    rec.title AS title,
    similarUsersCount,
    round(avgRecommendedRating * 100) / 100.0 AS avgRecommendedRating
ORDER BY similarUsersCount DESC, avgRecommendedRating DESC, title ASC
LIMIT 20;

// -----------------------------------------------------
// Query 6
// Найкоротший ланцюжок зв'язку між двома користувачами
// через спільні фільми
// -----------------------------------------------------
MATCH (u1:User {userId: 1}), (u2:User {userId: 100})
MATCH p = shortestPath((u1)-[:RATED*..6]-(u2))
RETURN
    length(p) AS pathLength,
    [n IN nodes(p) |
        CASE
            WHEN n:User THEN 'User(' + toString(n.userId) + ')'
            WHEN n:Movie THEN 'Movie(' + n.title + ')'
            ELSE 'Unknown'
        END
    ] AS pathNodes;