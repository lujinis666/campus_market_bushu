from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import admin_required
from routes.community import post_to_dict
from routes.products import product_to_dict

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats(_admin_id):
    db = get_db()
    try:
        return jsonify({
            'users': db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c'],
            'users_active': db.execute('SELECT COUNT(*) as c FROM users WHERE is_active=1').fetchone()['c'],
            'users_banned': db.execute('SELECT COUNT(*) as c FROM users WHERE is_active=0').fetchone()['c'],
            'posts': db.execute('SELECT COUNT(*) as c FROM posts').fetchone()['c'],
            'products_active': db.execute("SELECT COUNT(*) as c FROM products WHERE status='active'").fetchone()['c'],
            'products_all': db.execute('SELECT COUNT(*) as c FROM products').fetchone()['c'],
            'announcements': db.execute('SELECT COUNT(*) as c FROM announcements').fetchone()['c'],
        })
    finally:
        db.close()


@admin_bp.route('/users', methods=['GET'])
@admin_required
def admin_list_users(_admin_id):
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(50, max(1, int(request.args.get('per_page', 15))))
    q = request.args.get('q', '').strip()
    offset = (page - 1) * per_page
    db = get_db()
    try:
        where = ['1=1']
        params = []
        if q:
            where.append('(u.username LIKE ? OR u.email LIKE ? OR u.nickname LIKE ?)')
            kw = f'%{q}%'
            params.extend([kw, kw, kw])
        w = ' AND '.join(where)
        total = db.execute(f'SELECT COUNT(*) as c FROM users u WHERE {w}', params).fetchone()['c']
        rows = db.execute(
            f'''SELECT u.id, u.username, u.email, u.nickname, u.school, u.is_active, u.is_admin,
                       u.last_login, u.created_at, u.verified
                FROM users u WHERE {w} ORDER BY u.id DESC LIMIT ? OFFSET ?''',
            params + [per_page, offset]
        ).fetchall()
        items = [dict(r) for r in rows]
        return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})
    finally:
        db.close()


@admin_bp.route('/users/<int:uid>', methods=['PATCH'])
@admin_required
def admin_patch_user(admin_id, uid):
    if uid == admin_id:
        return jsonify({'error': '不能对自己执行该操作'}), 400
    data = request.get_json() or {}
    db = get_db()
    try:
        target = db.execute(
            'SELECT id,is_admin,is_active FROM users WHERE id=?', (uid,)
        ).fetchone()
        if not target:
            return jsonify({'error': '用户不存在'}), 404
        if target['is_admin']:
            return jsonify({'error': '不能封禁或其他管理员账号'}), 403
        if 'is_active' in data:
            v = 1 if data['is_active'] else 0
            db.execute('UPDATE users SET is_active=? WHERE id=?', (v, uid))
            db.commit()
        row = db.execute(
            '''SELECT id, username, email, nickname, school, is_active, is_admin, last_login, created_at, verified
               FROM users WHERE id=?''',
            (uid,)
        ).fetchone()
        return jsonify(dict(row))
    finally:
        db.close()


@admin_bp.route('/posts', methods=['GET'])
@admin_required
def admin_list_posts(_admin_id):
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(50, max(1, int(request.args.get('per_page', 15))))
    q = request.args.get('q', '').strip()
    offset = (page - 1) * per_page
    db = get_db()
    try:
        where = ['1=1']
        params = []
        if q:
            where.append('(p.title LIKE ? OR p.content LIKE ?)')
            kw = f'%{q}%'
            params.extend([kw, kw])
        w = ' AND '.join(where)
        total = db.execute(f'SELECT COUNT(*) as c FROM posts p WHERE {w}', params).fetchone()['c']
        rows = db.execute(
            f'''SELECT p.*, u.username as author_username, u.nickname as author_nickname
                FROM posts p JOIN users u ON p.user_id=u.id
                WHERE {w} ORDER BY p.id DESC LIMIT ? OFFSET ?''',
            params + [per_page, offset]
        ).fetchall()
        items = []
        for r in rows:
            pr = db.execute('SELECT * FROM posts WHERE id=?', (r['id'],)).fetchone()
            pd = post_to_dict(pr, db, None)
            pd['author_username'] = r['author_username']
            pd['author_nickname'] = r['author_nickname']
            items.append(pd)
        return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})
    finally:
        db.close()


@admin_bp.route('/posts/<int:pid>', methods=['DELETE'])
@admin_required
def admin_delete_post(_admin_id, pid):
    db = get_db()
    try:
        post = db.execute('SELECT id FROM posts WHERE id=?', (pid,)).fetchone()
        if not post:
            return jsonify({'error': '帖子不存在'}), 404
        db.execute('DELETE FROM post_likes WHERE post_id=?', (pid,))
        db.execute('DELETE FROM posts WHERE id=?', (pid,))
        db.commit()
        return jsonify({'message': '已删除帖子'})
    finally:
        db.close()


