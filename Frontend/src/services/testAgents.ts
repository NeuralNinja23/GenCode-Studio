// Stubs to mirror GenCode Studio testing agent hooks (frontend side)
export type QAIssue = { file: string; line?: number; severity: 'low'|'medium'|'high'; description: string; suggested_fix?: string };
export type TestReport = { passed: boolean; summary: string; issues: QAIssue[] };

export async function invokeFrontendTester(context: { contract: string; backendReport: TestReport; files: { path: string; code: string }[] }): Promise<TestReport> {
  // Placeholder stub; backend orchestrates real testing. This simply returns a pass.
  return { passed: true, summary: 'Stub frontend tester pass.', issues: [] };
}

export async function invokeBackendTester(context: { contract: string; files: { path: string; code: string }[] }): Promise<TestReport> {
  // Placeholder stub; backend orchestrates real testing. This simply returns a pass.
  return { passed: true, summary: 'Stub backend tester pass.', issues: [] };
}

