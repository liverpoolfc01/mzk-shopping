from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


# ============================================================
# Core User & Address
# ============================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), default='')
    phone = db.Column(db.String(20), default='')
    role = db.Column(db.Enum('admin', 'user'), default='user')
    status = db.Column(db.SmallInteger, default=1)  # 1=active, 0=disabled
    avatar = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    addresses = db.relationship('UserAddress', backref='user', lazy='dynamic')
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic')
    orders = db.relationship('Order', backref='user', lazy='dynamic')


class UserAddress(db.Model):
    __tablename__ = 'user_addresses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    province = db.Column(db.String(30), default='')
    city = db.Column(db.String(30), default='')
    district = db.Column(db.String(30), default='')
    detail = db.Column(db.String(200), nullable=False)
    is_default = db.Column(db.SmallInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# Product & Category
# ============================================================

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    parent_id = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)
    icon = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='category', lazy='dynamic')


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), nullable=True)
    stock = db.Column(db.Integer, default=0)
    images = db.Column(db.Text, default='[]')  # JSON array of image paths
    main_image = db.Column(db.String(255), default='')
    detail_images = db.Column(db.Text, default='[]')  # JSON array
    sales_count = db.Column(db.Integer, default=0)
    status = db.Column(db.SmallInteger, default=1)  # 1=on_sale, 0=off_sale
    is_recommend = db.Column(db.SmallInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_images(self):
        try:
            return json.loads(self.images) if self.images else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_main_image(self):
        images = self.get_images()
        return images[0] if images else '/static/uploads/placeholder.png'

    def get_detail_images(self):
        try:
            return json.loads(self.detail_images) if self.detail_images else []
        except (json.JSONDecodeError, TypeError):
            return []


class ProductSku(db.Model):
    __tablename__ = 'product_skus'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    sku_name = db.Column(db.String(100), default='')
    price = db.Column(db.Numeric(10, 2), nullable=True)
    stock = db.Column(db.Integer, default=0)
    attrs = db.Column(db.Text, default='{}')  # JSON: {"color":"Red","size":"L"}

    product = db.relationship('Product', backref=db.backref('skus', lazy='dynamic'))


# ============================================================
# Cart
# ============================================================

class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    sku_id = db.Column(db.Integer, nullable=True)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


# ============================================================
# Orders
# ============================================================

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    address_snapshot = db.Column(db.Text, nullable=False)  # JSON
    product_total = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    shipping_fee = db.Column(db.Numeric(10, 2), default=0)
    pay_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum('pending_pay', 'pending_ship', 'shipped', 'completed',
                'cancelled', 'refunding', 'refunded'),
        default='pending_pay'
    )
    payment_method = db.Column(db.String(20), default='simulated')
    remark = db.Column(db.String(500), default='')
    paid_at = db.Column(db.DateTime, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    logs = db.relationship('OrderLog', backref='order', lazy='dynamic')

    def get_address_snapshot(self):
        try:
            return json.loads(self.address_snapshot)
        except (json.JSONDecodeError, TypeError):
            return {}


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_snapshot = db.Column(db.Text, nullable=False)  # JSON
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    def get_snapshot(self):
        try:
            return json.loads(self.product_snapshot)
        except (json.JSONDecodeError, TypeError):
            return {}


class OrderLog(db.Model):
    __tablename__ = 'order_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(50), default='')
    detail = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# Marketing: Coupons
# ============================================================

class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('fixed', 'percent'), nullable=False)
    value = db.Column(db.Numeric(10, 2), nullable=False)
    min_amount = db.Column(db.Numeric(10, 2), default=0)
    total_count = db.Column(db.Integer, nullable=False)
    used_count = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserCoupon(db.Model):
    __tablename__ = 'user_coupons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=False)
    status = db.Column(db.Enum('unused', 'used', 'expired'), default='unused')
    used_order_id = db.Column(db.Integer, nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)
    expired_at = db.Column(db.DateTime, nullable=False)

    coupon = db.relationship('Coupon')


# ============================================================
# Marketing: Group Buy
# ============================================================

