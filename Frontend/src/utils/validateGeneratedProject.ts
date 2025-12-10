// frontend/src/utils/validateGeneratedProject.ts
import { FilePayload } from '../hooks/usePreview';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validate an agent-generated Vite+React+TS project.
 * Extra checks:
 *  - Ensures main.tsx imports App
 *  - Detects pages/components referenced but missing
 *  - Warns about unused files
 */
export function validateGeneratedProject(fileTree: FilePayload[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const paths = fileTree.map(f => f.path);

  // 1️⃣ Required entry & app
  if (!paths.includes('src/main.tsx')) errors.push('Missing src/main.tsx entry file.');
  if (!paths.includes('src/App.tsx')) errors.push('Missing src/App.tsx.');
  if (!paths.includes('index.html')) errors.push('Missing root index.html.');

  // 2️⃣ Pages
  const pageFiles = paths.filter(p => /^src\/pages\/.+\.tsx$/.test(p));
  if (pageFiles.length === 0) errors.push('No pages found in src/pages/. At least one page component required.');

  const misplacedPages = paths.filter(p => /^src\/components\/(Home|Login|Dashboard|Profile|Settings|Workout|Exercise)\.tsx$/.test(p));
  if (misplacedPages.length > 0) errors.push(`Page components found in src/components/: ${misplacedPages.join(', ')}`);

  // 3️⃣ Shadcn UI components
  const uiFiles = ['src/lib/ui/button.tsx', 'src/lib/ui/card.tsx', 'src/lib/ui/input.tsx', 'src/lib/ui/label.tsx'];
  uiFiles.forEach(file => {
    if (!paths.includes(file)) warnings.push(`Recommended Shadcn UI file missing: ${file}`);
  });

  // 4️⃣ CSS
  if (!paths.includes('src/index.css')) warnings.push('Missing src/index.css.');

  // 5️⃣ main.tsx must import App
  const mainFile = fileTree.find(f => f.path === 'src/main.tsx');
  if (mainFile && !/import\s+App\s+from\s+['"].\/App['"]/.test(mainFile.code)) {
    warnings.push('src/main.tsx does not import App component.');
  }

  // 6️⃣ Check App usage of pages
  const appFile = fileTree.find(f => f.path === 'src/App.tsx');
  if (appFile) {
    pageFiles.forEach(pagePath => {
      const pageName = pagePath.split('/').pop()?.replace('.tsx', '');
      if (pageName && !appFile.code.includes(pageName)) {
        warnings.push(`Page ${pageName} exists but is not referenced in App.tsx.`);
      }
    });
  }

  // 7️⃣ Detect unused files (optional: non-entry, non-page, non-UI)
  const usedPaths = new Set<string>();
  // mark entry points
  usedPaths.add('src/main.tsx');
  usedPaths.add('src/App.tsx');
  pageFiles.forEach(p => usedPaths.add(p));
  uiFiles.forEach(p => usedPaths.add(p));
  ['src/index.css', 'index.html'].forEach(p => usedPaths.add(p));

  paths.forEach(p => {
    if (!usedPaths.has(p)) warnings.push(`File exists but may be unused: ${p}`);
  });

  // 8️⃣ Detect obvious missing imports in code files
  fileTree.forEach(f => {
    const importMatches = f.code.match(/import\s+.*\s+from\s+['"](.*)['"]/g) || [];
    importMatches.forEach((imp: string) => {
      const match = imp.match(/from\s+['"](.*)['"]/);
      if (match) {
        let importPath = match[1];
        if (!importPath.startsWith('.') && !importPath.startsWith('/')) return; // skip node_modules
        if (importPath.startsWith('.')) {
          // resolve relative to file
          const fileDir = f.path.split('/').slice(0, -1).join('/');
          const resolved = (fileDir ? fileDir + '/' : '') + importPath.replace(/^\.\//, '');
          const resolvedWithTsx = paths.find(p => p.startsWith(resolved));
          if (!resolvedWithTsx) {
            warnings.push(`File ${f.path} imports ${importPath} but resolved path not found.`);
          }
        }
      }
    });
  });

  return { valid: errors.length === 0, errors, warnings };
}
