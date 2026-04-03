#!/usr/bin/env python3
"""
创建或提升管理员账号：设置 is_admin=1。
请先至少启动过一次应用（或运行 database.init_db）以完成数据库迁移。
"""

import sqlite3
from werkzeug.security import generate_password_hash
from database import DB_PATH, ensure_schema

def create_admin_user():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    c = conn.cursor()

    admin_username = 'admin'
    admin_email = 'admin@campusmarket.com'
    admin_password = 'Admin@123456'

    try:
        existing = c.execute(
            'SELECT id, is_admin FROM users WHERE username=? OR email=?',
            (admin_username, admin_email)
        ).fetchone()

        if existing:
            c.execute(
                'UPDATE users SET is_admin=1, is_active=1 WHERE id=?',
                (existing['id'],)
            )
            conn.commit()
            print('管理员账号已存在，已确保 is_admin=1。')
            print(f'用户ID: {existing["id"]}')
            print('若需重置密码，请删除该用户后重新运行本脚本，或直接在库中更新 password_hash。')
            return

        c.execute(
            '''
            INSERT INTO users (
                username, email, password_hash, nickname, school,
                department, verified, is_active, is_admin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                admin_username,
                admin_email,
                generate_password_hash(admin_password),
                '管理员',
                '北京大学',
                '校园市场管理团队',
                1,
                1,
                1,
            )
        )

        admin_id = c.lastrowid

        c.execute(
            '''
            INSERT INTO notifications (user_id, type, title, content)
            VALUES (?, ?, ?, ?)
            ''',
            (
                admin_id,
                'system',
                '欢迎加入校园市场管理团队！',
                '您已被任命为网站管理员，请访问 /admin 进入管理后台，并尽快修改初始密码。',
            )
        )

        conn.commit()
        print('管理员账号创建成功！')
        print(f'用户名: {admin_username}')
        print(f'邮箱: {admin_email}')
        print(f'密码: {admin_password}')
        print(f'用户ID: {admin_id}')
        print('管理后台: http://localhost:5000/admin')
        print('\n请首次登录后立即修改密码！')

    except Exception as e:
        print(f'创建管理员账号时出错: {e}')
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print('开始创建/同步管理员账号...')
    create_admin_user()
    print('\n完成！')
