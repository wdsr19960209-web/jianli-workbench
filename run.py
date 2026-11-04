#!/usr/bin/env python3
# 监理工作台：唯一启动入口。只用 Python 标准库，不用 pip 装任何东西。
# 只绑 127.0.0.1，不对外；病害和安全两页只读，不采集、不写台账。
# 五个页签与聊天预览第二十四版结构一致：首页 · 工程概括、巡查统计、
# 安全文件台账、病害台账、监理指令。监理问题那页已去掉。
# 公开库红线：不提交 .env、.db、真实台账、通讯录电话、示意图原图。

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
import instructions  # noqa: E402
import overview  # noqa: E402
import patrol_records  # noqa: E402
import patrol_stats  # noqa: E402
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


def home_body():
    cards = "".join(
        f"<div style='border:1px solid #ccc;border-radius:8px;padding:12px;"
        f"margin:8px;display:inline-block;vertical-align:top;width:280px'>"
        f"<b>{esc(s['road'])}</b><br>桩号：{esc(s['stake'])}<br>"
        + (f"管养里程：{s['mileage']} 公里<br>" if s["mileage"] else "")
        + f"工区：{esc(s['gongqu'])}</div>"
        for s in overview.SECTIONS)
    lines = "<br>".join(esc(x) for x in overview.GONGQU_LINES)
    return (
        f"<h2>安阳驻地办 · 工程概括</h2>"
        f"<p class='note'>安阳分公司管养里程 {overview.TOTAL_MILEAGE_KM} 公里。</p>"
        "<div style='border:2px dashed #ccc;border-radius:8px;padding:20px'>"
        "<b>安阳分公司管养路段示意图</b>"
        "<p class='note'>示意图原图是内部资料，不提交进公开库；"
        "本地版需要时把图放本机，再改这一处。</p></div>"
        f"<h3>各路段概括</h3>{cards}"
        f"<h3>工区对照</h3><p>{lines}</p>"
        "<p class='note'>本页只写路段、桩号、里程、工区结构，"
        "不写通讯录里的姓名、电话；通讯录只放在聊天预览里。</p>")


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
            return self._send(render.page("首页 · 工程概括", home_body()))

        if path == "/safety":
            rows, note = safety_read.read_safety_ledger(SAFETY_CSV)
            example = "examples" in SAFETY_CSV
            note += "（当前为示例假数据）" if example else ""
            body = (f"<p class='note'>{esc(note)}</p>"
                    "<p class='note'>登记和改状态仍在在线表里做，这里只展示，不改数据。"
                    "安全台账的处理状态与病害状态码不是一回事，不能混用。</p>"
                    + render.table(safety_read.COLUMNS, rows,
                                   lambda r: safety_status.color_for(r.get("处理状态"))))
            return self._send(render.page("安全文件台账", body))

        if path == "/disease":
            month = (query.get("month") or ["2026-11"])[0]
            show_closed = (query.get("show_closed") or ["0"])[0] == "1"
            rows, note = disease_live.read_month_csv(DISEASE_DIR, month)
            current_month = datetime.date.today().strftime("%Y-%m")
            is_current = month == current_month
            hidden_rows = [r for r in rows
                           if disease_status.should_hide(r, is_current)]
            visible_rows = [r for r in rows
                            if show_closed or not disease_status.should_hide(r, is_current)]
            company_rows = []
            for r in visible_rows:
                crow = disease_live.to_company_row(r)
                code = crow["状态码"]
                crow["状态码"] = f"{code}（{disease_status.text_for(code)}）"
                company_rows.append(crow)
            legend = "<br>".join(
                f"{k}：{v}" for k, v in disease_status.STATUS_TEXT.items())
            toggle = (f"<a href='/disease?month={esc(month)}&show_closed=0'>隐藏已闭环</a>"
                      if show_closed else
                      f"<a href='/disease?month={esc(month)}&show_closed=1'>"
                      "显示已闭环（状态5）</a>")
            body = (f"<p class='note'>{esc(note)}</p>"
                    f"<form>月份：<input name='month' value='{esc(month)}'>"
                    "<input type='submit' value='查看'></form>"
                    f"<p class='note'>共 {len(rows)} 条，"
                    f"隐藏 {len(hidden_rows)} 条"
                    "（仅当月、状态 5 且按期完成才隐藏，已完结月份全显；"
                    "点“显示已闭环”就相当于看完结月份）。"
                    f" {toggle}</p>"
                    f"<p class='note'>状态码规则：<br>{legend}</p>"
                    "<p class='note'>下面是公司在线表 12 列 + 状态码，"
                    "照这个顺序复制，正好一列对一列粘到公司在线表；"
                    "病害下发方式在示例里没有字段，留“待填写”，不等用户定下统一填什么不擅自填。</p>"
                    + render.table(
                        disease_live.COMPANY_COLUMNS, company_rows,
                        lambda r: disease_status.color_for(
                            str(r.get("状态码", ""))[:1])))
            return self._send(render.page(f"病害台账（{esc(month)}）", body))

        if path == "/patrol":
            view = (query.get("view") or ["day"])[0]
            label = (query.get("date") or ["2026-11-04"])[0]
            keyword = (query.get("q") or [""])[0]
            all_rows = patrol_records.list_patrol(DB, keyword)
            period = "month" if view == "month" else "day"
            stat_rows = patrol_stats.filter_by_period(all_rows, period, label)
            stat = patrol_stats.summarize(stat_rows, period)
            per_person = "".join(
                f"<tr><td>{esc(p)}</td><td>{c}</td></tr>"
                for p, c in sorted(stat["per_person"].items()))
            form = ("<form method='post' action='/patrol/add'>"
                    "日期：<input name='date' placeholder='2026-11-04'> "
                    "路线：<input name='route'> 路段：<input name='section'> "
                    "记录人：<input name='recorder'><br>"
                    "内容：<textarea name='content' rows='3' cols='80'></textarea><br>"
                    "<input type='submit' value='新增巡查记录'></form><hr>"
                    "<form>时间范围：<select name='view'>"
                    "<option value='day'" + (" selected" if view == "day" else "") + ">每日</option>"
                    "<option value='month'" + (" selected" if view == "month" else "") + ">每月</option>"
                    "</select> 日期/月份：<input name='date' value='" + esc(label) + "'>"
                    " 关键词：<input name='q' value='" + esc(keyword) + "'>"
                    "<input type='submit' value='查看'></form>")
            body = (form
                    + f"<h3>巡查统计（{'每日' if view == 'day' else '每月'}，{esc(label)}）</h3>"
                    f"<p class='note'>巡查次数：{stat['total']} 次。"
                    "巡查没有完成率，只看次数和轨迹，不算已完成和完成率。"
                    "里程和发现病害数待接智养平台（里程字段名待确认，"
                    "病害靠巡查记录编号关联），接通前不编造。</p>"
                    "<table><tr><th>巡查人</th><th>巡查次数</th></tr>"
                    + (per_person or "<tr><td colspan='2'>暂无数据</td></tr>")
                    + f"<tr><td><b>合计</b></td><td><b>{stat['total']}</b></td></tr></table>"
                    "<h3>巡查记录（本机新增）</h3>"
                    + render.table(
                        ["id", "date", "route", "section", "recorder", "content"],
                        all_rows))
            return self._send(render.page("巡查统计", body))

        if path == "/instruction":
            problem = (query.get("problem") or [""])[0]
            hazard = (query.get("hazard") or [""])[0]
            basis = (query.get("basis") or [""])[0]
            overdue = (query.get("overdue") or [""])[0]
            draft = ""
            if problem or hazard or basis or overdue:
                draft = instructions.build_instruction(problem, hazard, basis, {}, overdue)
            form = ("<form>"
                    "巡查发现的问题：<br><textarea name='problem' rows='2' cols='80'>"
                    + esc(problem) + "</textarea><br>"
                    "危害后果：<br><textarea name='hazard' rows='2' cols='80'>"
                    + esc(hazard) + "</textarea><br>"
                    "合同 / 规范依据：<br><textarea name='basis' rows='2' cols='80'>"
                    + esc(basis) + "</textarea><br>"
                    "逾期责任：<br><textarea name='overdue' rows='2' cols='80'>"
                    + esc(overdue) + "</textarea><br>"
                    "<input type='submit' value='生成指令草稿'></form>")
            body = (form
                    + "<p class='note'>只套既有模板格式，不替你定责任，缺的留空。</p>"
                    + (f"<pre>{esc(draft)}</pre>" if draft else ""))
            return self._send(render.page("监理指令", body))

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
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print(f"监理工作台：http://127.0.0.1:{PORT}/ （只绑本机，按 Ctrl+C 停止）")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
