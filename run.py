#!/usr/bin/env python3
# 监理工作台骨架：唯一启动入口。只用 Python 标准库，不用 pip 装任何东西。
# 只绑 127.0.0.1，不对外；病害和安全两页只读，不采集、不写台账。

import datetime
import html
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
for folder in ("安全", "工作台", "病害台账"):
    sys.path.insert(0, os.path.join(BASE, folder))

import disease_live  # noqa: E402
import disease_status  # noqa: E402
import issues  # noqa: E402
import patrol_records  # noqa: E402
import render  # noqa: E402
import safety_read  # noqa: E402
import safety_status  # noqa: E402


def load_env():
    env = {}
    path = os.path.join(BASE, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    return env


ENV = load_env()
PORT = int(ENV.get("PORT") or os.environ.get("PORT") or 8080)
DB = os.path.join(BASE, ENV.get("WORKBENCH_DB") or "data/workbench.db")
SAFETY_CSV = ENV.get("SAFETY_LEDGER_CSV") or os.path.join(
    BASE, "data/examples/safety_example.csv")
DISEASE_DIR = ENV.get("DISEASE_LEDGER_DIR") or os.path.join(BASE, "data/examples")


def esc(value):
    return html.escape(str(value or ""))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 保持终端干净
        pass

    def _send(self, body):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        path = parsed.path

        if path == "/":
            body = ("<p class='note'>骨架版：只在本地跑，不推 GitHub，不含真实数据。"
                    "安全和病害两页只读；巡查记录、监理问题存在本机 data/workbench.db，"
                    "已被 .gitignore 挡住。</p><ul>"
                    "<li><a href='/safety'>安全文件台账</a></li>"
                    "<li><a href='/disease'>病害台账</a></li>"
                    "<li><a href='/patrol'>巡查记录</a></li>"
                    "<li><a href='/issues'>监理问题</a></li></ul>")
            return self._send(render.page("监理工作台", body))

        if path == "/safety":
            rows, note = safety_read.read_safety_ledger(SAFETY_CSV)
            example = "examples" in SAFETY_CSV
            note += "（当前为示例假数据）" if example else ""
            body = (f"<p class='note'>{esc(note)}</p>"
                    "<p class='note'>登记和改状态仍在在线表里做，这里只展示，不改数据。</p>"
                    + render.table(safety_read.COLUMNS, rows,
                                   lambda r: safety_status.color_for(r.get("处理状态"))))
            return self._send(render.page("安全文件台账", body))

        if path == "/disease":
            month = (query.get("month") or ["2026-11"])[0]
            rows, note = disease_live.read_month_csv(DISEASE_DIR, month)
            current_month = datetime.date.today().strftime("%Y-%m")
            visible = [r for r in rows
                       if not disease_status.should_hide(r, month == current_month)]
            hidden = len(rows) - len(visible)
            cols = disease_live.COLUMNS
            body = (f"<p class='note'>{esc(note)}</p>"
                    f"<form>月份：<input name='month' value='{esc(month)}'>"
                    "<input type='submit' value='查看'></form>"
                    f"<p class='note'>共 {len(rows)} 条，隐藏 {hidden} 条"
                    "（仅当月、状态 5 且按期完成才隐藏，已完结月份全显）。</p>"
                    + render.table(cols, visible,
                                   lambda r: disease_status.color_for(r.get("状态码"))))
            return self._send(render.page(f"病害台账（{esc(month)}）", body))

        if path == "/patrol":
            keyword = (query.get("q") or [""])[0]
            rows = patrol_records.list_patrol(DB, keyword)
            cols = ["id", "date", "route", "section", "recorder", "content"]
            form = ("<form method='post' action='/patrol/add'>"
                    "日期：<input name='date' placeholder='2026-11-04'> "
                    "路线：<input name='route'> 路段：<input name='section'> "
                    "记录人：<input name='recorder'><br>"
                    "内容：<textarea name='content' rows='3' cols='80'></textarea><br>"
                    "<input type='submit' value='新增巡查记录'></form><hr>"
                    "<form>关键词：<input name='q' value='" + esc(keyword) + "'>"
                    "<input type='submit' value='搜索'></form>")
            return self._send(render.page("巡查记录", form + render.table(cols, rows)))

        if path == "/issues":
            rows = issues.list_issues(DB)
            cols = ["id", "date", "route", "location", "description",
                    "unit", "status", "deadline"]
            form = ("<form method='post' action='/issues/add'>"
                    "日期：<input name='date'> 路线：<input name='route'> "
                    "位置：<input name='location'> 承包单位：<input name='unit'><br>"
                    "问题：<textarea name='description' rows='3' cols='80'></textarea><br>"
                    "状态：<input name='status' placeholder='待整改'> "
                    "期限：<input name='deadline'> "
                    "<input type='submit' value='新增监理问题'></form><hr>")
            return self._send(render.page("监理问题", form + render.table(cols, rows)))

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        fields = {k: v[0] for k, v in
                  parse_qs(self.rfile.read(length).decode("utf-8")).items()}
        if self.path == "/patrol/add":
            patrol_records.add_patrol(DB, fields.get("date", ""), fields.get("route", ""),
                                      fields.get("section", ""), fields.get("recorder", ""),
                                      fields.get("content", ""))
            return self._redirect("/patrol")
        if self.path == "/issues/add":
            issues.add_issue(DB, fields.get("date", ""), fields.get("route", ""),
                             fields.get("location", ""), fields.get("description", ""),
                             fields.get("unit", ""), fields.get("status", ""),
                             fields.get("deadline", ""))
            return self._redirect("/issues")
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print(f"监理工作台骨架：http://127.0.0.1:{PORT}/ （只绑本机，按 Ctrl+C 停止）")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
