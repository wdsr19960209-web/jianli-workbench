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
