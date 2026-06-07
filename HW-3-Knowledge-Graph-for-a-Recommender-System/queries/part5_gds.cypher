// =====================================================
// PART 5. GRAPH DATA SCIENCE
// Neo4j 5.x / reduced working subgraphs
// =====================================================


// =====================================================
// 5.1. PAGERANK ON MOVIE GRAPH
// =====================================================

CALL gds.graph.drop('movieGraph')
YIELD graphName
RETURN graphName;

MATCH ()-[r:CO_RATED]-()
DELETE r;

CALL {
  MATCH (m:Movie)<-[r:RATED]-()
  WITH m, count(r) AS ratingCount
  WHERE ratingCount >= 500
  RETURN collect(m.movieId) AS topMovieIds
}
MATCH (m1:Movie)<-[r1:RATED]-(u:User)-[r2:RATED]->(m2:Movie)
WHERE r1.rating >= 5
  AND r2.rating >= 5
  AND id(m1) < id(m2)
  AND m1.movieId IN topMovieIds
  AND m2.movieId IN topMovieIds
WITH m1, m2, count(u) AS weight
WHERE weight >= 2
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
  relationshipWeightProperty: 'weight'
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
// 5.2. LOUVAIN ON USER SIMILARITY GRAPH
// =====================================================

CALL gds.graph.drop('userSimilarity')
YIELD graphName
RETURN graphName;

MATCH ()-[r:SIMILAR]-()
DELETE r;

:auto
CALL {
  MATCH (u:User)-[r:RATED]->()
  WITH u, count(r) AS ratingCount
  WHERE ratingCount >= 20
  RETURN u.userId AS userId
  ORDER BY ratingCount DESC
  LIMIT 10
}
WITH userId
CALL {
  WITH userId
  MATCH (u1:User {userId: userId})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
  WHERE r1.rating >= 4
    AND r2.rating >= 4
    AND id(u1) < id(u2)
  WITH u1, u2, count(m) AS weight
  WHERE weight >= 1
  MERGE (u1)-[s:SIMILAR]-(u2)
  SET s.weight = weight,
      s.distance = 1.0 / weight
} IN TRANSACTIONS OF 1 ROW;

CALL gds.graph.project(
  'userSimilarity',
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
// 5.3. DIJKSTRA ON USER GRAPH
// =====================================================

CALL gds.graph.drop('userGraph')
YIELD graphName
RETURN graphName;

MATCH ()-[r:SIMILAR]-()
DELETE r;

:auto
CALL {
  MATCH (u:User)-[r:RATED]->()
  WITH u, count(r) AS ratingCount
  WHERE ratingCount >= 20
  RETURN u.userId AS userId
  ORDER BY ratingCount DESC
  LIMIT 10
}
WITH userId
CALL {
  WITH userId
  MATCH (u1:User {userId: userId})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
  WHERE r1.rating >= 4
    AND r2.rating >= 4
    AND id(u1) < id(u2)
  WITH u1, u2, count(m) AS weight
  WHERE weight >= 1
  MERGE (u1)-[s:SIMILAR]-(u2)
  SET s.weight = weight,
      s.distance = 1.0 / weight
} IN TRANSACTIONS OF 1 ROW;

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

MATCH (s:User)-[rel:SIMILAR]-(t:User)
WITH s, t, rel
ORDER BY rel.weight DESC
LIMIT 1
CALL gds.shortestPath.dijkstra.stream('userGraph', {
  sourceNode: s,
  targetNode: t,
  relationshipWeightProperty: 'distance'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
RETURN
  gds.util.asNode(sourceNode).userId AS sourceUser,
  gds.util.asNode(targetNode).userId AS targetUser,
  totalCost,
  [nodeId IN nodeIds | gds.util.asNode(nodeId).userId] AS userPath,
  size(nodeIds) - 1 AS hops,
  costs
LIMIT 1;

CALL gds.graph.drop('userGraph')
YIELD graphName
RETURN graphName;

MATCH ()-[r:SIMILAR]-()
DELETE r;