import re
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

from config import Config
from models import db, User, Order, PLANS

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    from api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/launcher")

    # ---------- helpers ----------
    def current_user():
        uid = session.get("uid")
        if not uid:
            return None
        return db.session.get(User, uid)

    def login_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not current_user():
                return redirect(url_for("login", next=request.path))
            return fn(*a, **kw)
        return wrapper

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u or not u.is_admin:
                abort(404)
            return fn(*a, **kw)
        return wrapper

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user(), "plans": PLANS}

    # ---------- pages ----------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/pricing")
    def pricing():
        return render_template("pricing.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user():
            return redirect(url_for("profile"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "")

            if not USERNAME_RE.match(username):
                flash("Логин: 3-20 символов, латиница/цифры/подчёркивание.", "error")
            elif len(password) < 6:
                flash("Пароль должен быть не короче 6 символов.", "error")
            elif password != confirm:
                flash("Пароли не совпадают.", "error")
            elif User.query.filter_by(username=username).first():
                flash("Такой логин уже занят.", "error")
            else:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                session["uid"] = user.id
                flash("Аккаунт создан.", "success")
                return redirect(url_for("profile"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("profile"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session["uid"] = user.id
                return redirect(request.args.get("next") or url_for("profile"))
            flash("Неверный логин или пароль.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/profile")
    @login_required
    def profile():
        user = current_user()
        my_orders = user.orders.order_by(Order.created_at.desc()).limit(10).all()
        return render_template("profile.html", user=user, orders=my_orders)

    @app.route("/profile/regenerate-token", methods=["POST"])
    @login_required
    def regenerate_token():
        user = current_user()
        user.regenerate_license_token()
        db.session.commit()
        flash("Токен лаунчера обновлён.", "success")
        return redirect(url_for("profile"))

    @app.route("/buy/<plan_key>", methods=["POST"])
    @login_required
    def buy(plan_key):
        if plan_key not in PLANS:
            abort(404)
        user = current_user()
        plan = PLANS[plan_key]
        order = Order(user_id=user.id, plan=plan_key, price=plan["price"], status="pending")
        db.session.add(order)
        db.session.commit()
        flash(
            f"Заявка на «{plan['label']}» создана ({plan['price']}₽). "
            "Оплата пока не автоматизирована — переведите средства и дождитесь подтверждения администратором.",
            "success",
        )
        return redirect(url_for("profile"))

    # ---------- admin ----------
    @app.route("/admin")
    @admin_required
    def admin_home():
        pending = Order.query.filter_by(status="pending").order_by(Order.created_at.asc()).all()
        return render_template("admin.html", pending=pending)

    @app.route("/admin/orders/<int:order_id>/approve", methods=["POST"])
    @admin_required
    def admin_approve(order_id):
        order = db.session.get(Order, order_id) or abort(404)
        if order.status == "pending":
            plan = PLANS[order.plan]
            if order.plan == "hwid_reset":
                order.user.hwid = None
            else:
                order.user.extend_subscription(plan["days"])
            order.status = "paid"
            from models import now
            order.resolved_at = now()
            db.session.commit()
            flash(f"Заказ #{order.id} подтверждён.", "success")
        return redirect(url_for("admin_home"))

    @app.route("/admin/orders/<int:order_id>/cancel", methods=["POST"])
    @admin_required
    def admin_cancel(order_id):
        order = db.session.get(Order, order_id) or abort(404)
        if order.status == "pending":
            order.status = "cancelled"
            from models import now
            order.resolved_at = now()
            db.session.commit()
        return redirect(url_for("admin_home"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
