from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user
from app.decorators import login_required
from app.models import db, CartItem, Product
from app.helpers import get_param
import json

cart_bp = Blueprint('cart', __name__)


@cart_bp.route('/cart')
@login_required
def view_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.id.desc()).all()
    total = sum(float(item.product.price) * item.quantity for item in items if item.product)
    return render_template('cart.html', items=items, total=total)


@cart_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json() if request.is_json else request.form
    product_id = get_param(data, 'product_id', cast=int)
    sku_id = get_param(data, 'sku_id', cast=int)
    quantity = get_param(data, 'quantity', 1, cast=int)

    if not product_id or quantity < 1:
        return jsonify({'success': False, 'message': '参数错误'}), 400

    # Check if product exists and is on sale
    product = Product.query.get(product_id)
    if not product or product.status != 1:
        return jsonify({'success': False, 'message': '商品不存在或已下架'}), 400

    if product.stock < quantity:
        return jsonify({'success': False, 'message': '库存不足'}), 400

    # Check if already in cart, update quantity
    existing = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id,
        sku_id=sku_id
    ).first()

    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            sku_id=sku_id,
            quantity=quantity
        )
        db.session.add(item)

    db.session.commit()

    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'message': '已加入购物车', 'cart_count': cart_count})


@cart_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    data = request.get_json() if request.is_json else request.form
    quantity = get_param(data, 'quantity', 1, cast=int)

    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = min(quantity, 99)
    db.session.commit()

    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'cart_count': cart_count})


@cart_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403

    db.session.delete(item)
    db.session.commit()

    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'cart_count': cart_count})


@cart_bp.route('/cart/count')
@login_required
def cart_count():
    count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})
