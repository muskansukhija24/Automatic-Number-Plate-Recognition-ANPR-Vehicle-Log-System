"""
Unit Tests for Module 3: DBManager SQLite Storage and Audit Queries.
"""

import os
import pytest

from src.db_manager import DBManager


@pytest.fixture
def temp_db(tmp_path):
    """Fixture returning a fresh DBManager pointing to a temporary database file."""
    db_file = os.path.join(tmp_path, "test_vehicles.db")
    return DBManager(db_path=db_file)


class TestDBManager:
    """Test suite for SQLite CRUD operations, flagging, and export."""

    def test_init_creates_tables(self, temp_db):
        """Test database and table initialization."""
        assert os.path.exists(temp_db.db_path)
        stats = temp_db.get_summary_stats()
        assert stats["total_scans"] == 0

    def test_insert_and_get_log(self, temp_db):
        """Test inserting a detection record and retrieving it."""
        log_id = temp_db.insert_log(
            plate_number="DL01AB1234",
            confidence=0.95,
            image_path="sample.jpg",
            flagged=0,
            status="DETECTED",
        )
        assert log_id == 1

        logs = temp_db.get_logs()
        assert len(logs) == 1
        record = logs[0]
        assert record["id"] == 1
        assert record["plate_number"] == "DL01AB1234"
        assert record["confidence"] == 0.95
        assert record["flagged"] == 0
        assert record["status"] == "DETECTED"

    def test_search_by_plate(self, temp_db):
        """Test searching records by exact and partial plate substring."""
        temp_db.insert_log("MH12DE1433", 0.92, "img1.jpg")
        temp_db.insert_log("MH14AB9999", 0.88, "img2.jpg")
        temp_db.insert_log("KA05NB9876", 0.96, "img3.jpg")

        # Substring search
        mh_results = temp_db.search_by_plate("MH")
        assert len(mh_results) == 2

        # Exact match
        exact_results = temp_db.search_by_plate("MH12DE1433", exact=True)
        assert len(exact_results) == 1
        assert exact_results[0]["plate_number"] == "MH12DE1433"

    def test_flagging_and_blacklist_inheritance(self, temp_db):
        """Test flagging a vehicle and ensuring future scans inherit flagged status."""
        temp_db.insert_log("DL01AB1234", 0.95, "img1.jpg", flagged=0)
        assert temp_db.is_plate_flagged("DL01AB1234") is False

        # Blacklist the vehicle
        temp_db.set_flag("DL01AB1234", flagged=True)
        assert temp_db.is_plate_flagged("DL01AB1234") is True

        # Subsequent scan should automatically inherit flagged=1
        new_id = temp_db.insert_log("DL01AB1234", 0.96, "img2.jpg")
        new_record = temp_db.search_by_plate("DL01AB1234", exact=True)[0]
        assert new_record["flagged"] == 1

        # Unflag the vehicle
        temp_db.set_flag("DL01AB1234", flagged=False)
        assert temp_db.is_plate_flagged("DL01AB1234") is False

    def test_summary_statistics(self, temp_db):
        """Test calculation of dashboard summary metrics."""
        temp_db.insert_log("DL01AB1234", 0.90, "img1.jpg", flagged=0, status="DETECTED")
        temp_db.insert_log("MH12DE1433", 0.80, "img2.jpg", flagged=1, status="DETECTED")
        temp_db.insert_log("UNREADABLE", 0.00, "img3.jpg", flagged=0, status="UNREADABLE")

        stats = temp_db.get_summary_stats()
        assert stats["total_scans"] == 3
        assert stats["today_scans"] == 3
        assert stats["flagged_count"] == 1
        assert stats["unreadable_count"] == 1
        # Average confidence should be (0.90 + 0.80) / 2 = 0.85
        assert stats["avg_confidence"] == 0.85

    def test_export_to_csv(self, temp_db, tmp_path):
        """Test exporting database records to a valid CSV file."""
        temp_db.insert_log("DL01AB1234", 0.95, "img1.jpg")
        temp_db.insert_log("MH12DE1433", 0.90, "img2.jpg")

        csv_file = os.path.join(tmp_path, "exported_logs.csv")
        exported_path = temp_db.export_to_csv(csv_file)
        assert os.path.exists(exported_path)

        with open(exported_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 data rows
            assert "plate_number" in lines[0]
            assert any("DL01AB1234" in line for line in lines)
            assert any("MH12DE1433" in line for line in lines)
