from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from app.decorators import admin_required
from app.models import db, User, Product, Category, Order, OrderItem, OrderLog
from app.models import Coupon, GroupBuy, LotteryActivity, FlashSale, BargainActivity, BlindBox
from app.helpers import save_upload
from datetime import datetime
import json
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username, role='admin').first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('欢迎回来，管理员！', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('用户名或密码错误', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/')
@admin_required
def dashboard():
    # Stats
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_revenue = db.session.query(db.func.sum(Order.pay_amount)).filter(
        Order.status.in_(['pending_ship', 'shipped', 'completed'])
    ).scalar() or 0

    recent_orders = Order.query.order_by(Order.id.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           total_users=total_users,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders)


# ============================================================
# Admin: Products
# ============================================================

@admin_bp.route('/products')
@admin_required
def products():
    page = request.args.get('page', 1, type=int)
    products = Product.query.order_by(Product.id.desc()).paginate(page=page, per_page=15)
    categories = Category.query.all()
    return render_template('admin/products_list.html', products=products, categories=categories)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        category_id = request.form.get('category_id', type=int)
        price = request.form.get('price', type=float)
        original_price = request.form.get('original_price', type=float) or None
        stock = request.form.get('stock', 0, type=int)
        is_recommend = request.form.get('is_recommend', 0, type=int)

        # Handle image uploads
        images = []
        main_image = ''
        for i in range(1, 6):
            file = request.files.get(f'image_{i}')
            if file and file.filename:
                path = save_upload(file)
                if path:
                    images.append(path)
                    if not main_image:
                        main_image = path

        product = Product(
            name=name,
            description=description,
            category_id=category_id if category_id else None,
            price=price,
            original_price=original_price,
            stock=stock,
            images=json.dumps(images),
            main_image=main_image,
            detail_images='[]',
            is_recommend=is_recommend,
            status=1,
        )
        db.session.add(product)
        db.session.commit()
        flash('商品添加成功！', 'success')
        return redirect(url_for('admin.products'))

    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories, product=None)


@admin_bp.route('/products/edit/<int:pid>', methods=['GET', 'POST'])
@admin_required
def edit_product(pid):
    product = Product.query.get_or_404(pid)

    if request.method == 'POST':
        product.name = request.form.get('name', product.name)
        product.description = request.form.get('description', product.description)
        product.category_id = request.form.get('category_id', type=int) or None
        product.price = request.form.get('price', type=float) or product.price
        product.original_price = request.form.get('original_price', type=float)
        product.stock = request.form.get('stock', 0, type=int)
        product.is_recommend = request.form.get('is_recommend', 0, type=int)

        # Handle new images
        for i in range(1, 4):
            file = request.files.get(f'image_{i}')
            if file and file.filename:
                path = save_upload(file)
                if path:
                    current_images = product.get_images()
                    current_images.append(path)
                    product.images = json.dumps(current_images)
                    if not product.main_image:
                        product.main_image = path

        product.updated_at = datetime.utcnow()
        db.session.commit()
        flash('商品更新成功！', 'success')
        return redirect(url_for('admin.products'))

    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories, product=product)


@admin_bp.route('/products/delete/<int:pid>', methods=['POST'])
@admin_required
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    product.status = 0
    db.session.commit()
    return jsonify({'success': True, 'message': '商品已下架'})


# ============================================================
# Admin: Orders
# ============================================================

@admin_bp.route('/orders')
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.id.desc()).paginate(page=page, per_page=15)
    return render_template('admin/orders_list.html', orders=orders, current_status=status_filter)


@admin_bp.route('/orders/<int:oid>')
@admin_required
def order_detail(oid):
    order = Order.query.get_or_404(oid)
    return render_template('admin/order_detail.html', order=order)


@admin_bp.route('/orders/ship/<int:oid>', methods=['POST'])
@admin_required
def ship_order(oid):
    order = Order.query.get_or_404(oid)
    if order.status != 'pending_ship':
        return jsonify({'success': False, 'message': '订单状态异常'}), 400

    order.status = 'shipped'
    order.shipped_at = datetime.utcnow()
    log = OrderLog(order_id=oid, action='shipped', operator=current_user.username, detail='商家已发货')
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': '已标记发货'})


@admin_bp.route('/orders/refund/<int:oid>', methods=['POST'])
@admin_required
def approve_refund(oid):
    order = Order.query.get_or_404(oid)
    if order.status != 'refunding':
        return jsonify({'success': False, 'message': '订单状态异常'}), 400

    order.status = 'refunded'
    log = OrderLog(order_id=oid, action='refunded', operator=current_user.username, detail='商家同意退款')
    db.session.add(log)

    # Restore stock
    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity

    db.session.commit()
    return jsonify({'success': True, 'message': '退款已处理'})


# ============================================================
# Admin: Users
# ============================================================

@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.id.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users_list.html', users=users)


@admin_bp.route('/users/status/<int:uid>', methods=['POST'])
@admin_required
def toggle_user_status(uid):
    user = User.query.get_or_404(uid)
    user.status = 0 if user.status == 1 else 1
    db.session.commit()
    return jsonify({'success': True, 'message': f'用户已{"启用" if user.status == 1 else "禁用"}'})


# ============================================================
# Admin: Coupons
# ============================================================

@admin_bp.route('/coupons')
@admin_required
def coupons():
    coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    return render_template('admin/coupons_list.html', coupons=coupons)


