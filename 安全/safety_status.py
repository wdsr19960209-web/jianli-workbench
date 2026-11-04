# 安全文件台账：处理状态 -> 背景色，与在线表下拉颜色一致。
# 这里只做颜色映射，不改状态。状态只能由用户在在线表下拉里自选。

STATUS_COLORS = {
    "待处理": "#fff2cc",
    "待确认": "#fce5cd",
    "已处理": "#d9ead3",
    "已登记": "#cfe2f3",
    "无需处理": "#e0e0e0",
    "已销号": "#d9d2e9",
}


def color_for(status):
    return STATUS_COLORS.get((status or "").strip(), "#ffffff")
