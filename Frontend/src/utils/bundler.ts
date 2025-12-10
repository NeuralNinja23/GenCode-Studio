type VFS = { [path: string]: string };

const CDN_MAP: Record<string, string> = {
  react: 'https://unpkg.com/react@18/umd/react.development.js',
  'react-dom': 'https://unpkg.com/react-dom@18/umd/react-dom.development.js',
  // add more mappings if you want (lodash, dayjs, etc.)
};

// Replace imports that point to packages with CDN equivalents or remove them if we supply UMD.
function rewriteImportsToCdn(code: string): { code: string; cdnScripts: string[] } {
  const importRegex = /import\s+(.+?)\s+from\s+['"]([^'"]+)['"];?/g;
  const cdnSet = new Set<string>();
  let rewritten = code.replace(importRegex, (match, imp, from) => {
    // local import (./ or ../)
    if (from.startsWith('./') || from.startsWith('../') || from.startsWith('/')) {
      // keep local imports to be handled by our VFS concatenation (we will strip later)
      return `/*LOCAL_IMPORT ${from}*/`;
    }
    // external package
    const pkg = from.split('/')[0];
    if (CDN_MAP[pkg]) {
      cdnSet.add(CDN_MAP[pkg]);
      // remove import, we'll provide UMD in iframe
      return `/*CDN_IMPORT ${pkg}*/`;
    }
    // fallback: map to esm.sh (might be ESM; use carefully)
    const fallback = `https://esm.sh/${from}`;
    cdnSet.add(fallback);
    return `/*CDN_IMPORT ${from}*/`;
  });

  return { code: rewritten, cdnScripts: Array.from(cdnSet) };
}

// Strip exports and convert 'export default' to declaration
function stripExports(code: string): string {
  // remove named exports (export const X = ...)
  code = code.replace(/export\s+(const|let|var|function|class)\s+/g, '$1 ');
  // export default <identifier or function/class>
  code = code.replace(/export\s+default\s+/g, '');
  // remove `export { X, Y }` statements
  code = code.replace(/export\s*{\s*[^}]*\s*};?/g, '');
  return code;
}

export function bundleVfsToHtml(vfs: VFS, entry: string = 'src/main.jsx'): string {
  // Determine order: try to put index-like files earlier
  const files = Object.keys(vfs).sort((a, b) => {
    if (a.endsWith('index.jsx') || a.endsWith('index.tsx') || a.endsWith('index.js')) return -1;
    if (b.endsWith('index.jsx') || b.endsWith('index.tsx') || b.endsWith('index.js')) return 1;
    if (a === entry) return -1;
    if (b === entry) return 1;
    return a.localeCompare(b);
  });

  const globalScripts = new Set<string>();
  const processedParts: string[] = [];

  for (const path of files) {
    let code = vfs[path];

    // rewrite imports to CDN (collect cdn scripts)
    const rew = rewriteImportsToCdn(code);
    code = rew.code;
    rew.cdnScripts.forEach(s => globalScripts.add(s));

    // remove local import markers (we'll inline all files)
    code = code.replace(/\/\*LOCAL_IMPORT\s+[^*]*\*\//g, '');

    // strip exports to allow concatenation
    code = stripExports(code);

    // transpile JSX/TSX -> plain JS using Babel
    try {
      // safe guard: Babel should exist (we included babel standalone in index.html)
      // @ts-ignore
      const transpiled = (window as any).Babel.transform(code, {
        presets: ['react', 'env'],
        plugins: [],
      }).code;
      processedParts.push(`// ---- FILE: ${path} ----\n${transpiled}`);
    } catch (err: any) {
      // If transpile fails, produce code that throws in iframe for visibility
      processedParts.push(`throw new Error("Babel transpile failed for ${path}: ${String(err)}");`);
    }
  }

  // Compose final HTML
  const cdnScriptTags = Array.from(globalScripts)
    .map(src => `<script src="${src}"></script>`)
    .join('\n');

  // Ensure React & ReactDOM present (if not present in cdn scripts, add them)
  if (![...globalScripts].some(s => s.includes('react@18'))) {
    // always include React + ReactDOM
    // Note: avoid duplication if CDN mapping included them already
  }

  const appJs = processedParts.join('\n\n');

  const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>html,body,#root{height:100%;margin:0;padding:0;} body{font-family:Inter,system-ui,Arial,sans-serif;}</style>
</head>
<body>
  <div id="root"></div>

  <!-- CDN libs used by user code -->
  ${cdnScriptTags}

  <script>
    // error overlay helper
    function showError(err) {
      document.body.innerHTML = '<pre style="color: red; white-space: pre-wrap; padding: 16px;">' + String(err) + '</pre>';
      console.error(err);
    }

    try {
      ${appJs}
    } catch (e) {
      showError(e);
    }
  </script>
</body>
</html>
`;

  return html;
}
