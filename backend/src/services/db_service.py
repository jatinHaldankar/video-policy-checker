import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DbService:
    """
    Zero-cost database service using Python's built-in SQLite.
    Stores audit jobs and results in a local 'jobs.db' file.
    """
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Standard SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the SQLite database schema."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT,
                        video_name TEXT,
                        final_status TEXT,
                        final_report TEXT,
                        compliance_issues TEXT,
                        pharma_checks TEXT,
                        errors TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            logger.info("Local SQLite database initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")

    def create_job(self, job_id: str, video_name: str):
        """Register a new job in the database."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO jobs (job_id, status, video_name) VALUES (?, ?, ?)",
                    (job_id, "queued", video_name)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")

    def update_job(self, job_id: str, updates: Dict[str, Any]):
        """Update job fields. Automatically serializes lists/dicts to JSON."""
        try:
            fields = []
            values = []
            for key, value in updates.items():
                fields.append(f"{key} = ?")
                if isinstance(value, (list, dict)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
            
            values.append(job_id)
            query = f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?"
            
            with self._get_connection() as conn:
                conn.execute(query, tuple(values))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single job by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
        return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Retrieve all jobs, sorted by creation date."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a clean dictionary with parsed JSON."""
        d = dict(row)
        # Parse JSON strings back into Python objects
        for field in ["compliance_issues", "pharma_checks", "errors"]:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except:
                    d[field] = []
            else:
                d[field] = []
        return d
