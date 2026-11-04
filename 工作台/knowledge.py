# 知识库：本地条目关键词搜索。条目以后由用户自己加，这里不预置内容。


def search_knowledge(entries, keyword):
    """entries 为 [{'title': ..., 'content': ...}]，keyword 为空时返回全部。"""
    if not keyword:
        return list(entries)
    keyword = keyword.strip()
    return [e for e in entries
            if keyword in e.get("title", "") or keyword in e.get("content", "")]
