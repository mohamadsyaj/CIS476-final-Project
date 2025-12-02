from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from models import db
from models.user import User
from models.vault_item import VaultItem
from models.notification import Notification
from datetime import datetime, timedelta
from patterns.observer import BookingSubject, UserObserver
from patterns.data_proxy import DataProxy, mask_preview, mask_preview_dict
from patterns.singleton import UserSession
from patterns.password_builder import generate_password as builder_generate_password
from models.unmask_token import UnmaskToken
from utils.crypto import load_key, encrypt_json, decrypt_json
import os


app = Flask(__name__)
app.secret_key = os.environ.get('MYPASS_SECRET', 'supersecretkey')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'mypass.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def _infer_display_type(item_type, key):
    k = (key or '').lower()
    if 'passport' in k or 'license' in k or 'ssn' in k:
        return 'Identity'
    if 'card' in k or 'cvv' in k or (item_type and item_type.lower().startswith('credit') and 'expiry' in k):
        return 'CreditCard'
    return item_type or 'Item'


def check_and_notify_expiries(user):
    if not user:
        return
    items = VaultItem.query.filter_by(user_id=user.id).all()
    subj = BookingSubject()
    subj.attach(UserObserver(user))
    now = datetime.utcnow()
    for it in items:
        try:
            data = decrypt_json(it.encrypted_data) or {}
        except Exception:
            data = {}
        for k, v in data.items():
            if not v:
                continue
            key = (k or '').lower()
            # determine if field looks like an expiry
            is_expiry = False
            if 'expiry' in key or 'exp' in key:
                if key == 'expiry':
                    if (it.item_type or '').lower().startswith('credit') or (it.item_type or '').lower() == 'identity':
                        is_expiry = True
                else:
                    is_expiry = True
            if not is_expiry:
                continue
            try:
                exp_date = datetime.fromisoformat(v)
            except Exception:
                try:
                    exp_date = datetime.fromisoformat(v + '-01')
                except Exception:
                    exp_date = None
            if not exp_date:
                continue
            display_type = _infer_display_type(it.item_type, key)
            if exp_date < now:
                subj.status_changed(f'Item "{it.title}" ({display_type}) has expired ({k}).')
            elif exp_date < now + timedelta(days=30):
                subj.status_changed(f'Item "{it.title}" ({display_type}) will expire soon ({k}).')


def password_is_strong(pw: str) -> bool:
    if not pw or len(pw) < 8:
        return False
    if pw.lower() == pw:
        return False
    if not any(c.isdigit() for c in pw):
        return False
    return True


