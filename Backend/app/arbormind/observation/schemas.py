# app/arbormind/observation/schemas.py
"""
ArborMind SQLite Schemas - Ground Truth Execution Memory

INVARIANT: This is APPEND-ONLY telemetry, not intelligence.
INVARIANT: No reads during execution (except Phase 5 executive reads).
INVARIANT: No prompts or embeddings stored.
"""

SCHEMA_VERSION = 4  # v4: Added step_state_snapshots (SSS)

SCHEMAS = {
    # ═══════════════════════════════════════════════════════════════════
    # 🧠 RUNS - Top-level workflow executions
    # ═══════════════════════════════════════════════════════════════════
    "runs": """
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            started_at DATETIME NOT NULL,
            finished_at DATETIME,
            status TEXT,               -- pending | success | failure | aborted
            archetype TEXT,
            domain TEXT,
            user_request TEXT,
            entropy REAL,
            total_steps INTEGER DEFAULT 0,
            completed_steps INTEGER DEFAULT 0,
            failed_steps INTEGER DEFAULT 0
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 🌿 BRANCHES - Reasoning tree branches
    # ═══════════════════════════════════════════════════════════════════
    "branches": """
        CREATE TABLE IF NOT EXISTS branches (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            parent_id TEXT,
            step_name TEXT,
            depth INTEGER DEFAULT 0,
            entropy REAL,
            attention REAL,
            status TEXT,               -- active | pruned | healed | dormant | completed
            convergence_state TEXT,    -- progress | converging | stalled | diverging | terminal
            created_at DATETIME NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 🔀 DECISIONS - Proto-V vectors (KEY TABLE for future learning)
    # ═══════════════════════════════════════════════════════════════════
    "decisions": """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            branch_id TEXT,
            step TEXT NOT NULL,        -- architecture | frontend_mock | backend | ...
            agent TEXT,                -- Marcus | Derek | Victoria | Luna
            action TEXT NOT NULL,      -- RUN_TOOL | HEAL | MUTATE | STOP
            tool TEXT,                 -- Tool selected (if RUN_TOOL)
            reason TEXT,               -- invariant_violation | entropy_high | approved | ...
            outcome TEXT,              -- success | failure | pending
            confidence REAL,
            entropy REAL,
            duration_ms INTEGER,       -- Execution duration
            artifacts_count INTEGER,   -- Number of artifacts produced
            created_at DATETIME NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 📁 ARTIFACTS - Now with LINEAGE BINDING
    # ═══════════════════════════════════════════════════════════════════
    "artifacts": """
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT UNIQUE,   -- Unique content-based ID
            run_id TEXT NOT NULL,
            
            -- LINEAGE BINDING: Branch
            branch_id TEXT,            -- Branch that produced this
            branch_depth INTEGER,      -- Depth at creation
            
            -- LINEAGE BINDING: Action
            step TEXT NOT NULL,
            action_type TEXT,          -- generate | improve | repair | validate | integrate
            decision_id INTEGER,       -- Link to decisions table
            
            -- LINEAGE BINDING: Agent
            agent_name TEXT,           -- Derek | Victoria | Luna | Marcus
            
            -- Artifact identity
            path TEXT NOT NULL,
            size_bytes INTEGER,
            checksum TEXT,
            
            -- Lineage chain
            lineage_type TEXT,         -- generated | modified | healed | mutated | merged
            parent_artifact_id TEXT,   -- For modified artifacts
            
            -- Context at creation
            entropy_at_creation REAL,
            convergence_state TEXT,
            
            -- Approval status
            approved BOOLEAN DEFAULT 0,
            rejection_reason TEXT,
            
            created_at DATETIME NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id),
            FOREIGN KEY(decision_id) REFERENCES decisions(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 🚨 FAILURES - Learning gold for future healing
    # ═══════════════════════════════════════════════════════════════════
    "failures": """
        CREATE TABLE IF NOT EXISTS failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            branch_id TEXT,
            step TEXT NOT NULL,
            agent TEXT,
            failure_type TEXT,         -- invariant | truncation | quality | timeout | exception
            severity TEXT,             -- fatal | non_fatal (Phase 2)
            message TEXT,
            stack_trace TEXT,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 👁️ SUPERVISOR_VERDICTS - Preference shaping data
    # ═══════════════════════════════════════════════════════════════════
    "supervisor_verdicts": """
        CREATE TABLE IF NOT EXISTS supervisor_verdicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            step TEXT NOT NULL,
            agent TEXT NOT NULL,       -- The agent that produced output (Derek, Victoria)
            supervisor TEXT,           -- The supervisor (Marcus)
            verdict TEXT NOT NULL,     -- approved | rejected
            quality_score REAL,
            rejection_reasons TEXT,    -- JSON array of reasons
            files_count INTEGER,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 🔧 TOOL_INVOCATIONS (TIT) - Tool Invocation Trace (v3)
    # ═══════════════════════════════════════════════════════════════════
    "tool_invocations": """
        CREATE TABLE IF NOT EXISTS tool_invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Lineage
            run_id TEXT NOT NULL,
            branch_id TEXT,
            decision_id INTEGER,
            step TEXT NOT NULL,
            agent TEXT NOT NULL,
            
            -- Tool identity
            tool_name TEXT NOT NULL,
            tool_type TEXT NOT NULL,
            
            -- Invocation context
            invocation_index INTEGER,
            called_at DATETIME NOT NULL,
            duration_ms INTEGER,
            
            -- Raw I/O (truncated, forensic only)
            input_summary TEXT,
            output_summary TEXT,
            
            -- Result
            status TEXT NOT NULL,      -- success | failure | timeout | aborted
            error_type TEXT,
            error_message TEXT,
            
            -- Resource signals
            tokens_used INTEGER,
            model_name TEXT,
            retries INTEGER DEFAULT 0,
            
            -- Integrity
            schema_version INTEGER DEFAULT 1,
            
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(decision_id) REFERENCES decisions(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 📸 STEP_STATE_SNAPSHOTS (SSS) - Workspace State Capture (v4)
    # Phase 3 Primitive: Pure observation, no semantics
    # ═══════════════════════════════════════════════════════════════════
    "step_state_snapshots": """
        CREATE TABLE IF NOT EXISTS step_state_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Position in execution
            run_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            position TEXT NOT NULL,    -- entry | exit
            timestamp DATETIME NOT NULL,
            
            -- Artifact inventory
            artifact_count INTEGER NOT NULL,
            artifact_paths_hash TEXT,  -- SHA256 of sorted paths
            artifact_manifest TEXT,    -- JSON: [{path, size_bytes}]
            
            -- Workspace fingerprint
            workspace_hash TEXT,       -- Hash of full workspace tree
            
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    """,
    
    # ═══════════════════════════════════════════════════════════════════
    # 📊 SCHEMA_INFO - Version tracking
    # ═══════════════════════════════════════════════════════════════════
    "schema_info": """
        CREATE TABLE IF NOT EXISTS schema_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """,
}

# Indexes for efficient queries (offline learning)
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_branches_run ON branches(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_decisions_run ON decisions(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_decisions_step ON decisions(step)",
    "CREATE INDEX IF NOT EXISTS idx_decisions_outcome ON decisions(outcome)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_failures_run ON failures(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_failures_type ON failures(failure_type)",
    "CREATE INDEX IF NOT EXISTS idx_verdicts_run ON supervisor_verdicts(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_verdicts_verdict ON supervisor_verdicts(verdict)",
    # LINEAGE INDEXES
    "CREATE INDEX IF NOT EXISTS idx_artifacts_branch ON artifacts(branch_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_agent ON artifacts(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_action ON artifacts(action_type)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_lineage ON artifacts(lineage_type)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_parent ON artifacts(parent_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_branches_convergence ON branches(convergence_state)",
    # TIT INDEXES (v3)
    "CREATE INDEX IF NOT EXISTS idx_tit_run_id ON tool_invocations(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_tit_step ON tool_invocations(step)",
    "CREATE INDEX IF NOT EXISTS idx_tit_tool_name ON tool_invocations(tool_name)",
    "CREATE INDEX IF NOT EXISTS idx_tit_status ON tool_invocations(status)",
    # SSS INDEXES (v4)
    "CREATE INDEX IF NOT EXISTS idx_sss_run_id ON step_state_snapshots(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_sss_step ON step_state_snapshots(step_name)",
    "CREATE INDEX IF NOT EXISTS idx_sss_position ON step_state_snapshots(position)",
]

