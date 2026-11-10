#!/usr/bin/env python3
# 监理工作台：唯一启动入口。只用 Python 标准库，不用 pip 装任何东西。
# 只绑 127.0.0.1，不对外；病害和安全两页只读，不采集、不写台账。
# 五个页签与聊天预览第二十四版结构一致：首页 · 工程概括、巡查统计、
# 安全文件台账、病害台账、监理指令。监理问题那页已去掉。
# 公开库红线：不提交 .env、.db、真实台账、通讯录电话、示意图原图。

import datetime
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
for folder in ("安全", "工作台", "病害台账"):
    sys.path.insert(0, os.path.join(BASE, folder))

import charts  # noqa: E402
import disease_excel  # noqa: E402
import disease_live  # noqa: E402
import disease_patrol  # noqa: E402
import disease_status  # noqa: E402
import patrol_excel  # noqa: E402
import instructions  # noqa: E402
import overview  # noqa: E402
import render  # noqa: E402
import safety_read  # noqa: E402
import safety_status  # noqa: E402
try:
    # 本机版专用通讯录（含电话），只在 Mac 本地版文件夹里有；
    # 公开版没有这个文件时，首页自动不显示通讯录，绝不因此报错。
    import contacts_local  # noqa: E402
except ImportError:
    contacts_local = None
try:
    # 本机版专用已有指令示例（含真实指令正文），只在 Mac 本地版文件夹里有；
    # 公开版没有这个文件时，指令页自动不显示示例入口，绝不因此报错。
    # 示例本身（标题、正文）全在 local_examples.py 里，run.py 里只有示例编号和
    # 选取逻辑，不含任何真实指令内容，所以这段代码可以进公开库。
    import local_examples  # noqa: E402
except ImportError:
    local_examples = None


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
# 路径里的 ~ 展开成用户主目录，这样 Mac 本地版 .env 里可以直接写 ~/Desktop/...。
# 优先级：.env 文件 > 环境变量 > 默认示例路径。
DB = os.path.expanduser(os.path.join(
    BASE, ENV.get("WORKBENCH_DB") or os.environ.get("WORKBENCH_DB")
    or "data/workbench.db"))
SAFETY_CSV = os.path.expanduser(ENV.get("SAFETY_LEDGER_CSV")
    or os.environ.get("SAFETY_LEDGER_CSV")
    or os.path.join(BASE, "data/examples/safety_example.csv"))
DISEASE_DIR = os.path.expanduser(ENV.get("DISEASE_LEDGER_DIR")
    or os.environ.get("DISEASE_LEDGER_DIR")
    or os.path.join(BASE, "data/examples"))


def load_disease_month(month):
    """月度病害优先读真实月度 xlsx（病害处置台账_YYYY-MM.xlsx），
    没有 xlsx 时回落到示例 CSV。返回 (rows, note, is_xlsx)。"""
    xlsx_rows, xlsx_note = disease_excel.read_month_xlsx(DISEASE_DIR, month)
    if xlsx_rows or "读取失败" in xlsx_note:
        return xlsx_rows, xlsx_note, True
    if os.path.exists(os.path.join(DISEASE_DIR, "病害处置台账_%s.xlsx" % month)):
        return xlsx_rows, xlsx_note, True
    csv_rows, csv_note = disease_live.read_month_csv(DISEASE_DIR, month)
    return csv_rows, csv_note, False


def esc(value):
    return html.escape(str(value or ""))


