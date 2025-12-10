// frontend/src/components/LogsViewerModal.tsx
import React, { useState, useEffect, useRef } from 'react';
import deploymentService from '../services/deploymentService';
import './LogsViewerModal.css';

interface LogsViewerModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

type LogLevel = 'ALL' | 'INFO' | 'WARNING' | 'ERROR';

export const LogsViewerModal: React.FC<LogsViewerModalProps> = ({
  projectId,
  isOpen,
  onClose
}) => {
  const [logs, setLogs] = useState('');
  const [filteredLogs, setFilteredLogs] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel>('ALL');
  const [searchText, setSearchText] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
      const interval = setInterval(fetchLogs, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [isOpen, projectId]);

  useEffect(() => {
    filterLogs(logs, logLevel, searchText);
  }, [logs, logLevel, searchText]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  const fetchLogs = async () => {
    try {
      const response = await deploymentService.getDeploymentLogs(projectId);
      const allLogs = `${response.buildLogs || ''}\n${response.deploymentLogs || ''}`;
      setLogs(allLogs);
      setError('');
    } catch (err: any) {
      setError('Failed to load logs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filterLogs = (fullLogs: string, level: LogLevel, search: string) => {
    let filtered = fullLogs;

    // Filter by log level
    if (level !== 'ALL') {
      const lines = filtered.split('\n');
      const levelKeyword = `[${level}]`;
      filtered = lines
        .filter(line => line.includes(levelKeyword) || line.includes(`[${level}]`))
        .join('\n');
    }

    // Filter by search text
    if (search.trim()) {
      const lines = filtered.split('\n');
      filtered = lines
        .filter(line => line.toLowerCase().includes(search.toLowerCase()))
        .join('\n');
    }

    setFilteredLogs(filtered);
  };

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(filteredLogs);
  };

  const handleDownloadLogs = async () => {
    try {
      const fileBlob = await deploymentService.downloadLogs(projectId);
      const url = window.URL.createObjectURL(fileBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `deployment-${projectId}-logs.txt`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch (err: any) {
      setError('Failed to download logs');
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="logs-viewer-modal-overlay">
      <div className="logs-viewer-modal">
        <div className="logs-viewer-modal-header">
          <h2>📋 Deployment Logs</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="logs-viewer-toolbar">
          <div className="toolbar-group">
            <label htmlFor="log-level">Log Level:</label>
            <select
              id="log-level"
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value as LogLevel)}
            >
              <option value="ALL">All Levels</option>
              <option value="INFO">Info Only</option>
              <option value="WARNING">Warnings</option>
              <option value="ERROR">Errors Only</option>
            </select>
          </div>

          <div className="toolbar-group">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="toolbar-group">
            <label>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
          </div>

          <div className="toolbar-actions">
            <button onClick={handleCopyLogs} className="btn-action">
              📋 Copy All
            </button>
            <button onClick={handleDownloadLogs} className="btn-action">
              ⬇️ Download
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="logs-viewer-content">
          {loading && <div className="loading">Loading logs...</div>}
          {!loading && (
            <div className="logs-display">
              <pre className="logs-text">
                {filteredLogs || 'No logs available'}
                <div ref={logsEndRef} />
              </pre>
            </div>
          )}
        </div>

        <div className="logs-viewer-footer">
          <span className="log-count">
            Showing {filteredLogs.split('\n').filter(l => l.trim()).length} of{' '}
            {logs.split('\n').filter(l => l.trim()).length} log lines
          </span>
          <button onClick={onClose} className="btn-primary">Close</button>
        </div>
      </div>
    </div>
  );
};

export default LogsViewerModal;
