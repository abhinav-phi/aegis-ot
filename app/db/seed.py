"""Bootstrap seed: admin user from env + production KB corpus.

Idempotent. Required before first use outside dev (config.validate_safety).
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Dataset, User, UserRole
from app.db.session import SessionLocal


def seed_admin(db) -> None:
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        print("seed: AEGIS_OT_ADMIN_EMAIL/PASSWORD unset; skipping admin bootstrap")
        return
    existing = db.execute(select(User).where(User.email == s.admin_email)).scalar_one_or_none()
    if existing:
        print(f"seed: admin {s.admin_email} already present")
        return
    user = User(email=s.admin_email, password_hash=hash_password(s.admin_password), is_active=True)
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role="admin"))
    print(f"seed: created admin {s.admin_email}")


def seed_primary_dataset(db) -> None:
    """Register the synthetic mini-fixture as the primary dataset (fresh setup).

    Real SWaT/WUSTL ingestion is license-gated and performed via the datasets API.
    """
    import hashlib

    fixture = Path("data/fixtures/swat_mini.csv")
    if not fixture.exists():
        from pipeline.ingest.synthetic import to_csv_bytes

        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_bytes(to_csv_bytes())
    sha = hashlib.sha256(fixture.read_bytes()).hexdigest()
    existing = db.execute(select(Dataset).where(Dataset.key == "synthetic")).scalar_one_or_none()
    if existing:
        return
    lines = fixture.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0].split(",")
    sensors = [c for c in header if c not in ("timestamp", "label")]
    ds = Dataset(
        key="synthetic",
        display_name="SWaT-style synthetic mini-fixture (development)",
        source_url="local://data/fixtures/swat_mini.csv",
        sha256=sha,
        record_count=len(lines) - 1,
        sensor_columns=sensors,
        primary=True,
    )
    db.add(ds)
    print("seed: registered synthetic fixture dataset")


def seed_kb(db) -> None:
    """Load production KB corpus (trusted/public only — R11)."""
    from pipeline.rag.kb import build_kb

    build_kb(db, collection="aegis_kb_prod", root=Path("configs/kb"))


def main() -> None:
    with SessionLocal() as db:
        seed_admin(db)
        seed_primary_dataset(db)
        try:
            seed_kb(db)
        except FileNotFoundError as e:
            print(f"seed: KB corpus missing ({e}); run after configs/kb exists")
        db.commit()
    print("seed: OK")


if __name__ == "__main__":
    sys.exit(main())
