// frontend/src/components/FileTree.tsx
import React, { useState } from 'react';
import { FileTreeNode } from '../types';

// File type icon colors
const getFileIconColor = (name: string): string => {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  const colors: Record<string, string> = {
    ts: '#3178c6',
    tsx: '#3178c6',
    js: '#f7df1e',
    jsx: '#61dafb',
    css: '#264de4',
    scss: '#cd6799',
    html: '#e34f26',
    json: '#cbcb41',
    md: '#083fa1',
    py: '#3776ab',
    yml: '#cb171e',
    yaml: '#cb171e',
    env: '#ecd53f',
    gitignore: '#f14e32',
    dockerfile: '#2496ed',
    svg: '#ffb13b',
    png: '#a4c639',
    jpg: '#a4c639',
  };
  return colors[ext] || '#6b7280';
};

// Get file icon based on extension
const FileIcon = ({ name }: { name: string }) => {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  const color = getFileIconColor(name);

  // TypeScript/JavaScript
  if (['ts', 'tsx', 'js', 'jsx'].includes(ext)) {
    return (
      <div className="w-4 h-4 rounded-sm flex items-center justify-center text-[8px] font-bold"
        style={{ backgroundColor: color, color: ext.includes('ts') ? 'white' : 'black' }}>
        {ext.toUpperCase().slice(0, 2)}
      </div>
    );
  }

  // Default file icon
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
};

// Folder icon with open/closed state
const FolderIcon = ({ isOpen }: { isOpen: boolean }) => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill={isOpen ? "#fbbf24" : "none"}
    stroke="#fbbf24" strokeWidth="2">
    {isOpen ? (
      <path d="M5 19a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4.586a1 1 0 0 1 .707.293L12 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5zM5 8v9h15l-2-9H5z" />
    ) : (
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L8.6 3.3A2 2 0 0 0 6.9 2H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2Z" />
    )}
  </svg>
);

// Chevron icon for folder expand/collapse
const ChevronIcon = ({ isOpen }: { isOpen: boolean }) => (
  <svg
    className={`w-3 h-3 text-zinc-500 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="m9 18 6-6-6-6" />
  </svg>
);

interface FileTreeItemProps {
  node: FileTreeNode;
  onSelectFile: (path: string) => void;
  selectedFile: string | null;
  depth?: number;
}

const FileTreeItem: React.FC<FileTreeItemProps> = ({
  node,
  onSelectFile,
  selectedFile,
  depth = 0
}) => {
  const [isOpen, setIsOpen] = useState(depth < 2); // Auto-expand first 2 levels
  const isFolder = node.type === 'folder';
  const isSelected = node.path === selectedFile;
  const hasChildren = node.children && node.children.length > 0;

  const handleClick = () => {
    if (isFolder) {
      setIsOpen(!isOpen);
    } else {
      onSelectFile(node.path);
    }
  };

  return (
    <li className="select-none">
      <div
        onClick={handleClick}
        className={`
          group flex items-center gap-1.5 px-2 py-1 rounded-md text-sm cursor-pointer
          transition-all duration-150 ease-out
          ${isSelected
            ? 'bg-gradient-to-r from-purple-600/30 to-purple-500/20 text-white ring-1 ring-purple-500/50'
            : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
          }
        `}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {/* Expand/collapse chevron for folders */}
        {isFolder && hasChildren && (
          <ChevronIcon isOpen={isOpen} />
        )}
        {isFolder && !hasChildren && (
          <span className="w-3" />
        )}

        {/* File/folder icon */}
        <span className="flex-shrink-0">
          {isFolder ? <FolderIcon isOpen={isOpen} /> : <FileIcon name={node.name} />}
        </span>

        {/* File/folder name */}
        <span className={`truncate ${isSelected ? 'font-medium' : ''}`}>
          {node.name}
        </span>

        {/* Subtle glow effect on hover for files */}
        {!isFolder && !isSelected && (
          <span className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
            <svg className="w-3 h-3 text-zinc-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </span>
        )}
      </div>

      {/* Children */}
      {isFolder && hasChildren && isOpen && (
        <ul className="relative">
          {/* Vertical line connecting children */}
          <div
            className="absolute left-0 top-0 bottom-2 w-px bg-zinc-800"
            style={{ marginLeft: `${depth * 12 + 16}px` }}
          />
          {node.children!
            .sort((a, b) => {
              if (a.type === 'folder' && b.type === 'file') return -1;
              if (a.type === 'file' && b.type === 'folder') return 1;
              return a.name.localeCompare(b.name);
            })
            .map(child => (
              <FileTreeItem
                key={child.path}
                node={child}
                onSelectFile={onSelectFile}
                selectedFile={selectedFile}
                depth={depth + 1}
              />
            ))}
        </ul>
      )}
    </li>
  );
};

interface FileTreeProps {
  nodes: FileTreeNode[];
  onSelectFile: (path: string) => void;
  selectedFile: string | null;
}

export const FileTree: React.FC<FileTreeProps> = ({ nodes, onSelectFile, selectedFile }) => {
  const sortedNodes = [...nodes].sort((a, b) => {
    if (a.type === 'folder' && b.type === 'file') return -1;
    if (a.type === 'file' && b.type === 'folder') return 1;
    return a.name.localeCompare(b.name);
  });

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-zinc-500">
        <svg className="w-12 h-12 mb-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L8.6 3.3A2 2 0 0 0 6.9 2H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2Z" />
        </svg>
        <p className="text-sm">No files yet</p>
        <p className="text-xs text-zinc-600 mt-1">Files will appear here after generation</p>
      </div>
    );
  }

  return (
    <ul className="space-y-0.5">
      {sortedNodes.map(node => (
        <FileTreeItem
          key={node.path}
          node={node}
          onSelectFile={onSelectFile}
          selectedFile={selectedFile}
        />
      ))}
    </ul>
  );
};
