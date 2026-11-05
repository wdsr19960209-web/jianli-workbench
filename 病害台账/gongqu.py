# 病害台账所属标段（工区）对照：用户 2026-11-04 亲定的规则。
# 京港澳高速 -> 安阳工区；大广高速 -> 滑县工区；濮卫高速 -> 滑卫工区；
# 安罗高速 K0-K58+748 -> 二安工区，K58+748-K105+800 -> 滑卫工区；
# 南林高速 -> 内黄工区；沿太行高速 -> 林州工区。
# 安罗分界精确桩号 K58+748（2026-11-05 管辖路段情况表），取代此前 K58+749。
# 这里只写路段与工区的对照，不写任何通讯录里的姓名、电话。

import re

GONGQU_MAP = [
    ("京港澳高速", "安阳工区"),
    ("大广高速", "滑县工区"),
    ("濮卫高速", "滑卫工区"),
    ("南林高速", "内黄工区"),
    ("太行高速", "林州工区"),
]

ANLUO_SPLIT_KM = 58.748  # K58+748


def _stake_km(stake):
    """把 K58+748、K100+000、57.856 这类桩号换算成公里数，算不出来返回 None。
    平台桩号多为十进制公里数（57.856、58.800），必须先按浮点数解析，
    否则 58.800 会被当成 58，K58+748 分界就失效了。"""
    s = str(stake or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    match = re.search(r"K?(\d+)(?:\+(\d+))?", s)
    if not match:
        return None
    km = float(match.group(1))
    if match.group(2):
        km += int(match.group(2)) / 1000
    return km


def gongqu_for(road, stake=""):
    """返回路段对应的工区。安罗高速按桩号分段，其余按路段名对照。"""
    road = str(road or "")
    if "安罗高速" in road or "安罗" in road:
        km = _stake_km(stake)
        if km is None:
            return "滑卫工区"
        return "二安工区" if km < ANLUO_SPLIT_KM else "滑卫工区"
    for name, gongqu in GONGQU_MAP:
        if name in road:
            return gongqu
    return "待填写"