def _section_block(i, s):
    # 折叠路段行：标题行 8 列对齐（见 render.py .sec），点开显示本段详情；
    # name='sec' 让 8 段一次只展开一个；纯 HTML details/summary，不用 JS。
    bridges_n = s["bridges"].split("座")[0]
    tolls_n = len(s["tolls"].split("、"))
    rows = [
        ("桩号", s["stake"]),
        ("管养里程", f"{s['mileage']} 公里"),
    ]
    if s.get("deducted"):
        rows.append(("扣除桥隧等后里程", f"{s['deducted']:.3f} 公里"))
    if s.get("opened"):
        rows.append(("通车时间", s["opened"]))
    if s.get("inspected"):
        rows.append(("定检时间", s["inspected"]))
    rows.append(("双幅车道数", str(s["lanes"]) if s.get("lanes") else "—"))
    rows.append(("工区", s["gongqu"]))
    if s.get("note"):
        rows.append(("备注", s["note"]))
    rows += [
        ("桥梁", s.get("bridges") or "—"),
        ("特大桥", s.get("mega_bridges") or "无"),
        ("服务区", s.get("services") or "无"),
        ("停车区", s.get("parking") or "无"),
        ("收费站", s.get("tolls") or "无"),
    ]
    body = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows)
    return (
        f"<details class='sec' name='sec' style='animation-delay:{i * 0.07:.2f}s'>"
        "<summary>"
        "<span class='arrow'>▸</span>"
        f"<span class='road'>{esc(s['road'])}</span>"
        f"<span class='pile'>{esc(s['stake'])}</span>"
        f"<span class='mi'>{s['mileage']} 公里</span>"
        f"<span class='ln'>{s['lanes']} 车道</span>"
        f"<span class='gq'>{esc(s['gongqu'])}</span>"
        f"<span class='br'>桥梁 {bridges_n} 座</span>"
        f"<span class='tl'>收费站 {tolls_n} 座</span>"
        "</summary>"
        f"<div class='body'><dl>{body}</dl></div>"
        "</details>")


