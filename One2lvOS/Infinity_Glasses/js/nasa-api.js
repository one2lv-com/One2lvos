// NASA JWST Image API Integration
class NASAImageAPI {
    constructor() {
        this.baseURL = 'https://images-api.nasa.gov';
        this.cache = new Map();
        this.currentImages = [];
    }

    async searchImages(query = 'james webb', page = 1) {
        const cacheKey = `${query}-${page}`;

        // Check cache first
        if (this.cache.has(cacheKey)) {
            console.log('Returning cached results for:', query);
            return this.cache.get(cacheKey);
        }

        try {
            const url = `${this.baseURL}/search?q=${encodeURIComponent(query)}&media_type=image&page=${page}`;
            console.log('Fetching from NASA API:', url);

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`NASA API error: ${response.status}`);
            }

            const data = await response.json();

            if (!data.collection || !data.collection.items) {
                throw new Error('Invalid response format from NASA API');
            }

            const items = data.collection.items.map(item => {
                const data = item.data[0];
                const links = item.links || [];
                const imageLink = links.find(link => link.rel === 'preview');

                return {
                    title: data.title || 'Untitled',
                    description: data.description || 'No description available',
                    dateCreated: data.date_created || null,
                    nasaId: data.nasa_id || '',
                    thumbnail: imageLink ? imageLink.href : null,
                    keywords: data.keywords || [],
                    center: data.center || 'NASA',
                    photographer: data.photographer || null
                };
            });

            const result = {
                items: items,
                total: data.collection.metadata?.total_hits || items.length,
                query: query,
                page: page
            };

            // Cache the result
            this.cache.set(cacheKey, result);
            this.currentImages = items;

