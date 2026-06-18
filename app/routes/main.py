from flask import Blueprint, render_template, request
from app.models import Product, Category, FlashSale
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    # Get recommended products
    recommended = Product.query.filter_by(status=1, is_recommend=1).limit(8).all()
    # Get flash sales
    now = datetime.utcnow()
    flash_sales = FlashSale.query.filter(
        FlashSale.status == 1,
        FlashSale.start_time <= now,
        FlashSale.end_time >= now
    ).limit(4).all()
    # Get categories
    categories = Category.query.order_by(Category.sort_order).all()
    # Hot products (by sales)
    hot_products = Product.query.filter_by(status=1).order_by(Product.sales_count.desc()).limit(8).all()

    return render_template('home.html',
                           recommended=recommended,
                           flash_sales=flash_sales,
                           categories=categories,
                           hot_products=hot_products,
                           now=now)


@main_bp.route('/products')
def product_list():
    page = request.args.get('page', 1, type=int)
    cat_id = request.args.get('cat', 0, type=int)
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'default')

    query = Product.query.filter_by(status=1)

    if cat_id > 0:
        query = query.filter_by(category_id=cat_id)
    if q:
        query = query.filter(Product.name.like(f'%{q}%'))

    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'sales':
        query = query.order_by(Product.sales_count.desc())
    else:
        query = query.order_by(Product.id.desc())

    pagination = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.order_by(Category.sort_order).all()

    return render_template('products/list.html',
                           products=pagination.items,
                           pagination=pagination,
                           categories=categories,
                           current_cat=cat_id,
                           q=q,
                           sort=sort)


@main_bp.route('/products/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.status == 1
    ).limit(4).all()

    return render_template('products/detail.html', product=product, related=related)


@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return product_list()
    products = Product.query.filter(
        Product.name.like(f'%{q}%'),
        Product.status == 1
    ).limit(20).all()
    return render_template('products/list.html', products=products, q=q, categories=Category.query.all())
