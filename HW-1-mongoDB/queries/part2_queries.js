// queries/part2_queries.js
// Run:
// mongosh "YOUR_MONGO_URI/spotify" --file HW-1/queries/part2_queries.js

const dbName = "spotify";
const collectionName = "tracks";
const database = db.getSiblingDB(dbName);

print("\n==============================");
print("Part 2 - Query 1: Party tracks");
print("==============================");

const partyTracks = database[collectionName]
  .find(
    {
      "audio_features.danceability": { $gt: 0.7 },
      "audio_features.energy": { $gt: 0.7 },
      duration_ms: { $gte: 180000, $lte: 300000 }
    },
    {
      _id: 0,
      track_name: 1,
      artists: 1,
      track_genre: 1,
      duration_ms: 1,
      popularity: 1,
      "audio_features.danceability": 1,
      "audio_features.energy": 1
    }
  )
  .sort({ popularity: -1 })
  .limit(20)
  .toArray();

print(`Found party tracks: ${partyTracks.length}`);
printjson(partyTracks);

print("\n==============================================");
print("Part 2 - Query 2: Artists whose all tracks are popular");
print("==============================================");

const popularArtists = database[collectionName].aggregate([
  { $unwind: "$artists" },
  {
    $group: {
      _id: "$artists",
      track_count: { $sum: 1 },
      min_popularity: { $min: "$popularity" },
      avg_popularity: { $avg: "$popularity" }
    }
  },
  {
    $match: {
      track_count: { $gte: 3 },
      min_popularity: { $gte: 60 }
    }
  },
  {
    $project: {
      _id: 0,
      artist: "$_id",
      track_count: 1,
      min_popularity: 1,
      avg_popularity: { $round: ["$avg_popularity", 1] }
    }
  },
  { $sort: { avg_popularity: -1, track_count: -1, artist: 1 } },
  { $limit: 20 }
]).toArray();

print(`Found artists: ${popularArtists.length}`);
printjson(popularArtists);

print("\n==============================================");
print("Part 2 - Query 3: Tempo outliers within each genre");
print("==============================================");

const tempoOutliers = database[collectionName].aggregate([
  {
    $group: {
      _id: "$track_genre",
      avg_tempo: { $avg: "$audio_features.tempo" },
      std_tempo: { $stdDevPop: "$audio_features.tempo" },
      tracks: {
        $push: {
          _id: "$_id",
          track_name: "$track_name",
          popularity: "$popularity",
          artists: "$artists",
          audio_features: {
            tempo: "$audio_features.tempo"
          }
        }
      }
    }
  },
  {
    $addFields: {
      outlier_threshold: {
        $add: ["$avg_tempo", { $multiply: [2, "$std_tempo"] }]
      }
    }
  },
  {
    $project: {
      _id: 0,
      genre: "$_id",
      avg_tempo: { $round: ["$avg_tempo", 1] },
      outlier_threshold: { $round: ["$outlier_threshold", 1] },
      outlier_tracks: {
        $filter: {
          input: "$tracks",
          as: "track",
          cond: {
            $gt: ["$$track.audio_features.tempo", "$outlier_threshold"]
          }
        }
      }
    }
  },
  {
    $match: {
      "outlier_tracks.0": { $exists: true }
    }
  },
  { $sort: { genre: 1 } }
]).toArray();

print(`Genres with tempo outliers: ${tempoOutliers.length}`);
printjson(tempoOutliers);

print("\n==============================================");
print("Part 2 - Query 4: Background work tracks");
print("==============================================");

const workTracks = database[collectionName]
  .find(
    {
      "audio_features.loudness": { $lt: -10 },
      "audio_features.speechiness": { $lt: 0.1 },
      "audio_features.instrumentalness": { $gt: 0.5 },
      explicit: false
    },
    {
      _id: 0,
      track_name: 1,
      artists: 1,
      track_genre: 1,
      explicit: 1,
      popularity: 1,
      "audio_features.loudness": 1,
      "audio_features.speechiness": 1,
      "audio_features.instrumentalness": 1
    }
  )
  .sort({ popularity: -1 })
  .limit(20)
  .toArray();

print(`Found background work tracks: ${workTracks.length}`);
printjson(workTracks);