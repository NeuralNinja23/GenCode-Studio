// This is the in-memory "virtual file system" for our preview.
let virtualFiles = {};

/**
 * A simple helper function to determine the MIME type from a file path.
 * @param {string} filePath - The path of the file (e.g., 'bundle.js').
 * @returns {string} The corresponding MIME type.
 */
const getContentType = (filePath) => {
    if (filePath.endsWith('.css')) return 'text/css';
    if (filePath.endsWith('.js') || filePath.endsWith('.mjs')) return 'application/javascript';
    if (filePath.endsWith('.json')) return 'application/json';
    if (filePath.endsWith('.html')) return 'text/html';
    if (filePath.endsWith('.svg')) return 'image/svg+xml';
    if (filePath.endsWith('.png')) return 'image/png';
    if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) return 'image/jpeg';
    return 'text/plain';
};

// Listen for messages from the main application.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SET_FILES') {
    virtualFiles = event.data.files;
    console.log('[Service Worker] Virtual file system updated.');
  }
});

// Intercept all network requests.
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (self.origin !== url.origin) {
    return;
  }

  const handleRequest = async () => {
    if (Object.keys(virtualFiles).length === 0) {
      return fetch(event.request);
    }

    if (url.pathname === '/') {
      const indexHtml = virtualFiles['index.html'] || '<!DOCTYPE html><html><body><h1>Project not found. Waiting for files...</h1></body></html>';
      return new Response(indexHtml, { headers: { 'Content-Type': 'text/html' } });
    }

    const filePath = url.pathname.substring(1);
    if (virtualFiles[filePath]) {
      const fileContent = virtualFiles[filePath];
      const contentType = getContentType(filePath);
      return new Response(fileContent, { headers: { 'Content-Type': contentType } });
    }
    
    return fetch(event.request);
  };

  event.respondWith(handleRequest());
});

self.addEventListener('install', () => {
  self.skipWaiting();
  console.log('[Service Worker] Installed.');
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
  console.log('[Service Worker] Activated and in control.');
});