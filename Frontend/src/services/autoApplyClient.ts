// frontend/src/services/autoApplyClient.ts
const BACKEND_URL = (import.meta as any).env?.VITE_BACKEND_URL || (import.meta as any).env?.REACT_APP_BACKEND_URL || '';
const BASE = BACKEND_URL ? `${BACKEND_URL.replace(/\/$/, '')}/api/workspace` : '/api/workspace';

export async function applyInstruction(
  projectId: string,
  instruction: string
): Promise<{ success: boolean; applied: number; changedFiles: { path: string }[]; rationale?: string }> {
  const r = await fetch(`${BASE}/apply/${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instruction }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ message: 'Apply failed' }));
    throw new Error(err.message);
  }
  return r.json();
}
