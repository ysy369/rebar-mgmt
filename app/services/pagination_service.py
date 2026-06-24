# ============================================
# 钢筋精细化管理平台 — 分页工具
# ============================================
from flask import current_app, request


def get_page() -> int:
    """从请求参数中获取当前页码，默认第1页"""
    try:
        page = int(request.args.get("page", 1))
        return page if page > 0 else 1
    except (ValueError, TypeError):
        return 1


def paginate(query, page=None, per_page=None, count=True):
    """对 SQLAlchemy 查询对象进行分页

    Args:
        query: SQLAlchemy BaseQuery
        page: 当前页码，默认从请求参数读取
        per_page: 每页条数，默认读取配置 PAGE_SIZE
        count: 是否计算总数

    Returns:
        Pagination 对象
    """
    if page is None:
        page = get_page()
    if per_page is None:
        per_page = current_app.config.get("PAGE_SIZE", 20)
    return query.paginate(page=page, per_page=per_page, count=count, error_out=False)


def pagination_url(endpoint, page, args=None):
    """生成分页链接，保留当前查询参数并替换 page"""
    from flask import url_for

    if args is None:
        args = request.args.to_dict()
    args["page"] = page
    return url_for(endpoint, **args)
