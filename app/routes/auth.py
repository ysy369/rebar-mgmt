# ============================================
# 钢筋精细化管理平台 — 认证蓝图（登录/登出）
# ============================================
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models.user import User
from app.services.auth_service import log_operation

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """用户登录"""
    # 已登录则跳转
    if current_user.is_authenticated:
        return redirect_to_dashboard()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        platform_type = request.form.get("platformType", "jinguan")

        if not username or not password:
            flash("请输入账号和密码。", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("账号或密码错误，请重试。", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("该账号已被禁用，请联系管理员。", "warning")
            return render_template("auth/login.html")

        # 登录成功
        login_user(user, remember=request.form.get("remember") == "on")
        user.last_login_at = datetime.utcnow()

        from app import db

        db.session.commit()

        # 存储当前平台类型到 session
        session["platform_type"] = platform_type

        log_operation(user.id, "login", f"用户 {username} 登录（平台: {platform_type}）", request.remote_addr)

        flash(f"欢迎回来，{user.display_name}！", "success")
        return redirect_to_dashboard()

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """用户登出"""
    username = current_user.username
    logout_user()
    flash("您已安全退出。", "info")
    return redirect(url_for("auth.login"))


def redirect_to_dashboard():
    """登录后跳转：优先跟随 next 参数，否则到首页"""
    from flask import request
    next_url = request.args.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("home.index"))
