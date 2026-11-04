# 安全文件台账：只读。
# 读本机 CSV，不写、不改状态、不自动采集。登记仍走在线表。

import csv
import os

COLUMNS = ["序号", "类型", "文件名/通知摘要", "文件类型", "文件日期/通知日期",
           "登记日期", "分类", "关键词", "来源", "初步判断", "处理状态", "备注"]


def read_safety_ledger(csv_path):
    """返回 (rows, source_note)。文件不存在时返回空表，不报错、不编造。"""
    if not csv_path or not os.path.exists(csv_path):
        return [], "未找到本机安全台账 CSV，当前显示为空。请在 .env 里填 SAFETY_LEDGER_CSV。"
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({c: (row.get(c) or "") for c in COLUMNS})
    return rows, f"来源：本机 CSV（{csv_path}），只读展示"
