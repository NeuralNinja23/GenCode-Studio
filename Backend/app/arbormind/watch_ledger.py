# app/arbormind/watch_ledger.py
"""
ArborMind Ledger Watcher - Real-time execution monitoring.

Watches the SQLite ExecutionLedger for live execution events.
Run with: python -m app.arbormind.watch_ledger
"""

import sqlite3
import time
import os
import json
from datetime import datetime
from pathlib import Path

# Configuration - SQLite DB (canonical source)
DB_PATH = Path(__file__).parent.parent.parent / "arbormind_runs" / "arbormind.db"
REFRESH_RATE = 2.0  # Seconds


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_connection():
    """Get read-only connection to the ledger DB."""
    try:
        if not DB_PATH.exists():
            return None
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Waiting for DB connection... ({e})")
        return None


def fetch_latest_run(conn):
    """Fetch the most recent run."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM runs ORDER BY timestamp DESC LIMIT 1")
        return cursor.fetchone()
    except sqlite3.OperationalError:
        return None


def fetch_run_steps(conn, run_id):
    """Reconstruct steps from step_events for display."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM step_events WHERE run_id = ? ORDER BY timestamp",
            (run_id,)
        )
        events = cursor.fetchall()
        
        steps = {}
        ordered_steps = []
        
        for e in events:
            name = e['step_name']
            if name not in steps:
                steps[name] = {"name": name, "status": "RUNNING", "duration": "..."}
                ordered_steps.append(steps[name])
            
            if e['event_type'] == "EXIT":
                try:
                    payload = json.loads(e['payload']) if e['payload'] else {}
                    steps[name]['status'] = payload.get('status', 'DONE')
                except:
                    steps[name]['status'] = 'DONE'
                steps[name]['duration'] = "DONE"
        
        return ordered_steps
    except sqlite3.OperationalError:
        return []


def fetch_recent_failures(conn, run_id):
    """Fetch recent failure events."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM failure_events WHERE run_id = ? ORDER BY timestamp DESC LIMIT 5",
            (run_id,)
        )
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []


def fetch_recent_decisions(conn, run_id):
    """Fetch recent decision events."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM decision_events WHERE run_id = ? ORDER BY timestamp DESC LIMIT 5",
            (run_id,)
        )
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []


def fetch_tool_traces(conn, run_id):
    """Fetch tool invocation traces."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM tool_invocations WHERE run_id = ? ORDER BY timestamp DESC LIMIT 5",
            (run_id,)
        )
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []


def main():
    print(f"Watching Execution Ledger (SQLite): {DB_PATH}")
    print("Waiting for activity...")
    
    while True:
        try:
            conn = get_connection()
            if not conn:
                time.sleep(REFRESH_RATE)
                continue
                
            run = fetch_latest_run(conn)
            
            if run:
                clear_screen()
                print(f"╔══════════════════════════════════════════════════════════════╗")
                print(f"║  ARBORMIND EXECUTION LEDGER ({datetime.now().strftime('%H:%M:%S')})                    ║")
                print(f"╠══════════════════════════════════════════════════════════════╣")
                print(f"║  RUN ID: {run['run_id']:<50} ║")
                print(f"║  STATUS: {run['status_event']:<50} ║")
                print(f"║  START:  {run['timestamp'][:19]:<50} ║")
                print(f"╠══════════════════════════════════════════════════════════════╣")
                
                # Show Steps (Reconstructed from Events)
                steps = fetch_run_steps(conn, run['run_id'])
                print(f"║  STEPS ({len(steps)}):                                                 ║")
                for step in steps:
                    status = step['status']
                    if status in ["COMPLETED", "success"]:
                        icon = "✅"
                    elif status == "FAILED":
                        icon = "❌"
                    else:
                        icon = "⏳"
                    print(f"║    {icon} {step['name']:<25} │ {status:<24} ║")
                
                print(f"╠══════════════════════════════════════════════════════════════╣")
                
                # Show Failures
                failures = fetch_recent_failures(conn, run['run_id'])
                if failures:
                    print(f"║  ⚠️  FAILURES:                                                ║")
                    for f in failures:
                        msg = f['message'][:45] if f['message'] else "No message"
                        print(f"║    [{f['step']:<12}] {msg:<44} ║")
                else:
                    print(f"║  ✅ No failures recorded                                      ║")
                    
                print(f"╠══════════════════════════════════════════════════════════════╣")

                # Show Recent Decisions
                decisions = fetch_recent_decisions(conn, run['run_id'])
                if decisions:
                    print(f"║  🧠 RECENT DECISIONS:                                         ║")
                    for d in decisions:
                        try:
                            payload = json.loads(d['raw_payload']) if d['raw_payload'] else {}
                            decision = payload.get('decision', 'UNKNOWN')[:20]
                        except:
                            decision = "???"
                        agent = d['source_agent'][:10] if d['source_agent'] else "?"
                        step = d['step'][:12] if d['step'] else "?"
                        print(f"║    [{step:<12}][{agent:<10}] → {decision:<22} ║")

                print(f"╚══════════════════════════════════════════════════════════════╝")
            else:
                print("No runs found in ledger.")

            conn.close()
            time.sleep(REFRESH_RATE)
            
        except KeyboardInterrupt:
            print("\nStopped watcher.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(REFRESH_RATE)


if __name__ == "__main__":
    main()
