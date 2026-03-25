from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from database import get_db
from functools import wraps

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = 'campus_market_jwt_secret_2024_pku'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': '未提供认证token'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'token已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'token无效'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

def optional_auth(f):
    """Like token_required but allows unauthenticated requests (user_id=None)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user_id = None
        if token:
            try:
                data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                current_user_id = data['user_id']
            except Exception:
                pass
        return f(current_user_id, *args, **kwargs)
    return decorated

def make_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def user_to_dict(row, public=False):
    d = dict(row)
    if public:
        d.pop('password_hash', None)
        d.pop('email', None)
        d.pop('phone', None)
        d.pop('wechat', None)
    else:
        d.pop('password_hash', None)
    return d

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['username', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'缺少字段: {field}'}), 400

    username = data['username'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    if len(username) < 2 or len(username) > 20:
        return jsonify({'error': '用户名长度需在2-20字符之间'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400

    db = get_db()
    try:
        if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
            return jsonify({'error': '用户名已被注册'}), 409
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            return jsonify({'error': '邮箱已被注册'}), 409

        nickname = data.get('nickname', username)
        school = data.get('school', '北京大学')
        department = data.get('department', '')
        grade = data.get('grade', '')

        cursor = db.execute(
            '''INSERT INTO users (username,email,password_hash,nickname,school,department,grade)
               VALUES (?,?,?,?,?,?,?)''',
            (username, email, generate_password_hash(password), nickname, school, department, grade)
        )
        db.commit()
        user_id = cursor.lastrowid

        # Welcome notification
        db.execute(
            '''INSERT INTO notifications (user_id,type,title,content)
               VALUES (?,?,?,?)''',
            (user_id, 'system', '欢迎加入 Campus Market！', '你好！欢迎使用校园二手交易平台。完善个人资料可以提升买家信任度哦～')
        )
        db.commit()

        user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        token = make_token(user_id)
        return jsonify({'token': token, 'user': user_to_dict(user)}), 201
    finally:
        db.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier', '').strip()  # username or email
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': '请输入账号和密码'}), 400

    db = get_db()
    try:
        user = db.execute(
            'SELECT * FROM users WHERE username=? OR email=?',
            (identifier, identifier.lower())
        ).fetchone()

        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': '账号或密码错误'}), 401

        if not user['is_active']:
            return jsonify({'error': '账号已被禁用，请联系客服'}), 403

        token = make_token(user['id'])
        return jsonify({'token': token, 'user': user_to_dict(user)})
    finally:
        db.close()

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user_id):
    db = get_db()
    try:
        user = db.execute('SELECT * FROM users WHERE id=?', (current_user_id,)).fetchone()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        unread_msgs = db.execute(
            '''SELECT COUNT(*) as cnt FROM messages m
               JOIN conversations c ON m.conversation_id=c.id
               WHERE m.is_read=0 AND m.sender_id!=? AND (c.user1_id=? OR c.user2_id=?)''',
            (current_user_id, current_user_id, current_user_id)
        ).fetchone()['cnt']
        unread_notifs = db.execute(
            'SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND is_read=0',
            (current_user_id,)
        ).fetchone()['cnt']
        result = user_to_dict(user)
        result['unread_messages'] = unread_msgs
        result['unread_notifications'] = unread_notifs
        return jsonify(result)
    finally:
        db.close()

@auth_bp.route('/me', methods=['PUT'])
@token_required
def update_me(current_user_id):
    data = request.get_json()
    allowed = ['nickname', 'school', 'department', 'grade', 'bio', 'wechat', 'phone']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': '没有可更新的字段'}), 400

    db = get_db()
    try:
        set_clause = ', '.join(f'{k}=?' for k in updates)
        db.execute(f'UPDATE users SET {set_clause} WHERE id=?', list(updates.values()) + [current_user_id])
        db.commit()
        user = db.execute('SELECT * FROM users WHERE id=?', (current_user_id,)).fetchone()
        return jsonify(user_to_dict(user))
    finally:
        db.close()

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user_id):
    data = request.get_json()
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if len(new_pw) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    db = get_db()
    try:
        user = db.execute('SELECT * FROM users WHERE id=?', (current_user_id,)).fetchone()
        if not check_password_hash(user['password_hash'], old_pw):
            return jsonify({'error': '原密码错误'}), 400
        db.execute('UPDATE users SET password_hash=? WHERE id=?',
                   (generate_password_hash(new_pw), current_user_id))
        db.commit()
        return jsonify({'message': '密码修改成功'})
    finally:
        db.close()
