from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import token_required, optional_auth

community_bp = Blueprint('community', __name__)

def post_to_dict(row, db, current_user_id=None):
    d = dict(row)
    user = db.execute('SELECT id,nickname,avatar_url,school,department,grade FROM users WHERE id=?',
                      (d['user_id'],)).fetchone()
    if user:
        d['author'] = dict(user)
    imgs = db.execute('SELECT filename FROM post_images WHERE post_id=? ORDER BY id', (d['id'],)).fetchall()
    d['images'] = [i['filename'] for i in imgs]
    if current_user_id:
        d['liked'] = bool(db.execute('SELECT 1 FROM post_likes WHERE user_id=? AND post_id=?',
                                      (current_user_id, d['id'])).fetchone())
    else:
        d['liked'] = False
    return d

@community_bp.route('/posts', methods=['GET'])
@optional_auth
def list_posts(current_user_id):
    db = get_db()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        post_type = request.args.get('type', '')
        keyword = request.args.get('q', '')

        where = ['1=1']
        params = []
        if post_type and post_type != 'all':
            where.append('post_type=?'); params.append(post_type)
        if keyword:
            where.append('(title LIKE ? OR content LIKE ?)')
            kw = f'%{keyword}%'; params.extend([kw, kw])

        where_str = ' AND '.join(where)
        offset = (page - 1) * per_page
        total = db.execute(f'SELECT COUNT(*) as cnt FROM posts WHERE {where_str}', params).fetchone()['cnt']
        rows = db.execute(f'SELECT * FROM posts WHERE {where_str} ORDER BY created_at DESC LIMIT ? OFFSET ?',
                          params + [per_page, offset]).fetchall()
        return jsonify({'items': [post_to_dict(r, db, current_user_id) for r in rows], 'total': total})
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>', methods=['GET'])
@optional_auth
def get_post(current_user_id, pid):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM posts WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'error': '帖子不存在'}), 404
        db.execute('UPDATE posts SET view_count=view_count+1 WHERE id=?', (pid,))
        db.commit()
        return jsonify(post_to_dict(row, db, current_user_id))
    finally:
        db.close()

