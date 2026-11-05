# 公共页面渲染：所有页面共用同一套样式，表格上下左右居中。
# 界面风格（2026-11-05 用户要求简单好看后重做）：
# 参考 GitHub 上 AdminLTE、TailAdmin、shadcn 风格管理后台的共性做法，
# 但不引 Bootstrap、Tailwind 或任何外部文件，样式全部手写内联在这一处，
# 本机离线也能打开：浅灰底 + 白色内容区 + 一个主色 + 圆角卡片式表格，
# 导航做成顶部 pill 按钮，当前页高亮，别的什么都不加。

CSS = """
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  margin:0;background:#f3f4f6;color:#1f2937;line-height:1.6}
a{color:#2563eb;text-decoration:none}
a:hover{text-decoration:underline}
.topbar{background:#fff;border-bottom:1px solid #e5e7eb}
.topbar .wrap{display:flex;align-items:center;gap:24px;flex-wrap:wrap;padding:14px 20px}
.brand{font-size:17px;font-weight:700;color:#111827;white-space:nowrap}
nav a{display:inline-block;padding:7px 14px;border-radius:999px;color:#4b5563}
nav a:hover{background:#eff6ff;text-decoration:none}
nav a.active{background:#2563eb;color:#fff}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 40px}
h1{font-size:22px;margin:24px 0 4px;color:#111827}
h3{font-size:16px;margin:26px 0 10px;padding-left:10px;border-left:4px solid #2563eb;color:#111827}
table{border-collapse:collapse;width:100%;margin-top:12px;background:#fff;
  border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}
th,td{padding:9px 10px;text-align:center;vertical-align:middle;word-break:break-word;
  border-bottom:1px solid #eef2f7;font-size:14px}
th{background:#f8fafc;color:#374151;font-weight:600}
tr:hover{background:#f9fafb}
.note{color:#6b7280;font-size:13px}
input,textarea,select{padding:8px 10px;margin:4px 0;border:1px solid #d1d5db;
  border-radius:8px;background:#fff;font-size:14px}
input[type=submit],button{padding:8px 16px;border:none;border-radius:8px;
  background:#2563eb;color:#fff;cursor:pointer;font-size:14px}
input[type=submit]:hover,button:hover{background:#1d4ed8}
button:disabled{background:#9ca3af;cursor:default}
pre{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:14px;overflow:auto}
thead th{position:sticky;top:36px;z-index:2}
.sticky-note{position:sticky;top:0;background:#fff;z-index:3;padding:6px 0;
  font-size:13px;color:#374151;border-bottom:1px solid #e5e7eb}
"""

# 五个页签，与预览第四版起的结构一致：监理问题那页已去掉，不再出现在导航里。
NAV_ITEMS = [("/", "首页 · 工程概括"), ("/patrol", "巡查统计"),
             ("/safety", "安全文件台账"), ("/disease", "病害台账"),
             ("/instruction", "监理指令")]


def _nav(title):
    links = []
    for href, label in NAV_ITEMS:
        active = ""
        if ((href == "/" and title.startswith("首页"))
                or (href == "/patrol" and title.startswith("巡查"))
                or (href == "/safety" and title.startswith("安全"))
                or (href == "/disease" and title.startswith("病害"))
                or (href == "/instruction" and title.startswith("监理指令"))):
            active = " class='active'"
        links.append(f"<a href='{href}'{active}>{label}</a>")
    return ("<header class='topbar'><div class='wrap'>"
            "<span class='brand'>安阳驻地办 · 监理工作台</span>"
            f"<nav>{''.join(links)}</nav></div></header>")


def page(title, body):
    return ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>{title}</title><style>{CSS}</style></head><body>"
            f"{_nav(title)}<main class='wrap'><h1>{title}</h1>{body}</main></body></html>")


def table(headers, rows, row_color=None):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        color = row_color(row) if row_color else ""
        style = f" style='background:{color}'" if color else ""
        cells = "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
        body += f"<tr{style}>{cells}</tr>"
    if not rows:
        body = f"<tr><td colspan='{len(headers)}'>暂无数据</td></tr>"
    # 表头放进 thead，配合 CSS 里的 sticky：往下翻页时表头停在顶部不动。
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
