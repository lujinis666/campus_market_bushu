from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import token_required, optional_auth
import os, uuid
from werkzeug.utils import secure_filename

products_bp = Blueprint('products', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def product_to_dict(row, db, current_user_id=None):
    d = dict(row)
    # Get seller info
    seller = db.execute('SELECT id,nickname,avatar_url,school,department,grade,rating,rating_count,sell_count,verified FROM users WHERE id=?',
                        (d['user_id'],)).fetchone()
    if seller:
        d['seller'] = dict(seller)
    # Get images
    imgs = db.execute('SELECT filename FROM product_images WHERE product_id=? ORDER BY sort_order', (d['id'],)).fetchall()
    d['images'] = [i['filename'] for i in imgs]
    # Favorite status
    if current_user_id:
        fav = db.execute('SELECT 1 FROM favorites WHERE user_id=? AND product_id=?',
                         (current_user_id, d['id'])).fetchone()
        d['is_favorited'] = bool(fav)
    else:
        d['is_favorited'] = False
    # Comment count
    d['comment_count'] = db.execute('SELECT COUNT(*) as cnt FROM product_comments WHERE product_id=?',
                                     (d['id'],)).fetchone()['cnt']
    # Tags as list
    d['tags_list'] = [t.strip() for t in d.get('tags', '').split(',') if t.strip()]
    # Trade types as list
    d['trade_types_list'] = [t.strip() for t in d.get('trade_types', '').split(',') if t.strip()]
    return d

@products_bp.route('', methods=['GET'])
@optional_auth
def list_products(current_user_id):
    db = get_db()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        category = request.args.get('category', '')
        condition = request.args.get('condition', '')
        min_price = request.args.get('min_price', '')
        max_price = request.args.get('max_price', '')
        sort = request.args.get('sort', 'latest')
        keyword = request.args.get('q', '')
        tab = request.args.get('tab', '')  # wanted, all etc
        user_id = request.args.get('user_id', '')
        status = request.args.get('status', 'active')

        where = ['p.status=?']
        params = [status]

        if tab == 'wanted':
            where.append("p.status='wanted'")
            params = []
        if category:
            where.append('p.category=?'); params.append(category)
        if condition:
            where.append('p.condition=?'); params.append(condition)
        if min_price:
            where.append('p.price>=?'); params.append(float(min_price))
        if max_price:
            where.append('p.price<=?'); params.append(float(max_price))
        if keyword:
            where.append("(p.title LIKE ? OR p.description LIKE ? OR p.tags LIKE ?)")
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])
        if user_id:
            where.append('p.user_id=?'); params.append(int(user_id))

        order = {
            'latest': 'p.created_at DESC',
            'price_asc': 'p.price ASC',
            'price_desc': 'p.price DESC',
            'popular': 'p.like_count DESC',
            'views': 'p.views DESC',
        }.get(sort, 'p.created_at DESC')

        where_str = ' AND '.join(where)
        offset = (page - 1) * per_page

        total = db.execute(f'SELECT COUNT(*) as cnt FROM products p WHERE {where_str}', params).fetchone()['cnt']
        rows = db.execute(f'SELECT p.* FROM products p WHERE {where_str} ORDER BY {order} LIMIT ? OFFSET ?',
                          params + [per_page, offset]).fetchall()

        items = [product_to_dict(row, db, current_user_id) for row in rows]
        return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page, 'pages': (total + per_page - 1) // per_page})
    finally:
        db.close()

@products_bp.route('/<int:pid>', methods=['GET'])
@optional_auth
def get_product(current_user_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '商品不存在'}), 404
        # Increment views
        db.execute('UPDATE products SET views=views+1 WHERE id=?', (pid,))
        db.commit()
        return jsonify(product_to_dict(row, db, current_user_id))
    finally:
        db.close()

