from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from app.decorators import login_required
from app.models import db, User, UserAddress, UserCoupon, Coupon
from app.helpers import get_param
from datetime import datetime

user_bp = Blueprint('user', __name__)


@user_bp.route('/user/center')
@login_required
def center():
    from app.models import Order
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).limit(5).all()
    order_counts = {
        'pending_pay': Order.query.filter_by(user_id=current_user.id, status='pending_pay').count(),
        'pending_ship': Order.query.filter_by(user_id=current_user.id, status='pending_ship').count(),
        'shipped': Order.query.filter_by(user_id=current_user.id, status='shipped').count(),
        'completed': Order.query.filter_by(user_id=current_user.id, status='completed').count(),
    }
    return render_template('user/center.html', orders=orders, order_counts=order_counts)


@user_bp.route('/user/addresses')
@login_required
def addresses():
    addresses = UserAddress.query.filter_by(user_id=current_user.id).order_by(
        UserAddress.is_default.desc(), UserAddress.id.desc()
    ).all()
    return render_template('user/addresses.html', addresses=addresses)


@user_bp.route('/user/address/add', methods=['POST'])
@login_required
def add_address():
    data = request.get_json()
    receiver_name = data.get('receiver_name', '').strip()
    phone = data.get('phone', '').strip()
    province = data.get('province', '').strip()
    city = data.get('city', '').strip()
    district = data.get('district', '').strip()
    detail = data.get('detail', '').strip()
    is_default = get_param(data, 'is_default', 0, cast=int)

    if not receiver_name or not phone or not detail:
        return jsonify({'success': False, 'message': '请填写必要信息'}), 400

    if is_default:
        UserAddress.query.filter_by(user_id=current_user.id, is_default=1).update({'is_default': 0})

    addr = UserAddress(
        user_id=current_user.id,
        receiver_name=receiver_name,
        phone=phone,
        province=province,
        city=city,
        district=district,
        detail=detail,
        is_default=is_default,
    )
    db.session.add(addr)
    db.session.commit()

    return jsonify({'success': True, 'message': '地址添加成功', 'id': addr.id})


@user_bp.route('/user/address/edit/<int:addr_id>', methods=['POST'])
@login_required
def edit_address(addr_id):
    addr = UserAddress.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    data = request.get_json()
    addr.receiver_name = data.get('receiver_name', addr.receiver_name)
    addr.phone = data.get('phone', addr.phone)
    addr.province = data.get('province', addr.province)
    addr.city = data.get('city', addr.city)
    addr.district = data.get('district', addr.district)
    addr.detail = data.get('detail', addr.detail)

    is_default = get_param(data, 'is_default', 0, cast=int)
    if is_default:
        UserAddress.query.filter_by(user_id=current_user.id, is_default=1).update({'is_default': 0})
        addr.is_default = 1

    db.session.commit()
    return jsonify({'success': True, 'message': '地址更新成功'})


@user_bp.route('/user/address/delete/<int:addr_id>', methods=['POST'])
@login_required
def delete_address(addr_id):
    addr = UserAddress.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    was_default = addr.is_default
    db.session.delete(addr)
    db.session.commit()

    # If deleted address was default, set another as default
    if was_default:
        next_addr = UserAddress.query.filter_by(user_id=current_user.id).first()
        if next_addr:
            next_addr.is_default = 1
            db.session.commit()

    return jsonify({'success': True, 'message': '地址已删除'})


@user_bp.route('/user/address/default/<int:addr_id>', methods=['POST'])
@login_required
def set_default_address(addr_id):
    addr = UserAddress.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    UserAddress.query.filter_by(user_id=current_user.id, is_default=1).update({'is_default': 0})
    addr.is_default = 1
    db.session.commit()

    return jsonify({'success': True, 'message': '已设为默认地址'})


@user_bp.route('/user/coupons')
@login_required
def my_coupons():
    now = datetime.utcnow()
    # Update expired coupons
    expired = UserCoupon.query.filter_by(user_id=current_user.id, status='unused').filter(
        UserCoupon.expired_at < now
    ).all()
    for uc in expired:
        uc.status = 'expired'
    if expired:
        db.session.commit()

    unused = UserCoupon.query.filter_by(user_id=current_user.id, status='unused').filter(
        UserCoupon.expired_at >= now
    ).all()
    used = UserCoupon.query.filter_by(user_id=current_user.id, status='used').all()
    expired_list = UserCoupon.query.filter_by(user_id=current_user.id, status='expired').all()

    return render_template('user/coupons.html', unused=unused, used=used, expired=expired_list)


@user_bp.route('/user/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        current_user.email = email
        current_user.phone = phone
        db.session.commit()
        flash('资料更新成功', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/center.html')
