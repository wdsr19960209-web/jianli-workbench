# 巡查统计（从月度病害表推导）：按巡查记录编号去重算巡查次数。
# 口径必须写清楚：月度病害表里只有“发现了病害的巡查”，
# 没发现病害的巡查不在表里，所以这里算出来的次数是下限，会比真实巡查次数少。
# 里程在这里算不出来：病害记录里没有里程字段，巡查记录对象也是空的，
# 在智养巡查记录里里程字段名确认之前，里程一律标“待接平台”，不编造。

from collections import Counter, defaultdict


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
    """扫月度表文件夹，返回 [月份, ...] 按月升序；
    各月的巡查次数由调用方按月读表后算，见 run.py 巡查页每月趋势。"""
    import os
    import re
    months = set()
    if directory and os.path.isdir(directory):
        for name in os.listdir(directory):
            match = re.match(r"病害处置台账_(\d{4}-\d{2})\.xlsx$", name)
            if match:
                months.add(match.group(1))
            match = re.match(r"disease_(\d{4}-\d{2})(?:_example)?\.csv$", name)
            if match:
                months.add(match.group(1))
    # 读表要走 run.py 的 load_disease_month，这里只做月份扫描；
    # 真正的按月计数由调用方按月读表后用 summarize_from_diseases 算，
    # 避免 disease_patrol 反向依赖 run.py。
    return sorted(months)