def home_body():
    # 总览条数字从 SECTIONS 现算，与 overview.FACILITIES_NOTE 里的合计保持一致；改数据时两处一起改。
    bridges_total = sum(int(s["bridges"].split("座")[0]) for s in overview.SECTIONS)
    mega_total = sum(len(s["mega_bridges"].split("、")) for s in overview.SECTIONS if s.get("mega_bridges"))
    services_total = sum(len(s["services"].split("、")) for s in overview.SECTIONS if s.get("services"))
    parking_total = sum(len(s["parking"].split("、")) for s in overview.SECTIONS if s.get("parking"))
    tolls_total = sum(len(s["tolls"].split("、")) for s in overview.SECTIONS)
    stats = (
        "<div class='stats'>"
        f"<div class='stat'><b>{overview.TOTAL_MILEAGE_KM} 公里</b><span>管养里程</span></div>"
        f"<div class='stat'><b>{len(overview.SECTIONS)} 个</b><span>路段</span></div>"
        f"<div class='stat'><b>{bridges_total} 座</b><span>桥梁（特大桥 {mega_total} 座）</span></div>"
        f"<div class='stat'><b>{services_total} 座</b><span>服务区</span></div>"
        f"<div class='stat'><b>{parking_total} 处</b><span>停车区</span></div>"
        f"<div class='stat'><b>{tolls_total} 座</b><span>收费站</span></div>"
        f"<div class='stat'><b>{overview.CULVERT_TOTAL} 座</b><span>涵洞</span></div>"
        "</div>")
    sections = "".join(_section_block(i, s) for i, s in enumerate(overview.SECTIONS))
    culverts = "、".join(f"{esc(name)} {count}" for name, count in overview.CULVERT_BY_ROAD)
    culvert_line = (f"<p class='note'>涵洞：安阳分公司共 {overview.CULVERT_TOTAL} 座"
                    f"（{culverts}）。</p>")
    lines = "<br>".join(esc(x) for x in overview.GONGQU_LINES)
    map_file = os.path.join(BASE, "管养路段示意图.png")
    if os.path.exists(map_file):
        map_block = ("<img src='/map.png' style='max-width:100%;border:1px solid #ccc'>"
                     "<p class='note'>安阳分公司管养路段示意图（本机图片，仅本机可见）。</p>")
    else:
        map_block = ("<div style='border:2px dashed #ccc;border-radius:8px;padding:20px'>"
                     "<b>安阳分公司管养路段示意图</b>"
                     "<p class='note'>示意图原图是内部资料，不提交进公开库；"
                     "把原图存为工作台文件夹里的“管养路段示意图.png”，"
                     "这里就会自动显示出来。</p></div>")
    contacts_block = ""
    if contacts_local is not None:
        # 本机版才有：监理通讯录、工区通讯录（含电话），公开版不显示。
        sup = "".join(
            f"<tr><td>{esc(c['name'])}</td><td>{esc(c['phone'])}</td>"
            f"<td>{esc(c['scope'])}</td><td>{esc(c['note'])}</td></tr>"
            for c in contacts_local.SUPERVISORS)
        gong = "".join(
            f"<tr><td>{esc(c['road'])}</td><td>{esc(c['stake'])}</td>"
            f"<td>{esc(c['name'])}</td><td>{esc(c['phone'])}</td>"
            f"<td>{esc(c['gongqu'])}</td></tr>"
            for c in contacts_local.GONGQU_CONTACTS)
        contacts_block = (
            "<h3>安阳驻地办通讯录</h3>"
            "<table><tr><th>姓名</th><th>电话</th><th>管辖路段</th><th>备注</th></tr>"
            + sup + "</table>"
            "<h3>安阳各工区通讯录</h3>"
            "<table><tr><th>管辖路段</th><th>桩号</th><th>姓名</th><th>电话</th><th>工区</th></tr>"
            + gong + "</table>"
            "<p class='note'>通讯录只在本机版里，公开版没有，勿把本机版文件夹推到公开库。</p>")
    return (
        f"<h2>安阳驻地办 · 工程概括</h2>"
        f"<p class='note'>安阳分公司管养里程 {overview.TOTAL_MILEAGE_KM} 公里。</p>"
        + map_block
        + stats
        + f"<h3>各路段概括</h3>{sections}"
        + culvert_line
        + f"<p class='note'>{esc(overview.FACILITIES_NOTE)}</p>"
        + f"<h3>工区对照</h3><p>{lines}</p>"
        + contacts_block)


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
            # 归档预览：填了信息点“归档”后，只在当前页面多一行预览，
            # 不写本机 CSV、不动在线表；正式归档仍走在线表。
            preview_row = None
            new_name = (query.get("new_name") or [""])[0]
            if new_name.strip():
                preview_row = {c: "" for c in safety_read.COLUMNS}
                preview_row["序号"] = str(len(rows) + 1)
                preview_row["文件名/通知摘要"] = new_name
                preview_row["类型"] = (query.get("new_type") or [""])[0]
                preview_row["文件日期/通知日期"] = (query.get("new_date") or [""])[0]
                preview_row["处理状态"] = "待处理"
                preview_row["备注"] = "预览行，未写入在线表"
                rows = rows + [preview_row]
            form = ("<form>文件名/通知摘要：<input name='new_name' size='40'> "
                    "类型：<input name='new_type'> "
                    "日期：<input name='new_date' placeholder='2026-11-05'> "
                    "<input type='submit' value='归档（仅预览）'></form>")
            body = (f"<p class='note'>{esc(note)}</p>"
                    "<p class='note'>登记和改状态仍在在线表里做，这里只展示，不改数据。"
                    "安全台账的处理状态与病害状态码不是一回事，不能混用。</p>"
                    + form
                    + render.table(safety_read.COLUMNS, rows,
                                   lambda r: safety_status.color_for(r.get("处理状态"))))
            return self._send(render.page("安全文件台账", body))

        if path == "/disease":
            # 默认月份取当天所在月，不再写死 2026-11，下个月打开还是当月。
            month = (query.get("month") or
                     [datetime.date.today().strftime("%Y-%m")])[0]
            show_closed = (query.get("show_closed") or ["0"])[0] == "1"
            rows, note, _is_xlsx = load_disease_month(month)
            current_month = datetime.date.today().strftime("%Y-%m")
            is_current = month == current_month

            def _is_hidden(r):
                # xlsx 里行隐藏标记和状态 5 按期完成规则，两边只要一边说藏就藏；
                # 已完结月份：xlsx 本身已取消隐藏，should_hide 也返回 False。
                return bool(r.get("_行已隐藏")) or \
                    disease_status.should_hide(r, is_current)

            hidden_rows = [r for r in rows if _is_hidden(r)]
            visible_rows = [r for r in rows
                            if show_closed or not _is_hidden(r)]
            # 状态码只显示数字：括号里的含义上面统计表里已有含义一列，表里再写是多余的。
            # 首列加序号：按当前显示的行顺序从 1 编起（取消隐藏后全显时也一样顺延）。
            company_rows = []
            for i, r in enumerate(visible_rows, 1):
                crow = disease_live.to_company_row(r)
                crow["序号"] = str(i)
                company_rows.append(crow)
            daily_diseases, _daily_patrols = charts.daily_counts(rows, month)
            # 当月状态码统计：放每人图右边空白处，0/3/4/5 各多少条、占当月多少比例。
            # 0/3/4/5 四行永远显示（含 0 条的也显示 0），再加数据里出现过的其它码
            # （比如状态码还没填的空行），这样各行加起来一定等于总数，不会再出现
            # 合计 9 条、下面几行只加到 6 条的情况。
            from collections import Counter
            total = len(rows)
            code_counts = Counter()
            for r in rows:
                key = str(r.get("状态码", "")).strip()[:1] or "未填"
                code_counts[key] += 1
            ordered_codes = ["0", "3", "4", "5"] + [
                c for c in sorted(code_counts)
                if c not in ("0", "3", "4", "5")]
            stat_lines = []
            for code in ordered_codes:
                count = code_counts.get(code, 0)
                pct = f"{count / total * 100:.1f}%" if total else "0.0%"
                meaning = disease_status.text_for(code) if code != "未填" else "状态码未填"
                stat_lines.append(
                    f"<tr><td>{esc(code)}</td>"
                    f"<td>{esc(meaning)}</td>"
                    f"<td>{count}</td><td>{pct}</td></tr>")
            status_stat = (
                f"<div><h3>当月状态码统计（共 {total} 条）</h3>"
                "<table><thead><tr><th>状态码</th><th>含义</th>"
                "<th>条数</th><th>占比</th></tr></thead><tbody>"
                + "".join(stat_lines)
                + f"<tr><td><b>合计</b></td><td></td><td><b>{total}</b></td>"
                f"<td><b>{'100.0%' if total else '0.0%'}</b></td></tr></tbody></table></div>")
            # 病害页不再统计巡查次数：巡查次数只在巡查页统计，这里只留发现病害数。
            # 界面协调：趋势图拉满内容宽（1100），不再左边一小块、右边空一大块；
            # 统计表拉满剩余宽度，不再缩在右边一小条。
            # 两边底对齐：每人图高度不再写死 210，改成按右边统计表的实际行数算
            # （表头 1 行 + 状态码行 + 合计 1 行；行高约 41：字 14 号行高 1.6、
            # 上下内边距各 9、边框 1，再加表格上边距 12 与边框 2），
            # 这样哪天多一行“未填”之类的，图跟着长高，底边还是齐平的。
            # 两边各有一个 h3 标题，高度相同，不用再算。
            stat_rows = 1 + len(stat_lines) + 1
            person_height = 14 + 41 * stat_rows
            trend = (f"<h3>趋势图（{esc(month)}）</h3>"
                     + charts.svg_bars(daily_diseases, "每日发现病害数", width=1100)
                     + "<div style='display:flex;gap:20px;align-items:flex-start'>"
                     "<div><h3>每人发现病害数</h3>"
                     + charts.svg_bars(charts.per_person_discovered(rows, month),
                                       "每人发现病害数", bar_color="#e69138",
                                       width=640, height=person_height)
                     + "</div>"
                     + "<div style='flex:1'>" + status_stat + "</div></div>")
            # 状态码规则注释已删：上面状态码统计表里已有含义一列，注释是多余的。
            # 表头冻结仍保留（thead sticky），往下翻时表头停在顶部不动。
            # 取消隐藏按钮：点开显示全部已隐藏行，方便整表复制到其他表格；
            # 显示之后点“恢复隐藏”回到默认只看未闭环的状态。
            toggle = (f"<a href='/disease?month={esc(month)}&show_closed=0'>"
                      "<button type='button'>恢复隐藏</button></a>"
                      if show_closed else
                      f"<a href='/disease?month={esc(month)}&show_closed=1'>"
                      "<button type='button'>取消隐藏</button></a>")
            body = (f"<p class='note'>{esc(note)}</p>"
                    f"<form>月份：<input name='month' value='{esc(month)}'>"
                    "<input type='submit' value='查看'></form>"
                    f"<p class='note'>共 {len(rows)} 条，"
                    f"隐藏 {len(hidden_rows)} 条"
                    "（仅当月、状态 5 且按期完成才隐藏，已完结月份全显）。"
                    f" {toggle}</p>"
                    + trend
                    + render.table(
                        ["序号"] + disease_live.COMPANY_COLUMNS + ["巡查记录编号"],
                        company_rows,
                        lambda r: disease_status.color_for(
                            str(r.get("状态码", ""))[:1]),
                        cls="grid"))
            return self._send(render.page(f"病害台账（{esc(month)}）", body))

        if path == "/patrol":
            # 巡查页只做两件事：上面查询 + 趋势，下面接巡查记录台账。
            # 新增巡查记录、本机新增统计、本机新增记录表、生成巡查报告都已去掉。
            # 巡查次数只按巡查记录编号去重算，不算发现病害数，不算完成率。
            view = (query.get("view") or ["day"])[0]
            if view not in ("day", "month"):
                view = "day"
            # 默认日期取当天（服务器本地日期），不再写死 2026-11-04：
            # 以前不带日期打开巡查页，永远看到的是 11 月 4 日那天的记录。
            label = (query.get("date") or
                     [datetime.date.today().isoformat()])[0]
            keyword = (query.get("q") or [""])[0]
            month_label = label[:7]
            if view == "month":
                label = month_label
            day_label = label if len(label) == 10 else month_label + "-01"
            # 每日 / 每月用按钮切换，不用下拉框。
            toggle = (
                f"<a href='/patrol?view=day&date={esc(day_label)}&q={esc(keyword)}'>"
                f"<button type='button'{' disabled' if view == 'day' else ''}>每日</button></a> "
                f"<a href='/patrol?view=month&date={esc(month_label)}&q={esc(keyword)}'>"
                f"<button type='button'{' disabled' if view == 'month' else ''}>每月</button></a>")
            form = (f"<p>{toggle}</p>"
                    "<form>日期/月份：<input name='date' value='" + esc(label) + "'>"
                    " 关键词（巡查人/路段/记录编号）：<input name='q' value='" + esc(keyword) + "'>"
                    f"<input type='hidden' name='view' value='{view}'>"
                    "<input type='submit' value='查看'></form>")
            d_rows, _d_note, _d_xlsx = load_disease_month(month_label)
            # 巡查优先读采集脚本单独写的月度巡查台账（有病害没病害的巡查都在里面）；
            # 巡查台账文件还没生成时，回落到按病害表推导的老口径（那时没病害的巡查不在内）。
            p_rows, _p_note, p_found = patrol_excel.read_patrol_month(DISEASE_DIR, month_label)
            if view == "day":
                # 每日：趋势是当月每天的巡查次数，台账是当天的巡查记录。
                if p_found:
                    daily_patrols = disease_patrol.daily_patrol_counts(p_rows, month_label)
                    ledger = disease_patrol.ledger_from_patrol_rows(p_rows, "day", label, keyword)
                else:
                    _daily_diseases, daily_patrols = charts.daily_counts(d_rows, month_label)
                    ledger = disease_patrol.patrol_ledger(d_rows, "day", label, keyword)
                trend = (f"<h3>趋势图（{esc(month_label)}，每日巡查次数）</h3>"
                         + charts.svg_bars(daily_patrols, "每日巡查次数（去重巡查记录编号）",
                                           bar_color="#6aa84f", width=1100))
                total_patrols = len(ledger)
                total_diseases = sum(r["发现病害数"] for r in ledger)
            else:
                # 每月：趋势是各月的巡查次数，台账是当月的巡查记录。
                monthly_pairs = []
                for m in disease_patrol.monthly_patrol_counts(DISEASE_DIR):
                    m_p_rows, _m_p_note, m_p_found = patrol_excel.read_patrol_month(DISEASE_DIR, m)
                    if m_p_found:
                        m_stat = disease_patrol.summarize_from_patrol_rows(m_p_rows, "month", m)
                    else:
                        m_rows, _m_note, _m_xlsx = load_disease_month(m)
                        m_stat = disease_patrol.summarize_from_diseases(m_rows, "month", m)
                    monthly_pairs.append((m, m_stat["patrols"]))
                trend = ("<h3>趋势图（各月巡查次数）</h3>"
                         + charts.svg_bars(monthly_pairs, "每月巡查次数（去重巡查记录编号）",
                                           bar_color="#6aa84f", width=1100))
                if p_found:
                    ledger = disease_patrol.ledger_from_patrol_rows(p_rows, "month", month_label, keyword)
                else:
                    ledger = disease_patrol.patrol_ledger(d_rows, "month", month_label, keyword)
                total_patrols = len(ledger)
                total_diseases = sum(r["发现病害数"] for r in ledger)
            ledger_rows = ledger + [{"发现日期": "合计", "巡查人": "", "路段名称": "",
                                    "巡查记录编号": f"共 {total_patrols} 次",
                                    "发现病害数": total_diseases}]
            body = (form
                    + trend
                    + f"<h3>巡查记录台账（{'每日' if view == 'day' else '每月'}，{esc(label)}）</h3>"
                    "<p class='note'>只统计巡查次数（去重巡查记录编号），不算完成率。"
                    + ("口径：巡查台账由采集脚本每 15 分钟从平台同步，"
                       "8 名监理的巡查全在里面（含未发现病害的）。"
                       if p_found else
                       "口径：巡查台账文件尚未生成，暂按月度病害表推导——"
                       "月度病害表里只有发现了病害的巡查，没发现病害的巡查不在表里，"
                       "所以次数是下限，会比真实巡查次数少。")
                    + "里程待接平台（巡查记录里没有里程字段），这里不编造。</p>"
                    + render.table(["发现日期", "巡查人", "路段名称", "巡查记录编号", "发现病害数"],
                                   ledger_rows))
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
                    "巡查发现的问题：<br><textarea name='problem' rows='4' cols='60'>"
                    + esc(problem) + "</textarea><br>"
                    "危害后果：<br><textarea name='hazard' rows='2' cols='60'>"
                    + esc(hazard) + "</textarea><br>"
                    "合同 / 规范依据：<br><textarea name='basis' rows='2' cols='60'>"
                    + esc(basis) + "</textarea><br>"
                    "逾期责任：<br><textarea name='overdue' rows='2' cols='60'>"
                    + esc(overdue) + "</textarea><br>"
                    "<input type='submit' value='生成指令草稿'></form>")
            # 本地已有指令示例：只在 Mac 本地版有 local_examples.py 时才显示入口，
            # 示例列表（编号、标题、正文）全由那个文件提供，公开版看不到。
            example_block = ""
            if local_examples is not None:
                examples = getattr(local_examples, "EXAMPLES", [])
                selected = (query.get("example") or [""])[0]
                shown = None
                links = []
                for key, label, text in examples:
                    links.append(
                        f"<a href='/instruction?example={key}'>"
                        f"看本地已有指令示例（{esc(label)}）</a>")
                    if selected == key:
                        shown = (label, text)
                if shown:
                    example_block = (
                        f"<h3>本地已有指令示例（{esc(shown[0])}）</h3>"
                        "<p class='note'>仅对照格式用，不替换你现在用的指令模板。</p>"
                        f"<pre style='white-space:pre-wrap'>{esc(shown[1])}</pre>")
                elif links:
                    example_block = "<p>" + " ｜ ".join(links) + "</p>"
            # 监理指令台账：只在 Mac 本地版有 data/instruction_ledger.json 时才显示，
            # 台账数据（编号、标题、正文）全在那个文件里，run.py 里只有表头和查看逻辑，
            # 不含任何真实指令内容，所以这段代码可以进公开库。公开版没有这个文件时，
            # 指令页就是原来的填表 + 示例，不多出空台账。
            # 流程：你在聊天里发大概内容，助理成稿、你点头后，助理把成稿续进这个台账。
            ledger_block = ""
            ledger_path = os.path.join(BASE, "data", "instruction_ledger.json")
            if os.path.exists(ledger_path):
                try:
                    with open(ledger_path, encoding="utf-8") as f:
                        ledger = json.load(f).get("instructions", [])
                except Exception:
                    ledger = []
                if ledger:
                    ledger_rows = []
                    for i, item in enumerate(ledger):
                        ledger_rows.append({
                            "序号": str(i + 1),
                            "编号": esc(item.get("编号", "")),
                            "标题": esc(item.get("标题", "")),
                            "致": esc(item.get("致", "")),
                            "签发人": esc(item.get("签发人", "")),
                            "签发日期": esc(item.get("签发日期", "")),
                            "备注": esc(item.get("备注", "")),
                            "全文": f"<a href='/instruction?doc={i}'>查看全文</a>",
                        })
                    ledger_block = (
                        "<h3>监理指令台账</h3>"
                        "<p class='note'>已归档的指令都在这里，点查看全文看正文；"
                        "新指令成稿后由助理续进台账。</p>"
                        + render.table(
                            ["序号", "编号", "标题", "致", "签发人", "签发日期",
                             "备注", "全文"], ledger_rows))
                    doc_idx = (query.get("doc") or [""])[0]
                    if doc_idx.isdigit() and int(doc_idx) < len(ledger):
                        item = ledger[int(doc_idx)]
                        ledger_block += (
                            f"<h3>{esc(item.get('编号', ''))} "
                            f"{esc(item.get('标题', ''))}</h3>"
                            f"<pre style='white-space:pre-wrap'>"
                            f"{esc(item.get('正文', ''))}</pre>"
                            "<p><a href='/instruction'>回指令页</a></p>")
            # 左填右预览：左边填，右边实时出草稿，病害页“出文档”带过来的问题已填在左边。
            body = ("<div style='display:flex;gap:20px;align-items:flex-start'>"
                    f"<div style='flex:1'>{form}</div>"
                    "<div style='flex:1;border:1px solid #ccc;padding:12px'>"
                    "<h3>预览</h3>"
                    "<p class='note'>只套既有模板格式，不替你定责任，缺的留空。</p>"
                    + (f"<pre style='white-space:pre-wrap'>{esc(draft)}</pre>" if draft else
                       "<p class='note'>左边填完点“生成指令草稿”，草稿出现在这里。</p>")
                    + "</div></div>" + example_block + ledger_block)
            return self._send(render.page("监理指令", body))

        if path == "/map.png":
            # 本机图片：工作台文件夹里有“管养路段示意图.png”才返回，否则 404，
            # 首页自动退回占位说明。图片本身不提交进公开库。
            map_file = os.path.join(BASE, "管养路段示意图.png")
            if os.path.exists(map_file):
                with open(map_file, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"not found")

    def do_POST(self):
        # 新增巡查记录功能已去掉，POST 统一返回 404，不再写本地数据库。
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print(f"监理工作台：http://127.0.0.1:{PORT}/ （只绑本机，按 Ctrl+C 停止）")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
