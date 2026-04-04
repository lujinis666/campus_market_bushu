import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'campus_market.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def ensure_schema(conn):
    """Migrate existing SQLite DBs created before admin/announcements columns existed."""
    c = conn.cursor()
    cols = [row[1] for row in c.execute('PRAGMA table_info(users)').fetchall()]
    if 'is_admin' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    if 'last_login' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN last_login TEXT')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    conn.commit()

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT DEFAULT '',
        school TEXT DEFAULT '北京大学',
        department TEXT DEFAULT '',
        grade TEXT DEFAULT '',
        avatar_url TEXT DEFAULT '',
        bio TEXT DEFAULT '',
        wechat TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        rating REAL DEFAULT 5.0,
        rating_count INTEGER DEFAULT 0,
        sell_count INTEGER DEFAULT 0,
        buy_count INTEGER DEFAULT 0,
        trade_amount REAL DEFAULT 0.0,
        verified INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        is_admin INTEGER DEFAULT 0,
        last_login TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # Products
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT '',
        condition TEXT DEFAULT '八成新',
        price REAL NOT NULL,
        original_price REAL DEFAULT 0,
        negotiable INTEGER DEFAULT 1,
        trade_types TEXT DEFAULT '校内自提',
        location TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        views INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        cover_emoji TEXT DEFAULT '📦',
        cover_color TEXT DEFAULT 'linear-gradient(135deg,#F5F5F5,#E0E0E0)',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Product Images
    c.execute('''CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    )''')

    # Comments on products
    c.execute('''CREATE TABLE IF NOT EXISTS product_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        like_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Favorites
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, product_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    )''')

    # Comment likes
    c.execute('''CREATE TABLE IF NOT EXISTS comment_likes (
        user_id INTEGER NOT NULL,
        comment_id INTEGER NOT NULL,
        PRIMARY KEY(user_id, comment_id)
    )''')

    # Conversations
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        product_id INTEGER DEFAULT NULL,
        last_message TEXT DEFAULT '',
        last_time TEXT DEFAULT (datetime('now','localtime')),
        unread_1 INTEGER DEFAULT 0,
        unread_2 INTEGER DEFAULT 0,
        UNIQUE(user1_id, user2_id, product_id),
        FOREIGN KEY(user1_id) REFERENCES users(id),
        FOREIGN KEY(user2_id) REFERENCES users(id)
    )''')

    # Messages
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        msg_type TEXT DEFAULT 'text',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(conversation_id) REFERENCES conversations(id),
        FOREIGN KEY(sender_id) REFERENCES users(id)
    )''')

    # Community Posts
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        post_type TEXT DEFAULT 'tip',
        budget REAL DEFAULT 0,
        urgency TEXT DEFAULT '',
        like_count INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0,
        comment_count INTEGER DEFAULT 0,
        share_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Post Images
    c.execute('''CREATE TABLE IF NOT EXISTS post_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
    )''')

    # Post Comments
    c.execute('''CREATE TABLE IF NOT EXISTS post_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        like_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Post Likes
    c.execute('''CREATE TABLE IF NOT EXISTS post_likes (
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        PRIMARY KEY(user_id, post_id)
    )''')

    # Ratings/Reviews
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reviewer_id INTEGER NOT NULL,
        reviewee_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
        content TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(reviewer_id, product_id),
        FOREIGN KEY(reviewer_id) REFERENCES users(id),
        FOREIGN KEY(reviewee_id) REFERENCES users(id)
    )''')

    # Notifications
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        link TEXT DEFAULT '',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # User blocks (拉黑)
    c.execute('''CREATE TABLE IF NOT EXISTS user_blocks (
        blocker_id INTEGER NOT NULL,
        blocked_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY (blocker_id, blocked_id),
        FOREIGN KEY(blocker_id) REFERENCES users(id),
        FOREIGN KEY(blocked_id) REFERENCES users(id)
    )''')

    # Reports/Complaints (用户举报)
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER NOT NULL,
        report_type TEXT NOT NULL,
        target_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(reporter_id) REFERENCES users(id)
    )''')

    # Site announcements (admin-managed)
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    conn.commit()
    ensure_schema(conn)

    # Seed demo data
    _seed_demo(conn)
    conn.close()

def _seed_demo(conn):
    c = conn.cursor()
    # Check if already seeded
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    from werkzeug.security import generate_password_hash
    import json

    users = [
        ('wangxiaoyu', 'wang@pku.edu.cn', generate_password_hash('password123'), '李康',
         '湖北工业大学大学', '计算机学院', '2021级', '李', 4.9, 23, 1),
        ('limingjun', 'li@pku.edu.cn', generate_password_hash('password123'), '郭佳陈',
         '湖北工业大学', '信息科学技术学院', '2022级', '郭', 4.7, 12, 1),
        ('chenmei', 'chen@pku.edu.cn', generate_password_hash('password123'), '滕家珍',
         '湖北工业大学', '外国语学院', '2020级', '滕', 5.0, 8, 1),
        ('zhanghao', 'zhang@pku.edu.cn', generate_password_hash('password123'), '熊天宇',
         '湖北工业大学大学', '经济学院', '2022级', '熊', 4.8, 31, 1),
        ('liuyang', 'liu@pku.edu.cn', generate_password_hash('password123'), '吴崇翔',
         '湖北工业大学', '艺术学院', '2023级', '吴', 4.6, 5, 0),
    ]
    for u in users:
        c.execute('''INSERT INTO users (username,email,password_hash,nickname,school,department,grade,
                     avatar_url,rating,sell_count,verified) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', u)

    uid = {row[0]: c.execute("SELECT id FROM users WHERE username=?", (row[0],)).fetchone()[0] for row in users}

    products_data = [
        (uid['wangxiaoyu'], 'MacBook Air M1 13寸 太空灰 8G+256G',
         '本人大三在读，因购入新设备出售此MacBook Air M1。使用约1.5年，电池健康度91%，外观无明显划痕，运行流畅。原装充电器和包装盒齐全，可开收据。',
         '数码电子', '八成新', 4200, 7499, 1, '校内自提,快递邮寄', '主校区 2号宿舍楼',
         'Apple,MacBook,M1芯片,学生用机', 'active', 0, 48, '💻', 'linear-gradient(135deg,#E3F2FD,#BBDEFB)'),
        (uid['chenmei'], '高数全套教材 同济第七版上下册',
         '九成新，几乎无笔记，大一下学期考完试就没用了，一直放在宿舍。',
         '教材书籍', '九成新', 35, 98, 1, '校内自提', '东校区 图书馆',
         '高数,同济,教材,数学', 'active', 0, 12, '📚', 'linear-gradient(135deg,#FFF3E0,#FFE0B2)'),
        (uid['liuyang'], '民谣吉他 40寸 原木色 初学者款',
         '七成新，音色良好，配有琴包、备用弦和调音器。买来练了半年，现在没时间弹了。',
         '乐器音响', '七成新', 280, 450, 1, '校内自提', '艺术学院',
         '吉他,民谣,乐器', 'active', 0, 23, '🎸', 'linear-gradient(135deg,#F3E5F5,#E1BEE7)'),
        (uid['zhanghao'], 'iPhone 13 128G 星光色',
         '九成新，无磕碰，屏幕无划痕，续航良好，电池健康93%，附原装充电头。',
         '数码电子', '九成新', 2800, 5199, 1, '校内自提,同城配送', '主校区',
         'iPhone,苹果,手机', 'active', 0, 67, '📱', 'linear-gradient(135deg,#E8F5E9,#C8E6C9)'),
        (uid['limingjun'], '迪卡侬登山背包 40L 全新',
         '全新未拆封，当时买多了，一直没用。原价199，急出。',
         '运动健身', '全新未拆封', 120, 199, 1, '校内自提', '主校区 体育馆',
         '背包,迪卡侬,户外,登山', 'active', 0, 8, '🎒', 'linear-gradient(135deg,#FFF8E1,#FFF3CD)'),
        (uid['wangxiaoyu'], '戴尔 27寸 4K IPS 显示器',
         '八成新，无亮点死点，接口齐全（HDMI/DP/USB），色彩准确，适合设计和编程。',
         '数码电子', '八成新', 1200, 2399, 1, '校内自提', '计算机学院',
         '显示器,戴尔,4K,设计', 'active', 0, 34, '🖥️', 'linear-gradient(135deg,#E8EAF6,#C5CAE9)'),
        (uid['chenmei'], '美利达公路自行车 21速变速',
         '七成新，变速流畅，刹车灵敏，适合校园骑行和通勤。已做过基础保养。',
         '出行工具', '七成新', 450, 1200, 1, '校内自提', '南校区',
         '自行车,公路车,美利达', 'active', 0, 19, '🚲', 'linear-gradient(135deg,#E0F7FA,#B2EBF2)'),
        (uid['liuyang'], '索尼 ZV-E10 微单相机 + 18-50镜头',
         '九成新，拍了两次就放着了。包括原装充电器、备用电池、存储卡、镜头盖等全套配件。',
         '数码电子', '九成新', 2200, 4499, 1, '校内自提,快递邮寄', '艺术学院',
         '索尼,微单,相机,ZVE10', 'active', 0, 56, '📷', 'linear-gradient(135deg,#FCE4EC,#F8BBD9)'),
    ]
    for p in products_data:
        c.execute('''INSERT INTO products (user_id,title,description,category,condition,price,original_price,
                     negotiable,trade_types,location,tags,status,views,like_count,cover_emoji,cover_color)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', p)

    # Seed posts
    posts_data = [
        (uid['wangxiaoyu'], '🎉 2024年末校园跳蚤市场开始报名！时间地点及规则公告',
         '一年一度的校园跳蚤市场将于12月22日（周日）在操场举行！今年新增电子产品专区和图书交换区，摊位限额80个，先报先得。所有在校生均可参与，无需摊位费，平台将统一提供二维码收款工具。报名截止12月18日，请在本帖回复或通过站内消息联系我们报名。\n\n活动时间：12月22日 上午9:00 - 下午4:00\n活动地点：主校区操场北侧\n报名方式：本帖回复或私信',
         'news', 0, '', 318, 2341, 47),
        (uid['chenmei'], '【急求】考研英语词汇书 + 真题汇编 整套，预算100元内',
         '考研刚结束，看了朋友的分数，打算再战一年。急需一套考研英语备考资料，红宝书或恋词都可以，最好有真题汇编（2010-2024）。100以内都可以，可以自提也可以快递。有的同学请站内联系我！',
         'wanted', 100, '很急，3天内', 12, 234, 8),
        (uid['limingjun'], '二手电子产品交易避坑指南——半年经验总结',
         '大家好，我在平台上买卖了十几次电子产品，总结了一些经验分享给大家。\n\n核心原则：\n1. 当面验货，开机测试所有功能\n2. 要求出示购买凭证（发票/苹果官网序列号查询）\n3. 电池健康度低于85%要大幅压价或放弃\n4. iPhone注意是否解ID锁，iPad注意MDM\n5. 笔记本要跑分测试，不能只看样子\n6. 转账时备注商品名，出问题有记录\n\n以下几类情况需要特别注意...',
         'tip', 0, '', 127, 891, 31),
        (uid['liuyang'], '毕业设计用完的画材和工具，9成新白送！来者自取~',
         '毕业设计做完了，一大堆专业画材和工具用不上了，白送给有需要的同学。\n\n包括：\n- 丙烯颜料（多色，各剩约1/2）\n- 画笔套装（油画笔+水粉笔）\n- 调色盘 x2\n- A1画板 x1\n- 素描本 A4 x3\n\n在学生活动中心302，本周五下午4-6点来取就行！先到先得，不接受预约哈。',
         'tip', 0, '', 89, 672, 52),
        (uid['zhanghao'], '【整理】各学院期末教材需求汇总，想出二手的同学可以参考',
         '临近期末，很多同学开始找二手教材了。我整理了一份各学院常用教材的需求列表，有对应教材的同学赶紧去发布吧，现在是最好出手的时候。\n\n需求量最大的：\n- 高等数学（同济版）\n- 线性代数\n- 大学物理\n- 英语综合教程\n- 马克思主义基本原理\n- C语言程序设计\n- 数据结构（严蔚敏版）',
         'news', 0, '', 203, 1543, 29),
    ]
    for p in posts_data:
        c.execute('''INSERT INTO posts (user_id,title,content,post_type,budget,urgency,like_count,view_count,comment_count)
                     VALUES (?,?,?,?,?,?,?,?,?)''', p)

    # Seed some product comments
    comments = [
        (1, uid['zhanghao'], None, '请问电池健康度还剩多少？日常使用续航怎么样？', 8),
        (1, uid['liuyang'], None, '这个配置很值！我上学期买了差不多的，4500买的，你这个价格还包原装配件真的很合适', 12),
        (1, uid['chenmei'], None, '4200可以再便宜一点不？我看其他的4000也有的啊', 1),
    ]
    for cmt in comments:
        c.execute('''INSERT INTO product_comments (product_id,user_id,parent_id,content,like_count)
                     VALUES (?,?,?,?,?)''', cmt)

    # Seed reply to first comment
    c.execute('''INSERT INTO product_comments (product_id,user_id,parent_id,content,like_count)
                 VALUES (?,?,?,?,?)''', (1, uid['wangxiaoyu'], 1, '电池健康度91%，日常轻量任务续航7-8小时，编程开发4-5小时左右，完全够用！', 3))

    # Seed post comments for all 5 posts
    post_ids = [row[0] for row in c.execute("SELECT id FROM posts ORDER BY id").fetchall()]

    post_comments_data = [
        # Post 1: 跳蚤市场公告
        (post_ids[0], uid['limingjun'],  None, '太好了！每年都期待这个！请问今年电子产品区有什么限制吗，iPad能卖吗', 34),
        (post_ids[0], uid['chenmei'],    None, '报名了！我准备出一堆大一的教材，希望能碰到有缘人😊', 18),
        (post_ids[0], uid['zhanghao'],   None, '操场北侧停车方便吗？我有些大件想搬过去', 7),
        (post_ids[0], uid['liuyang'],    None, '去年买了好多东西，今年打算换个角色当摊主哈哈', 22),
        (post_ids[0], uid['wangxiaoyu'], 1,    '可以的，只要是合规的电子产品都没问题，iPad欢迎！', 15),
        (post_ids[0], uid['wangxiaoyu'], 3,    '操场北门外面有停车位，也可以用小推车，我们会提供一些搬运工具', 9),

        # Post 2: 求购考研资料
        (post_ids[1], uid['zhanghao'],   None, '我有一套木糖英语全套，2023年版的，你要吗？可以便宜卖你', 11),
        (post_ids[1], uid['wangxiaoyu'], None, '我去年考研用的资料还在，红宝书+张剑真题，八成新，80块卖你', 8),
        (post_ids[1], uid['liuyang'],    None, '加油！二战一定上岸！我室友二战考上了中科院，很励志的', 29),
        (post_ids[1], uid['chenmei'],    1,    '真的吗！那太好了，你站内消息发我一下，我看看版本对不对', 6),
        (post_ids[1], uid['chenmei'],    2,    '已经私信你了，谢谢！', 4),

        # Post 3: 二手电子避坑指南
        (post_ids[2], uid['chenmei'],    None, '写得太好了！尤其是ID锁那条，我差点被坑，当时验机的时候发现了才没买', 47),
        (post_ids[2], uid['zhanghao'],   None, '补充一条：买MacBook一定要在关于本机里看原装电池循环次数，超过500就要当心', 38),
        (post_ids[2], uid['wangxiaoyu'], None, '强烈推荐！我第一次买二手手机就踩坑了，要是早看到这篇就好了😭', 25),
        (post_ids[2], uid['liuyang'],    None, '感谢分享！能问一下验机软件推荐哪个吗？AIDA64还是其他的', 13),
        (post_ids[2], uid['limingjun'],  4,    'iPhone用"手机管家"或者直接看设置里的电池健康，安卓推荐AIDA64或者CPU-Z，都免费', 19),
        (post_ids[2], uid['limingjun'],  3,    '对的，转账备注这个习惯太重要了，我处理过一个纠纷就是因为没有记录，最后说不清楚', 16),

        # Post 4: 白送画材
        (post_ids[3], uid['limingjun'],  None, '太好人了！我室友学美术的，能帮她问一下丙烯颜料还有哪些颜色吗', 21),
        (post_ids[3], uid['zhanghao'],   None, '已经去取了！调色盘和画笔都带走了，非常感谢！东西很好😊', 33),
        (post_ids[3], uid['wangxiaoyu'], None, '这种互助精神太赞了，点赞！希望这些画材能帮到有需要的同学', 27),
        (post_ids[3], uid['chenmei'],    None, '请问A1画板还有吗？下周有绘画课需要用', 9),
        (post_ids[3], uid['liuyang'],    4,    '画板已经被取走了，不好意思！不过素描本还剩两本，你有需要的话可以来拿', 7),
        (post_ids[3], uid['liuyang'],    1,    '大概有十几种颜色，白、黑、红、黄、蓝、绿都有，你室友可以来看看，周五下午一定来哈', 11),

        # Post 5: 教材需求汇总
        (post_ids[4], uid['liuyang'],    None, '我有高数同济版第七版上下册，九成新，35块出，有需要的同学联系我', 16),
        (post_ids[4], uid['limingjun'],  None, '大物谁有啊，马原也需要，最好是配套习题册的那种', 12),
        (post_ids[4], uid['chenmei'],    None, '数据结构严蔚敏版我这有一本，成色还行，有需要的来找我，不贵', 9),
        (post_ids[4], uid['wangxiaoyu'], None, '感谢整理！建议再加一本线性代数同济版，需求量也很大', 21),
        (post_ids[4], uid['zhanghao'],   4,    '好的，已经补充进去了，谢谢提醒！', 8),
        (post_ids[4], uid['zhanghao'],   2,    '大物和马原我手上有，稍等我整理一下发帖', 6),
    ]
    for pc in post_comments_data:
        c.execute('''INSERT INTO post_comments (post_id,user_id,parent_id,content,like_count)
                     VALUES (?,?,?,?,?)''', pc)

    # Update comment_count on posts
    for pid in post_ids:
        cnt = c.execute('SELECT COUNT(*) FROM post_comments WHERE post_id=?', (pid,)).fetchone()[0]
        c.execute('UPDATE posts SET comment_count=? WHERE id=?', (cnt, pid))

    # Seed a conversation
    c.execute('''INSERT INTO conversations (user1_id,user2_id,product_id,last_message,unread_2)
                 VALUES (?,?,?,?,?)''', (uid['limingjun'], uid['wangxiaoyu'], 1, '好的，明天下午3点图书馆见！', 2))
    conv_id = c.lastrowid
    msgs = [
        (conv_id, uid['limingjun'], '你好！请问MacBook还在吗？'),
        (conv_id, uid['wangxiaoyu'], '在的！你有什么想了解的吗'),
        (conv_id, uid['limingjun'], '电池健康度多少了？日常用主要开发，够用吗'),
        (conv_id, uid['wangxiaoyu'], '91%，日常开发4-5小时完全没问题，我用过两年了也挺顺畅的'),
        (conv_id, uid['limingjun'], '那可以4000拿吗？或者给个最低价'),
        (conv_id, uid['wangxiaoyu'], '最低4100，原装充电器盒子都在，这个价真的很合适了😊'),
        (conv_id, uid['limingjun'], '好的成交！什么时候能见面交易'),
        (conv_id, uid['wangxiaoyu'], '明天下午3点，主楼图书馆门口可以吗'),
        (conv_id, uid['limingjun'], '好的，明天下午3点图书馆见！'),
    ]
    for m in msgs:
        c.execute('INSERT INTO messages (conversation_id,sender_id,content) VALUES (?,?,?)', m)

    conn.commit()
    print("[DB] Demo data seeded successfully.")

if __name__ == '__main__':
    init_db()
    print("[DB] Database initialized at", DB_PATH)
