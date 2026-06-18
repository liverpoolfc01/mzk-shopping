from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from app.decorators import login_required
from app.models import db, Product, Order, OrderItem, OrderLog, UserCoupon, Coupon
from app.models import GroupBuy, GroupBuyGroup, GroupBuyParticipant
from app.models import LotteryActivity, LotteryRecord
from app.models import FlashSale
from app.models import BargainActivity, BargainRecord, BargainHelper
from app.models import BlindBox, BlindBoxOrder
from app.helpers import generate_order_no, get_param
from datetime import datetime, timedelta
import json
import random

marketing_bp = Blueprint('marketing', __name__)


# ============================================================
# Coupon: claim
# ============================================================

@marketing_bp.route('/coupon/claim/<int:coupon_id>', methods=['POST'])
@login_required
def claim_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    now = datetime.utcnow()

    if coupon.status != 1:
        return jsonify({'success': False, 'message': '优惠券已下架'}), 400
    if now < coupon.start_time or now > coupon.end_time:
        return jsonify({'success': False, 'message': '不在有效期内'}), 400
    if coupon.used_count >= coupon.total_count:
        return jsonify({'success': False, 'message': '优惠券已被领完'}), 400

    # Check if user already has this coupon
    existing = UserCoupon.query.filter_by(user_id=current_user.id, coupon_id=coupon_id, status='unused').first()
    if existing:
        return jsonify({'success': False, 'message': '已领取过该优惠券'}), 400

    uc = UserCoupon(
        user_id=current_user.id,
        coupon_id=coupon_id,
        status='unused',
        expired_at=coupon.end_time,
    )
    coupon.used_count += 1
    db.session.add(uc)
    db.session.commit()

    return jsonify({'success': True, 'message': '优惠券领取成功！'})


# ============================================================
# Group Buy
# ============================================================

@marketing_bp.route('/group-buy')
def group_buy_list():
    now = datetime.utcnow()
    group_buys = GroupBuy.query.filter(
        GroupBuy.status == 1,
        GroupBuy.start_time <= now,
        GroupBuy.end_time >= now
    ).all()
    return render_template('marketing/group_buy_list.html', group_buys=group_buys)


@marketing_bp.route('/group-buy/<int:gb_id>')
def group_buy_detail(gb_id):
    gb = GroupBuy.query.get_or_404(gb_id)
    now = datetime.utcnow()

    # Find forming groups
    forming_groups = GroupBuyGroup.query.filter_by(
        group_buy_id=gb_id, status='forming'
    ).filter(GroupBuyGroup.expire_time > now).all()

    return render_template('marketing/group_buy_detail.html', gb=gb, forming_groups=forming_groups, now=now)


@marketing_bp.route('/group-buy/<int:gb_id>/create-group', methods=['POST'])
@login_required
def create_group(gb_id):
    gb = GroupBuy.query.get_or_404(gb_id)
    now = datetime.utcnow()

    if now < gb.start_time or now > gb.end_time:
        return jsonify({'success': False, 'message': '活动未开始或已结束'}), 400

    # Check if user already has a forming group for this GB
    existing = GroupBuyGroup.query.filter_by(
        group_buy_id=gb_id, leader_user_id=current_user.id, status='forming'
    ).first()
    if existing:
        return jsonify({'success': False, 'message': '已有一个进行中的拼团', 'group_id': existing.id}), 400

    # Create order for the leader
    product = Product.query.get(gb.product_id)
    if not product or product.stock < 1:
        return jsonify({'success': False, 'message': '商品库存不足'}), 400

    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot='{}',
        product_total=gb.group_price,
        discount_amount=0,
        shipping_fee=0,
        pay_amount=gb.group_price,
        status='pending_ship',
        paid_at=now,
    )
    db.session.add(order)
    db.session.flush()

    oi = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_snapshot=json.dumps({'name': product.name, 'price': float(gb.group_price), 'main_image': product.main_image}, ensure_ascii=False),
        quantity=1,
        price=gb.group_price,
        subtotal=float(gb.group_price),
    )
    db.session.add(oi)
    product.stock -= 1
    product.sales_count += 1

    # Create group
    group = GroupBuyGroup(
        group_buy_id=gb_id,
        leader_user_id=current_user.id,
        current_count=1,
        status='forming',
        expire_time=now + timedelta(hours=gb.duration_hours),
    )
    db.session.add(group)
    db.session.flush()

    participant = GroupBuyParticipant(
        group_id=group.id,
        user_id=current_user.id,
        order_id=order.id,
        is_leader=1,
    )
    db.session.add(participant)

    log = OrderLog(order_id=order.id, action='paid', operator=current_user.username, detail='拼团订单(团长)')
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': '开团成功！', 'group_id': group.id})


