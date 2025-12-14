#!/usr/bin/env python3
"""
ArborMind Comprehensive Metrics Viewer

Displays HONEST metrics including:
1. Pipeline-level success/failure rates
2. Per-step success rates
3. Routing decision outcomes
4. Failure analysis

Usage:
    python scripts/view_metrics.py
"""
import sqlite3
from pathlib import Path

# Construct paths directly to avoid import dependencies
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
ARBORMIND_STORAGE_DIR = BACKEND_ROOT / "data" / "arbormind"

V_VECTOR_DB_PATH = ARBORMIND_STORAGE_DIR / "v_vector_history.db"
METRICS_DB_PATH = ARBORMIND_STORAGE_DIR / "arbormind_metrics.db"
PIPELINE_DB_PATH = ARBORMIND_STORAGE_DIR / "pipeline_metrics.db"


def get_pipeline_stats():
    """Get overall pipeline run statistics."""
    if not PIPELINE_DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(PIPELINE_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Total runs
    c.execute("SELECT COUNT(*) FROM pipeline_runs")
    total_runs = c.fetchone()[0]
    
    # Completed runs with outcomes
    c.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as succeeded,
            SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
            AVG(CASE WHEN status = 'success' THEN duration_seconds END) as avg_success_duration,
            AVG(total_steps_succeeded) as avg_steps_succeeded
        FROM pipeline_runs
    """)
    row = c.fetchone()
    
    # By archetype
    c.execute("""
        SELECT archetype, 
               COUNT(*) as total,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as succeeded,
               SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) as failed
        FROM pipeline_runs
        WHERE status IN ('success', 'failure')
        GROUP BY archetype
        ORDER BY total DESC
        LIMIT 10
    """)
    archetype_stats = c.fetchall()
    
    # Recent runs (last 10)
    c.execute("""
        SELECT run_id, archetype, status, final_step, 
               total_steps_succeeded, duration_seconds, error_message
        FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT 10
    """)
    recent_runs = c.fetchall()
    
    conn.close()
    
    completed = (row["succeeded"] or 0) + (row["failed"] or 0)
    
    return {
        "total_runs": total_runs,
        "completed": completed,
        "succeeded": row["succeeded"] or 0,
        "failed": row["failed"] or 0,
        "running": row["running"] or 0,
        "success_rate": (row["succeeded"] or 0) / completed if completed > 0 else 0.0,
        "avg_success_duration": row["avg_success_duration"],
        "avg_steps_succeeded": row["avg_steps_succeeded"],
        "archetype_stats": archetype_stats,
        "recent_runs": recent_runs,
    }


def get_step_stats():
    """Get per-step success metrics."""
    if not PIPELINE_DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(PIPELINE_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT step_name,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as succeeded,
               SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN healed = 1 THEN 1 ELSE 0 END) as healed,
               AVG(attempts) as avg_attempts,
               AVG(duration_seconds) as avg_duration
        FROM step_outcomes
        WHERE status IN ('success', 'failure')
        GROUP BY step_name
        ORDER BY 
            CASE step_name 
                WHEN 'analysis' THEN 1
                WHEN 'architecture' THEN 2
                WHEN 'frontend_mock' THEN 3
                WHEN 'contracts' THEN 4
                WHEN 'backend_implementation' THEN 5
                WHEN 'system_integration' THEN 6
                WHEN 'testing_backend' THEN 7
                WHEN 'frontend_integration' THEN 8
                WHEN 'testing_frontend' THEN 9
                WHEN 'preview_final' THEN 10
                ELSE 99
            END
    """)
    step_stats = c.fetchall()
    
    conn.close()
    return step_stats


