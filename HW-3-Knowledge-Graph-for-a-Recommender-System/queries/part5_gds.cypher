// =====================================================
// PART 5. GRAPH DATA SCIENCE
// =====================================================

// =====================================================
// 5.1. PAGERANK НА ГРАФІ ФІЛЬМІВ
// =====================================================

// cleanup старих тимчасових ребер
MATCH ()-[r:CO_RATED]-()
DELETE r;

// якщо movieGraph вже існує з попереднього запуску,
// вручну виконайте перед цим:
// CALL gds.graph.drop('movieGraph');

MATCH (m1:Movie)<-[r1:RATED]-(u:User)-[r2:RATED]->(m2:Movie)
WHERE r1.rating >= 4
  AND r2.rating >= 4
  AND id(m1) < id(m2)
WITH m1, m2, count(u) AS weight
WHERE weight >= 3
MERGE (m1)-[co:CO_RATED]-(m2)
SET co.weight = weight;

CALL gds.graph.project(
  'movieGraph',
  'Movie',
  {
    CO_RATED: {
      orientation: 'UNDIRECTED',
      properties: 'weight'
    }
  }
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount;

CALL gds.pageRank.stream('movieGraph', {
  relationshipWeightProperty: 'weight',
  maxIterations: 20,
  dampingFactor: 0.85
})
YIELD nodeId, score
RETURN
  gds.util.asNode(nodeId).movieId AS movieId,
  gds.util.asNode(nodeId).title AS title,
  score
ORDER BY score DESC
LIMIT 20;

CALL gds.graph.drop('movieGraph')
YIELD graphName
RETURN graphName;

MATCH ()-[r:CO_RATED]-()
DELETE r;


// =====================================================
// 5.2. LOUVAIN НА ГРАФІ СХОЖОСТІ КОРИСТУВАЧІВ
// =====================================================

MATCH ()-[r:SIMILAR]-()
DELETE r;

// якщо userSimilarity вже існує з попереднього запуску,
// вручну виконайте перед цим:
// CALL gds.graph.drop('userSimilarity');

MATCH (u1:User)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
WHERE r1.rating >= 4
  AND r2.rating >= 4
  AND id(u1) < id(u2)
WITH u1, u2, count(m) AS weight
WHERE weight >= 3
MERGE (u1)-[s:SIMILAR]-(u2)
SET s.weight = weight;

CALL gds.graph.project(
  'userSimilarity',
  'User',
  {
    SIMILAR: {
      orientation: 'UNDIRECTED',
      properties: 'weight'
    }
  }
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount;

CALL gds.louvain.stream('userSimilarity', {
  relationshipWeightProperty: 'weight'
})
YIELD nodeId, communityId
WITH communityId, count(*) AS clusterSize
RETURN communityId, clusterSize
ORDER BY clusterSize DESC
LIMIT 10;

CALL gds.louvain.stream('userSimilarity', {
  relationshipWeightProperty: 'weight'
})
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS u, communityId
MATCH (u)-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE r.rating >= 4
WITH communityId, g.name AS genre, count(*) AS freq
ORDER BY communityId, freq DESC
WITH communityId, collect({genre: genre, freq: freq}) AS genres
RETURN
  communityId,
  genres[0..3] AS topGenres
LIMIT 10;

CALL gds.graph.drop('userSimilarity')
YIELD graphName
RETURN graphName;

MATCH ()-[r:SIMILAR]-()
DELETE r;


// =====================================================
// 5.3. DIJKSTRA МІЖ КОРИСТУВАЧАМИ
// =====================================================

MATCH ()-[r:SIMILAR]-()
DELETE r;

// якщо userGraph вже існує з попереднього запуску,
// вручну виконайте перед цим:
// CALL gds.graph.drop('userGraph');

MATCH (u1:User)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
WHERE r1.rating >= 4
  AND r2.rating >= 4
  AND id(u1) < id(u2)
WITH u1, u2, count(m) AS weight
WHERE weight >= 3
MERGE (u1)-[s:SIMILAR]-(u2)
SET s.weight = weight,
    s.distance = 1.0 / weight;

CALL gds.graph.project(
  'userGraph',
  'User',
  {
    SIMILAR: {
      orientation: 'UNDIRECTED',
      properties: ['weight', 'distance']
    }
  }
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount;

MATCH (source:User {userId: 1}), (target:User {userId: 100})
CALL gds.shortestPath.dijkstra.stream('userGraph', {
  sourceNode: source,
  targetNode: target,
  relationshipWeightProperty: 'distance'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
RETURN
  gds.util.asNode(sourceNode).userId AS sourceUser,
  gds.util.asNode(targetNode).userId AS targetUser,
  totalCost,
  [nodeId IN nodeIds | gds.util.asNode(nodeId).userId] AS userPath,
  size(nodeIds) - 1 AS hops,
  costs;

CALL gds.graph.drop('userGraph')
YIELD graphName
RETURN graphName;

MATCH ()-[r:SIMILAR]-()
DELETE r;