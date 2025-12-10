import { useState, useCallback } from 'react';
import { getWorkspaceFiles, getFileContent } from '../services/agentService';

export interface FileTreeNode {
    name: string;
    path: string;
    type: 'file' | 'directory';
    children?: FileTreeNode[];
}

export const useFileTree = (projectId: string | undefined) => {
    const [fileTree, setFileTree] = useState<FileTreeNode[]>([]);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [selectedFileContent, setSelectedFileContent] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchFileTree = useCallback(async () => {
        if (!projectId) return;

        setIsLoading(true);
        setError(null);

        try {
            const data = await getWorkspaceFiles(projectId);
            setFileTree(data as FileTreeNode[]);
        } catch (err) {
            console.error('File tree error:', err);
            setError('Failed to load file tree');
        } finally {
            setIsLoading(false);
        }
    }, [projectId]);

    const fetchFileContent = useCallback(async (filePath: string) => {
        if (!projectId) return;

        setIsLoading(true);
        setError(null);

        try {
            const content = await getFileContent(projectId, filePath);
            setSelectedFileContent(content);
            setSelectedFile(filePath);
        } catch (err) {
            console.error('File content error:', err);
            setError('Failed to load file content');
            setSelectedFileContent('');
        } finally {
            setIsLoading(false);
        }
    }, [projectId]);

    const selectFile = useCallback((filePath: string) => {
        fetchFileContent(filePath);
    }, [fetchFileContent]);

    return {
        fileTree,
        selectedFile,
        selectedFileContent,
        isLoading,
        error,
        fetchFileTree,
        selectFile,
        refreshFileTree: fetchFileTree,
    };
};
