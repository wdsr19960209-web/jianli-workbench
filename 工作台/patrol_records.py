# 巡查记录：本地 SQLite 存取、按日期和关键词查。
# 数据库文件在本机 data/workbench.db，已被 .gitignore 挡住，不提交。

import os
import sqlite3


def _connect(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS patrol (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, route TEXT, section TEXT, recorder TEXT, content TEXT)""")
    return conn


def list_patrol(db_path, keyword=""):
    conn = _connect(db_path)
    try:
        if keyword:
            like = f"%{keyword}%"
            cur = conn.execute(
                "SELECT id, date, route, section, recorder, content FROM patrol "
                "WHERE date LIKE ? OR route LIKE ? OR section LIKE ? OR content LIKE ? "
                "ORDER BY date DESC, id DESC", (like, like, like, like))
        else:
            cur = conn.execute(
                "SELECT id, date, route, section, recorder, content FROM patrol "
                "ORDER BY date DESC, id DESC")
        return [dict(zip(["id", "date", "route", "section", "recorder", "content"], r))
                for r in cur.fetchall()]
    finally:
        conn.close()


def add_patrol(db_path, date, route, section, recorder, content):
    conn = _connect(db_path)
    try:
        conn.execute("INSERT INTO patrol (date, route, section, recorder, content) "
                     "VALUES (?, ?, ?, ?, ?)", (date, route, section, recorder, content))
        conn.commit()
    finally:
        conn.close()
