# 病害处置台账：状态码含义、颜色、当月隐藏规则。
# 注意：这套状态码（0/3/4/5）与安全台账的下拉状态不是一回事，不能混用。
# 状态码含义是用户 2026-11-04 亲定的规则，覆盖此前“已处置=5”的粗略说法。

STATUS_TEXT = {
    "0": "安阳分公司没有制单",
    "3": "施工单位正在施工",
    "4": "需要监理验收",
    "5": "已经完成闭环",
}

STATUS_COLORS = {
    "0": "#f4cccc",
    "3": "#fff2cc",
    "4": "#cfe2f3",
    "5": "#d9ead3",
}


def text_for(code):
    return STATUS_TEXT.get(str(code).strip(), "")


def color_for(code):
    return STATUS_COLORS.get(str(code).strip(), "#ffffff")


def should_hide(row, is_current_month):
    """只有当月、状态 5 且按期完成的行才隐藏；已完结月份全部显示。

    预览里“显示已闭环”展开，就相当于看一个已完结月份。
    本骨架示例 CSV 里用“逾期状态”列判断是否按期：值为“未逾期”才算按期。
    真实 Excel 接入时，按实际“是否按期完成”字段改这一处即可。
    """
    if not is_current_month:
        return False
    return str(row.get("状态码", "")).strip() == "5" and \
        str(row.get("逾期状态", "")).strip() == "未逾期"
