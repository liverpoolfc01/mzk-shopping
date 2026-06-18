import os
from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.models import db, User


login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    # Point static_folder to project root's static/ directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(__name__, static_folder=static_dir, static_url_path='/static')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure upload directory exists
    upload_dir = os.path.join(static_dir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir

    # Create a proper placeholder image if it doesn't exist
    placeholder_path = os.path.join(upload_dir, 'placeholder.png')
    if not os.path.exists(placeholder_path):
        _create_placeholder(placeholder_path)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.cart import cart_bp
    from app.routes.order import order_bp
    from app.routes.user import user_bp
    from app.routes.marketing import marketing_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(marketing_bp)
    app.register_blueprint(admin_bp)

    # Context processors
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        cart_count = 0
        if current_user.is_authenticated:
            from app.models import CartItem
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return dict(cart_count=cart_count)

    return app


def _create_placeholder(path):
    """Create a proper 200x200 gray placeholder PNG image."""
    import struct
    import zlib

    width, height = 200, 200
    # Create a simple gray gradient PNG

    def create_png(w, h):
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            return struct.pack('>I', len(data)) + c + crc

        # IHDR
        ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
        ihdr = chunk(b'IHDR', ihdr_data)

        # IDAT: gray pixels with "商品图片" text approximation
        raw = b''
        for y in range(h):
            raw += b'\x00'  # filter byte
            for x in range(w):
                # Light gray background
                r, g, b = 240, 240, 240
                # Draw a simple border
                if x < 2 or x >= w-2 or y < 2 or y >= h-2:
                    r, g, b = 220, 220, 220
                raw += struct.pack('BBB', r, g, b)

        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')

        return b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend

    png_data = create_png(width, height)
    with open(path, 'wb') as f:
        f.write(png_data)
