// queries/part4_indexes.js
// Run:
// mongosh "YOUR_MONGO_URI/spotify" --file HW-1/queries/part4_indexes.js

const database = db.getSiblingDB("spotify");
const tracks = database.tracks;

print("\n====================================================");
print("Part 4 — Task 1: Explain before index");
print("====================================================");

const query1ExplainBefore = tracks.find(
  {
    track_genre: "pop",
    "audio_features.danceability": { $gte: 0.7 }
  },
  {
    track_name: 1,
    popularity: 1,
    track_genre: 1,
    "audio_features.danceability": 1
  }
).sort({ popularity: -1 }).explain("executionStats");

printjson(query1ExplainBefore);

print("\n====================================================");
print("Part 4 — Task 1: Create index");
print("====================================================");

// ESR: Equality -> Sort -> Range
const index1Name = tracks.createIndex(
  {
    track_genre: 1,
    popularity: -1,
    "audio_features.danceability": 1
  },
  {
    name: "idx_genre_popularity_danceability"
  }
);

print(`Created index: ${index1Name}`);

print("\n====================================================");
print("Part 4 — Task 1: Explain after index");
print("====================================================");

const query1ExplainAfter = tracks.find(
  {
    track_genre: "pop",
    "audio_features.danceability": { $gte: 0.7 }
  },
  {
    track_name: 1,
    popularity: 1,
    track_genre: 1,
    "audio_features.danceability": 1
  }
).sort({ popularity: -1 }).explain("executionStats");

printjson(query1ExplainAfter);

print("\n====================================================");
print("Part 4 — Task 2: Create index for work-music query");
print("====================================================");

// Equality first, then range fields
const index2Name = tracks.createIndex(
  {
    explicit: 1,
    "audio_features.instrumentalness": 1,
    "audio_features.speechiness": 1
  },
  {
    name: "idx_explicit_instrumentalness_speechiness"
  }
);

print(`Created index: ${index2Name}`);

print("\n====================================================");
print("Part 4 — Task 2: Explain work-music query");
print("====================================================");

const query2Explain = tracks.find(
  {
    explicit: false,
    "audio_features.instrumentalness": { $gt: 0.5 },
    "audio_features.speechiness": { $lt: 0.1 }
  },
  {
    track_name: 1,
    artists: 1,
    explicit: 1,
    "audio_features.instrumentalness": 1,
    "audio_features.speechiness": 1
  }
).explain("executionStats");

printjson(query2Explain);

print("\n====================================================");
print("Part 4 — Existing indexes");
print("====================================================");

printjson(tracks.getIndexes());