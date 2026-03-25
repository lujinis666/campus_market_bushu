from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import token_required

messages_bp = Blueprint('messages', __name__)

def _pair_blocked(db, uid_a, uid_b):
    return db.execute(
        '''SELECT 1 FROM user_blocks WHERE
           (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)''',
        (uid_a, uid_b, uid_b, uid_a)
    ).fetchone() is not None

def conv_to_dict(row, db, current_user_id):
    d = dict(row)
    other_id = d['user2_id'] if d['user1_id'] == current_user_id else d['user1_id']
    other = db.execute('SELECT id,nickname,avatar_url,school,department FROM users WHERE id=?', (other_id,)).fetchone()
    if other:
        d['other_user'] = dict(other)
    d['unread'] = d['unread_1'] if d['user1_id'] == current_user_id else d['unread_2']
    if d.get('product_id'):
        product = db.execute('SELECT id,title,price,cover_emoji,cover_color,status FROM products WHERE id=?',
                             (d['product_id'],)).fetchone()
        d['product'] = dict(product) if product else None
    return d

@messages_bp.route('/conversations', methods=['GET'])
@token_required
def list_conversations(current_user_id):
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT * FROM conversations
               WHERE user1_id=? OR user2_id=?
               ORDER BY last_time DESC''',
            (current_user_id, current_user_id)
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            oid = d['user2_id'] if d['user1_id'] == current_user_id else d['user1_id']
            if _pair_blocked(db, current_user_id, oid):
                continue
            out.append(conv_to_dict(row, db, current_user_id))
        return jsonify(out)
    finally:
        db.close()

@messages_bp.route('/conversations/<int:cid>', methods=['GET'])
@token_required
def get_conversation(current_user_id, cid):
    db = get_db()
    try:
        conv = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if not conv or (conv['user1_id'] != current_user_id and conv['user2_id'] != current_user_id):
            return jsonify({'error': '会话不存在或无权限'}), 404
        other_id = conv['user2_id'] if conv['user1_id'] == current_user_id else conv['user1_id']
        if _pair_blocked(db, current_user_id, other_id):
            return jsonify({'error': '无法查看该会话'}), 403

        # Mark as read
        if conv['user1_id'] == current_user_id:
            db.execute('UPDATE conversations SET unread_1=0 WHERE id=?', (cid,))
        else:
            db.execute('UPDATE conversations SET unread_2=0 WHERE id=?', (cid,))
        db.execute('UPDATE messages SET is_read=1 WHERE conversation_id=? AND sender_id!=?',
                   (cid, current_user_id))
        db.commit()

        page = int(request.args.get('page', 1))
        per_page = 50
        offset = (page - 1) * per_page

        msgs = db.execute(
            '''SELECT m.*, u.nickname, u.avatar_url FROM messages m
               JOIN users u ON m.sender_id=u.id
               WHERE m.conversation_id=?
               ORDER BY m.created_at DESC LIMIT ? OFFSET ?''',
            (cid, per_page, offset)
        ).fetchall()
        msgs = list(reversed([dict(m) for m in msgs]))

        return jsonify({
            'conversation': conv_to_dict(conv, db, current_user_id),
            'messages': msgs
        })
    finally:
        db.close()

@messages_bp.route('/conversations/start', methods=['POST'])
@token_required
def start_conversation(current_user_id):
    data = request.get_json()
    other_id = data.get('user_id')
    product_id = data.get('product_id')

    if not other_id:
        return jsonify({'error': '缺少对方用户ID'}), 400
    if other_id == current_user_id:
        return jsonify({'error': '不能和自己发消息'}), 400

    db = get_db()
    try:
        if _pair_blocked(db, current_user_id, other_id):
            return jsonify({'error': '无法与该用户发消息'}), 403
        u1, u2 = min(current_user_id, other_id), max(current_user_id, other_id)
        existing = db.execute(
            'SELECT * FROM conversations WHERE user1_id=? AND user2_id=? AND (product_id=? OR product_id IS NULL)',
            (u1, u2, product_id)
        ).fetchone()

        if existing:
            return jsonify({'conversation_id': existing['id']})

        cursor = db.execute(
            'INSERT INTO conversations (user1_id,user2_id,product_id) VALUES (?,?,?)',
            (u1, u2, product_id)
        )
        db.commit()
        return jsonify({'conversation_id': cursor.lastrowid}), 201
    finally:
        db.close()

@messages_bp.route('/conversations/<int:cid>/messages', methods=['POST'])
@token_required
def send_message(current_user_id, cid):
    db = get_db()
    try:
        conv = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if not conv or (conv['user1_id'] != current_user_id and conv['user2_id'] != current_user_id):
            return jsonify({'error': '无权限'}), 403
        other_id = conv['user2_id'] if conv['user1_id'] == current_user_id else conv['user1_id']
        if _pair_blocked(db, current_user_id, other_id):
            return jsonify({'error': '无法向对方发送消息'}), 403

        data = request.get_json()
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': '消息不能为空'}), 400
        if len(content) > 1000:
            return jsonify({'error': '消息过长'}), 400

        cursor = db.execute(
            'INSERT INTO messages (conversation_id,sender_id,content) VALUES (?,?,?)',
            (cid, current_user_id, content)
        )

        # Update conversation
        if conv['user1_id'] == other_id:
            db.execute("UPDATE conversations SET last_message=?, last_time=datetime('now','localtime'), unread_1=unread_1+1 WHERE id=?",
                       (content[:100], cid))
        else:
            db.execute("UPDATE conversations SET last_message=?, last_time=datetime('now','localtime'), unread_2=unread_2+1 WHERE id=?",
                       (content[:100], cid))

        # Notification
        db.execute('''INSERT INTO notifications (user_id,type,title,content,link) VALUES (?,?,?,?,?)''',
                   (other_id, 'message', '收到新消息', content[:50], f'/messages/{cid}'))
        db.commit()

        msg_id = cursor.lastrowid
        msg = db.execute(
            'SELECT m.*, u.nickname, u.avatar_url FROM messages m JOIN users u ON m.sender_id=u.id WHERE m.id=?',
            (msg_id,)
        ).fetchone()
        return jsonify(dict(msg)), 201
    finally:
        db.close()

@messages_bp.route('/unread-count', methods=['GET'])
@token_required
def unread_count(current_user_id):
    db = get_db()
    try:
        count = db.execute(
            '''SELECT COALESCE(SUM(CASE WHEN user1_id=? THEN unread_1 ELSE unread_2 END),0) as cnt
               FROM conversations WHERE user1_id=? OR user2_id=?''',
            (current_user_id, current_user_id, current_user_id)
        ).fetchone()['cnt']
        return jsonify({'count': count})
    finally:
        db.close()

@messages_bp.route('/conversations/<int:cid>', methods=['DELETE'])
@token_required
def delete_conversation(current_user_id, cid):
    db = get_db()
    try:
        conv = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if not conv or (conv['user1_id'] != current_user_id and conv['user2_id'] != current_user_id):
            return jsonify({'error': '会话不存在或无权限'}), 404
        db.execute('DELETE FROM messages WHERE conversation_id=?', (cid,))
        db.execute('DELETE FROM conversations WHERE id=?', (cid,))
        db.commit()
        return jsonify({'message': '已删除'})
    finally:
        db.close()