class GroupBuy(db.Model):
    __tablename__ = 'group_buys'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    group_price = db.Column(db.Numeric(10, 2), nullable=False)
    required_count = db.Column(db.Integer, default=2)
    duration_hours = db.Column(db.Integer, default=24)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


class GroupBuyGroup(db.Model):
    __tablename__ = 'group_buy_groups'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_buy_id = db.Column(db.Integer, db.ForeignKey('group_buys.id'), nullable=False)
    leader_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_count = db.Column(db.Integer, default=1)
    status = db.Column(db.Enum('forming', 'success', 'failed'), default='forming')
    expire_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    group_buy = db.relationship('GroupBuy')
    leader = db.relationship('User', foreign_keys=[leader_user_id])
    participants = db.relationship('GroupBuyParticipant', backref='group', lazy='dynamic')


class GroupBuyParticipant(db.Model):
    __tablename__ = 'group_buy_participants'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group_buy_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    is_leader = db.Column(db.SmallInteger, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


# ============================================================
# Marketing: Lottery
# ============================================================

class LotteryActivity(db.Model):
    __tablename__ = 'lottery_activities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    prizes = db.Column(db.Text, nullable=False)  # JSON
    cost_type = db.Column(db.Enum('free', 'points'), default='free')
    cost_amount = db.Column(db.Integer, default=0)
    daily_limit = db.Column(db.Integer, default=1)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_prizes(self):
        try:
            return json.loads(self.prizes)
        except (json.JSONDecodeError, TypeError):
            return []


class LotteryRecord(db.Model):
    __tablename__ = 'lottery_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lottery_id = db.Column(db.Integer, db.ForeignKey('lottery_activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prize_index = db.Column(db.Integer, nullable=False)
    prize_name = db.Column(db.String(100), nullable=False)
    is_winner = db.Column(db.SmallInteger, default=1)
    status = db.Column(db.Enum('pending', 'claimed'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lottery = db.relationship('LotteryActivity')


# ============================================================
# Marketing: Flash Sale
# ============================================================

class FlashSale(db.Model):
    __tablename__ = 'flash_sales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    flash_price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    limit_per_user = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


# ============================================================
# Marketing: Bargain
# ============================================================

class BargainActivity(db.Model):
    __tablename__ = 'bargain_activities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    floor_price = db.Column(db.Numeric(10, 2), nullable=False)
    max_helpers = db.Column(db.Integer, default=10)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


class BargainRecord(db.Model):
    __tablename__ = 'bargain_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bargain_id = db.Column(db.Integer, db.ForeignKey('bargain_activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_price = db.Column(db.Numeric(10, 2), nullable=False)
    helper_count = db.Column(db.Integer, default=0)
    max_helpers = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('bargaining', 'bought', 'expired'), default='bargaining')
    order_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bargain = db.relationship('BargainActivity')
    user = db.relationship('User', foreign_keys=[user_id],
                           backref=db.backref('bargain_records', lazy='dynamic'))


class BargainHelper(db.Model):
    __tablename__ = 'bargain_helpers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bargain_record_id = db.Column(db.Integer, db.ForeignKey('bargain_records.id'), nullable=False)
    helper_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reduced_amount = db.Column(db.Numeric(10, 2), nullable=False)
    helped_at = db.Column(db.DateTime, default=datetime.utcnow)

    record = db.relationship('BargainRecord', backref=db.backref('helpers', lazy='dynamic'))


# ============================================================
# Marketing: Blind Box
# ============================================================

class BlindBox(db.Model):
    __tablename__ = 'blind_boxes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    price = db.Column(db.Numeric(10, 2), nullable=False)
    contents = db.Column(db.Text, nullable=False)  # JSON
    total_count = db.Column(db.Integer, nullable=False)
    sold_count = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.SmallInteger, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_contents(self):
        try:
            return json.loads(self.contents)
        except (json.JSONDecodeError, TypeError):
            return []


class BlindBoxOrder(db.Model):
    __tablename__ = 'blind_box_orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    blind_box_id = db.Column(db.Integer, db.ForeignKey('blind_boxes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    prize_content = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    blind_box = db.relationship('BlindBox')
    user = db.relationship('User')
    order = db.relationship('Order')
