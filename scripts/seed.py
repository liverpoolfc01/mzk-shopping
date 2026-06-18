"""Seed the database with default data.
Creates: admin account, test user, 5 categories, 20 products,
3 coupons, 1 group buy, 1 lottery, 1 flash sale.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, UserAddress, Category, Product, Coupon
from app.models import GroupBuy, LotteryActivity, FlashSale
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json

app = create_app()


def seed():
    with app.app_context():
        print('Seeding database...')

        # ---- Users ----
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('test1234'),
                email='admin@mzk-shop.com',
                role='admin',
                status=1
            )
            db.session.add(admin)
            print('Created admin account: admin / test1234')

        if not User.query.filter_by(username='test').first():
            user = User(
                username='test',
                password_hash=generate_password_hash('test1234'),
                email='test@example.com',
                phone='13800138000',
                role='user',
                status=1
            )
            db.session.add(user)
            db.session.flush()

            # Add a default address for test user
            addr = UserAddress(
                user_id=user.id,
                receiver_name='测试用户',
                phone='13800138000',
                province='广东省',
                city='深圳市',
                district='南山区',
                detail='科技园路1号创新大厦A座1001室',
                is_default=1
            )
            db.session.add(addr)
            print('Created test user: test / test1234')

        db.session.commit()

        # ---- Categories ----
        categories_data = [
            {'name': '手机数码', 'sort_order': 1, 'icon': '📱'},
            {'name': '服装鞋帽', 'sort_order': 2, 'icon': '👗'},
            {'name': '食品饮料', 'sort_order': 3, 'icon': '🍜'},
            {'name': '家居用品', 'sort_order': 4, 'icon': '🏠'},
            {'name': '美妆护肤', 'sort_order': 5, 'icon': '💄'},
        ]

        cat_objs = {}
        for cdata in categories_data:
            existing = Category.query.filter_by(name=cdata['name']).first()
            if existing:
                cat_objs[cdata['name']] = existing
            else:
                cat = Category(**cdata)
                db.session.add(cat)
                db.session.flush()
                cat_objs[cdata['name']] = cat
        db.session.commit()
        print(f'Created/verified {len(cat_objs)} categories')

        # ---- Products (20) ----
        products_data = [
            # 手机数码 (4)
            {'name': 'iPhone 15 Pro Max 256GB', 'description': 'Apple最新旗舰手机，A17 Pro芯片，钛金属设计，4800万像素主摄', 'category': '手机数码', 'price': 9999.00, 'original_price': 10999.00, 'stock': 50},
            {'name': '华为Mate 60 Pro', 'description': '麒麟9000S芯片，卫星通话，超可靠玄武架构', 'category': '手机数码', 'price': 6999.00, 'original_price': 7999.00, 'stock': 30},
            {'name': 'Sony WH-1000XM5 头戴式降噪耳机', 'description': '业界领先的降噪技术，30小时续航，舒适佩戴', 'category': '手机数码', 'price': 2299.00, 'original_price': 2999.00, 'stock': 100},
            {'name': 'iPad Air M2 11英寸', 'description': 'M2芯片，Liquid Retina显示屏，支持Apple Pencil Pro', 'category': '手机数码', 'price': 4799.00, 'original_price': 4999.00, 'stock': 40},
            # 服装鞋帽 (4)
            {'name': 'Nike Air Jordan 1 Retro High OG', 'description': '经典复刻，头层牛皮，Air Sole气垫', 'category': '服装鞋帽', 'price': 1299.00, 'original_price': 1499.00, 'stock': 200},
            {'name': '优衣库轻薄羽绒服', 'description': '90%白鹅绒，轻薄保暖，可收纳设计', 'category': '服装鞋帽', 'price': 499.00, 'original_price': 799.00, 'stock': 500},
            {'name': 'Levi\'s 501经典直筒牛仔裤', 'description': '原创直筒版型，100%纯棉丹宁，经典永不过时', 'category': '服装鞋帽', 'price': 599.00, 'original_price': 899.00, 'stock': 150},
            {'name': 'Adidas Ultraboost 23 跑鞋', 'description': 'Boost中底科技，Primeknit+编织鞋面，极致脚感', 'category': '服装鞋帽', 'price': 899.00, 'original_price': 1299.00, 'stock': 180},
            # 食品饮料 (4)
            {'name': '三只松鼠坚果大礼包 1588g', 'description': '12袋精选坚果零食，年货送礼佳品，每日坚果混合装', 'category': '食品饮料', 'price': 99.00, 'original_price': 168.00, 'stock': 1000},
            {'name': '茅台飞天53度 500ml', 'description': '贵州茅台酒，酱香型白酒典范，国酒之尊', 'category': '食品饮料', 'price': 1499.00, 'original_price': 1999.00, 'stock': 20},
            {'name': 'Swisse 钙+维生素D 150片', 'description': '澳洲进口，柠檬酸钙易吸收，强健骨骼牙齿', 'category': '食品饮料', 'price': 119.00, 'original_price': 199.00, 'stock': 300},
            {'name': '星巴克中度烘焙咖啡豆 1.13kg', 'description': '100%阿拉比卡咖啡豆，焦糖风味，醇香浓郁', 'category': '食品饮料', 'price': 168.00, 'original_price': 228.00, 'stock': 250},
            # 家居用品 (4)
            {'name': '小米米家扫地机器人3C', 'description': 'LDS激光导航，5000Pa大吸力，智能路径规划', 'category': '家居用品', 'price': 1299.00, 'original_price': 1699.00, 'stock': 80},
            {'name': '戴森V15 Detect无绳吸尘器', 'description': '激光探测微尘，LCD屏实时显示，60分钟续航', 'category': '家居用品', 'price': 4990.00, 'original_price': 5490.00, 'stock': 35},
            {'name': '网易严选泰国乳胶枕', 'description': '93%天然乳胶含量，人体工学曲线，透气抗菌', 'category': '家居用品', 'price': 199.00, 'original_price': 399.00, 'stock': 600},
            {'name': 'MUJI 超声波香薰机', 'description': '简约设计，静音运行，4小时定时，柔和LED灯', 'category': '家居用品', 'price': 288.00, 'original_price': 388.00, 'stock': 120},
            # 美妆护肤 (4)
            {'name': 'SK-II 神仙水 230ml', 'description': '含90%以上PITERA™精华，焕发肌肤晶莹剔透', 'category': '美妆护肤', 'price': 1370.00, 'original_price': 1590.00, 'stock': 60},
            {'name': '兰蔻小黑瓶精华肌底液 50ml', 'description': '第二代小黑瓶，修护肌肤屏障，提升肌肤光泽', 'category': '美妆护肤', 'price': 899.00, 'original_price': 1100.00, 'stock': 70},
            {'name': 'Tom Ford 黑管唇膏 #16 Scarlet Rouge', 'description': '经典番茄红，丝滑质地，显白不挑皮', 'category': '美妆护肤', 'price': 420.00, 'original_price': 480.00, 'stock': 150},
            {'name': '雅诗兰黛持妆粉底液 30ml', 'description': 'DW持妆粉底，24小时控油遮瑕，哑光妆效', 'category': '美妆护肤', 'price': 395.00, 'original_price': 450.00, 'stock': 90},
        ]

        img_map = {
            '手机数码': ['/static/uploads/placeholder.png'],
            '服装鞋帽': ['/static/uploads/placeholder.png'],
            '食品饮料': ['/static/uploads/placeholder.png'],
            '家居用品': ['/static/uploads/placeholder.png'],
            '美妆护肤': ['/static/uploads/placeholder.png'],
        }

        existing_products = Product.query.count()
        if existing_products < 20:
            for idx, pdata in enumerate(products_data):
                cat = cat_objs[pdata['category']]
                images = json.dumps(img_map.get(pdata['category'], ['/static/uploads/placeholder.png']))
                product = Product(
                    name=pdata['name'],
                    description=pdata['description'],
                    category_id=cat.id,
                    price=pdata['price'],
                    original_price=pdata['original_price'],
                    stock=pdata['stock'],
                    images=images,
                    main_image=img_map.get(pdata['category'], ['/static/uploads/placeholder.png'])[0],
                    detail_images='[]',
                    sales_count=0,
                    status=1,
                    is_recommend=1 if idx < 8 else 0,
                )
                db.session.add(product)
            db.session.commit()
            print(f'Created 20 products')
        else:
            print(f'Products already exist ({existing_products}), skipping')

        # ---- Coupons ----
        if Coupon.query.count() == 0:
            now = datetime.utcnow()
            coupons = [
                Coupon(name='新人专享10元券', type='fixed', value=10.00, min_amount=50.00,
                       total_count=500, used_count=0,
                       start_time=now, end_time=now + timedelta(days=90)),
                Coupon(name='满200减30', type='fixed', value=30.00, min_amount=200.00,
                       total_count=200, used_count=0,
                       start_time=now, end_time=now + timedelta(days=60)),
                Coupon(name='全场85折', type='percent', value=15.00, min_amount=100.00,
                       total_count=100, used_count=0,
                       start_time=now, end_time=now + timedelta(days=30)),
            ]
            db.session.add_all(coupons)
            db.session.commit()
            print('Created 3 coupons')
        else:
            print('Coupons already exist, skipping')

        # ---- Group Buy ----
        if GroupBuy.query.count() == 0:
            product = Product.query.first()
            if product:
                now = datetime.utcnow()
                gb = GroupBuy(
                    product_id=product.id,
                    title=f'{product.name} 三人拼团',
                    group_price=round(float(product.price) * 0.75, 2),
                    required_count=3,
                    duration_hours=24,
                    start_time=now,
                    end_time=now + timedelta(days=30),
                    status=1,
                )
                db.session.add(gb)
                db.session.commit()
                print('Created 1 group buy')
        else:
            print('Group buys already exist, skipping')

        # ---- Lottery ----
        if LotteryActivity.query.count() == 0:
            now = datetime.utcnow()
            prizes = json.dumps([
                {'name': 'iPhone 15 Pro Max', 'count': 1, 'prob': 0.01, 'image': ''},
                {'name': '50元优惠券', 'count': 50, 'prob': 0.10, 'image': ''},
                {'name': '20元优惠券', 'count': 100, 'prob': 0.15, 'image': ''},
                {'name': '10元优惠券', 'count': 200, 'prob': 0.24, 'image': ''},
                {'name': '5元红包', 'count': 500, 'prob': 0.30, 'image': ''},
                {'name': '谢谢参与', 'count': 9999, 'prob': 0.70, 'image': ''},
            ])
            lottery = LotteryActivity(
                title='618年中大抽奖',
                description='活动期间每位用户每天可抽奖1次，丰厚奖品等你来拿！',
                start_time=now,
                end_time=now + timedelta(days=30),
                prizes=prizes,
                cost_type='free',
                daily_limit=1,
                status=1,
            )
            db.session.add(lottery)
            db.session.commit()
            print('Created 1 lottery activity')
        else:
            print('Lottery already exists, skipping')

        # ---- Flash Sale ----
        if FlashSale.query.count() == 0:
            second_product = Product.query.order_by(Product.id).offset(1).first()
            if second_product:
                now = datetime.utcnow()
                fs = FlashSale(
                    product_id=second_product.id,
                    title=f'{second_product.name} 限时秒杀',
                    flash_price=round(float(second_product.price) * 0.5, 2),
                    stock=20,
                    limit_per_user=1,
                    start_time=now,
                    end_time=now + timedelta(days=7),
                    status=1,
                )
                db.session.add(fs)
                db.session.commit()
                print('Created 1 flash sale')
        else:
            print('Flash sales already exist, skipping')

        print('\n✅ Database seeding complete!')


if __name__ == '__main__':
    seed()