@marketing_bp.route('/group-buy/<int:group_id>/join', methods=['POST'])
@login_required
def join_group(group_id):
    group = GroupBuyGroup.query.get_or_404(group_id)
    now = datetime.utcnow()

    if group.status != 'forming':
        return jsonify({'success': False, 'message': '该团状态异常'}), 400
    if now > group.expire_time:
        group.status = 'failed'
        db.session.commit()
        return jsonify({'success': False, 'message': '该团已过期'}), 400
    if group.current_count >= group.group_buy.required_count:
        return jsonify({'success': False, 'message': '该团已满'}), 400

    gb = group.group_buy
    product = Product.query.get(gb.product_id)
    if not product or product.stock < 1:
        return jsonify({'success': False, 'message': '商品库存不足'}), 400

    # Create order
    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot='{}',
        product_total=gb.group_price,
        pay_amount=gb.group_price,
        status='pending_ship',
        paid_at=now,
    )
    db.session.add(order)
    db.session.flush()

    oi = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_snapshot=json.dumps({'name': product.name, 'price': float(gb.group_price), 'main_image': product.main_image}, ensure_ascii=False),
        quantity=1,
        price=gb.group_price,
        subtotal=float(gb.group_price),
    )
    db.session.add(oi)
    product.stock -= 1
    product.sales_count += 1

    participant = GroupBuyParticipant(
        group_id=group.id,
        user_id=current_user.id,
        order_id=order.id,
        is_leader=0,
    )
    db.session.add(participant)

    group.current_count += 1
    if group.current_count >= gb.required_count:
        group.status = 'success'

    log = OrderLog(order_id=order.id, action='paid', operator=current_user.username, detail='拼团订单(参团)')
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '参团成功！' + ('🎉 拼团成功！' if group.status == 'success' else f'还需{gb.required_count - group.current_count}人'),
    })


# ============================================================
# Lottery
# ============================================================

@marketing_bp.route('/lottery')
def lottery_list():
    now = datetime.utcnow()
    lotteries = LotteryActivity.query.filter(
        LotteryActivity.status == 1,
        LotteryActivity.start_time <= now,
        LotteryActivity.end_time >= now
    ).all()
    return render_template('marketing/lottery_list.html', lotteries=lotteries)


@marketing_bp.route('/lottery/<int:lid>')
def lottery_detail(lid):
    lottery = LotteryActivity.query.get_or_404(lid)
    now = datetime.utcnow()

    # Check daily limit for this user
    can_draw = True
    daily_count = 0
    if current_user.is_authenticated:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = LotteryRecord.query.filter(
            LotteryRecord.lottery_id == lid,
            LotteryRecord.user_id == current_user.id,
            LotteryRecord.created_at >= today_start
        ).count()
        if daily_count >= lottery.daily_limit:
            can_draw = False

    return render_template('marketing/lottery_detail.html', lottery=lottery, can_draw=can_draw, daily_count=daily_count)


