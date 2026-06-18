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
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure upload directory exists
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Create a placeholder image
    placeholder_path = os.path.join(app.config['UPLOAD_FOLDER'], 'placeholder.png')
    if not os.path.exists(placeholder_path):
        # Create a simple 1-pixel PNG as placeholder
        # Minimal valid PNG
        png_data = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
                    b'\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        with open(placeholder_path, 'wb') as f:
            f.write(png_data)

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
