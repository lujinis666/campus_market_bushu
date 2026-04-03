import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, send_from_directory, jsonify, request
from database import init_db
from routes.auth import auth_bp
from routes.products import products_bp
from routes.messages import messages_bp
from routes.community import community_bp
from routes.users import users_bp
from routes.admin import admin_bp

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 启动时自动初始化数据库（gunicorn 直接启动 app 时也能正常建表和写入演示数据）
init_db()

# ===== CORS =====
@app.after_request
def add_cors(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS,PATCH'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return app.make_default_options_response()

# ===== Blueprints =====
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(products_bp, url_prefix='/api/products')
app.register_blueprint(messages_bp, url_prefix='/api/messages')
app.register_blueprint(community_bp, url_prefix='/api/community')
app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# ===== Static file serving =====
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/upload', methods=['POST'])
def general_upload():
    """General purpose image upload endpoint"""
    from routes.auth import token_required
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': '未认证'}), 401
    import jwt
    SECRET_KEY = 'campus_market_jwt_secret_2024_pku'
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return jsonify({'error': '认证失败'}), 401

    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
    file = request.files['file']
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not file or not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed):
        return jsonify({'error': '不支持的格式'}), 400

    import uuid
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        from PIL import Image
        img = Image.open(file.stream)
        img = img.convert('RGB')
        if max(img.size) > 1200:
            img.thumbnail((1200, 1200), Image.LANCZOS)
        img.save(filepath, quality=85, optimize=True)
    except Exception:
        file.seek(0)
        file.save(filepath)

    return jsonify({'filename': filename, 'url': f'/uploads/{filename}'}), 201

@app.route('/api/search/suggestions', methods=['GET'])
def search_suggestions():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])
    from database import get_db
    db = get_db()
    try:
        rows = db.execute(
            "SELECT DISTINCT title FROM products WHERE title LIKE ? AND status='active' LIMIT 8",
            (f'%{q}%',)
        ).fetchall()
        return jsonify([r['title'] for r in rows])
    finally:
        db.close()

@app.route('/api/stats', methods=['GET'])
def platform_stats():
    from database import get_db
    db = get_db()
    try:
        users = db.execute('SELECT COUNT(*) as cnt FROM users').fetchone()['cnt']
        products = db.execute("SELECT COUNT(*) as cnt FROM products WHERE status='active'").fetchone()['cnt']
        today_products = db.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE date(created_at)=date('now','localtime')"
        ).fetchone()['cnt']
        messages = db.execute('SELECT COUNT(*) as cnt FROM messages').fetchone()['cnt']
        return jsonify({
            'users': users,
            'active_products': products,
            'today_products': today_products,
            'messages': messages
        })
    finally:
        db.close()

@app.route('/api/announcements', methods=['GET'])
def list_public_announcements():
    """首页等平台公告（仅展示启用项）。"""
    from database import get_db
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT id, title, content, created_at, sort_order
               FROM announcements WHERE is_active=1
               ORDER BY sort_order ASC, id DESC'''
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()

@app.route('/api/categories', methods=['GET'])
def get_categories():
    from database import get_db
    db = get_db()
    try:
        rows = db.execute(
            "SELECT category, COUNT(*) as count FROM products WHERE status='active' GROUP BY category ORDER BY count DESC"
        ).fetchall()
        cats = [{'name': r['category'], 'count': r['count']} for r in rows]
        return jsonify(cats)
    finally:
        db.close()

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件过大，最大20MB'}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("  Campus Market Backend")
    print("  Initializing database...")
    init_db()
    print("  Server starting at http://localhost:5000")
    print("  API base: http://localhost:5000/api")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)

_static_dir = os.path.join(os.path.dirname(__file__), 'static')

@app.route('/admin')
@app.route('/admin/')
def serve_admin():
    return send_from_directory(_static_dir, 'admin.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    static_dir = _static_dir
    if path and os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, 'index.html')