@marketing_bp.route('/lottery/<int:lid>/draw', methods=['POST'])
@login_required
def lottery_draw(lid):
    lottery = LotteryActivity.query.get_or_404(lid)
    now = datetime.utcnow()

    if now < lottery.start_time or now > lottery.end_time:
        return jsonify({'success': False, 'message': '活动未开始或已结束'}), 400

    # Check daily limit
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = LotteryRecord.query.filter(
        LotteryRecord.lottery_id == lid,
        LotteryRecord.user_id == current_user.id,
        LotteryRecord.created_at >= today_start
    ).count()
    if daily_count >= lottery.daily_limit:
        return jsonify({'success': False, 'message': '今日抽奖次数已用完'}), 400

    # Weighted random selection
    prizes = lottery.get_prizes()
    if not prizes:
        return jsonify({'success': False, 'message': '奖品数据异常'}), 400

    # Normalize: prize with highest prob is the "consolation" prize
    total_prob = sum(p['prob'] for p in prizes)
    rand_val = random.random() * total_prob
    cumulative = 0
    selected_index = len(prizes) - 1  # default to last prize
    for i, prize in enumerate(prizes):
        cumulative += prize['prob']
        if rand_val <= cumulative:
            selected_index = i
            break

    selected_prize = prizes[selected_index]
    is_winner = selected_prize['name'] != '谢谢参与'

    record = LotteryRecord(
        lottery_id=lid,
        user_id=current_user.id,
        prize_index=selected_index,
        prize_name=selected_prize['name'],
        is_winner=1 if is_winner else 0,
        status='pending',
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'success': True,
        'prize_name': selected_prize['name'],
        'is_winner': is_winner,
    })


# ============================================================
# Flash Sale
# ============================================================

@marketing_bp.route('/flash-sale')
def flash_sale_list():
    now = datetime.utcnow()
    ongoing = FlashSale.query.filter(
        FlashSale.status == 1,
        FlashSale.start_time <= now,
        FlashSale.end_time >= now
    ).all()
    upcoming = FlashSale.query.filter(
        FlashSale.status == 1,
        FlashSale.start_time > now
    ).all()
    return render_template('marketing/flash_sale_list.html', ongoing=ongoing, upcoming=upcoming, now=now)


@marketing_bp.route('/flash-sale/<int:fs_id>/buy', methods=['POST'])
@login_required
def flash_sale_buy(fs_id):
    fs = FlashSale.query.with_for_update().get_or_404(fs_id)
    now = datetime.utcnow()

    if now < fs.start_time or now > fs.end_time:
        return jsonify({'success': False, 'message': '秒杀活动未开始或已结束'}), 400
    if fs.stock <= 0:
        return jsonify({'success': False, 'message': '已售罄'}), 400

    # Check per-user limit
    data = request.get_json() if request.is_json else {}
    address_id = get_param(data, 'address_id', cast=int)
    if not address_id:
        return jsonify({'success': False, 'message': '请选择收货地址'}), 400

    existing_orders = Order.query.join(OrderItem).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == fs.product_id,
        Order.created_at >= fs.start_time,
        Order.created_at <= fs.end_time,
        Order.status != 'cancelled',
    ).count()

    if existing_orders >= fs.limit_per_user:
        return jsonify({'success': False, 'message': f'每个用户限购{fs.limit_per_user}件'}), 400

    # Create order
    product = fs.product
    address_snapshot = '{}'
    from app.models import UserAddress
    addr = UserAddress.query.get(address_id)
    if addr and addr.user_id == current_user.id:
        address_snapshot = json.dumps({
            'receiver_name': addr.receiver_name,
            'phone': addr.phone,
            'province': addr.province,
            'city': addr.city,
            'district': addr.district,
            'detail': addr.detail,
        }, ensure_ascii=False)

    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot=address_snapshot,
        product_total=fs.flash_price,
        pay_amount=float(fs.flash_price),
        status='pending_pay',
    )
    db.session.add(order)
    db.session.flush()

    oi = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_snapshot=json.dumps({'name': product.name, 'price': float(fs.flash_price), 'main_image': product.main_image}, ensure_ascii=False),
        quantity=1,
        price=fs.flash_price,
        subtotal=float(fs.flash_price),
    )
    db.session.add(oi)

    fs.stock -= 1

    log = OrderLog(order_id=order.id, action='created', operator=current_user.username, detail='秒杀订单')
    db.session.add(log)

    db.session.commit()

    return jsonify({'success': True, 'message': '秒杀成功！', 'order_id': order.id})


