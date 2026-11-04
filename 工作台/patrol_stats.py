# 巡查统计：只算巡查次数，不算完成率。
# 用户 2026-11-04 明确纠正：巡查本身没有完成率，只看当日巡查轨迹。
# 时间范围只剩每日和每月，不用 7D/2W/4W 那套英文缩写。
# 本骨架只按本地巡查记录算次数；里程和发现病害数要等智养平台字段确认
# （巡查记录里程字段名目前未知，病害靠巡查记录编号 XCJL… 关联），
# 在接通之前不编造这两个数，页面上如实标“待接平台”。

from collections import Counter


def summarize(records, period):
    """records 为巡查记录 dict 列表；period 为 'day' 或 'month'。

    返回 {"total": 总次数, "per_person": {人名: 次数}}。
    按日时调用方先把 records 筛到某一天，按月时筛到某一个月。
    """
    counts = Counter(r.get("recorder", "") for r in records)
    counts.pop("", None)
    return {"total": len(records), "per_person": dict(counts)}


def filter_by_period(records, period, label):
    """label 按日形如 2026-11-04，按月形如 2026-11；日期字段为空的行不计入。"""
    if period == "month":
        return [r for r in records if str(r.get("date", "")).startswith(label)]
    return [r for r in records if str(r.get("date", "")) == label]