def get_failure_analysis():
    """Get analysis of where pipelines fail most often."""
    if not PIPELINE_DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(PIPELINE_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Which steps fail most
    c.execute("""
        SELECT step_name, error_type, 
               COUNT(*) as failure_count,
               GROUP_CONCAT(SUBSTR(error_message, 1, 50), ' | ') as sample_errors
        FROM step_outcomes
        WHERE status = 'failure'
        GROUP BY step_name, error_type
        ORDER BY failure_count DESC
        LIMIT 15
    """)
    failures = c.fetchall()
    
    # Final step when pipeline fails
    c.execute("""
        SELECT final_step, COUNT(*) as count
        FROM pipeline_runs
        WHERE status = 'failure'
        GROUP BY final_step
        ORDER BY count DESC
        LIMIT 10
    """)
    failure_points = c.fetchall()
    
    conn.close()
    return {"step_failures": failures, "failure_points": failure_points}


def get_routing_stats():
    """Get routing metrics summary from database."""
    if not METRICS_DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(METRICS_DB_PATH)
    c = conn.cursor()
    
    # Total decisions
    c.execute("SELECT COUNT(*) FROM routing_metrics")
    total = c.fetchone()[0]
    
    # Success rate
    c.execute("SELECT AVG(success) FROM routing_metrics")
    success_rate = c.fetchone()[0] or 0.0
    
    # Average retry count
    c.execute("SELECT AVG(retry_count) FROM routing_metrics")
    avg_retries = c.fetchone()[0] or 0.0
    
    # T-AM usage and impact
    c.execute("SELECT COUNT(*) FROM routing_metrics WHERE used_tam = 1")
    tam_count = c.fetchone()[0]
    
    c.execute("SELECT AVG(success) FROM routing_metrics WHERE used_tam = 1")
    tam_success_rate = c.fetchone()[0] or 0.0
    
    c.execute("SELECT AVG(success) FROM routing_metrics WHERE used_tam = 0")
    no_tam_success_rate = c.fetchone()[0] or 0.0
    
    # By archetype
    c.execute("""
        SELECT archetype, COUNT(*) as count, AVG(success) as success_rate
        FROM routing_metrics
        GROUP BY archetype
        ORDER BY count DESC
        LIMIT 5
    """)
    archetype_stats = c.fetchall()
    
    # By context type
    c.execute("""
        SELECT context_type, COUNT(*) as count, AVG(success) as success_rate
        FROM routing_metrics
        GROUP BY context_type
        ORDER BY count DESC
        LIMIT 5
    """)
    context_stats = c.fetchall()
    
    conn.close()
    
    return {
        "total_decisions": total,
        "success_rate": success_rate,
        "avg_retry_count": avg_retries,
        "tam_usage_count": tam_count,
        "tam_success_rate": tam_success_rate,
        "no_tam_success_rate": no_tam_success_rate,
        "tam_impact": tam_success_rate - no_tam_success_rate if tam_count > 0 else 0.0,
        "archetype_stats": archetype_stats,
        "context_stats": context_stats,
    }


def get_v_vector_stats():
    """Get V-Vector learning statistics."""
    if not V_VECTOR_DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(V_VECTOR_DB_PATH)
    c = conn.cursor()
    
    # Total decisions recorded
    c.execute("SELECT COUNT(*) FROM decisions")
    total_decisions = c.fetchone()[0]
    
    # Decisions with outcomes
    c.execute("SELECT COUNT(*) FROM decisions WHERE outcome IS NOT NULL")
    decisions_with_outcomes = c.fetchone()[0]
    
    # Evolved vectors
    c.execute("SELECT COUNT(*) FROM evolved_vectors")
    evolved_count = c.fetchone()[0]
    
    # Average success rate of evolved vectors
    c.execute("SELECT AVG(success_rate) FROM evolved_vectors")
    avg_success_rate = c.fetchone()[0] or 0.0
    
    # Average confidence
    c.execute("SELECT AVG(confidence) FROM evolved_vectors")
    avg_confidence = c.fetchone()[0] or 0.0
    
    # Top performing evolved vectors
    c.execute("""
        SELECT context_key, success_rate, sample_count, confidence
        FROM evolved_vectors
        ORDER BY success_rate * confidence DESC
        LIMIT 5
    """)
    top_vectors = c.fetchall()
    
    # By context type
    c.execute("""
        SELECT SUBSTR(context_key, 1, INSTR(context_key || ':', ':') - 1) as context_type,
               COUNT(*) as count,
               AVG(success_rate) as avg_success
        FROM evolved_vectors
        GROUP BY context_type
        ORDER BY count DESC
        LIMIT 5
    """)
    context_breakdown = c.fetchall()
    
    conn.close()
    
    return {
        "total_decisions": total_decisions,
        "decisions_with_outcomes": decisions_with_outcomes,
        "evolved_vectors": evolved_count,
        "avg_success_rate": avg_success_rate,
        "avg_confidence": avg_confidence,
        "coverage": decisions_with_outcomes / max(1, total_decisions),
        "top_vectors": top_vectors,
        "context_breakdown": context_breakdown,
    }


def main():
    print("=" * 70)
    print("🌳 ARBORMIND COMPREHENSIVE METRICS")
    print("=" * 70)
    
    pipeline_stats = get_pipeline_stats()
    step_stats = get_step_stats()
    failure_analysis = get_failure_analysis()
    routing_stats = get_routing_stats()
    v_vector_stats = get_v_vector_stats()
    
    # ═══════════════════════════════════════════════════════
    # PIPELINE SUCCESS RATES (THE TRUTH!)
    # ═══════════════════════════════════════════════════════
    if pipeline_stats and pipeline_stats["completed"] > 0:
        print("\n" + "=" * 70)
        print(" 📊 PIPELINE SUCCESS RATES (THE REAL METRICS)")
        print("=" * 70)
        
        success_pct = pipeline_stats["success_rate"] * 100
        
        # Visual indicator based on success rate
        if success_pct >= 80:
            indicator = "🟢"
        elif success_pct >= 50:
            indicator = "🟡"
        else:
            indicator = "🔴"
        
        print(f"\n{indicator} Overall Pipeline Success Rate: {success_pct:.1f}%")
        print(f"   Total Runs: {pipeline_stats['total_runs']}")
        print(f"   Completed: {pipeline_stats['completed']} ({pipeline_stats['succeeded']} ✅ / {pipeline_stats['failed']} ❌)")
        if pipeline_stats['running'] > 0:
            print(f"   Currently Running: {pipeline_stats['running']}")
        
        if pipeline_stats['avg_success_duration']:
            print(f"   Avg Success Duration: {pipeline_stats['avg_success_duration']:.1f}s")
        if pipeline_stats['avg_steps_succeeded']:
            print(f"   Avg Steps Completed: {pipeline_stats['avg_steps_succeeded']:.1f}")
        
        # By archetype
        if pipeline_stats['archetype_stats']:
            print("\n--- By Archetype ---")
            for row in pipeline_stats['archetype_stats']:
                arch = row["archetype"] or "unknown"
                total = row["total"]
                succeeded = row["succeeded"]
                rate = (succeeded / total * 100) if total > 0 else 0
                print(f"  {arch}: {rate:.0f}% ({succeeded}/{total})")
        
        # Recent runs
        if pipeline_stats['recent_runs']:
            print("\n--- Recent Runs ---")
            for run in pipeline_stats['recent_runs'][:5]:
                status_icon = "✅" if run["status"] == "success" else ("❌" if run["status"] == "failure" else "⏳")
                arch = run["archetype"] or "?"
                final = run["final_step"] or "?"
                steps = run["total_steps_succeeded"] or 0
                duration = run["duration_seconds"]
                duration_str = f"{duration:.0f}s" if duration else "?"
                print(f"  {status_icon} [{arch}] → {final} ({steps} steps, {duration_str})")
    
    elif pipeline_stats is None:
        print("\n" + "=" * 70)
        print(" 📊 PIPELINE SUCCESS RATES")
        print("=" * 70)
        print("\n⚠️  No pipeline metrics database found.")
        print(f"   Expected: {PIPELINE_DB_PATH}")
        print("   Run a workflow to start collecting pipeline metrics.")
    
    # ═══════════════════════════════════════════════════════
    # PER-STEP SUCCESS RATES
    # ═══════════════════════════════════════════════════════
    if step_stats:
        print("\n" + "=" * 70)
        print(" 📈 PER-STEP SUCCESS RATES")
        print("=" * 70)
        
        print(f"\n{'Step':<25} {'Success':<10} {'Healed':<8} {'Avg Time':<10}")
        print("-" * 55)
        for row in step_stats:
            step = row["step_name"]
            total = row["total"]
            succeeded = row["succeeded"]
            healed = row["healed"] or 0
            rate = (succeeded / total * 100) if total > 0 else 0
            healed_pct = (healed / total * 100) if total > 0 else 0
            avg_dur = row["avg_duration"]
            dur_str = f"{avg_dur:.1f}s" if avg_dur else "-"
            
            # Color indicator
            if rate >= 90:
                indicator = "🟢"
            elif rate >= 70:
                indicator = "🟡"
            else:
                indicator = "🔴"
            
            print(f"{indicator} {step:<22} {rate:>5.0f}% ({succeeded}/{total})  {healed_pct:>4.0f}%    {dur_str}")
    
    # ═══════════════════════════════════════════════════════
    # FAILURE ANALYSIS
    # ═══════════════════════════════════════════════════════
    if failure_analysis:
        print("\n" + "=" * 70)
        print(" ❌ FAILURE ANALYSIS (Where Things Break)")
        print("=" * 70)
        
        if failure_analysis['failure_points']:
            print("\n--- Pipeline Failure Points ---")
            for row in failure_analysis['failure_points']:
                step = row["final_step"] or "unknown"
                count = row["count"]
                print(f"  {step}: {count} failures")
        
        if failure_analysis['step_failures']:
            print("\n--- Step Failures by Type ---")
            for row in failure_analysis['step_failures']:
                step = row["step_name"]
                error_type = row["error_type"] or "unknown"
                count = row["failure_count"]
                print(f"  {step} ({error_type}): {count}x")
    
    # ═══════════════════════════════════════════════════════
    # ROUTING METRICS (Legacy - for comparison)
    # ═══════════════════════════════════════════════════════
    if routing_stats and routing_stats['total_decisions'] > 0:
        print("\n" + "=" * 70)
        print(" 🧭 ROUTING METRICS (Decision-Level, May Differ from Pipeline)")
        print("=" * 70)
        
        print(f"\nTotal Routing Decisions: {routing_stats['total_decisions']}")
        print(f"Routing Success Rate: {routing_stats['success_rate']:.1%}")
        print(f"Average Retry Count: {routing_stats['avg_retry_count']:.2f}")
        
        print("\n--- T-AM Analysis ---")
        print(f"Decisions with T-AM: {routing_stats['tam_usage_count']}")
        if routing_stats['tam_usage_count'] > 0:
            print(f"T-AM Success Rate: {routing_stats['tam_success_rate']:.1%}")
            print(f"No T-AM Success Rate: {routing_stats['no_tam_success_rate']:.1%}")
            print(f"T-AM Impact: {routing_stats['tam_impact']:+.1%}")
        else:
            print("  (No T-AM usage yet)")
    
    # ═══════════════════════════════════════════════════════
    # V-VECTOR LEARNING STATS
    # ═══════════════════════════════════════════════════════
    if v_vector_stats and v_vector_stats['total_decisions'] > 0:
        print("\n" + "=" * 70)
        print(" 🧬 V-VECTOR LEARNING (Self-Evolution)")
        print("=" * 70)
        
        print(f"\nTotal Routing Decisions: {v_vector_stats['total_decisions']}")
        print(f"Decisions with Outcomes: {v_vector_stats['decisions_with_outcomes']} ({v_vector_stats['coverage']:.1%} coverage)")
        print(f"Evolved V-Vectors: {v_vector_stats['evolved_vectors']}")
        print(f"Average Success Rate: {v_vector_stats['avg_success_rate']:.1%}")
        print(f"Average Confidence: {v_vector_stats['avg_confidence']:.1%}")
        
        if v_vector_stats['top_vectors']:
            print("\n--- Top Performing Evolved Vectors ---")
            for vec_key, success, samples, conf in v_vector_stats['top_vectors']:
                parts = vec_key.split(':')
                if len(parts) >= 3:
                    context = parts[0]
                    archetype = parts[1]
                    option = parts[2]
                    print(f"  {context}/{option} ({archetype}): {success:.1%} success, n={samples}, conf={conf:.2f}")
                else:
                    print(f"  {vec_key}: {success:.1%} success, n={samples}, conf={conf:.2f}")
    
    print("\n" + "=" * 70)
    
    # Summary guidance
    if pipeline_stats and pipeline_stats["completed"] > 0:
        rate = pipeline_stats["success_rate"]
        if rate < 0.3:
            print("\n⚠️  LOW SUCCESS RATE - Focus on debugging the most common failure point.")
        elif rate < 0.7:
            print("\n💡 MODERATE SUCCESS - Good progress, but room for improvement.")
        else:
            print("\n✅ HIGH SUCCESS - Great job! System is performing well.")
    
    total = (routing_stats or {}).get('total_decisions', 0) + (pipeline_stats or {}).get('completed', 0)
    
    if total < 10:
        print("\n💡 Note: Limited data. Run 10+ workflows for meaningful stats.")
    elif total < 50:
        print("\n💡 Note: Growing dataset. 50+ workflows recommended for significance.")
    else:
        print(f"\n✅ Good sample size ({total} total data points)!")


if __name__ == "__main__":
    main()