# ============================================================
# Bargain
# ============================================================

@marketing_bp.route('/bargain')
def bargain_list():
    now = datetime.utcnow()
    bargains = BargainActivity.query.filter(
        BargainActivity.status == 1,
        BargainActivity.start_time <= now,
        BargainActivity.end_time >= now
    ).all()
    return render_template('marketing/bargain_list.html', bargains=bargains)


@marketing_bp.route('/bargain/<int:bid>')
def bargain_detail(bid):
    bargain = BargainActivity.query.get_or_404(bid)
    record = None
    if current_user.is_authenticated:
        record = BargainRecord.query.filter_by(
            bargain_id=bid, user_id=current_user.id, status='bargaining'
        ).first()
    return render_template('marketing/bargain_detail.html', bargain=bargain, record=record)


@marketing_bp.route('/bargain/<int:bid>/start', methods=['POST'])
@login_required
def start_bargain(bid):
    bargain = BargainActivity.query.get_or_404(bid)
    now = datetime.utcnow()

    if now < bargain.start_time or now > bargain.end_time:
        return jsonify({'success': False, 'message': '活动未开始或已结束'}), 400

    existing = BargainRecord.query.filter_by(
        bargain_id=bid, user_id=current_user.id, status='bargaining'
    ).first()
    if existing:
        return jsonify({'success': False, 'message': '已有一个进行中的砍价', 'record_id': existing.id}), 400

    record = BargainRecord(
        bargain_id=bid,
        user_id=current_user.id,
        current_price=bargain.original_price,
        helper_count=0,
        max_helpers=bargain.max_helpers,
        status='bargaining',
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'message': '砍价开始！分享给好友帮你砍价吧！', 'record_id': record.id})


@marketing_bp.route('/bargain/<int:record_id>/help', methods=['POST'])
@login_required
def help_bargain(record_id):
    record = BargainRecord.query.get_or_404(record_id)
    if record.status != 'bargaining':
        return jsonify({'success': False, 'message': '砍价已结束'}), 400
    if record.helper_count >= record.max_helpers:
        return jsonify({'success': False, 'message': '已达到最大帮砍次数'}), 400

    # Random reduction amount
    remaining = float(record.current_price) - float(record.bargain.floor_price)
    if remaining <= 0:
        return jsonify({'success': False, 'message': '已砍到最低价'}), 400

    # Reduction: 5-20% of remaining amount
    reduction = round(random.uniform(0.05, 0.20) * remaining, 2)
    reduction = max(0.01, min(reduction, remaining))

    record.current_price = round(float(record.current_price) - reduction, 2)
    record.helper_count += 1

    # Check if hit floor
    if float(record.current_price) <= float(record.bargain.floor_price):
        record.current_price = record.bargain.floor_price

    helper = BargainHelper(
        bargain_record_id=record_id,
        helper_user_id=current_user.id,
        reduced_amount=reduction,
    )
    db.session.add(helper)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'帮砍成功！砍掉 ¥{reduction:.2f}',
        'current_price': float(record.current_price),
        'helper_count': record.helper_count,
        'max_helpers': record.max_helpers,
    })