@community_bp.route('/posts', methods=['POST'])
@token_required
def create_post(current_user_id):
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title or not content:
        return jsonify({'error': '标题和内容不能为空'}), 400

    db = get_db()
    try:
        cursor = db.execute(
            '''INSERT INTO posts (user_id,title,content,post_type,budget,urgency)
               VALUES (?,?,?,?,?,?)''',
            (current_user_id, title, content,
             data.get('post_type', 'tip'),
             float(data.get('budget', 0)),
             data.get('urgency', ''))
        )
        db.commit()
        pid = cursor.lastrowid
        post = db.execute('SELECT * FROM posts WHERE id=?', (pid,)).fetchone()
        return jsonify(post_to_dict(post, db, current_user_id)), 201
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>', methods=['DELETE'])
@token_required
def delete_post(current_user_id, pid):
    db = get_db()
    try:
        post = db.execute('SELECT * FROM posts WHERE id=?', (pid,)).fetchone()
        if not post:
            return jsonify({'error': '帖子不存在'}), 404
        if post['user_id'] != current_user_id:
            return jsonify({'error': '无权限'}), 403
        db.execute('DELETE FROM posts WHERE id=?', (pid,))
        db.commit()
        return jsonify({'message': '已删除'})
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>/like', methods=['POST'])
@token_required
def like_post(current_user_id, pid):
    db = get_db()
    try:
        existing = db.execute('SELECT 1 FROM post_likes WHERE user_id=? AND post_id=?',
                              (current_user_id, pid)).fetchone()
        if existing:
            db.execute('DELETE FROM post_likes WHERE user_id=? AND post_id=?', (current_user_id, pid))
            db.execute('UPDATE posts SET like_count=MAX(0,like_count-1) WHERE id=?', (pid,))
            db.commit()
            return jsonify({'liked': False})
        else:
            db.execute('INSERT INTO post_likes VALUES (?,?)', (current_user_id, pid))
            db.execute('UPDATE posts SET like_count=like_count+1 WHERE id=?', (pid,))
            db.commit()
            return jsonify({'liked': True})
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>/comments', methods=['GET'])
def get_post_comments(pid):
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT pc.*, u.nickname, u.avatar_url, u.school
               FROM post_comments pc JOIN users u ON pc.user_id=u.id
               WHERE pc.post_id=? AND pc.parent_id IS NULL
               ORDER BY pc.created_at ASC''', (pid,)
        ).fetchall()
        comments = []
        for row in rows:
            d = dict(row)
            replies = db.execute(
                '''SELECT pc.*, u.nickname, u.avatar_url
                   FROM post_comments pc JOIN users u ON pc.user_id=u.id
                   WHERE pc.parent_id=? ORDER BY pc.created_at ASC''', (d['id'],)
            ).fetchall()
            d['replies'] = [dict(r) for r in replies]
            comments.append(d)
        return jsonify(comments)
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>/comments', methods=['POST'])
@token_required
def add_post_comment(current_user_id, pid):
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '评论不能为空'}), 400

    db = get_db()
    try:
        post = db.execute('SELECT * FROM posts WHERE id=?', (pid,)).fetchone()
        if not post:
            return jsonify({'error': '帖子不存在'}), 404

        cursor = db.execute(
            'INSERT INTO post_comments (post_id,user_id,parent_id,content) VALUES (?,?,?,?)',
            (pid, current_user_id, data.get('parent_id'), content)
        )
        db.execute('UPDATE posts SET comment_count=comment_count+1 WHERE id=?', (pid,))
        db.commit()

        cmt = db.execute(
            'SELECT pc.*, u.nickname, u.avatar_url, u.school FROM post_comments pc JOIN users u ON pc.user_id=u.id WHERE pc.id=?',
            (cursor.lastrowid,)
        ).fetchone()
        return jsonify(dict(cmt)), 201
    finally:
        db.close()

@community_bp.route('/wanted', methods=['GET'])
def get_wanted():
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT p.*, u.nickname, u.avatar_url FROM posts p JOIN users u ON p.user_id=u.id
               WHERE p.post_type='wanted' ORDER BY p.created_at DESC LIMIT 8'''
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()

@community_bp.route('/posts/<int:pid>/images', methods=['POST'])
@token_required
def upload_post_image(current_user_id, pid):
    import os, uuid
    from flask import request as req
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    db = get_db()
    try:
        post = db.execute('SELECT * FROM posts WHERE id=?', (pid,)).fetchone()
        if not post:
            return jsonify({'error': '帖子不存在'}), 404
        if post['user_id'] != current_user_id:
            return jsonify({'error': '无权限'}), 403
        if 'image' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        file = request.files['image']
        allowed = {'png','jpg','jpeg','gif','webp'}
        if not file or not ('.' in file.filename and file.filename.rsplit('.',1)[1].lower() in allowed):
            return jsonify({'error': '不支持的格式'}), 400
        ext = file.filename.rsplit('.',1)[1].lower()
        filename = f"post_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        try:
            from PIL import Image
            img = Image.open(file.stream)
            img = img.convert('RGB')
            if max(img.size) > 1200:
                img.thumbnail((1200, 1200), Image.LANCZOS)
            img.save(filepath, quality=85, optimize=True)
        except Exception:
            file.seek(0); file.save(filepath)
        db.execute('INSERT INTO post_images (post_id, filename) VALUES (?,?)', (pid, filename))
        db.commit()
        return jsonify({'filename': filename, 'url': f'/uploads/{filename}'}), 201
    finally:
        db.close()

@community_bp.route('/hot-tags', methods=['GET'])
def hot_tags():
    return jsonify(['期末教材', '跳蚤市场', '考研资料', '数码好物', '宿舍必备', '毕业季', '电子产品', '二手避坑', '校园生活', '换购'])
