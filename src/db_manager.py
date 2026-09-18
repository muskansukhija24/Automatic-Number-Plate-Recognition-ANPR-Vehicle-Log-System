"""
Module 3: Vehicle Log & Database Storage (SQLite).

Handles persistent logging of plate detection results, search queries,
vehicle blacklisting/flagging, statistical summaries, and CSV exports.
"""

import csv
from datetime import datetime
import os
import sqlite3
from typing import Any, Dict, List, Optional, Union

from src.logger import logger


class DBManager:
    """
    SQLite Database Manager for ANPR Vehicle Logs.
    """

    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "vehicle_logs.db",
    )

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection and verify table schema.

        Args:
            db_path: Path to the SQLite database file. Defaults to 'data/vehicle_logs.db'.
        """
        self.db_path = os.path.abspath(db_path or self.DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection configured with dictionary row factory."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create vehicle_logs table and performance indexes if they do not exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS vehicle_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            confidence REAL NOT NULL,
            image_path TEXT NOT NULL,
            flagged INTEGER DEFAULT 0,
            status TEXT DEFAULT 'DETECTED'
        );

        CREATE INDEX IF NOT EXISTS idx_logs_plate ON vehicle_logs(plate_number);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON vehicle_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_logs_flagged ON vehicle_logs(flagged);
        """
        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
        logger.debug(f"Database initialized at {self.db_path}")

    def is_plate_flagged(self, plate_number: str) -> bool:
        """
        Check if a given plate number is currently marked as flagged/blacklisted.

        Args:
            plate_number: Clean alphanumeric plate number.

        Returns:
            bool: True if previously flagged, False otherwise.
        """
        clean_plate = plate_number.strip().upper()
        if not clean_plate or clean_plate == "UNREADABLE":
            return False

        query = "SELECT COUNT(*) as count FROM vehicle_logs WHERE plate_number = ? AND flagged = 1"
        with self._get_connection() as conn:
            row = conn.execute(query, (clean_plate,)).fetchone()
            return bool(row["count"] > 0)

    def insert_log(
        self,
        plate_number: str,
        confidence: float,
        image_path: str,
        flagged: Optional[int] = None,
        status: str = "DETECTED",
    ) -> int:
        """
        Insert a new detection log entry.

        Args:
            plate_number: Normalized alphanumeric license plate string.
            confidence: Recognition confidence score (0.0 to 1.0).
            image_path: Path of the source image processed.
            flagged: 1 for flagged/blacklisted, 0 for standard. If None, inherits blacklist status.
            status: Detection status ('DETECTED', 'UNREADABLE', etc.).

        Returns:
            int: Primary key ID of the newly inserted log record.
        """
        clean_plate = plate_number.strip().upper()

        # Inherit blacklist flag status if not explicitly overridden
        if flagged is None:
            flagged = 1 if self.is_plate_flagged(clean_plate) else 0

        query = """
        INSERT INTO vehicle_logs (plate_number, confidence, image_path, flagged, status)
        VALUES (?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                query,
                (clean_plate, round(float(confidence), 3), image_path, int(flagged), status),
            )
            conn.commit()
            log_id = cursor.lastrowid

        logger.info(
            f"Logged vehicle: ID={log_id} Plate='{clean_plate}' "
            f"Conf={confidence:.2f} Flagged={flagged} Status={status}"
        )
        return log_id

    def get_logs(
        self,
        date_str: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve log entries, optionally filtered by date.

        Args:
            date_str: Optional filter in 'YYYY-MM-DD' format. If None, returns latest scans.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List[Dict[str, Any]]: List of log records.
        """
        with self._get_connection() as conn:
            if date_str:
                query = """
                SELECT id, plate_number, timestamp, confidence, image_path, flagged, status
                FROM vehicle_logs
                WHERE date(timestamp) = date(?)
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """
                cursor = conn.execute(query, (date_str, limit, offset))
            else:
                query = """
                SELECT id, plate_number, timestamp, confidence, image_path, flagged, status
                FROM vehicle_logs
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """
                cursor = conn.execute(query, (limit, offset))

            rows = [dict(row) for row in cursor.fetchall()]
        return rows

    def search_by_plate(
        self, plate_query: str, exact: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search vehicle logs for a specific license plate.

        Args:
            plate_query: Search string (e.g. 'DL01' or full plate).
            exact: If True, requires exact match. Otherwise performs substring LIKE query.

        Returns:
            List[Dict[str, Any]]: Matching records ordered by timestamp descending.
        """
        clean_query = plate_query.strip().upper()
        with self._get_connection() as conn:
            if exact:
                query = """
                SELECT id, plate_number, timestamp, confidence, image_path, flagged, status
                FROM vehicle_logs
                WHERE plate_number = ?
                ORDER BY timestamp DESC
                """
                cursor = conn.execute(query, (clean_query,))
            else:
                query = """
                SELECT id, plate_number, timestamp, confidence, image_path, flagged, status
                FROM vehicle_logs
                WHERE plate_number LIKE ?
                ORDER BY timestamp DESC
                """
                cursor = conn.execute(query, (f"%{clean_query}%",))

            rows = [dict(row) for row in cursor.fetchall()]
        return rows

    def set_flag(self, plate_number: str, flagged: bool = True) -> int:
        """
        Flag or unflag a vehicle plate number (add or remove from watchlist/blacklist).

        Args:
            plate_number: Target license plate string.
            flagged: True to flag (blacklist), False to unflag.

        Returns:
            int: Number of rows updated or affected.
        """
        clean_plate = plate_number.strip().upper()
        flag_val = 1 if flagged else 0

        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE vehicle_logs SET flagged = ? WHERE plate_number = ?",
                (flag_val, clean_plate),
            )
            conn.commit()
            rows_updated = cursor.rowcount

            # If plate had no prior logs, create a watchlist entry
            if rows_updated == 0 and flagged:
                conn.execute(
                    """
                    INSERT INTO vehicle_logs (plate_number, confidence, image_path, flagged, status)
                    VALUES (?, 1.0, 'MANUAL_BLACKLIST_ENTRY', 1, 'FLAGGED')
                    """,
                    (clean_plate,),
                )
                conn.commit()
                rows_updated = 1

        action_word = "Flagged/Blacklisted" if flagged else "Unflagged"
        logger.info(f"{action_word} plate '{clean_plate}' (affected {rows_updated} records).")
        return rows_updated

    def get_summary_stats(self) -> Dict[str, Union[int, float]]:
        """
        Calculate and return aggregate dashboard metrics.

        Returns:
            Dict containing total_scans, today_scans, flagged_count,
            unreadable_count, and avg_confidence.
        """
        with self._get_connection() as conn:
            # Total records
            total_scans = conn.execute(
                "SELECT COUNT(*) as c FROM vehicle_logs"
            ).fetchone()["c"]

            # Today's records
            today_scans = conn.execute(
                "SELECT COUNT(*) as c FROM vehicle_logs WHERE date(timestamp) = date('now', 'localtime')"
            ).fetchone()["c"]

            # Flagged records
            flagged_count = conn.execute(
                "SELECT COUNT(*) as c FROM vehicle_logs WHERE flagged = 1"
            ).fetchone()["c"]

            # Unreadable records
            unreadable_count = conn.execute(
                "SELECT COUNT(*) as c FROM vehicle_logs WHERE status = 'UNREADABLE'"
            ).fetchone()["c"]

            # Average confidence of readable detections
            avg_row = conn.execute(
                "SELECT AVG(confidence) as avg_conf FROM vehicle_logs WHERE status != 'UNREADABLE'"
            ).fetchone()
            avg_conf = (
                round(float(avg_row["avg_conf"]), 3)
                if avg_row["avg_conf"] is not None
                else 0.0
            )

        return {
            "total_scans": total_scans,
            "today_scans": today_scans,
            "flagged_count": flagged_count,
            "unreadable_count": unreadable_count,
            "avg_confidence": avg_conf,
        }

    def export_to_csv(self, output_filepath: str) -> str:
        """
        Export all vehicle log records to a CSV file.

        Args:
            output_filepath: Target destination for the exported CSV file.

        Returns:
            str: Absolute filepath of the written CSV.
        """
        abs_output = os.path.abspath(output_filepath)
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, plate_number, timestamp, confidence, image_path, flagged, status
                FROM vehicle_logs
                ORDER BY timestamp DESC
                """
            )
            rows = cursor.fetchall()

        fieldnames = ["id", "plate_number", "timestamp", "confidence", "image_path", "flagged", "status"]

        with open(abs_output, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        logger.info(f"Exported {len(rows)} records to CSV: '{abs_output}'")
        return abs_output