@admin_bp.route('/post-comments/<int:cid>', methods=['DELETE'])
@admin_required
def admin_delete_post_comment(_admin_id, cid):
    db = get_db()
    try:
        row = db.execute('SELECT id, post_id FROM post_comments WHERE id=?', (cid,)).fetchone()
        if not row:
            return jsonify({'error': '评论不存在'}), 404
        post_id = row['post_id']
        db.execute('DELETE FROM post_comments WHERE parent_id=?', (cid,))
        db.execute('DELETE FROM post_comments WHERE id=?', (cid,))
        cnt = db.execute('SELECT COUNT(*) as c FROM post_comments WHERE post_id=?', (post_id,)).fetchone()['c']
        db.execute('UPDATE posts SET comment_count=? WHERE id=?', (cnt, post_id))
        db.commit()
        return jsonify({'message': '已删除评论'})
    finally:
        db.close()


@admin_bp.route('/products', methods=['GET'])
@admin_required
def admin_list_products(_admin_id):
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(50, max(1, int(request.args.get('per_page', 15))))
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    offset = (page - 1) * per_page
    db = get_db()
    try:
        where = ['1=1']
        params = []
        if status:
            where.append('p.status=?')
            params.append(status)
        if q:
            where.append('(p.title LIKE ? OR p.description LIKE ?)')
            kw = f'%{q}%'
            params.extend([kw, kw])
        w = ' AND '.join(where)
        total = db.execute(f'SELECT COUNT(*) as c FROM products p WHERE {w}', params).fetchone()['c']
        rows = db.execute(
            f'''SELECT p.*, u.username as seller_username
                FROM products p JOIN users u ON p.user_id=u.id
                WHERE {w} ORDER BY p.id DESC LIMIT ? OFFSET ?''',
            params + [per_page, offset]
        ).fetchall()
        items = []
        for r in rows:
            pr = db.execute('SELECT * FROM products WHERE id=?', (r['id'],)).fetchone()
            pd = product_to_dict(pr, db, None)
            pd['seller_username'] = r['seller_username']
            items.append(pd)
        return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})
    finally:
        db.close()


@admin_bp.route('/products/<int:pid>', methods=['DELETE'])
@admin_required
def admin_delete_product(_admin_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT id FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '商品不存在'}), 404
        db.execute("UPDATE products SET status='deleted', updated_at=datetime('now','localtime') WHERE id=?", (pid,))
        db.commit()
        return jsonify({'message': '已下架删除该商品'})
    finally:
        db.close()


@admin_bp.route('/announcements', methods=['GET'])
@admin_required
def admin_list_announcements(_admin_id):
    db = get_db()
    try:
        rows = db.execute(
            'SELECT * FROM announcements ORDER BY sort_order ASC, id DESC'
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()


@admin_bp.route('/announcements', methods=['POST'])
@admin_required
def admin_create_announcement(_admin_id):
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return jsonify({'error': '标题和内容不能为空'}), 400
    is_active = 1 if data.get('is_active', True) else 0
    sort_order = int(data.get('sort_order', 0))
    db = get_db()
    try:
        cur = db.execute(
            '''INSERT INTO announcements (title, content, is_active, sort_order)
               VALUES (?,?,?,?)''',
            (title, content, is_active, sort_order)
        )
        db.commit()
        aid = cur.lastrowid
        row = db.execute('SELECT * FROM announcements WHERE id=?', (aid,)).fetchone()
        return jsonify(dict(row)), 201
    finally:
        db.close()


@admin_bp.route('/announcements/<int:aid>', methods=['PUT'])
@admin_required
def admin_update_announcement(_admin_id, aid):
    data = request.get_json() or {}
    db = get_db()
    try:
        row = db.execute('SELECT id FROM announcements WHERE id=?', (aid,)).fetchone()
        if not row:
            return jsonify({'error': '公告不存在'}), 404
        fields = []
        vals = []
        if 'title' in data:
            t = (data.get('title') or '').strip()
            if not t:
                return jsonify({'error': '标题不能为空'}), 400
            fields.append('title=?')
            vals.append(t)
        if 'content' in data:
            c = (data.get('content') or '').strip()
            if not c:
                return jsonify({'error': '内容不能为空'}), 400
            fields.append('content=?')
            vals.append(c)
        if 'is_active' in data:
            fields.append('is_active=?')
            vals.append(1 if data['is_active'] else 0)
        if 'sort_order' in data:
            fields.append('sort_order=?')
            vals.append(int(data['sort_order']))
        if not fields:
            return jsonify({'error': '没有可更新字段'}), 400
        fields.append("updated_at=datetime('now','localtime')")
        vals.append(aid)
        db.execute(f"UPDATE announcements SET {', '.join(fields)} WHERE id=?", vals)
        db.commit()
        out = db.execute('SELECT * FROM announcements WHERE id=?', (aid,)).fetchone()
        return jsonify(dict(out))
    finally:
        db.close()


@admin_bp.route('/announcements/<int:aid>', methods=['DELETE'])
@admin_required
def admin_delete_announcement(_admin_id, aid):
    db = get_db()
    try:
        r = db.execute('DELETE FROM announcements WHERE id=?', (aid,))
        db.commit()
        if r.rowcount == 0:
            return jsonify({'error': '公告不存在'}), 404
        return jsonify({'message': '已删除'})
    finally:
        db.close()