            return result;

        } catch (error) {
            console.error('NASA API Error:', error);

            // Return fallback JWST images if API fails
            return this.getFallbackImages(query);
        }
    }

    getFallbackImages(query) {
        // Fallback to known JWST images if API is unavailable
        const fallbackImages = [
            {
                title: 'JWST First Deep Field',
                description: 'Webb\'s First Deep Field is the first operational image taken by the James Webb Space Telescope. The deep field view shows the galaxy cluster SMACS 0723.',
                dateCreated: '2022-07-12',
                nasaId: 'GSFC_20220712_JWST_FirstImages_01',
                thumbnail: 'https://stsci-opo.org/STScI-01G7JJADTH90FR98AKKJFKSS0B.png',
                keywords: ['jwst', 'deep field', 'galaxy cluster', 'smacs 0723'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Carina Nebula',
                description: 'This landscape of "mountains" and "valleys" speckled with glittering stars is actually the edge of a nearby, young, star-forming region called NGC 3324 in the Carina Nebula.',
                dateCreated: '2022-07-12',
                nasaId: 'GSFC_20220712_JWST_FirstImages_02',
                thumbnail: 'https://stsci-opo.org/STScI-01G7ETS03YR1TS8VVZRMFXZ0F2.png',
                keywords: ['jwst', 'carina nebula', 'ngc 3324', 'star formation'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Southern Ring Nebula',
                description: 'The Southern Ring, or "Eight-Burst" nebula, is a planetary nebula – an expanding cloud of gas, surrounding a dying star.',
                dateCreated: '2022-07-12',
                nasaId: 'GSFC_20220712_JWST_FirstImages_03',
                thumbnail: 'https://stsci-opo.org/STScI-01G7ETS3YXN38Q8W9VHVQVF7PH.png',
                keywords: ['jwst', 'southern ring nebula', 'planetary nebula'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Stephan\'s Quintet',
                description: 'Stephan\'s Quintet, a visual grouping of five galaxies, is best known for being prominently featured in the holiday classic film, "It\'s a Wonderful Life."',
                dateCreated: '2022-07-12',
                nasaId: 'GSFC_20220712_JWST_FirstImages_04',
                thumbnail: 'https://stsci-opo.org/STScI-01G7ETSCYA6T131QEJQ6KRXTNR.png',
                keywords: ['jwst', 'stephans quintet', 'galaxy group'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Exoplanet WASP-96b',
                description: 'Webb\'s detailed observation of this hot, puffy planet outside our solar system reveals the clear signature of water, along with evidence of haze and clouds.',
                dateCreated: '2022-07-12',
                nasaId: 'GSFC_20220712_JWST_FirstImages_05',
                thumbnail: 'https://stsci-opo.org/STScI-01G7DA5ADA2WDSK1K36Exoplanet_NIRSpec_transmission.png',
                keywords: ['jwst', 'exoplanet', 'wasp-96b', 'spectroscopy'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Pillars of Creation',
                description: 'The Pillars of Creation are set off in a kaleidoscope of color in Webb\'s near-infrared-light view.',
                dateCreated: '2022-10-19',
                nasaId: 'GSFC_20221019_JWST_PillarsOfCreation',
                thumbnail: 'https://stsci-opo.org/STScI-01GF423GBQSK6ANC89NTFJW8VM.png',
                keywords: ['jwst', 'pillars of creation', 'eagle nebula', 'm16'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Cartwheel Galaxy',
                description: 'The Cartwheel Galaxy shines in this new image from Webb, revealing new details about star formation and the galaxy\'s central black hole.',
                dateCreated: '2022-08-02',
                nasaId: 'GSFC_20220802_JWST_Cartwheel',
                thumbnail: 'https://stsci-opo.org/STScI-01G8JZRNZXVMX8M3J84EHM0V2S.png',
                keywords: ['jwst', 'cartwheel galaxy', 'ring galaxy'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            },
            {
                title: 'JWST Tarantula Nebula',
                description: 'The James Webb Space Telescope reveals the Tarantula Nebula in a new light, including tens of thousands of never-before-seen young stars.',
                dateCreated: '2022-09-06',
                nasaId: 'GSFC_20220906_JWST_Tarantula',
                thumbnail: 'https://stsci-opo.org/STScI-01GA76Q01D09HFEV174SVMQDMV.png',
                keywords: ['jwst', 'tarantula nebula', '30 doradus', 'star formation'],
                center: 'NASA/GSFC',
                photographer: 'NASA, ESA, CSA, STScI'
            }
        ];

        // Filter by query if provided
        const filtered = query ? fallbackImages.filter(img =>
            img.title.toLowerCase().includes(query.toLowerCase()) ||
            img.keywords.some(k => k.toLowerCase().includes(query.toLowerCase()))
        ) : fallbackImages;

        this.currentImages = filtered;

        return {
            items: filtered,
            total: filtered.length,
            query: query,
            page: 1,
            fallback: true
        };
    }

    async getAssetManifest(nasaId) {
        try {
            const url = `${this.baseURL}/asset/${nasaId}`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Asset manifest error: ${response.status}`);
            }

            const data = await response.json();
            return data.collection.items;

        } catch (error) {
            console.error('Asset manifest error:', error);
            return [];
        }
    }

    async searchByKeywords(keywords = []) {
        if (keywords.length === 0) {
            return this.getFallbackImages('');
        }

        const query = keywords.join(' ');
        return this.searchImages(query);
    }

    async getRandomJWSTImage() {
        const jwstQueries = [
            'james webb deep field',
            'jwst nebula',
            'jwst galaxy',
            'james webb first images',
            'jwst pillars'
        ];

        const randomQuery = jwstQueries[Math.floor(Math.random() * jwstQueries.length)];
        const results = await this.searchImages(randomQuery);

        if (results.items.length > 0) {
            const randomIndex = Math.floor(Math.random() * results.items.length);
            return results.items[randomIndex];
        }

        return null;
    }

    clearCache() {
        this.cache.clear();
        console.log('NASA API cache cleared');
    }

    getCachedQueries() {
        return Array.from(this.cache.keys());
    }
}

// Auto-update manager for JWST images
class JWSTAutoUpdater {
    constructor(api, updateInterval = 30000) {
        this.api = api;
        this.updateInterval = updateInterval;
        this.isRunning = false;
        this.intervalId = null;
        this.currentQuery = 'james webb';
        this.callbacks = [];
    }

    start() {
        if (this.isRunning) {
            console.log('Auto-updater already running');
            return;
        }

        console.log(`Starting JWST auto-updater (interval: ${this.updateInterval}ms)`);
        this.isRunning = true;

        // Initial fetch
        this.update();

        // Set up interval
        this.intervalId = setInterval(() => {
            this.update();
        }, this.updateInterval);
    }

    stop() {
        if (!this.isRunning) {
            return;
        }

        console.log('Stopping JWST auto-updater');
        this.isRunning = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async update() {
        try {
            console.log(`Fetching JWST images: "${this.currentQuery}"`);
            const results = await this.api.searchImages(this.currentQuery);

            // Notify all callbacks
            this.callbacks.forEach(callback => {
                try {
                    callback(results);
                } catch (error) {
                    console.error('Callback error:', error);
                }
            });

        } catch (error) {
            console.error('Auto-update error:', error);
        }
    }

    setQuery(query) {
        this.currentQuery = query;
        if (this.isRunning) {
            this.update();
        }
    }

    setInterval(ms) {
        this.updateInterval = ms;

        if (this.isRunning) {
            this.stop();
            this.start();
        }
    }

    onUpdate(callback) {
        this.callbacks.push(callback);
    }

    removeCallback(callback) {
        const index = this.callbacks.indexOf(callback);
        if (index !== -1) {
            this.callbacks.splice(index, 1);
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NASAImageAPI, JWSTAutoUpdater };
}