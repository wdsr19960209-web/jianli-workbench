# 监理指令：只套用户既有模板的格式，内容由调用方填，不替你定责任、不编数字。
#
# 模板结构（用户既有习惯）：
#   开头：巡查发现的问题 + 危害后果 + 合同/规范依据 + 责令整改
#   正文：方案及排查台账 / 实质整改 / 安全作业 / 自检报验及信息系统录入 / 常态化养护
#   末尾：逾期责任


def build_instruction(problem, hazard, basis, items, overdue_note):
    """items 为 5 条正文的 dict，缺哪条就留空位，不编造。"""
    keys = ["方案及排查台账", "实质整改", "安全作业",
            "自检报验及信息系统录入", "常态化养护"]
    body = "\n".join(f"{i}. {k}：{items.get(k, '（待填写）')}"
                     for i, k in enumerate(keys, 1))
    return (f"巡查发现的问题：{problem}\n危害后果：{hazard}\n"
            f"合同/规范依据：{basis}\n责令整改如下：\n{body}\n"
            f"逾期责任：{overdue_note}")
