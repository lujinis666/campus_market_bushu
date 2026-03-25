from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import token_required, optional_auth
import os, uuid
from werkzeug.utils import secure_filename

users_bp = Blueprint('users', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

@users_bp.route('/<int:uid>', methods=['GET'])
@optional_auth
def get_user(current_user_id, uid):
    db = get_db()
    try:
        user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        d = dict(user)
        d.pop('password_hash', None)
        if uid != current_user_id:
            d.pop('email', None)
            d.pop('phone', None)
            d.pop('wechat', None)
        # Stats
        d['active_products'] = db.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE user_id=? AND status='active'", (uid,)
        ).fetchone()['cnt']
        reviews = db.execute(
            'SELECT score FROM reviews WHERE reviewee_id=?', (uid,)
        ).fetchall()
        if reviews:
            d['rating'] = round(sum(r['score'] for r in reviews) / len(reviews), 1)
            d['rating_count'] = len(reviews)
        return jsonify(d)
    finally:
        db.close()

@users_bp.route('/<int:uid>/products', methods=['GET'])
@optional_auth
def get_user_products(current_user_id, uid):
    db = get_db()
    try:
        status = request.args.get('status', 'active')
        rows = db.execute(
            'SELECT * FROM products WHERE user_id=? AND status=? ORDER BY created_at DESC',
            (uid, status)
        ).fetchall()
        from routes.products import product_to_dict
        return jsonify([product_to_dict(r, db, current_user_id) for r in rows])
    finally:
        db.close()

@users_bp.route('/<int:uid>/favorites', methods=['GET'])
@token_required
def get_favorites(current_user_id, uid):
    if uid != current_user_id:
        return jsonify({'error': '无权限查看他人收藏'}), 403
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT p.* FROM products p JOIN favorites f ON p.id=f.product_id
               WHERE f.user_id=? AND p.status='active'
               ORDER BY f.created_at DESC''',
            (uid,)
        ).fetchall()
        from routes.products import product_to_dict
        return jsonify([product_to_dict(r, db, current_user_id) for r in rows])
    finally:
        db.close()

@users_bp.route('/<int:uid>/avatar', methods=['POST'])
@token_required
def upload_avatar(current_user_id, uid):
    if uid != current_user_id:
        return jsonify({'error': '无权限'}), 403
    if 'avatar' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
    file = request.files['avatar']
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not file or not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed):
        return jsonify({'error': '不支持的格式'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        from PIL import Image
        img = Image.open(file.stream)
        img = img.convert('RGB')
        img.thumbnail((300, 300), Image.LANCZOS)
        img.save(filepath, quality=85)
    except Exception:
        file.seek(0)
        file.save(filepath)

    # Delete old avatar
    db = get_db()
    try:
        old = db.execute('SELECT avatar_url FROM users WHERE id=?', (uid,)).fetchone()
        if old and old['avatar_url'] and not old['avatar_url'].startswith('http'):
            old_path = os.path.join(UPLOAD_FOLDER, old['avatar_url'])
            if os.path.exists(old_path):
                os.remove(old_path)
        db.execute('UPDATE users SET avatar_url=? WHERE id=?', (filename, uid))
        db.commit()
        return jsonify({'avatar_url': filename, 'url': f'/uploads/{filename}'})
    finally:
        db.close()

@users_bp.route('/<int:uid>/reviews', methods=['GET'])
def get_reviews(uid):
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT r.*, u.nickname, u.avatar_url FROM reviews r
               JOIN users u ON r.reviewer_id=u.id
               WHERE r.reviewee_id=? ORDER BY r.created_at DESC''', (uid,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()

@users_bp.route('/<int:uid>/reviews', methods=['POST'])
@token_required
def add_review(current_user_id, uid):
    if uid == current_user_id:
        return jsonify({'error': '不能评价自己'}), 400
    data = request.get_json()
    score = int(data.get('score', 5))
    if score < 1 or score > 5:
        return jsonify({'error': '评分需在1-5之间'}), 400
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'error': '需要关联商品'}), 400

    db = get_db()
    try:
        if db.execute('SELECT 1 FROM reviews WHERE reviewer_id=? AND product_id=?',
                      (current_user_id, product_id)).fetchone():
            return jsonify({'error': '已评价过该商品'}), 409
        db.execute(
            'INSERT INTO reviews (reviewer_id,reviewee_id,product_id,score,content) VALUES (?,?,?,?,?)',
            (current_user_id, uid, product_id, score, data.get('content', ''))
        )
        # Update user rating
        reviews = db.execute('SELECT score FROM reviews WHERE reviewee_id=?', (uid,)).fetchall()
        avg = round(sum(r['score'] for r in reviews) / len(reviews), 1)
        db.execute('UPDATE users SET rating=?, rating_count=? WHERE id=?', (avg, len(reviews), uid))
        db.commit()
        return jsonify({'message': '评价成功', 'new_rating': avg}), 201
    finally:
        db.close()

# Notifications
@users_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    db = get_db()
    try:
        page = int(request.args.get('page', 1))
        rows = db.execute(
            'SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20 OFFSET ?',
            (current_user_id, (page-1)*20)
        ).fetchall()
        unread = db.execute('SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND is_read=0',
                            (current_user_id,)).fetchone()['cnt']
        return jsonify({'items': [dict(r) for r in rows], 'unread': unread})
    finally:
        db.close()

@users_bp.route('/notifications/read-all', methods=['POST'])
@token_required
def read_all_notifications(current_user_id):
    db = get_db()
    try:
        db.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (current_user_id,))
        db.commit()
        return jsonify({'message': '已全部标记已读'})
    finally:
        db.close()
