/**
 * One2lvOS WebDAV Protocol Handler
 * WebDAV client used by the Network Manager (mesh routing).
 *
 * Paths given to every operation are relative to the connection's base path
 * ("/" = the folder the connection points at). ".." segments are refused.
 * Bodies are handled as Buffers so binary files survive a round trip.
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

const TIMEOUT_MS = 20000;
const MAX_DOWNLOAD = 100 * 1024 * 1024;

function xmlDecode(s) {
    return String(s || '')
        .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n))
        .replace(/&amp;/g, '&');
}

function tag(xml, name) {
    const m = xml.match(new RegExp(`<(?:[\\w-]+:)?${name}\\b[^>]*>([\\s\\S]*?)</(?:[\\w-]+:)?${name}>`, 'i'));
    return m ? xmlDecode(m[1].trim()) : null;
}

class WebDAVHandler {
    constructor() {
        this.name = 'webdav';
        this.sessions = new Map();
    }

    static credentialsOf(connection) {
        if (typeof connection.resolveCredentials === 'function') return connection.resolveCredentials();
        return connection.credentials;
    }

    /**
     * Connect to WebDAV server (verified with a PROPFIND on the base folder)
     */
    async connect(connection) {
        const { host, port, path = '/' } = connection;
        const secure = connection.secure === true || Number(port) === 443;
        let basePath = '/' + String(path || '/').replace(/^\/+/, '');
        if (!basePath.endsWith('/')) basePath += '/';
        const portPart = port ? `:${port}` : '';
        const baseUrl = `${secure ? 'https' : 'http'}://${host}${portPart}${encodeURI(basePath)}`;

        const session = {
            id: connection.id,
            baseUrl,
            basePath: new URL(baseUrl).pathname,
            credentials: WebDAVHandler.credentialsOf(connection),
            connected: true
        };

        try {
            await this.propfind(session, '/', 0);
            this.sessions.set(connection.id, session);
            return session;
        } catch (error) {
            throw new Error(`WebDAV connection failed: ${error.message}`);
        }
    }

    async disconnect(handle) {
        if (handle && handle.id) this.sessions.delete(handle.id);
    }

    /** Build an absolute URL for a path relative to the connection's base folder. */
    resolve(session, remotePath = '/', isDir = false) {
        const parts = String(remotePath || '/').split('/').filter(p => p && p !== '.');
        if (parts.some(p => p === '..')) throw new Error('Path may not contain ".."');
        let rel = parts.map(encodeURIComponent).join('/');
        if (rel && isDir) rel += '/';
        return new URL(rel, session.baseUrl);
    }

    authHeaders(session, extra = {}) {
        const headers = { ...extra };
        const c = session.credentials;
        if (c && (c.username || c.password)) {
            headers['Authorization'] = 'Basic ' + Buffer.from(`${c.username || ''}:${c.password || ''}`).toString('base64');
        }
        return headers;
    }

    async propfind(session, remotePath, depth = 1) {
        const body = `<?xml version="1.0" encoding="utf-8" ?>
<D:propfind xmlns:D="DAV:">
  <D:prop>
    <D:displayname/>
    <D:getcontentlength/>
    <D:getcontenttype/>
    <D:creationdate/>
    <D:getlastmodified/>
    <D:resourcetype/>
  </D:prop>
</D:propfind>`;
        const url = this.resolve(session, remotePath, true);
        return this.request(url, {
            method: 'PROPFIND',
            headers: this.authHeaders(session, {
                'Content-Type': 'application/xml; charset=utf-8',
                'Content-Length': Buffer.byteLength(body),
                'Depth': String(depth)
            })
        }, body);
    }

    async get(session, remotePath) {
        return this.request(this.resolve(session, remotePath), { method: 'GET', headers: this.authHeaders(session) });
    }

    async put(session, remotePath, data) {
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data == null ? '' : (typeof data === 'string' ? data : JSON.stringify(data)));
        return this.request(this.resolve(session, remotePath), {
            method: 'PUT',
            headers: this.authHeaders(session, { 'Content-Length': buf.length, 'Content-Type': 'application/octet-stream' })
        }, buf);
    }

    async mkcol(session, remotePath) {
        return this.request(this.resolve(session, remotePath, true), { method: 'MKCOL', headers: this.authHeaders(session) });
    }

    async delete(session, remotePath) {
        if (!String(remotePath || '').split('/').filter(Boolean).length) throw new Error('Refusing to delete the root folder');
        return this.request(this.resolve(session, remotePath), { method: 'DELETE', headers: this.authHeaders(session) });
    }

    async copy(session, srcPath, dstPath) {
        return this.request(this.resolve(session, srcPath), {
            method: 'COPY',
            headers: this.authHeaders(session, { 'Destination': this.resolve(session, dstPath).href, 'Overwrite': 'F' })
        });
    }

    async move(session, srcPath, dstPath) {
        return this.request(this.resolve(session, srcPath), {
            method: 'MOVE',
            headers: this.authHeaders(session, { 'Destination': this.resolve(session, dstPath).href, 'Overwrite': 'F' })
        });
    }

    /**
     * HTTP/HTTPS request; resolves with a Buffer body for 2xx, rejects otherwise.
     */
    async request(url, options, body = null) {
        return new Promise((resolve, reject) => {
            const client = url.protocol === 'https:' ? https : http;
            const req = client.request(url, { ...options, timeout: TIMEOUT_MS }, (res) => {
                const chunks = [];
                let size = 0;
                res.on('data', (chunk) => {
                    size += chunk.length;
                    if (size > MAX_DOWNLOAD) { req.destroy(new Error('File too large (over 100 MB)')); return; }
                    chunks.push(chunk);
                });
                res.on('end', () => {
                    const buf = Buffer.concat(chunks);
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        resolve({ status: res.statusCode, headers: res.headers, body: buf });
                    } else {
                        const msg = res.statusCode === 401 ? 'wrong username or password'
                            : res.statusCode === 404 ? 'not found'
                            : res.statusCode === 405 ? 'not allowed (does it already exist?)'
                            : res.statusCode === 412 ? 'destination already exists'
                            : res.statusMessage;
                        reject(new Error(`HTTP ${res.statusCode}: ${msg}`));
                    }
                });
            });
            req.on('timeout', () => req.destroy(new Error(`timed out after ${TIMEOUT_MS / 1000}s`)));
            req.on('error', reject);
            if (body) req.write(body);
            req.end();
        });
    }

    /**
     * Parse a PROPFIND multistatus (any namespace prefix) into entries relative
     * to the connection's base folder. The listed folder itself is left out.
     */
    parseXmlResponse(xmlData, session, listedPath = '/') {
        const xml = Buffer.isBuffer(xmlData) ? xmlData.toString('utf8') : String(xmlData || '');
        const items = [];
        const re = /<(?:[\w-]+:)?response\b[^>]*>([\s\S]*?)<\/(?:[\w-]+:)?response>/gi;
        const base = session ? session.basePath : '/';
        const listed = '/' + String(listedPath || '/').split('/').filter(Boolean).join('/');
        for (const m of xml.matchAll(re)) {
            const r = m[1];
            const hrefRaw = tag(r, 'href');
            if (!hrefRaw) continue;
            let hrefPath;
            try { hrefPath = new URL(hrefRaw, session ? session.baseUrl : 'http://x/').pathname; } catch { continue; }
            let decoded;
            try { decoded = decodeURIComponent(hrefPath); } catch { decoded = hrefPath; }
            let baseDecoded;
            try { baseDecoded = decodeURIComponent(base); } catch { baseDecoded = base; }
            let rel = decoded.startsWith(baseDecoded) ? decoded.slice(baseDecoded.length) : decoded;
            rel = '/' + rel.split('/').filter(Boolean).join('/');
            if (rel === listed) continue;
            const isDir = /<(?:[\w-]+:)?collection\b/i.test(r);
            const size = tag(r, 'getcontentlength');
            items.push({
                name: rel.split('/').filter(Boolean).pop() || tag(r, 'displayname') || rel,
                path: rel,
                href: hrefRaw,
                isDir,
                size: isDir ? 0 : (size ? parseInt(size, 10) || 0 : 0),
                type: isDir ? 'directory' : (tag(r, 'getcontenttype') || 'application/octet-stream'),
                modified: tag(r, 'getlastmodified')
            });
        }
        items.sort((a, b) => (b.isDir - a.isDir) || a.name.localeCompare(b.name));
        return items;
    }
}

module.exports = WebDAVHandler;
