#!/usr/bin/env python3
"""
Campus Market - 校园二手交易平台
启动脚本：自动初始化数据库、加载演示数据并启动服务器
"""
import os, sys, subprocess, webbrowser, time, threading

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

def check_deps():
    missing = []
    try: import flask
    except: missing.append('flask')
    try: import jwt
    except: missing.append('PyJWT')
    try: import PIL
    except: missing.append('Pillow')
    if missing:
        print(f"[!] 缺少依赖: {', '.join(missing)}")
        print(f"    运行: pip3 install {' '.join(missing)} --break-system-packages")
        sys.exit(1)

def open_browser():
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("=" * 55)
    print("  🏫 Campus Market · 校园闲置交易平台")
    print("=" * 55)
    check_deps()
    from database import init_db
    print("  📦 初始化数据库...")
    init_db()
    print("  ✅ 数据库就绪")

    # 云平台（Railway/Render）通过环境变量 PORT 指定端口，本地默认 5000
    port = int(os.environ.get('PORT', 5000))
    is_local = not os.environ.get('PORT')

    print(f"  🚀 启动服务器: http://localhost:{port}")
    print(f"  📖 API文档: http://localhost:{port}/api")
    print()
    print("  演示账号: limingjun / password123")
    print("=" * 55)

    # 仅本地运行时自动打开浏览器
    if is_local:
        threading.Thread(target=open_browser, daemon=True).start()

    from app import app
    app.run(host='0.0.0.0', port=port, debug=False)
