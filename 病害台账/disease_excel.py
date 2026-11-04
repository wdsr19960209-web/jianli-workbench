# 病害月度 xlsx：纯标准库读取，不装 openpyxl，不碰采集脚本。
# 月度表是 Mac 上病害脚本用 openpyxl 写的，工作表名固定为“病害处置台账”，
# 第一行是列名（与 disease_live.COLUMNS 一致），状态 5 按期完成的行在当月
# 是 Excel 行隐藏（已完结月份取消隐藏），这里把隐藏标记也读出来。
# xlsx 本质是 zip + xml：共享字符串在 xl/sharedStrings.xml，
# 工作表在 xl/worksheets/sheet*.xml，工作表名到文件的对应在
# xl/workbook.xml 和 xl/_rels/workbook.xml.rels 里。
# 日期在月度表里本来就是字符串（脚本的 dstr），所以这里不猜数字日期格式；
# 桩号是数字时按原值返回，调用方需要显示时再格式化。

import os
import re
import xml.etree.ElementTree as ET
import zipfile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}

SHEET_NAME = "病害处置台账"


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _shared_strings(zf):
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root:
        parts = []
        for node in si.iter():
            if _local(node.tag) == "t":
                parts.append(node.text or "")
        out.append("".join(parts))
    return out


def _sheet_path(zf, wanted):
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return "xl/worksheets/sheet1.xml"
    rel_map = {}
    for rel in rels:
        rel_map[rel.get("Id")] = rel.get("Target")
    for sheet in wb.iter():
        if _local(sheet.tag) != "sheet":
            continue
        if sheet.get("name") == wanted:
            rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rid, "worksheets/sheet1.xml")
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            return target
    return "xl/worksheets/sheet1.xml"


def _col_index(ref):
    match = re.match(r"([A-Z]+)", ref or "")
    if not match:
        return 0
    n = 0
    for ch in match.group(1):
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _cell_value(cell, shared):
    ctype = cell.get("t")
    if ctype == "s":
        idx = cell.find("m:v", NS)
        if idx is None or idx.text is None:
            return ""
        try:
            return shared[int(idx.text)]
        except (ValueError, IndexError):
            return ""
    if ctype == "inlineStr":
        parts = [n.text or "" for n in cell.iter()
                 if _local(n.tag) == "t"]
        return "".join(parts)
    if ctype == "str":
        v = cell.find("m:v", NS)
        return v.text if v is not None else ""
    if ctype == "b":
        v = cell.find("m:v", NS)
        return "是" if v is not None and v.text == "1" else ""
    v = cell.find("m:v", NS)
    if v is None or v.text is None:
        return ""
    text = v.text
    try:
        num = float(text)
    except ValueError:
        return text
    if num == int(num):
        return int(num)
    return num


def read_month_xlsx(directory, month):
    """month 形如 2026-11。返回 (rows, note)。
    rows 每行是 {列名: 值}，另带内部键“_行已隐藏”（True/False），
    调用方展示时不把这个键当列显示。找不到文件时返回空表，不报错。"""
    if not directory:
        return [], "未配置 DISEASE_LEDGER_DIR，当前显示为空。"
    path = os.path.join(directory, "病害处置台账_%s.xlsx" % month)
    if not os.path.exists(path):
        return [], "未找到 %s 的月度表（%s），当前显示为空。" % (month, path)
    try:
        with zipfile.ZipFile(path) as zf:
            shared = _shared_strings(zf)
            sheet_path = _sheet_path(zf, SHEET_NAME)
            root = ET.fromstring(zf.read(sheet_path))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        return [], "月度表 %s 读取失败：%s" % (os.path.basename(path), exc)
    headers = []
    rows = []
    for row in root.iter():
        if _local(row.tag) != "row":
            continue
        if row.get("r") == "1" or not headers:
            # 第一行是表头；如果表头行不是 r=1，按遇到的第一行算表头
            pass
        cells = {}
        for cell in row:
            if _local(cell.tag) != "c":
                continue
            cells[_col_index(cell.get("r"))] = _cell_value(cell, shared)
        if not headers:
            headers = [str(cells.get(i, "")).strip()
                       for i in range(1, max(cells) + 1 if cells else 1)]
            continue
        item = {}
        for i, name in enumerate(headers, 1):
            if name:
                item[name] = cells.get(i, "")
        if any(str(v).strip() for v in item.values()):
            item["_行已隐藏"] = row.get("hidden") in ("1", "true")
            rows.append(item)
    return rows, "来源：本机月度 xlsx（%s），只读展示" % path
