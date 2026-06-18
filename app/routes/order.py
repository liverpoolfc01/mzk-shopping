from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from app.decorators import login_required
from app.models import db, CartItem, Product, Order, OrderItem, OrderLog
from app.models import UserAddress, UserCoupon, Coupon
from app.helpers import generate_order_no, apply_coupon, get_param
from datetime import datetime
import json

order_bp = Blueprint('order', __name__)


@order_bp.route('/order/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.id.desc()).all()
    if not cart_items:
        flash('购物车是空的，请先添加商品', 'warning')
        return redirect(url_for('cart.view_cart'))

    addresses = UserAddress.query.filter_by(user_id=current_user.id).order_by(UserAddress.is_default.desc()).all()

    # Calculate totals
    product_total = sum(float(item.product.price) * item.quantity for item in cart_items if item.product)
    total_quantity = sum(item.quantity for item in cart_items)

    # Get available coupons
    now = datetime.utcnow()
    available_coupons = UserCoupon.query.filter_by(
        user_id=current_user.id,
        status='unused'
    ).join(Coupon).filter(
        Coupon.start_time <= now,
        Coupon.end_time >= now
    ).all()

    # Default address
    default_address = next((a for a in addresses if a.is_default), addresses[0] if addresses else None)

    return render_template('order/checkout.html',
                           cart_items=cart_items,
                           addresses=addresses,
                           default_address=default_address,
                           product_total=product_total,
                           total_quantity=total_quantity,
                           coupons=available_coupons)


@order_bp.route('/order/create', methods=['POST'])
@login_required
def create_order():
    data = request.get_json()
    address_id = get_param(data, 'address_id', cast=int)
    coupon_id = get_param(data, 'coupon_id', cast=int)
    remark = get_param(data, 'remark', '')

    if not address_id:
        return jsonify({'success': False, 'message': '请选择收货地址'}), 400

    address = UserAddress.query.get(address_id)
    if not address or address.user_id != current_user.id:
        return jsonify({'success': False, 'message': '收货地址无效'}), 400

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'success': False, 'message': '购物车是空的'}), 400

    # Validate stock
    for item in cart_items:
        if item.product.stock < item.quantity:
            return jsonify({
                'success': False,
                'message': f'"{item.product.name}" 库存不足，当前库存: {item.product.stock}'
            }), 400

    # Calculate totals
    product_total = sum(float(item.product.price) * item.quantity for item in cart_items)

    # Apply coupon
    discount = 0
    user_coupon = None
    if coupon_id:
        user_coupon = UserCoupon.query.get(coupon_id)
        if user_coupon and user_coupon.user_id == current_user.id and user_coupon.status == 'unused':
            discount = apply_coupon(user_coupon.coupon, product_total)

    pay_amount = max(0, product_total - discount)

    # Create order
    address_snapshot = json.dumps({
        'receiver_name': address.receiver_name,
        'phone': address.phone,
        'province': address.province,
        'city': address.city,
        'district': address.district,
        'detail': address.detail,
    }, ensure_ascii=False)

    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot=address_snapshot,
        product_total=product_total,
        discount_amount=discount,
        shipping_fee=0,
        pay_amount=pay_amount,
        status='pending_pay',
        remark=remark,
    )
    db.session.add(order)
    db.session.flush()

    # Create order items and deduct stock
    for item in cart_items:
        product_snapshot = json.dumps({
            'name': item.product.name,
            'price': float(item.product.price),
            'main_image': item.product.main_image,
        }, ensure_ascii=False)

        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_snapshot=product_snapshot,
            quantity=item.quantity,
            price=item.product.price,
            subtotal=float(item.product.price) * item.quantity,
        )
        db.session.add(order_item)

        # Deduct stock
        item.product.stock -= item.quantity
        item.product.sales_count += item.quantity

    # Mark coupon as used
    if user_coupon:
        user_coupon.status = 'used'
        user_coupon.used_order_id = order.id
        user_coupon.used_at = datetime.utcnow()

    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()

    # Log
    log = OrderLog(order_id=order.id, action='created', operator=current_user.username,
                   detail=f'订单创建，待支付 ¥{pay_amount:.2f}')
    db.session.add(log)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '订单创建成功',
        'order_id': order.id,
        'order_no': order.order_no,
    })


