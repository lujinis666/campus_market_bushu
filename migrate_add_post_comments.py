"""
migrate_add_post_comments.py
运行一次即可：python3 migrate_add_post_comments.py
为现有数据库的帖子添加种子评论
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db

db = get_db()
c = db.cursor()

# Already have comments?
existing = c.execute("SELECT COUNT(*) FROM post_comments").fetchone()[0]
if existing > 0:
    print(f"[跳过] 已存在 {existing} 条帖子评论，无需重复添加。")
    db.close()
    sys.exit(0)

# Get user ids
def uid(username):
    row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    return row[0] if row else None

u = {
    'wang': uid('wangxiaoyu'),
    'li':   uid('limingjun'),
    'chen': uid('chenmei'),
    'zhang':uid('zhanghao'),
    'liu':  uid('liuyang'),
}

# Get post ids in order
posts = [row[0] for row in c.execute("SELECT id FROM posts ORDER BY id").fetchall()]
if len(posts) < 5:
    print(f"[错误] 只找到 {len(posts)} 个帖子，需要至少5个。请先运行 python3 app.py 初始化数据。")
    db.close()
    sys.exit(1)
p = posts  # p[0]~p[4]

comments = [
    # Post 1: 跳蚤市场公告
    (p[0], u['li'],    None, '太好了！每年都期待这个！请问今年电子产品区有什么限制吗，iPad能卖吗', 34),
    (p[0], u['chen'],  None, '报名了！我准备出一堆大一的教材，希望能碰到有缘人😊', 18),
    (p[0], u['zhang'], None, '操场北侧停车方便吗？我有些大件想搬过去', 7),
    (p[0], u['liu'],   None, '去年买了好多东西，今年打算换个角色当摊主哈哈', 22),
    (p[0], u['wang'],  None, '可以的，只要是合规的电子产品都没问题，iPad欢迎！（回复第1楼）', 15),
    (p[0], u['wang'],  None, '操场北门外面有停车位，也可以用小推车，我们会提供搬运工具（回复第3楼）', 9),
    # Post 2: 求购考研资料
    (p[1], u['zhang'], None, '我有一套木糖英语全套，2023年版的，你要吗？可以便宜卖你', 11),
    (p[1], u['wang'],  None, '我去年考研用的资料还在，红宝书+张剑真题，八成新，80块卖你', 8),
    (p[1], u['liu'],   None, '加油！二战一定上岸！我室友二战考上了中科院，很励志的', 29),
    (p[1], u['chen'],  None, '真的吗！那太好了，你站内消息发我一下，我看看版本对不对（回复楼上）', 6),
    # Post 3: 电子避坑指南
    (p[2], u['chen'],  None, '写得太好了！尤其是ID锁那条，我差点被坑，验机时发现了才没买', 47),
    (p[2], u['zhang'], None, '补充一条：买MacBook一定要看原装电池循环次数，超过500就要当心', 38),
    (p[2], u['wang'],  None, '强烈推荐！我第一次买二手手机就踩坑了，要是早看到这篇就好了😭', 25),
    (p[2], u['liu'],   None, '感谢分享！能问一下验机软件推荐哪个吗？AIDA64还是其他的', 13),
    (p[2], u['li'],    None, 'iPhone直接看设置里电池健康，安卓推荐AIDA64或CPU-Z，都免费（回复验机问题）', 19),
    # Post 4: 白送画材
    (p[3], u['li'],    None, '太好人了！我室友学美术的，能帮她问一下丙烯颜料还有哪些颜色吗', 21),
    (p[3], u['zhang'], None, '已经去取了！调色盘和画笔都带走了，非常感谢！东西很好😊', 33),
    (p[3], u['wang'],  None, '这种互助精神太赞了！希望这些画材能帮到有需要的同学', 27),
    (p[3], u['chen'],  None, '请问A1画板还有吗？下周有绘画课需要用', 9),
    (p[3], u['liu'],   None, '画板已被取走，不好意思！素描本还剩两本，周五下午来拿哈（回复）', 7),
    # Post 5: 教材需求汇总
    (p[4], u['liu'],   None, '我有高数同济版第七版上下册，九成新，35块出，有需要联系我', 16),
    (p[4], u['li'],    None, '大物谁有啊，马原也需要，最好配套习题册的那种', 12),
    (p[4], u['chen'],  None, '数据结构严蔚敏版我这有一本，成色还行，有需要来找我，不贵', 9),
    (p[4], u['wang'],  None, '建议再加线性代数同济版，需求量也很大', 21),
    (p[4], u['zhang'], None, '好的，已经补充了，谢谢提醒！（回复楼上）', 8),
    (p[4], u['zhang'], None, '大物和马原我手上有，稍等整理一下发帖（回复）', 6),
]

for row in comments:
    c.execute('INSERT INTO post_comments (post_id,user_id,parent_id,content,like_count) VALUES (?,?,?,?,?)', row)

# Update comment_count
for pid in p:
    cnt = c.execute('SELECT COUNT(*) FROM post_comments WHERE post_id=?', (pid,)).fetchone()[0]
    c.execute('UPDATE posts SET comment_count=? WHERE id=?', (cnt, pid))

db.commit()
db.close()
print(f"✅ 已添加 {len(comments)} 条帖子评论！重启服务器后生效。")
