// frontend/src/components/CodeView.tsx
import React, { useMemo } from "react";
import { FileTree } from "./FileTree";
import CodeMirror from "@uiw/react-codemirror";
import { javascript } from "@codemirror/lang-javascript";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { FileTreeNode } from "../types";
import { SearchIcon, SaveIcon, FolderIcon } from "./Icons";

interface CodeViewProps {
  fileTree: FileTreeNode[];
  selectedFile: string | null;
  fileContent: string;
  onContentChange: (newContent: string) => void;
  onSelectFile: (filePath: string) => void;
}

// Get appropriate language extension based on file extension
const getLanguageExtension = (filename: string | null) => {
  if (!filename) return javascript({ jsx: true, typescript: true });

  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const isTypeScript = ext === 'ts' || ext === 'tsx';
  return javascript({ jsx: true, typescript: isTypeScript });
};

// Get file icon color
const getFileIconColor = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const colors: Record<string, string> = {
    ts: '#3178c6',
    tsx: '#3178c6',
    js: '#f7df1e',
    jsx: '#61dafb',
    css: '#264de4',
    py: '#3776ab',
    json: '#cbcb41',
    html: '#e34f26',
    md: '#083fa1',
  };
  return colors[ext] || '#6b7280';
};

const CodeView: React.FC<CodeViewProps> = ({
  fileTree,
  selectedFile,
  fileContent,
  onContentChange,
  onSelectFile,
}) => {
  const languageExtension = useMemo(
    () => getLanguageExtension(selectedFile),
    [selectedFile]
  );

  const fileName = selectedFile?.split('/').pop() || selectedFile?.split('\\').pop() || '';
  const fileIconColor = selectedFile ? getFileIconColor(selectedFile) : '#6b7280';

  return (
    <div className="flex h-full bg-zinc-950">
      {/* Sidebar - File Explorer */}
      <div className="w-64 flex flex-col border-r border-zinc-800/80 bg-zinc-900/50">
        {/* Sidebar Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800/80">
          <div className="flex items-center gap-2">
            <FolderIcon className="w-4 h-4 text-purple-400" />
            <h2 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
              Explorer
            </h2>
          </div>
          <button
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Search files"
          >
            <SearchIcon className="w-4 h-4" />
          </button>
        </div>

        {/* File Tree */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 custom-scrollbar">
          <FileTree
            nodes={fileTree}
            onSelectFile={onSelectFile}
            selectedFile={selectedFile}
          />
        </div>

        {/* Sidebar Footer - Stats */}
        {fileTree.length > 0 && (
          <div className="px-4 py-2 border-t border-zinc-800/80 text-xs text-zinc-600">
            {countFiles(fileTree)} files
          </div>
        )}
      </div>

      {/* Editor Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedFile ? (
          <>
            {/* Editor Header - Tab Bar */}
            <div className="flex items-center justify-between bg-zinc-900/80 border-b border-zinc-800/80">
              <div className="flex items-center">
                {/* Active Tab */}
                <div className="flex items-center gap-2 px-4 py-2 bg-zinc-950 border-r border-zinc-800/80 text-zinc-200">
                  {/* File type indicator dot */}
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: fileIconColor }}
                  />
                  <span className="text-sm font-medium">{fileName}</span>
                  {/* Close button */}
                  <button className="ml-2 p-0.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors">
                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Editor Actions */}
              <div className="flex items-center gap-1 px-3">
                <button
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
                             bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400
                             text-white shadow-lg shadow-purple-500/20 transition-all duration-200"
                  title="Save file (Ctrl+S)"
                >
                  <SaveIcon className="w-3.5 h-3.5" />
                  <span>Save</span>
                </button>
              </div>
            </div>

            {/* Breadcrumb Path */}
            <div className="flex items-center px-4 py-1.5 bg-zinc-900/40 border-b border-zinc-800/50 text-xs text-zinc-500">
              {selectedFile.split(/[/\\]/).map((part, index, arr) => (
                <React.Fragment key={index}>
                  <span className={index === arr.length - 1 ? 'text-zinc-300' : 'hover:text-zinc-400 cursor-pointer'}>
                    {part}
                  </span>
                  {index < arr.length - 1 && (
                    <svg className="w-3 h-3 mx-1 text-zinc-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="m9 18 6-6-6-6" />
                    </svg>
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Code Editor */}
            <div className="flex-1 overflow-hidden">
              <CodeMirror
                value={fileContent}
                height="100%"
                extensions={[languageExtension]}
                onChange={onContentChange}
                theme={vscodeDark}
                style={{ height: "100%", fontSize: "13px" }}
                basicSetup={{
                  lineNumbers: true,
                  highlightActiveLineGutter: true,
                  highlightActiveLine: true,
                  foldGutter: true,
                  autocompletion: true,
                  bracketMatching: true,
                  closeBrackets: true,
                  indentOnInput: true,
                }}
              />
            </div>

            {/* Status Bar */}
            <div className="flex items-center justify-between px-4 py-1 bg-zinc-900/80 border-t border-zinc-800/80 text-xs text-zinc-500">
              <div className="flex items-center gap-4">
                <span>UTF-8</span>
                <span>{getLanguageName(selectedFile)}</span>
              </div>
              <div className="flex items-center gap-4">
                <span>Ln 1, Col 1</span>
                <span>Spaces: 2</span>
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 bg-gradient-to-b from-zinc-950 to-zinc-900">
            <div className="relative">
              {/* Decorative background */}
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600/10 to-blue-600/10 blur-3xl rounded-full scale-150" />

              {/* Icon */}
              <div className="relative p-6 rounded-2xl bg-zinc-900/80 border border-zinc-800/80 shadow-2xl">
                <svg className="w-16 h-16 text-zinc-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
              </div>
            </div>

            <h3 className="mt-6 text-lg font-medium text-zinc-400">No file selected</h3>
            <p className="mt-2 text-sm text-zinc-600 max-w-xs text-center">
              Select a file from the explorer to view and edit its content
            </p>

            {/* Keyboard shortcut hint */}
            <div className="mt-6 flex items-center gap-2 text-xs text-zinc-600">
              <kbd className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono">Ctrl</kbd>
              <span>+</span>
              <kbd className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono">P</kbd>
              <span className="ml-2">Quick open</span>
            </div>
          </div>
        )}
      </div>

      {/* Custom scrollbar styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(113, 113, 122, 0.3);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(113, 113, 122, 0.5);
        }
      `}</style>
    </div>
  );
};

// Helper function to count files
function countFiles(nodes: FileTreeNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.type === 'file') {
      count++;
    } else if (node.children) {
      count += countFiles(node.children);
    }
  }
  return count;
}

// Helper function to get language name
function getLanguageName(filename: string | null): string {
  if (!filename) return 'Plain Text';
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const languages: Record<string, string> = {
    ts: 'TypeScript',
    tsx: 'TypeScript React',
    js: 'JavaScript',
    jsx: 'JavaScript React',
    py: 'Python',
    css: 'CSS',
    scss: 'SCSS',
    html: 'HTML',
    json: 'JSON',
    md: 'Markdown',
    yml: 'YAML',
    yaml: 'YAML',
  };
  return languages[ext] || 'Plain Text';
}

export default CodeView;
