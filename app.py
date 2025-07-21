from flask import Flask, render_template
from flask_login import LoginManager, login_required, current_user
from config import Config
from flask_babel import Babel
import os
from models import db
from models.product import Product
from models.category import Category
from models.user import User
from models.branch import Branch
from models.dealer import Dealer
from models.movement import ProductMovement
from models.request import ProductRequest
from models.notification import BranchNotification
from models.branch_inventory import BranchInventory

# Initialize extensions
login_manager = LoginManager()
babel = Babel()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    # إعداد صفحة تسجيل الدخول الافتراضية
    login_manager.login_view = 'auth.login'
    # Set Arabic as default language using locale_selector
    def get_locale():
        return 'ar'
    babel.init_app(app, locale_selector=get_locale)

    # Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    from routes.products import products_bp
    app.register_blueprint(products_bp)
    from routes.categories import categories_bp
    app.register_blueprint(categories_bp)
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    from routes.stats import stats_bp
    app.register_blueprint(stats_bp)
    from routes.movements import movements_bp
    app.register_blueprint(movements_bp)
    from routes.dealers import dealers_bp
    app.register_blueprint(dealers_bp)
    from routes.branches import branches_bp
    app.register_blueprint(branches_bp)
    from routes.branch_dashboard import branch_dashboard_bp
    app.register_blueprint(branch_dashboard_bp)
    from routes.pos import pos_bp
    app.register_blueprint(pos_bp)
    from routes.customers import customers_bp
    app.register_blueprint(customers_bp)
    from routes.reports import reports_bp
    app.register_blueprint(reports_bp)

    # Dashboard route
    @app.route("/")
    @login_required
    def dashboard():
        users_count = User.query.count()
        products_count = Product.query.count()
        categories_count = Category.query.count()
        branches_count = Branch.query.count()
        dealers_count = Dealer.query.count()
        movements_count = ProductMovement.query.count()

        # إشعارات المنتجات القليلة
        low_stock_products = Product.query.filter(Product.quantity < 10).all()
        notifications = []
        for p in low_stock_products:
            notifications.append(f"المنتج '{p.name}' متبقي منه {p.quantity} فقط في المخزون!")

        return render_template('dashboard.html',
                             users_count=users_count,
                             products_count=products_count,
                             categories_count=categories_count,
                             branches_count=branches_count,
                             dealers_count=dealers_count,
                             movements_count=movements_count,
                             notifications=notifications)

    # TODO: Register other blueprints (admin, products, stats, shifts)

    @app.template_filter('get_branch_name')
    def get_branch_name(branch_id):
        from models.branch import Branch
        branch = Branch.query.get(branch_id)
        return branch.name if branch else f'فرع {branch_id}'

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