@marketing_bp.route('/bargain/<int:record_id>/buy', methods=['POST'])
@login_required
def buy_bargain(record_id):
    record = BargainRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403
    if record.status != 'bargaining':
        return jsonify({'success': False, 'message': '砍价已结束'}), 400

    data = request.get_json() if request.is_json else {}
    address_id = get_param(data, 'address_id', cast=int)

    address_snapshot = '{}'
    if address_id:
        from app.models import UserAddress
        addr = UserAddress.query.get(address_id)
        if addr and addr.user_id == current_user.id:
            address_snapshot = json.dumps({
                'receiver_name': addr.receiver_name,
                'phone': addr.phone,
                'province': addr.province,
                'city': addr.city,
                'district': addr.district,
                'detail': addr.detail,
            }, ensure_ascii=False)

    product = record.bargain.product
    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot=address_snapshot,
        product_total=record.current_price,
        pay_amount=float(record.current_price),
        status='pending_pay',
    )
    db.session.add(order)
    db.session.flush()

    oi = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_snapshot=json.dumps({'name': product.name, 'price': float(record.current_price), 'main_image': product.main_image}, ensure_ascii=False),
        quantity=1,
        price=record.current_price,
        subtotal=float(record.current_price),
    )
    db.session.add(oi)

    record.status = 'bought'
    record.order_id = order.id

    log = OrderLog(order_id=order.id, action='created', operator=current_user.username,
                   detail=f'砍价订单，砍后价格 ¥{float(record.current_price):.2f}')
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': '下单成功！', 'order_id': order.id})


# ============================================================
# Blind Box
# ============================================================

@marketing_bp.route('/blind-box')
def blind_box_list():
    now = datetime.utcnow()
    boxes = BlindBox.query.filter(
        BlindBox.status == 1,
        BlindBox.start_time <= now,
        BlindBox.end_time >= now
    ).all()
    return render_template('marketing/blind_box_list.html', boxes=boxes)


@marketing_bp.route('/blind-box/<int:bb_id>')
def blind_box_detail(bb_id):
    box = BlindBox.query.get_or_404(bb_id)
    remaining = box.total_count - box.sold_count
    return render_template('marketing/blind_box_detail.html', box=box, remaining=remaining)


@marketing_bp.route('/blind-box/<int:bb_id>/open', methods=['POST'])
@login_required
def open_blind_box(bb_id):
    box = BlindBox.query.with_for_update().get_or_404(bb_id)
    now = datetime.utcnow()

    if now < box.start_time or now > box.end_time:
        return jsonify({'success': False, 'message': '活动未开始或已结束'}), 400
    if box.sold_count >= box.total_count:
        return jsonify({'success': False, 'message': '盲盒已售罄'}), 400

    # Weighted random prize selection
    contents = box.get_contents()
    total_prob = sum(c['prob'] for c in contents)
    rand_val = random.random() * total_prob
    cumulative = 0
    selected = contents[-1]
    for content in contents:
        cumulative += content['prob']
        if rand_val <= cumulative:
            selected = content
            break

    # Create order
    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        address_snapshot='{}',
        product_total=box.price,
        pay_amount=float(box.price),
        status='pending_ship',
        paid_at=now,
    )
    db.session.add(order)
    db.session.flush()

    oi = OrderItem(
        order_id=order.id,
        product_id=1,  # dummy
        product_snapshot=json.dumps({'name': f'盲盒 - {selected["name"]}', 'price': float(box.price), 'main_image': ''}, ensure_ascii=False),
        quantity=1,
        price=box.price,
        subtotal=float(box.price),
    )
    db.session.add(oi)

    box.sold_count += 1

    bbo = BlindBoxOrder(
        blind_box_id=bb_id,
        user_id=current_user.id,
        order_id=order.id,
        prize_content=selected['name'],
    )
    db.session.add(bbo)

    log = OrderLog(order_id=order.id, action='paid', operator=current_user.username,
                   detail=f'盲盒开箱，获得: {selected["name"]}')
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'恭喜获得：{selected["name"]}！',
        'prize': selected['name'],
        'order_id': order.id,
    })