@products_bp.route('', methods=['POST'])
@token_required
def create_product(current_user_id):
    data = request.get_json()
    required = ['title', 'price', 'category']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'缺少字段: {f}'}), 400

    db = get_db()
    try:
        cursor = db.execute(
            '''INSERT INTO products (user_id,title,description,category,condition,price,original_price,
               negotiable,trade_types,location,tags,cover_emoji,cover_color)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (current_user_id, data['title'], data.get('description',''),
             data['category'], data.get('condition','八成新'),
             float(data['price']), float(data.get('original_price', 0)),
             1 if data.get('negotiable', True) else 0,
             data.get('trade_types','校内自提'),
             data.get('location',''), data.get('tags',''),
             data.get('cover_emoji','📦'), data.get('cover_color','linear-gradient(135deg,#F5F5F5,#E0E0E0)'))
        )
        db.commit()
        pid = cursor.lastrowid

        # Add notification to followers (simplified: notify self)
        db.execute(
            '''INSERT INTO notifications (user_id,type,title,content,link)
               VALUES (?,?,?,?,?)''',
            (current_user_id, 'publish', '商品发布成功', f'您的商品「{data["title"]}」已成功发布！', f'/products/{pid}')
        )
        db.commit()

        product = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        return jsonify(product_to_dict(product, db, current_user_id)), 201
    finally:
        db.close()

@products_bp.route('/<int:pid>', methods=['PUT'])
@token_required
def update_product(current_user_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '商品不存在'}), 404
        if row['user_id'] != current_user_id:
            return jsonify({'error': '无权限修改'}), 403

        data = request.get_json()
        allowed = ['title','description','category','condition','price','original_price',
                   'negotiable','trade_types','location','tags','status','cover_emoji','cover_color']
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return jsonify({'error': '没有可更新的字段'}), 400

        set_clause = ', '.join(f'{k}=?' for k in updates)
        db.execute(f"UPDATE products SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?",
                   list(updates.values()) + [pid])
        db.commit()
        product = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        return jsonify(product_to_dict(product, db, current_user_id))
    finally:
        db.close()

@products_bp.route('/<int:pid>', methods=['DELETE'])
@token_required
def delete_product(current_user_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '商品不存在'}), 404
        if row['user_id'] != current_user_id:
            return jsonify({'error': '无权限删除'}), 403
        db.execute("UPDATE products SET status='deleted' WHERE id=?", (pid,))
        db.commit()
        return jsonify({'message': '已删除'})
    finally:
        db.close()

@products_bp.route('/<int:pid>/images', methods=['POST'])
@token_required
def upload_image(current_user_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '商品不存在'}), 404
        if row['user_id'] != current_user_id:
            return jsonify({'error': '无权限'}), 403

        if 'image' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        file = request.files['image']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Resize if too large
        try:
            from PIL import Image
            img = Image.open(filepath)
            if max(img.size) > 1200:
                img.thumbnail((1200, 1200), Image.LANCZOS)
                img.save(filepath, quality=85, optimize=True)
        except Exception:
            pass

        count = db.execute('SELECT COUNT(*) as cnt FROM product_images WHERE product_id=?', (pid,)).fetchone()['cnt']
        db.execute('INSERT INTO product_images (product_id,filename,sort_order) VALUES (?,?,?)',
                   (pid, filename, count))
        db.commit()
        return jsonify({'filename': filename, 'url': f'/uploads/{filename}'}), 201
    finally:
        db.close()

@products_bp.route('/<int:pid>/favorite', methods=['POST'])
@token_required
def toggle_favorite(current_user_id, pid):
    db = get_db()
    try:
        existing = db.execute('SELECT id FROM favorites WHERE user_id=? AND product_id=?',
                              (current_user_id, pid)).fetchone()
        if existing:
            db.execute('DELETE FROM favorites WHERE user_id=? AND product_id=?', (current_user_id, pid))
            db.execute('UPDATE products SET like_count=MAX(0,like_count-1) WHERE id=?', (pid,))
            db.commit()
            return jsonify({'favorited': False, 'message': '已取消收藏'})
        else:
            db.execute('INSERT INTO favorites (user_id,product_id) VALUES (?,?)', (current_user_id, pid))
            db.execute('UPDATE products SET like_count=like_count+1 WHERE id=?', (pid,))
            db.commit()
            # Notify seller
            product = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
            if product and product['user_id'] != current_user_id:
                db.execute('''INSERT INTO notifications (user_id,type,title,content,link)
                              VALUES (?,?,?,?,?)''',
                           (product['user_id'], 'like', '有人收藏了你的商品',
                            f'你的商品「{product["title"]}」被收藏了', f'/products/{pid}'))
                db.commit()
            return jsonify({'favorited': True, 'message': '收藏成功'})
    finally:
        db.close()

@products_bp.route('/<int:pid>/comments', methods=['GET'])
@optional_auth
def get_comments(current_user_id, pid):
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT pc.*, u.nickname, u.avatar_url, u.school, u.department
               FROM product_comments pc
               JOIN users u ON pc.user_id=u.id
               WHERE pc.product_id=? AND pc.parent_id IS NULL
               ORDER BY pc.created_at ASC''', (pid,)
        ).fetchall()

        comments = []
        for row in rows:
            d = dict(row)
            if current_user_id:
                d['liked'] = bool(db.execute('SELECT 1 FROM comment_likes WHERE user_id=? AND comment_id=?',
                                              (current_user_id, d['id'])).fetchone())
            # Replies
            replies = db.execute(
                '''SELECT pc.*, u.nickname, u.avatar_url
                   FROM product_comments pc JOIN users u ON pc.user_id=u.id
                   WHERE pc.parent_id=? ORDER BY pc.created_at ASC''', (d['id'],)
            ).fetchall()
            d['replies'] = [dict(r) for r in replies]
            comments.append(d)
        return jsonify(comments)
    finally:
        db.close()

