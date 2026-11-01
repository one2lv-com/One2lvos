// Vector Filesystem

(function(window) {
    'use strict';

    class VectorFS {
        constructor() {
            this.vectors = new Map();
        }

        async index(path, vector) {
            this.vectors.set(path, {
                path,
                vector,
                indexed: Date.now()
            });
        }

        async search(queryVector, topK = 10) {
            const results = [];

            for (const [path, entry] of this.vectors) {
                const similarity = this.cosineSimilarity(queryVector, entry.vector);
                results.push({ path, similarity });
            }

            results.sort((a, b) => b.similarity - a.similarity);
            return results.slice(0, topK);
        }

        cosineSimilarity(a, b) {
            if (!a || !b || a.length !== b.length) return 0;

            let dotProduct = 0;
            let normA = 0;
            let normB = 0;

            for (let i = 0; i < a.length; i++) {
                dotProduct += a[i] * b[i];
                normA += a[i] * a[i];
                normB += b[i] * b[i];
            }

            if (normA === 0 || normB === 0) return 0;
            return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
        }
    }

    window.VectorFS = new VectorFS();

})(window);
