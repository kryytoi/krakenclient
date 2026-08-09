import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash('Пользователь с таким именем или Email уже существует!', 'error')
                return redirect(url_for('register'))
                
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('profile'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                return redirect(url_for('profile'))
            flash('Неверный логин или пароль!', 'error')
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('index'))

    @app.route('/profile')
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        return render_template('profile.html', user=user)

    @app.route('/buy/<plan>', methods=['POST'])
    def buy(plan):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        now = datetime.now(timezone.utc)
        
        if plan == '30days':
            base_time = user.subscription_until.replace(tzinfo=timezone.utc) if (user.subscription_until and user.has_active_sub()) else now
            user.subscription_until = base_time + timedelta(days=30)
        elif plan == '120days':
            base_time = user.subscription_until.replace(tzinfo=timezone.utc) if (user.subscription_until and user.has_active_sub()) else now
            user.subscription_until = base_time + timedelta(days=120)
        elif plan == 'lifetime':
            user.is_lifetime = True
        elif plan == 'reset_hwid':
            user.hwid = None
            
        db.session.commit()
        return redirect(url_for('profile'))

    # REST API для связи с Лаунчером
    @app.route('/api/v1/login', methods=['POST'])
    def api_login():
        data = request.get_json(silent=True) or request.form
        user = User.query.filter_by(username=data.get('username')).first()
        if not user or not check_password_hash(user.password_hash, data.get('password', '')):
            return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401
            
        if not user.has_active_sub():
            return jsonify({"status": "error", "message": "Подписка не активна"}), 403
            
        hwid = data.get('hwid')
        if not user.hwid:
            user.hwid = hwid
            db.session.commit()
        elif user.hwid != hwid:
            return jsonify({"status": "error", "message": "HWID не совпадает! Сбросьте его в профиле"}), 403
            
        return jsonify({"status": "success", "user": user.to_dict()})

    return app

app = create_app()
