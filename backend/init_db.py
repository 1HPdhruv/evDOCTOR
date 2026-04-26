"""
==========================================================================
  DATABASE INITIALIZATION SCRIPT
  --------------------------------------------------------------------------
  Reads the EV_DTC_Dataset.csv and populates the fault_codes table.
  Run this script once before starting the backend server.

  Usage:
    cd backend
    python init_db.py
==========================================================================
"""

import pandas as pd
import os
import sys

# Add parent to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
import models


def init_db():
    """Create all tables and seed the database from CSV."""
    print("[init_db] Creating tables...")
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Check if data already exists (idempotent)
    existing = db.query(models.FaultCode).count()
    if existing > 0:
        print(f"[init_db] Database already contains {existing} fault codes. Skipping seed.")
        db.close()
        return

    # Locate CSV file
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "EV_DTC_Dataset.csv",
    )

    if not os.path.exists(csv_path):
        print(f"[init_db] ERROR: Dataset not found at {csv_path}")
        db.close()
        return

    print(f"[init_db] Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)

    records = []
    for _, row in df.iterrows():
        fault = models.FaultCode(
            code=str(row["Code"]).strip(),
            description=str(row["Description"]).strip(),
            category=str(row.get("Category", "General")).strip(),
            severity=str(row.get("Severity", "Medium")).strip(),
            solution=str(row["Solution"]).strip(),
            steps=str(row.get("Steps", "")).strip(),
            training_text=str(row["TrainingText"]).strip(),
        )
        records.append(fault)

    db.bulk_save_objects(records)
    db.commit()
    db.close()

    print(f"[init_db] Successfully loaded {len(records)} fault codes into database.")


if __name__ == "__main__":
    init_db()
