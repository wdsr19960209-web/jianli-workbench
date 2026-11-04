# 公共页面渲染：所有页面共用同一套样式，表格上下左右居中。

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  margin:24px auto;max-width:1200px;padding:0 16px;color:#222}
nav a{margin-right:16px}
table{border-collapse:collapse;width:100%;table-layout:auto;margin-top:12px}
th,td{border:1px solid #ccc;padding:8px;text-align:center;vertical-align:middle;word-break:break-word}
th{background:#f2f2f2}
.note{color:#666;font-size:14px}
input,textarea,select{padding:6px;margin:4px 0}
"""

# 五个页签，与预览第四版起的结构一致：监理问题那页已去掉，不再出现在导航里。
NAV = ('<nav><a href="/">首页 · 工程概括</a><a href="/patrol">巡查统计</a>'
       '<a href="/safety">安全文件台账</a><a href="/disease">病害台账</a>'
       '<a href="/instruction">监理指令</a></nav><hr>')


def page(title, body):
    return ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>{title}</title><style>{CSS}</style></head><body>"
            f"{NAV}<h1>{title}</h1>{body}</body></html>")


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
    return f"<table><tr>{head}</tr>{body}</table>"
