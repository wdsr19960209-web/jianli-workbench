# 病害处置台账：只读展示，不采集、不写表。
# 本骨架只读 CSV 示例格式。真实月度 Excel 接入时，另写 disease_excel.py，
# 绝不动 Mac 上正在跑的那套采集脚本。

import csv
import os

import gongqu

# 示例月度表的列（与真实月度表列名保持一致的方向，示例数据是假的）
COLUMNS = ["病害编号", "路线", "路段", "方向", "桩号", "病害类型", "病害数量",
           "单位", "巡查人", "责任单位", "发现日期", "是否处置", "处置完成日期",
           "整改措施", "整改期限", "逾期状态", "状态码", "备注",
           "巡查记录编号", "维修单号"]

# 公司在线表的前 12 列（用户 2026-11-04 按公司在线表截图定的列序）。
# 照这个顺序复制，正好一列对一列粘到公司在线表；状态码是内部字段，排在后面。
COMPANY_COLUMNS = ["发现病害日期", "所属标段", "路段名称", "桩号（位置）",
                   "幅别", "巡查人", "数量", "单位", "病害", "整改措施",
                   "整改时限", "病害下发方式", "状态码"]


def to_company_row(row):
    """把内部行换成公司在线表 12 列 + 状态码。病害下发方式在示例里没有字段，
    不擅自统一填，留“待填写”，等用户定下统一填什么再改。"""
    road = row.get("路线", "")
    return {
        "发现病害日期": row.get("发现日期", ""),
        "所属标段": gongqu.gongqu_for(road, row.get("桩号", "")),
        "路段名称": (road + row.get("路段", "")).strip(),
        "桩号（位置）": row.get("桩号", ""),
        "幅别": row.get("方向", ""),
        "巡查人": row.get("巡查人", ""),
        "数量": row.get("病害数量", ""),
        "单位": row.get("单位", ""),
        "病害": row.get("病害类型", ""),
        "整改措施": row.get("整改措施", ""),
        "整改时限": row.get("整改期限", ""),
        "病害下发方式": "待填写",
        "状态码": row.get("状态码", ""),
    }


def read_month_csv(directory, month):
    """month 形如 2026-11。返回 (rows, note)。找不到文件时返回空表。"""
    if not directory:
        return [], "未配置 DISEASE_LEDGER_DIR，当前显示为空。"
    path = os.path.join(directory, f"disease_{month}.csv")
    if not os.path.exists(path):
        # 示例目录用 disease_<月>_example.csv，演示用，不混入真实数据
        alt = os.path.join(directory, f"disease_{month}_example.csv")
        if os.path.exists(alt):
            path = alt
        else:
            return [], f"未找到 {month} 的月度文件（{path}），当前显示为空。"
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({c: (row.get(c) or "") for c in COLUMNS})
    return rows, f"来源：本机月度 CSV（{path}），只读展示"