@products_bp.route('/<int:pid>/comments', methods=['POST'])
@token_required
def add_comment(current_user_id, pid):
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '评论内容不能为空'}), 400
    if len(content) > 500:
        return jsonify({'error': '评论过长'}), 400

    db = get_db()
    try:
        product = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not product:
            return jsonify({'error': '商品不存在'}), 404

        parent_id = data.get('parent_id')
        cursor = db.execute(
            'INSERT INTO product_comments (product_id,user_id,parent_id,content) VALUES (?,?,?,?)',
            (pid, current_user_id, parent_id, content)
        )
        db.commit()
        cmt_id = cursor.lastrowid

        # Notify seller
        if product['user_id'] != current_user_id:
            db.execute('''INSERT INTO notifications (user_id,type,title,content,link) VALUES (?,?,?,?,?)''',
                       (product['user_id'], 'comment', '有人评论了你的商品',
                        f'「{content[:30]}...」', f'/products/{pid}'))
            db.commit()

        cmt = db.execute(
            '''SELECT pc.*, u.nickname, u.avatar_url, u.school, u.department
               FROM product_comments pc JOIN users u ON pc.user_id=u.id WHERE pc.id=?''',
            (cmt_id,)
        ).fetchone()
        return jsonify(dict(cmt)), 201
    finally:
        db.close()

@products_bp.route('/comments/<int:cid>/like', methods=['POST'])
@token_required
def like_comment(current_user_id, cid):
    db = get_db()
    try:
        existing = db.execute('SELECT 1 FROM comment_likes WHERE user_id=? AND comment_id=?',
                              (current_user_id, cid)).fetchone()
        if existing:
            db.execute('DELETE FROM comment_likes WHERE user_id=? AND comment_id=?', (current_user_id, cid))
            db.execute('UPDATE product_comments SET like_count=MAX(0,like_count-1) WHERE id=?', (cid,))
        else:
            db.execute('INSERT INTO comment_likes VALUES (?,?)', (current_user_id, cid))
            db.execute('UPDATE product_comments SET like_count=like_count+1 WHERE id=?', (cid,))
        db.commit()
        new_count = db.execute('SELECT like_count FROM product_comments WHERE id=?', (cid,)).fetchone()['like_count']
        return jsonify({'liked': not bool(existing), 'like_count': new_count})
    finally:
        db.close()