@order_bp.route('/order/pay/<int:order_id>')
@login_required
def pay_page(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权查看此订单', 'danger')
        return redirect(url_for('main.index'))

    if order.status != 'pending_pay':
        flash('该订单无需支付', 'warning')
        return redirect(url_for('order.order_detail', order_id=order.id))

    # Check if order is expired (> 30 min)
    elapsed = (datetime.utcnow() - order.created_at).total_seconds()
    if elapsed > 1800:  # 30 minutes
        order.status = 'cancelled'
        log = OrderLog(order_id=order.id, action='cancelled', operator='system',
                       detail='订单超时自动取消')
        db.session.add(log)
        # Restore stock
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity
        db.session.commit()
        flash('订单已超时取消，请重新下单', 'warning')
        return redirect(url_for('cart.view_cart'))

    remaining = max(0, int(1800 - elapsed))
    minutes = remaining // 60
    seconds = remaining % 60

    return render_template('order/pay.html', order=order,
                           remaining_minutes=minutes, remaining_seconds=seconds)


@order_bp.route('/order/pay/<int:order_id>', methods=['POST'])
@login_required
def process_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    if order.status != 'pending_pay':
        return jsonify({'success': False, 'message': '订单状态异常'}), 400

    # Simulate payment
    order.status = 'pending_ship'
    order.paid_at = datetime.utcnow()
    order.payment_method = 'simulated'

    log = OrderLog(order_id=order.id, action='paid', operator=current_user.username,
                   detail=f'模拟支付成功，实付 ¥{float(order.pay_amount):.2f}')
    db.session.add(log)

    db.session.commit()

    return jsonify({'success': True, 'message': '支付成功！', 'order_id': order.id})


@order_bp.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权查看此订单', 'danger')
        return redirect(url_for('main.index'))
    return render_template('order/success.html', order=order)


@order_bp.route('/order/list')
@login_required
def order_list():
    status_filter = request.args.get('status', '')
    query = Order.query.filter_by(user_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.id.desc()).all()
    return render_template('order/list.html', orders=orders, current_status=status_filter)


@order_bp.route('/order/detail/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权查看此订单', 'danger')
        return redirect(url_for('main.index'))
    return render_template('order/detail.html', order=order)


@order_bp.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    if order.status != 'pending_pay':
        return jsonify({'success': False, 'message': '只能取消待支付订单'}), 400

    order.status = 'cancelled'
    log = OrderLog(order_id=order.id, action='cancelled', operator=current_user.username,
                   detail='用户取消订单')
    db.session.add(log)

    # Restore stock
    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity

    # Restore coupon
    if order.discount_amount > 0:
        uc = UserCoupon.query.filter_by(used_order_id=order.id).first()
        if uc:
            uc.status = 'unused'
            uc.used_order_id = None
            uc.used_at = None

    db.session.commit()
    return jsonify({'success': True, 'message': '订单已取消'})


@order_bp.route('/order/confirm/<int:order_id>', methods=['POST'])
@login_required
def confirm_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    if order.status != 'shipped':
        return jsonify({'success': False, 'message': '订单状态异常'}), 400

    order.status = 'completed'
    order.completed_at = datetime.utcnow()
    log = OrderLog(order_id=order.id, action='completed', operator=current_user.username,
                   detail='用户确认收货')
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': '已确认收货'})


@order_bp.route('/order/refund/<int:order_id>', methods=['POST'])
@login_required
def request_refund(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    if order.status not in ('pending_ship', 'shipped'):
        return jsonify({'success': False, 'message': '当前状态不支持退款'}), 400

    order.status = 'refunding'
    log = OrderLog(order_id=order.id, action='refunding', operator=current_user.username,
                   detail='用户申请退款')
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': '退款申请已提交'})
