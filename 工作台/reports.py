# 周报 / 月报：只做计数汇总，不编造内容、不替你写结论。

from collections import Counter


def summarize(patrol_rows, issue_rows, disease_rows):
    issues = Counter(r.get("status", "") for r in issue_rows)
    disease = Counter(r.get("状态码", "") for r in disease_rows)
    return {
        "巡查记录条数": len(patrol_rows),
        "监理问题条数": len(issue_rows),
        "监理问题按状态": dict(issues),
        "病害条数": len(disease_rows),
        "病害按状态码": dict(disease),
    }
