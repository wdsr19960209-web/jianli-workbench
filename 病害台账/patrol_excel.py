# 巡查月度 xlsx：采集脚本每 15 分钟写的巡查记录台账（巡查记录台账_YYYY-MM.xlsx），
# 工作表名固定为“巡查记录台账”。有病害没病害的巡查都在里面，一行就是一次巡查。
# 解析复用 disease_excel 的标准库 zip+xml 读法，不装 openpyxl。
import os
import xml.etree.ElementTree as ET
import zipfile

import disease_excel

SHEET_NAME = "巡查记录台账"


def read_patrol_month(directory, month):
    """month 形如 2026-11。返回 (rows, note, found)。
    rows 每行：巡查日期/巡查人/路段名称/巡查记录编号/发现病害数（发现病害数为整数）。
    找不到文件时 found=False，返回空表，不报错；调用方回落到按病害表推导的老口径。"""
    if not directory:
        return [], "未配置 DISEASE_LEDGER_DIR，当前显示为空。", False
    path = os.path.join(directory, "巡查记录台账_%s.xlsx" % month)
    if not os.path.exists(path):
        return [], "未找到 %s 的巡查台账（%s），当前显示为空。" % (month, path), False
    try:
        with zipfile.ZipFile(path) as zf:
            shared = disease_excel._shared_strings(zf)
            sheet_path = disease_excel._sheet_path(zf, SHEET_NAME)
            root = ET.fromstring(zf.read(sheet_path))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        return [], "巡查台账 %s 读取失败：%s" % (os.path.basename(path), exc), True
    headers = []
    rows = []
    for row in root.iter():
        if disease_excel._local(row.tag) != "row":
            continue
        cells = {}
        for cell in row:
            if disease_excel._local(cell.tag) != "c":
                continue
            cells[disease_excel._col_index(cell.get("r"))] = disease_excel._cell_value(cell, shared)
        if not headers:
            headers = [str(cells.get(i, "")).strip()
                       for i in range(1, max(cells) + 1 if cells else 1)]
            continue
        item = {}
        for i, name in enumerate(headers, 1):
            if name:
                item[name] = cells.get(i, "")
        if any(str(v).strip() for v in item.values()):
            rows.append(item)
    return rows, "来源：本机巡查台账 xlsx（%s），只读展示" % path, True