@app.route('/')
def home():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    # If the server-side singleton/session references a user id that no longer
    # exists in the database (stale test state), clear the session and redirect
    # to login rather than raising an AttributeError.
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))
    try:
        check_and_notify_expiries(user)
    except Exception:
        pass
    notes = Notification.query.filter_by(user_id=user.id, is_read=False).order_by(Notification.timestamp.desc()).all()
    return render_template('home.html', user=user, notifications=notes)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Enforce server-side password strength parity with client
        if not password_is_strong(password):
            flash('Password does not meet strength requirements (min 8 chars, include upper, lower, and digit).', 'error')
            return redirect(url_for('register'))
        user = User(email=email,
                    sec_q1=request.form.get('q1'), sec_a1=request.form.get('a1'),
                    sec_q2=request.form.get('q2'), sec_a2=request.form.get('a2'),
                    sec_q3=request.form.get('q3'), sec_a3=request.form.get('a3'))
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            # account created successfully
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            flash('Unable to register that email.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            session['user_id'] = user.id
            # ensure server-side singleton session mirrors Flask session
            try:
                us = UserSession()
                us.set_user(user.id)
            except Exception:
                pass
            try:
                check_and_notify_expiries(user)
            except Exception:
                pass
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.before_request
def enforce_session_timeout():
    # server-side inactivity auto-lock using the Singleton UserSession
    user_id = session.get('user_id')
    us = UserSession()
    if user_id:
        # if singleton tracks a different user, initialize it
        if us.get_user_id() != user_id:
            us.set_user(user_id)
        # if locked, clear session and notify
        if us.is_locked():
            session.pop('user_id', None)
            us.clear()
            flash('Session locked due to inactivity. Please log in again.', 'info')
            return redirect(url_for('login'))
        # otherwise refresh last activity
        us.touch()



@app.route('/recover', methods=['GET', 'POST'])
def recover():
    # Password recovery flow using three security questions
    if request.method == 'POST':
        email = request.form.get('email')
        # If user is providing answers and a new password
        if request.form.get('reset') or request.form.get('new_password'):
            user = User.query.filter_by(email=request.form.get('email')).first()
            if not user:
                flash('Unknown email', 'error')
                return redirect(url_for('recover'))
            from patterns.chain_of_responsibility import verify_security_answers
            if not verify_security_answers(user, request.form):
                flash('Security answers incorrect', 'error')
                return redirect(url_for('recover'))
            new_password = request.form.get('new_password')
            if not new_password:
                flash('New password required', 'error')
                return redirect(url_for('recover'))
            # Enforce server-side password strength for recovery as well
            if not password_is_strong(new_password):
                flash('Password does not meet strength requirements (min 8 chars, include upper, lower, and digit).', 'error')
                return render_template('recover.html', user=user)
            user.set_password(new_password)
            db.session.commit()
            flash('Password reset successful. Please log in.', 'success')
            return redirect(url_for('login'))
        # initial step: user submitted email to begin recovery
        user = User.query.filter_by(email=email).first() if email else None
        return render_template('recover.html', user=user)
    return render_template('recover.html', user=None)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    try:
        us = UserSession()
        us.clear()
    except Exception:
        pass
    return redirect(url_for('login'))


@app.route('/vault')
def vault():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for('login'))
    items = VaultItem.query.filter_by(user_id=user_id).all()
    proxy = DataProxy()
    previews = []
    for it in items:
        data = decrypt_json(it.encrypted_data) or {}
        # provide both a masked dict for UI and a short string preview
        masked_dict = mask_preview_dict(data) if 'mask_preview_dict' in globals() or hasattr(proxy, 'mask_preview') else {}
        previews.append({'id': it.id, 'title': it.title, 'type': it.item_type, 'preview': masked_dict})
    return render_template('vault.html', items=previews)


@app.route('/vault/add', methods=['GET', 'POST'])
def add_item():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        item_type = request.form['item_type']
        title = request.form['title']
        data = {k: v for k, v in request.form.items() if k not in ('item_type', 'title')}
        encrypted = encrypt_json(data)
        it = VaultItem(user_id=user_id, item_type=item_type, title=title, encrypted_data=encrypted)
        db.session.add(it); db.session.commit()
        return redirect(url_for('vault'))
    return render_template('add_item.html')


@app.route('/vault/edit/<int:item_id>', methods=['GET', 'POST'])
def vault_edit(item_id):
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for('login'))
    it = VaultItem.query.get_or_404(item_id)
    if it.user_id != user_id:
        return 'Unauthorized', 403
    if request.method == 'POST':
        item_type = request.form['item_type']
        title = request.form['title']
        data = {k: v for k, v in request.form.items() if k not in ('item_type', 'title')}
        it.item_type = item_type
        it.title = title
        it.encrypted_data = encrypt_json(data)
        db.session.commit()
        return redirect(url_for('vault'))

    # prepare fields for form prefill
    data = decrypt_json(it.encrypted_data) or {}
    return render_template('add_item.html', item=it, fields=data)


