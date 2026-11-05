# 趋势图：纯标准库生成内联 SVG 柱状图，不引外部图表库。
# 预览第二十四版的结构是“上面趋势图、下面正式台账”，这里的图就是上面那一段。
# 数据全部来自调用方传进来的真实台账行，缺数据时返回空串，不画假图。


def svg_bars(pairs, title, bar_color="#4472c4", width=680, height=140):
    """pairs 为 [(标签, 数值), ...]，数值<=0 的也画（高度为 0 的基线）。
    标签过长时只显示后 5 个字，避免挤在一起。
    图改小一点、少占地方：高度由 180 改成 140；上边距由 20 改成 28，
    让最高柱子的数值标签不跟标题挤在一起。"""
    pairs = [(str(label), int(value)) for label, value in pairs]
    if not pairs:
        return ""
    max_value = max(v for _, v in pairs) or 1
    n = len(pairs)
    slot = width / n
    bar_w = max(4.0, slot * 0.6)
    top, bottom = 28, height - 24
    plot_h = bottom - top
    parts = [f"<svg width='{width}' height='{height}' "
             f"style='background:#fff;border:1px solid #e5e7eb;border-radius:8px'>",
             # 慢慢涨特效：纯 CSS，不引 JS、不引外部文件，离线也能跑。
             # 柱子从底座往上长：transform-box 必须定在柱子自身、原点在底部，
             # 否则 SVG 默认以整个画布左上角为原点，柱子会斜着长。
             # 一根接一根错开 0.07 秒，像波浪一样涨；顶上的数字晚 0.35 秒淡入；
             # 系统开了“减弱动态效果”时自动关掉特效。
             "<style>.bar{transform-box:fill-box;transform-origin:bottom;"
             "animation:bargrow .8s cubic-bezier(.22,1,.36,1) both}"
             "@keyframes bargrow{from{transform:scaleY(0);opacity:0}"
             "to{transform:scaleY(1);opacity:1}}"
             ".vlab{animation:fadein .4s ease both}"
             "@keyframes fadein{from{opacity:0}to{opacity:1}}"
             "@media (prefers-reduced-motion:reduce){.bar,.vlab{animation:none}}"
             "</style>",
             f"<text x='8' y='14' font-size='13'>{title}</text>"]
    for i, (label, value) in enumerate(pairs):
        x = slot * i + (slot - bar_w) / 2
        h = plot_h * value / max_value
        y = bottom - h
        parts.append(f"<rect class='bar' style='animation-delay:{i * 0.07:.2f}s' "
                     f"x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' "
                     f"height='{h:.1f}' fill='{bar_color}'/>")
        if value:
            parts.append(f"<text class='vlab' style='animation-delay:{i * 0.07 + 0.35:.2f}s' "
                         f"x='{x + bar_w / 2:.1f}' y='{y - 3:.1f}' "
                         f"font-size='11' text-anchor='middle'>{value}</text>")
        # 标签短的（如 2026-11、11-04、人名）原样显示；只有过长的才截后 5 字，
        # 否则每月趋势的“2026-11”会被截成“26-11”，看着像年份丢了。
        short = label[-5:] if len(label) > 8 else label
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


# 监理人员 8 人（只有姓名，没有电话）：每人发现病害数图里 8 人都要显示，
# 当月没发现病害的也显示 0，不只显示有数据的几个人。
PERSONNEL = ["姜付磊", "裴彤宇", "刘聪飞", "张永广",
             "逯付江", "张振伟", "王明超", "王清顺"]


def per_person_discovered(rows, month):
    """每人发现病害数（第二十四版小图只剩这一张，已处置图已删）。
    返回 8 名监理人员全员（含 0 条的），再加数据里出现过的其他人。"""
    from collections import Counter
    counts = Counter()
    for r in rows:
        date = str(r.get("发现日期", "")).strip()
        person = str(r.get("巡查人", "")).strip()
        if date.startswith(month) and person:
            counts[person] += 1
    out = [(name, counts.get(name, 0)) for name in PERSONNEL]
    out += [(name, counts[name]) for name in sorted(counts)
            if name not in PERSONNEL]
    return out
