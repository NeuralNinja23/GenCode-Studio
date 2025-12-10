// frontend/src/components/EnvironmentVariablesModal.tsx
import React, { useState, useEffect } from 'react';
import deploymentService from '../services/deploymentService';
import './EnvironmentVariablesModal.css';

interface EnvironmentVariablesModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void;
}

export const EnvironmentVariablesModal: React.FC<EnvironmentVariablesModalProps> = ({
  projectId,
  isOpen,
  onClose,
  onSave
}) => {
  const [environmentVars, setEnvironmentVars] = useState<Record<string, string>>({});
  const [envVarInput, setEnvVarInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showValues, setShowValues] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchEnvironmentVariables();
    }
  }, [isOpen, projectId]);

  const fetchEnvironmentVariables = async () => {
    try {
      setLoading(true);
      const response = await deploymentService.getEnvironmentVariables(projectId);
      setEnvironmentVars(response.environmentVars || {});
      setError('');
    } catch (err: any) {
      setError('Failed to load environment variables');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddEnvVar = () => {
    const [key, value] = envVarInput.split('=');
    if (key && value) {
      if (!/^[A-Z_][A-Z0-9_]*$/.test(key)) {
        setError('Key must be uppercase with underscores only');
        return;
      }
      setEnvironmentVars({ ...environmentVars, [key]: value });
      setEnvVarInput('');
      setError('');
    } else {
      setError('Invalid format. Use KEY=VALUE');
    }
  };

  const handleRemoveEnvVar = (key: string) => {
    const newVars = { ...environmentVars };
    delete newVars[key];
    setEnvironmentVars(newVars);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await deploymentService.updateEnvironmentVariables(projectId, environmentVars);
      setError('');
      onSave?.();
      onClose();
    } catch (err: any) {
      setError('Failed to update environment variables');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="env-vars-modal-overlay">
      <div className="env-vars-modal">
        <div className="env-vars-modal-header">
          <h2>🔐 Environment Variables</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="env-vars-modal-content">
          {loading ? (
            <div className="loading">Loading environment variables...</div>
          ) : (
            <>
              <div className="show-values-toggle">
                <input
                  type="checkbox"
                  id="show-values"
                  checked={showValues}
                  onChange={(e) => setShowValues(e.target.checked)}
                />
                <label htmlFor="show-values">Show Values</label>
              </div>

              {error && <div className="error-message">{error}</div>}

              <div className="form-group">
                <label>Add New Variable</label>
                <div className="env-var-input-group">
                  <input
                    type="text"
                    placeholder="KEY=VALUE"
                    value={envVarInput}
                    onChange={(e) => setEnvVarInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddEnvVar()}
                  />
                  <button onClick={handleAddEnvVar}>Add</button>
                </div>
                <small>Format: UPPERCASE_KEY=value (keys must be uppercase)</small>
              </div>

              <div className="form-group">
                <label>Current Variables ({Object.keys(environmentVars).length})</label>
                <div className="env-vars-list">
                  {Object.keys(environmentVars).length === 0 ? (
                    <p className="no-vars">No environment variables configured</p>
                  ) : (
                    Object.entries(environmentVars).map(([key, value]) => (
                      <div key={key} className="env-var-item encrypted">
                        <div className="env-var-content">
                          <span className="env-var-key">{key}</span>
                          <span className="env-var-value">
                            {showValues ? value : '••••••••'}
                          </span>
                          <span className="encryption-badge">🔒 Encrypted</span>
                        </div>
                        <button
                          className="remove-btn"
                          onClick={() => handleRemoveEnvVar(key)}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="security-notice">
                <p>🔒 All environment variables are encrypted at-rest and never logged.</p>
              </div>
            </>
          )}
        </div>

        <div className="env-vars-modal-footer">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={handleSave}
            className="btn-primary"
            disabled={saving || loading}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnvironmentVariablesModal;