@app.route('/vault/view/<int:item_id>')
def view_item(item_id):
    user_id = current_user_id()
    it = VaultItem.query.get_or_404(item_id)
    if it.user_id != user_id:
        return 'Unauthorized', 403
    data = decrypt_json(it.encrypted_data) or {}
    proxy = DataProxy()
    # masked mapping: field -> masked value
    try:
        from patterns.data_proxy import mask_preview_dict
        masked_map = mask_preview_dict(data)
    except Exception:
        # fallback to string preview if helper missing
        masked_map = {k: proxy._mask_value(v) if any(sub in (k or '').lower() for sub in proxy.SENSITIVE_SUBSTRINGS) else v for k, v in data.items()}
    return render_template('view_item.html', item=it, data=data, masked=masked_map)


@app.route('/vault/delete/<int:item_id>')
def delete_item(item_id):
    user_id = current_user_id()
    it = VaultItem.query.get_or_404(item_id)
    if it.user_id != user_id:
        return 'Unauthorized', 403
    db.session.delete(it); db.session.commit()
    return redirect(url_for('vault'))


@app.route('/generate_password')
def generate_password():
    length = int(request.args.get('length', 16))
    upper = request.args.get('upper', '1') in ('1', 'true', 'True')
    lower = request.args.get('lower', '1') in ('1', 'true', 'True')
    digits = request.args.get('digits', '1') in ('1', 'true', 'True')
    symbols = request.args.get('symbols', '0') in ('1', 'true', 'True')
    pwd = builder_generate_password(length=length, upper=upper, lower=lower, digits=digits, symbols=symbols)
    return jsonify({'password': pwd})


@app.route('/notifications/clear', methods=['POST'])
def clear_notifications():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for('login'))
    try:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        flash('Notifications cleared.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to clear notifications', 'error')
    return redirect(url_for('home'))


@app.route('/vault/copy/<int:item_id>/<path:field>')
def vault_copy(item_id, field):
    user_id = current_user_id()
    if not user_id:
        return jsonify({'value': None}), 403
    it = VaultItem.query.get_or_404(item_id)
    if it.user_id != user_id:
        return jsonify({'value': None}), 403
    data = decrypt_json(it.encrypted_data) or {}
    # field may be url-encoded; match case-insensitively
    val = None
    for k, v in data.items():
        if str(k).lower() == str(field).lower():
            val = v
            break

    # action: 'copy' or 'unmask' (default to copy)
    action = request.args.get('action', 'copy')
    try:
        us = UserSession()
    except Exception:
        us = None

    if action == 'unmask':
        # require a short-lived server-issued token for security
        token = request.args.get('token') or request.headers.get('X-Unmask-Token')
        if not token:
            return jsonify({'value': None, 'error': 'token_required'}), 400
        ut = UnmaskToken.validate(token, user_id=user_id, item_id=item_id, field=field)
        if not ut:
            return jsonify({'value': None, 'error': 'invalid_or_expired_token'}), 403
        # mark token used
        ut.used = True
        db.session.commit()
        # optional: record server-side unmask quota in singleton
        if us:
            us.record_unmask()

    return jsonify({'value': val})


@app.route('/vault/request_unmask_token/<int:item_id>/<path:field>', methods=['POST'])
def request_unmask_token(item_id, field):
    """Issue a short-lived unmask token. The UI should call this endpoint
    (POST) to receive a token, then call `/vault/copy?...&action=unmask&token=...`.
    """
    user_id = current_user_id()
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 403
    it = VaultItem.query.get_or_404(item_id)
    if it.user_id != user_id:
        return jsonify({'error': 'unauthorized'}), 403
    # issue token (short TTL)
    ut = UnmaskToken.issue(user_id=user_id, item_id=item_id, field=field, ttl_seconds=30)
    return jsonify({'token': ut.token, 'expires_at': ut.expires_at.isoformat()})


def current_user_id():
    """Resolve current user id using the server-side `UserSession` first,
    falling back to the Flask `session` cookie. This makes the singleton the
    authoritative source when initialized.
    """
    try:
        us = UserSession()
        uid = us.get_user_id()
        if uid:
            return uid
    except Exception:
        pass
    return session.get('user_id')


with app.app_context():
    os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)
    db.create_all()
    load_key()

if __name__ == '__main__':
    app.run(debug=True)

