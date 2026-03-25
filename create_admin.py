#!/usr/bin/env python3
"""
创建管理员账号的脚本
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

def create_admin_user():
    db_path = os.path.join(os.path.dirname(__file__), 'campus_market.db')

    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 管理员账号信息
    admin_username = 'admin'
    admin_email = 'admin@campusmarket.com'
    admin_password = 'Admin@123456'  # 建议首次登录后修改

    try:
        # 检查是否已存在管理员账号
        existing_admin = c.execute(
            'SELECT id FROM users WHERE username=? OR email=?',
            (admin_username, admin_email)
        ).fetchone()

        if existing_admin:
            print("管理员账号已存在！")
            print(f"用户ID: {existing_admin['id']}")
            return

        # 创建管理员账号
        # 设置 verified=1 表示已验证，is_active=1 表示活跃
        c.execute('''
            INSERT INTO users (
                username, email, password_hash, nickname, school,
                department, verified, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            admin_username,
            admin_email,
            generate_password_hash(admin_password),
            '管理员',
            '北京大学',
            '校园市场管理团队',
            1,  # verified
            1   # is_active
        ))

        # 获取新创建的用户ID
        admin_id = c.lastrowid

        # 添加系统通知
        c.execute('''
            INSERT INTO notifications (user_id, type, title, content)
            VALUES (?, ?, ?, ?)
        ''', (
            admin_id,
            'system',
            '欢迎加入校园市场管理团队！',
            '您已被任命为网站管理员，请及时修改初始密码并管理网站内容。'
        ))

        conn.commit()
        print("管理员账号创建成功！")
        print(f"用户名: {admin_username}")
        print(f"邮箱: {admin_email}")
        print(f"密码: {admin_password}")
        print(f"用户ID: {admin_id}")
        print("\n⚠️  请首次登录后立即修改密码！")

    except Exception as e:
        print(f"创建管理员账号时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("开始创建管理员账号...")
    create_admin_user()
    print("\n完成！")