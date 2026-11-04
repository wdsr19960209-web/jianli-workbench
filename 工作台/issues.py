# 监理问题：本地 SQLite 存取，与巡查记录共用一个本机数据库、不同表。

import os
import sqlite3


def _connect(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, route TEXT, location TEXT, description TEXT,
        unit TEXT, status TEXT, deadline TEXT)""")
    return conn


def list_issues(db_path):
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id, date, route, location, description, unit, status, deadline "
            "FROM issues ORDER BY date DESC, id DESC")
        return [dict(zip(["id", "date", "route", "location", "description",
                          "unit", "status", "deadline"], r)) for r in cur.fetchall()]
    finally:
        conn.close()


def add_issue(db_path, date, route, location, description, unit, status, deadline):
    conn = _connect(db_path)
    try:
        conn.execute("INSERT INTO issues (date, route, location, description, unit, "
                     "status, deadline) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (date, route, location, description, unit, status, deadline))
        conn.commit()
    finally:
        conn.close()
