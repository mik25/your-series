const express = require('express');
const { addonBuilder, getRouter } = require('stremio-addon-sdk');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const manifest = {
    id: 'community.yourtvstreams',
    version: '1.0.0',
    name: 'Fight Club',
    description: 'Stream TV series',
    resources: ['catalog', 'stream', 'meta'],
    types: ['series'],
    idPrefixes: ['tt'],
    catalogs: [
        {
            type: 'series',
            id: 'yourtvstreams',
            name: 'Fight Club',
            extraSupported: ['search']
        }
    ]
};

const builder = new addonBuilder(manifest);

// Function to read JSON files
function readJSONFile(filename) {
    const filePath = path.join(__dirname, filename);
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

// Load series data files
const seriesDataFiles = fs.readdirSync(__dirname)
    .filter(file => file.includes('_organized_series_data.json'));

console.log("Found series data files:", seriesDataFiles);

const seriesData = seriesDataFiles.reduce((accumulator, filename) => {
    console.log("Reading series data file:", filename);
    const data = readJSONFile(filename);
    console.log("Data:", data);
    return accumulator.concat(data);
}, []);

console.log("Merged series data:", seriesData);

builder.defineCatalogHandler(({ type, id, extra }) => {
    return new Promise((resolve) => {
        if (type === 'series' && id === 'yourtvstreams') { 
            const seriesMetas = seriesData.map(series => ({
                id: series.id,
                type: 'series',
                name: series.name,
                poster: series.poster
            }));

            if (extra && extra.search) {
                const searchQuery = extra.search.toLowerCase();
                resolve({ metas: seriesMetas.filter(meta => meta.name.toLowerCase().includes(searchQuery)) });
            } else {
                resolve({ metas: seriesMetas });
            }
        } else {
            resolve({ metas: [] });
        }
    });
});

builder.defineMetaHandler(({ id }) => {
    return new Promise((resolve) => {
        const series = seriesData.find(s => s.id === id);

        if (series) {
            resolve({
                meta: {
                    id: series.id,
                    type: 'series',
                    name: series.name,
                    poster: series.poster,
                }
            });
        } else {
            resolve({});
        }
    });
});

builder.defineStreamHandler(({ type, id }) => {
    return new Promise(async (resolve) => {
        const [seriesId, seasonNumber, episodeNumber] = id.split(':');

        const series = seriesData.find(s => s.id === seriesId);
        if (series) {
            const season = series.seasons.find(s => s.season == seasonNumber);
            if (season) {
                const episode = season.episodes.find(e => e.episode == episodeNumber);
                if (episode) {
                    // Assuming you have a function to check if the stream is live
                    // try {
                    //     const isLive = await isStreamLive(episode.stream_url);
                    //     if (isLive) {
                            resolve({
                                streams: [{
                                    title: `S${seasonNumber}E${episodeNumber}`,
                                    url: episode.stream_url
                                }]
                            });
                    //     } else {
                    //         resolve({ streams: [] });
                    //     }
                    // } catch (error) {
                    //     console.error("Error fetching stream:", error);
                    //     resolve({ streams: [] });
                    // }
                } else {
                    resolve({ streams: [] });
                }
            } else {
                resolve({ streams: [] });
            }
        } else {
            resolve({ streams: [] });
        }
    });
});

// Assuming you have a function to check if the stream is live
// async function isStreamLive(url) {
//     try {
//         const response = await axios.head(url);
//         return response.status === 200;
//     } catch (error) {
//         console.error(`Stream check failed for ${url}`, error);
//         return false;
//     }
// }

const addonInterface = builder.getInterface();

const app = express();
app.use(cors());
app.use('/', getRouter(addonInterface));
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something went wrong!');
});

const PORT = process.env.PORT || 7000;
app.listen(PORT, () => {
    console.log(`Your TV Streams Addon running on port ${PORT}`);
});
