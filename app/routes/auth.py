from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.status == 0:
                flash('账号已被禁用', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=request.form.get('remember'))
            flash(f'欢迎回来，{user.username}！', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/auth/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        if not username or not password:
            flash('请填写用户名和密码', 'danger')
            return render_template('auth/register.html')

        if len(username) < 3 or len(username) > 50:
            flash('用户名长度3-50个字符', 'danger')
            return render_template('auth/register.html')

        if password != password2:
            flash('两次密码输入不一致', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('密码长度至少6位', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已被注册', 'danger')
            return render_template('auth/register.html')

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            phone=phone,
            role='user',
            status=1,
        )
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/auth/merchant-register', methods=['GET', 'POST'])
def merchant_register():
    """Merchant/商家 registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        phone = request.form.get('phone', '').strip()

        if not username or not password:
            flash('请填写用户名和密码', 'danger')
            return render_template('auth/merchant_register.html')

        if len(username) < 3 or len(username) > 50:
            flash('用户名长度3-50个字符', 'danger')
            return render_template('auth/merchant_register.html')

        if password != password2:
            flash('两次密码输入不一致', 'danger')
            return render_template('auth/merchant_register.html')

        if len(password) < 6:
            flash('密码长度至少6位', 'danger')
            return render_template('auth/merchant_register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已被注册', 'danger')
            return render_template('auth/merchant_register.html')

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            phone=phone,
            role='admin',
            status=1,
        )
        db.session.add(user)
        db.session.commit()

        flash('商家注册成功！请登录商家后台', 'success')
        return redirect(url_for('admin.login'))

    return render_template('auth/merchant_register.html')


@auth_bp.route('/auth/logout')
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('main.index'))
