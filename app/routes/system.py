# ============================================
# 钢筋精细化管理平台 — 系统设置蓝图
# ============================================
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User
from app.services.auth_service import admin_required
from app.services.pagination_service import paginate


system_bp = Blueprint("system", __name__, template_folder="../templates/system")


def _bc(*items):
    """构造统一面包屑"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@system_bp.route("/users")
@login_required
@admin_required
def user_list():
    """用户列表（复用 admin/users 逻辑）"""
    pagination = paginate(User.query.order_by(User.role, User.username), per_page=20)
    return render_template(
        "system/users.html",
        pagination=pagination,
        breadcrumbs=_bc({"name": "系统设置", "url": None}, {"name": "用户管理", "url": None}),
        page_title="用户管理",
    )


@system_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def user_create():
    """创建用户"""
    if request.method == "POST":
        try:
            username = request.form["username"].strip()
            password = request.form["password"]
            display_name = request.form["display_name"].strip()
            role = request.form.get("role", "user")

            if User.query.filter_by(username=username).first():
                flash("账号已存在。", "danger")
                return render_template(
                    "system/users_form.html",
                    user=None,
                    breadcrumbs=_bc(
                        {"name": "系统设置", "url": None},
                        {"name": "用户管理", "url": url_for("system.user_list")},
                        {"name": "创建用户", "url": None},
                    ),
                    page_title="创建用户",
                )

            user = User(username=username, display_name=display_name, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"用户 {username} 创建成功。", "success")
            return redirect(url_for("system.user_list"))
        except Exception:
            flash("创建失败，请重试。", "danger")
    return render_template(
        "system/users_form.html",
        user=None,
        breadcrumbs=_bc(
            {"name": "系统设置", "url": None},
            {"name": "用户管理", "url": url_for("system.user_list")},
            {"name": "创建用户", "url": None},
        ),
        page_title="创建用户",
    )


@system_bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def user_edit(id):
    """编辑用户"""
    user = User.query.get_or_404(id)
    if request.method == "POST":
        try:
            user.display_name = request.form["display_name"].strip()
            user.role = request.form.get("role", "user")
            new_password = request.form.get("password")
            if new_password:
                user.set_password(new_password)
            db.session.commit()
            flash(f"用户 {user.username} 更新成功。", "success")
            return redirect(url_for("system.user_list"))
        except Exception:
            flash("更新失败，请重试。", "danger")
    return render_template(
        "system/users_form.html",
        user=user,
        breadcrumbs=_bc(
            {"name": "系统设置", "url": None},
            {"name": "用户管理", "url": url_for("system.user_list")},
            {"name": "编辑用户", "url": None},
        ),
        page_title="编辑用户",
    )


@system_bp.route("/users/<int:id>/toggle", methods=["POST"])
@login_required
@admin_required
def user_toggle(id):
    """启用/禁用用户"""
    user = User.query.get_or_404(id)
    if user.username == "admin":
        flash("不能禁用管理员账号。", "danger")
        return redirect(url_for("system.user_list"))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"用户 {user.username} 已{'启用' if user.is_active else '禁用'}。", "success")
    return redirect(url_for("system.user_list"))


@system_bp.route("/users/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def user_delete(id):
    """删除用户"""
    user = User.query.get_or_404(id)
    if user.username == "admin":
        flash("不能删除管理员账号。", "danger")
        return redirect(url_for("system.user_list"))
    db.session.delete(user)
    db.session.commit()
    flash(f"用户 {user.username} 已删除。", "success")
    return redirect(url_for("system.user_list"))
