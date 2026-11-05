# 巡查统计：优先读采集脚本单独写的月度巡查台账（巡查记录台账_YYYY-MM.xlsx），
# 有病害没病害的巡查都在里面，一行就是一次巡查。
# 巡查台账文件还没生成时（老数据），回落到从月度病害表推导的老口径：
# 月度病害表里只有“发现了病害的巡查”，没发现病害的巡查不在表里，
# 所以那时算出来的次数是下限，会比真实巡查次数少，页面上要写清楚。
# 里程在这里算不出来：病害记录里没有里程字段，巡查记录对象也是空的，
# 在智养巡查记录里里程字段名确认之前，里程一律标“待接平台”，不编造。

from collections import Counter, defaultdict


def _disease_count(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def ledger_from_patrol_rows(rows, period, label, keyword=""):
    """巡查记录台账文件已是一行一次巡查：只按日期/关键词过滤、按日期倒序排。
    rows 每行：巡查日期/巡查人/路段名称/巡查记录编号/发现病害数。
    巡查记录编号去重（同一编号只留一行），次数口径与老推导一致。"""
    out = []
    seen = set()
    for r in rows:
        date = str(r.get("巡查日期", "")).strip()
        if period == "month":
            if not date.startswith(label):
                continue
        elif date != label:
            continue
        person = str(r.get("巡查人", "")).strip()
        road = str(r.get("路段名称", "")).strip()
        code = str(r.get("巡查记录编号", "")).strip()
        if code in seen:
            continue
        seen.add(code)
        if keyword and keyword not in (person + road + code):
            continue
        out.append({"发现日期": date, "巡查人": person, "路段名称": road,
                    "巡查记录编号": code,
                    "发现病害数": _disease_count(r.get("发现病害数"))})
    out.sort(key=lambda x: (x["发现日期"], x["巡查人"], x["巡查记录编号"]),
             reverse=True)
    return out


def summarize_from_patrol_rows(rows, period, label):
    """从巡查台账行算巡查次数与病害条数（巡查记录编号去重）。
    返回 {"patrols": 巡查次数, "diseases": 病害条数, "per_person": {}}。"""
    if period == "month":
        picked = [r for r in rows if str(r.get("巡查日期", "")).startswith(label)]
    else:
        picked = [r for r in rows if str(r.get("巡查日期", "")) == label]
    codes = {str(r.get("巡查记录编号", "")).strip() for r in picked}
    codes.discard("")
    return {"patrols": len(codes),
            "diseases": sum(_disease_count(r.get("发现病害数")) for r in picked),
            "per_person": {}}


def daily_patrol_counts(rows, month):
    """从巡查台账行算当月每天的巡查次数：[(日期, 次数)] 按日期升序。
    每天按巡查记录编号去重。"""
    seen = defaultdict(set)
    for r in rows:
        date = str(r.get("巡查日期", "")).strip()
        code = str(r.get("巡查记录编号", "")).strip()
        if date.startswith(month) and code:
            seen[date].add(code)
    return [(d, len(seen[d])) for d in sorted(seen)]


def summarize_from_diseases(rows, period, label):
    """rows 为月度病害行（内部列名）。period 为 'day' 或 'month'，
    label 按日形如 2026-11-04，按月形如 2026-11。
    返回 {"patrols": 去重巡查次数, "diseases": 病害条数,
          "per_person": {人名: {"patrols": 次数, "diseases": 条数}}}。"""
    if period == "month":
        picked = [r for r in rows if str(r.get("发现日期", "")).startswith(label)]
    else:
        picked = [r for r in rows if str(r.get("发现日期", "")) == label]
    per_person = {}
    seen = defaultdict(set)
    disease_counts = Counter()
    for r in picked:
        person = str(r.get("巡查人", "")).strip()
        code = str(r.get("巡查记录编号", "")).strip()
        if not person:
            continue
        disease_counts[person] += 1
        if code:
            seen[person].add(code)
    for person in disease_counts:
        per_person[person] = {"patrols": len(seen[person]),
                              "diseases": disease_counts[person]}
    total_patrols = sum(v["patrols"] for v in per_person.values())
    return {"patrols": total_patrols, "diseases": len(picked),
            "per_person": per_person}


def patrol_ledger(rows, period, label, keyword=""):
    """巡查记录台账：按巡查记录编号去重，一条巡查记录就是一行。
    period 为 'day' 或 'month'，label 按日形如 2026-11-04，按月形如 2026-11。
    每行：发现日期、巡查人、路段名称、巡查记录编号、发现病害数。
    只有发现了病害的巡查才在月度病害表里，没病害的巡查不在表里。"""
    grouped = {}
    for r in rows:
        date = str(r.get("发现日期", "")).strip()
        code = str(r.get("巡查记录编号", "")).strip()
        if period == "month":
            if not date.startswith(label):
                continue
        elif date != label:
            continue
        if not code:
            continue
        person = str(r.get("巡查人", "")).strip()
        road = (str(r.get("路线", "")).strip()
                + str(r.get("路段", "")).strip())
        item = grouped.setdefault(code, {"date": date, "person": person,
                                         "roads": set(), "diseases": 0})
        item["roads"].add(road)
        item["diseases"] += 1
        if date < item["date"]:
            item["date"] = date
    out = []
    for code, item in grouped.items():
        road = " / ".join(sorted(x for x in item["roads"] if x))
        if keyword and keyword not in (item["person"] + road + code):
            continue
        out.append({"发现日期": item["date"], "巡查人": item["person"],
                    "路段名称": road, "巡查记录编号": code,
                    "发现病害数": item["diseases"]})
    out.sort(key=lambda x: (x["发现日期"], x["巡查人"], x["巡查记录编号"]),
             reverse=True)
    return out


def monthly_patrol_counts(directory):
    """扫台账文件夹，返回 [月份, ...] 按月升序；
    巡查台账文件和月度病害表都扫（巡查台账优先，病害表是回落）。
    各月的巡查次数由调用方按月读表后算，见 run.py 巡查页每月趋势。"""
    import os
    import re
    months = set()
    if directory and os.path.isdir(directory):
        for name in os.listdir(directory):
            match = re.match(r"巡查记录台账_(\d{4}-\d{2})\.xlsx$", name)
            if match:
                months.add(match.group(1))
            match = re.match(r"病害处置台账_(\d{4}-\d{2})\.xlsx$", name)
            if match:
                months.add(match.group(1))
            match = re.match(r"disease_(\d{4}-\d{2})(?:_example)?\.csv$", name)
            if match:
                months.add(match.group(1))
    # 读表要走 run.py 的 load_disease_month / patrol_excel，这里只做月份扫描；
    # 真正的按月计数由调用方按月读表后算，避免 disease_patrol 反向依赖 run.py。
    return sorted(months)
