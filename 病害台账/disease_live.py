# 病害处置台账：只读展示，不采集、不写表。
# 本骨架只读 CSV 示例格式。真实月度 Excel 接入时，另写 disease_excel.py，
# 绝不动 Mac 上正在跑的那套采集脚本。

import csv
import os

# 示例月度表的列（与真实月度表列名保持一致的方向，示例数据是假的）
COLUMNS = ["病害编号", "路线", "路段", "方向", "桩号", "病害类型", "病害数量",
           "单位", "巡查人", "责任单位", "发现日期", "是否处置", "处置完成日期",
           "整改措施", "整改期限", "逾期状态", "状态码", "备注",
           "巡查记录编号", "维修单号"]


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
