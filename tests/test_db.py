import sqlite3

from vclone import config, db


def test_init_db_creates_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()

    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO cases (name, client, target_person, authorization_ref) "
            "VALUES (?, ?, ?, ?)",
            ("Case A", "Client A", "Target A", "Contract-1"),
        )
        case_id = cur.lastrowid
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

    assert row["name"] == "Case A"
    assert row["closed_at"] is None


def test_init_db_migrates_legacy_schema(tmp_path, monkeypatch):
    db_path = str(tmp_path / "legacy.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)

    # Simulate a database created before the `closed_at` column existed.
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE cases ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, client TEXT, "
        "target_person TEXT, authorization_ref TEXT, created_at TEXT)"
    )
    conn.commit()
    conn.close()

    db.init_db()

    with db.get_conn() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(cases)")}
    assert "closed_at" in columns
