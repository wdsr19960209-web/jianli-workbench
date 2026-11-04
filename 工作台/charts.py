# 趋势图：纯标准库生成内联 SVG 柱状图，不引外部图表库。
# 预览第二十四版的结构是“上面趋势图、下面正式台账”，这里的图就是上面那一段。
# 数据全部来自调用方传进来的真实台账行，缺数据时返回空串，不画假图。


def svg_bars(pairs, title, bar_color="#4472c4", width=720, height=180):
    """pairs 为 [(标签, 数值), ...]，数值<=0 的也画（高度为 0 的基线）。
    标签过长时只显示后 5 个字，避免挤在一起。"""
    pairs = [(str(label), int(value)) for label, value in pairs]
    if not pairs:
        return ""
    max_value = max(v for _, v in pairs) or 1
    n = len(pairs)
    slot = width / n
    bar_w = max(4.0, slot * 0.6)
    top, bottom = 20, height - 24
    plot_h = bottom - top
    parts = [f"<svg width='{width}' height='{height}' "
             f"style='background:#fafafa;border:1px solid #ddd'>",
             f"<text x='8' y='14' font-size='13'>{title}</text>"]
    for i, (label, value) in enumerate(pairs):
        x = slot * i + (slot - bar_w) / 2
        h = plot_h * value / max_value
        y = bottom - h
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' "
                     f"height='{h:.1f}' fill='{bar_color}'/>")
        if value:
            parts.append(f"<text x='{x + bar_w / 2:.1f}' y='{y - 3:.1f}' "
                         f"font-size='11' text-anchor='middle'>{value}</text>")
        short = label[-5:] if len(label) > 5 else label
        parts.append(f"<text x='{x + bar_w / 2:.1f}' y='{height - 6}' "
                     f"font-size='11' text-anchor='middle'>{short}</text>")
    parts.append("</svg>")
    return "".join(parts)


def daily_counts(rows, month):
    """从月度病害行里按发现日期算：每天的病害条数、去重巡查次数。
    返回 ([(日期, 病害数)], [(日期, 巡查数)])，日期按升序排。"""
    from collections import Counter, defaultdict
    diseases = Counter()
    patrols = defaultdict(set)
    for r in rows:
        date = str(r.get("发现日期", "")).strip()
        if not date.startswith(month):
            continue
        diseases[date] += 1
        code = str(r.get("巡查记录编号", "")).strip()
        if code:
            patrols[date].add(code)
    days = sorted(diseases)
    return ([(d, diseases[d]) for d in days],
            [(d, len(patrols[d])) for d in days])


def per_person_discovered(rows, month):
    """每人发现病害数（第二十四版小图只剩这一张，已处置图已删）。"""
    from collections import Counter
    counts = Counter()
    for r in rows:
        date = str(r.get("发现日期", "")).strip()
        person = str(r.get("巡查人", "")).strip()
        if date.startswith(month) and person:
            counts[person] += 1
    return sorted(counts.items())