@admin_bp.route('/coupons/create', methods=['POST'])
@admin_required
def create_coupon():
    data = request.get_json() if request.is_json else request.form
    name = data.get('name', '')
    ctype = data.get('type', 'fixed')
    value = float(data.get('value', 0))
    min_amount = float(data.get('min_amount', 0))
    total_count = int(data.get('total_count', 100))
    start_time = datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M')

    coupon = Coupon(
        name=name, type=ctype, value=value, min_amount=min_amount,
        total_count=total_count,
        start_time=start_time, end_time=end_time
    )
    db.session.add(coupon)
    db.session.commit()
    return jsonify({'success': True, 'message': '优惠券创建成功'})


@admin_bp.route('/coupons/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_coupon(cid):
    coupon = Coupon.query.get_or_404(cid)
    coupon.status = 0
    db.session.commit()
    return jsonify({'success': True, 'message': '优惠券已删除'})


# ============================================================
# Admin: Group Buy
# ============================================================

@admin_bp.route('/group-buy')
@admin_required
def group_buy():
    group_buys = GroupBuy.query.order_by(GroupBuy.id.desc()).all()
    products = Product.query.filter_by(status=1).all()
    return render_template('admin/group_buy_list.html', group_buys=group_buys, products=products)


@admin_bp.route('/group-buy/create', methods=['POST'])
@admin_required
def create_group_buy():
    data = request.get_json() if request.is_json else request.form

    gb = GroupBuy(
        product_id=int(data.get('product_id')),
        title=data.get('title', ''),
        group_price=float(data.get('group_price', 0)),
        required_count=int(data.get('required_count', 2)),
        duration_hours=int(data.get('duration_hours', 24)),
        start_time=datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M'),
        status=1,
    )
    db.session.add(gb)
    db.session.commit()
    return jsonify({'success': True, 'message': '拼团活动创建成功'})


# ============================================================
# Admin: Lottery
# ============================================================

@admin_bp.route('/lottery')
@admin_required
def lottery():
    lotteries = LotteryActivity.query.order_by(LotteryActivity.id.desc()).all()
    return render_template('admin/lottery_list.html', lotteries=lotteries)


@admin_bp.route('/lottery/create', methods=['POST'])
@admin_required
def create_lottery():
    data = request.get_json() if request.is_json else request.form

    prizes_raw = data.get('prizes', '[]')
    if isinstance(prizes_raw, str):
        prizes = json.loads(prizes_raw)
    else:
        prizes = prizes_raw

    lottery = LotteryActivity(
        title=data.get('title', ''),
        description=data.get('description', ''),
        start_time=datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M'),
        prizes=json.dumps(prizes),
        daily_limit=int(data.get('daily_limit', 1)),
        status=1,
    )
    db.session.add(lottery)
    db.session.commit()
    return jsonify({'success': True, 'message': '抽奖活动创建成功'})


# ============================================================
# Admin: Flash Sale
# ============================================================

@admin_bp.route('/flash-sale')
@admin_required
def flash_sale():
    flash_sales = FlashSale.query.order_by(FlashSale.id.desc()).all()
    products = Product.query.filter_by(status=1).all()
    return render_template('admin/flash_sale_list.html', flash_sales=flash_sales, products=products)


@admin_bp.route('/flash-sale/create', methods=['POST'])
@admin_required
def create_flash_sale():
    data = request.get_json() if request.is_json else request.form

    fs = FlashSale(
        product_id=int(data.get('product_id')),
        title=data.get('title', ''),
        flash_price=float(data.get('flash_price', 0)),
        stock=int(data.get('stock', 10)),
        limit_per_user=int(data.get('limit_per_user', 1)),
        start_time=datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M'),
        status=1,
    )
    db.session.add(fs)
    db.session.commit()
    return jsonify({'success': True, 'message': '秒杀活动创建成功'})


# ============================================================
# Admin: Bargain
# ============================================================

@admin_bp.route('/bargain')
@admin_required
def bargain():
    bargains = BargainActivity.query.order_by(BargainActivity.id.desc()).all()
    products = Product.query.filter_by(status=1).all()
    return render_template('admin/bargain_list.html', bargains=bargains, products=products)


@admin_bp.route('/bargain/create', methods=['POST'])
@admin_required
def create_bargain():
    data = request.get_json() if request.is_json else request.form

    ba = BargainActivity(
        product_id=int(data.get('product_id')),
        title=data.get('title', ''),
        original_price=float(data.get('original_price', 0)),
        floor_price=float(data.get('floor_price', 0)),
        max_helpers=int(data.get('max_helpers', 10)),
        start_time=datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M'),
        status=1,
    )
    db.session.add(ba)
    db.session.commit()
    return jsonify({'success': True, 'message': '砍价活动创建成功'})


# ============================================================
# Admin: Blind Box
# ============================================================

@admin_bp.route('/blind-box')
@admin_required
def blind_box():
    boxes = BlindBox.query.order_by(BlindBox.id.desc()).all()
    return render_template('admin/blind_box_list.html', boxes=boxes)


@admin_bp.route('/blind-box/create', methods=['POST'])
@admin_required
def create_blind_box():
    data = request.get_json() if request.is_json else request.form

    contents_raw = data.get('contents', '[]')
    if isinstance(contents_raw, str):
        contents = json.loads(contents_raw)
    else:
        contents = contents_raw

    box = BlindBox(
        title=data.get('title', ''),
        description=data.get('description', ''),
        price=float(data.get('price', 0)),
        contents=json.dumps(contents),
        total_count=int(data.get('total_count', 100)),
        start_time=datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M'),
        status=1,
    )
    db.session.add(box)
    db.session.commit()
    return jsonify({'success': True, 'message': '盲盒活动创建成功'})
