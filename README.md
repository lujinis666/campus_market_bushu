# 🏫 Campus Market · 校园闲置交易平台

一个专为大学生打造的校内二手交易全栈 Web 应用。

## 🗂️ 项目结构

```
campus_market/
├── app.py               # Flask 主应用入口
├── database.py          # SQLite 数据库 & 种子数据
├── start.py             # 一键启动脚本
├── campus_market.db     # SQLite 数据库（首次运行自动生成）
├── uploads/             # 用户上传的图片
├── static/
│   └── index.html       # 前端单页应用（SPA）
└── routes/
    ├── auth.py          # 认证：注册/登录/JWT
    ├── products.py      # 商品：CRUD/图片/收藏/评论
    ├── messages.py      # 消息：会话/聊天记录
    ├── community.py     # 社区：帖子/求购/点赞
    └── users.py         # 用户：主页/头像/评价/通知
```

## ⚡ 快速启动

**方法一：一键启动**
```bash
python3 start.py
```

**方法二：手动启动**
```bash
pip3 install flask PyJWT Pillow --break-system-packages
python3 app.py
```

访问：http://localhost:5000

**演示账号：** `limingjun` / `password123`

---

## 🔌 API 接口文档

Base URL: `http://localhost:5000/api`

认证方式：`Authorization: Bearer <JWT_TOKEN>`

---

### 🔐 认证模块 `/auth`

| 方法   | 路径              | 说明             | 需要认证 |
|--------|-------------------|------------------|----------|
| POST   | `/auth/register`  | 注册新用户       | ❌       |
| POST   | `/auth/login`     | 登录获取 token   | ❌       |
| GET    | `/auth/me`        | 获取当前用户信息 | ✅       |
| PUT    | `/auth/me`        | 更新个人资料     | ✅       |
| POST   | `/auth/change-password` | 修改密码   | ✅       |

**注册请求体：**
```json
{
  "username": "student01",
  "email": "student@pku.edu.cn",
  "password": "password123",
  "nickname": "张同学",
  "school": "北京大学",
  "department": "计算机学院",
  "grade": "2022级"
}
```

**登录响应：**
```json
{
  "token": "eyJ...",
  "user": { "id": 1, "nickname": "张同学", "email": "...", ... }
}
```

---

### 📦 商品模块 `/products`

| 方法   | 路径                         | 说明             | 需要认证 |
|--------|------------------------------|------------------|----------|
| GET    | `/products`                  | 商品列表（带筛选）| ❌       |
| POST   | `/products`                  | 发布商品         | ✅       |
| GET    | `/products/<id>`             | 商品详情         | ❌       |
| PUT    | `/products/<id>`             | 更新商品         | ✅       |
| DELETE | `/products/<id>`             | 删除商品         | ✅       |
| POST   | `/products/<id>/images`      | 上传商品图片     | ✅       |
| POST   | `/products/<id>/favorite`    | 收藏/取消收藏    | ✅       |
| GET    | `/products/<id>/comments`    | 获取留言列表     | ❌       |
| POST   | `/products/<id>/comments`    | 发布留言         | ✅       |
| POST   | `/products/comments/<id>/like` | 点赞留言       | ✅       |

**商品列表查询参数：**
```
?page=1&per_page=12
&sort=latest|popular|price_asc|price_desc
&category=数码电子
&condition=八成新
&min_price=100&max_price=5000
&q=MacBook（关键词搜索）
&user_id=1（指定用户的商品）
&status=active|sold|deleted
```

**发布商品请求体：**
```json
{
  "title": "MacBook Air M1",
  "category": "数码电子",
  "condition": "八成新",
  "price": 4200,
  "original_price": 7499,
  "description": "使用1.5年，电池健康91%...",
  "tags": "苹果,M1,笔记本",
  "location": "主校区 图书馆门口",
  "trade_types": "校内自提,快递邮寄",
  "negotiable": 1,
  "cover_emoji": "💻",
  "cover_color": "linear-gradient(135deg,#E3F2FD,#BBDEFB)"
}
```

---

### 💬 消息模块 `/messages`

| 方法   | 路径                                    | 说明           | 需要认证 |
|--------|-----------------------------------------|----------------|----------|
| GET    | `/messages/conversations`              | 会话列表       | ✅       |
| POST   | `/messages/conversations/start`        | 发起新会话     | ✅       |
| GET    | `/messages/conversations/<id>`         | 获取会话消息   | ✅       |
| POST   | `/messages/conversations/<id>/messages`| 发送消息       | ✅       |
| GET    | `/messages/unread-count`               | 未读消息数     | ✅       |

**发起会话请求体：**
```json
{ "user_id": 3, "product_id": 1 }
```

---

### 🌐 社区模块 `/community`

| 方法   | 路径                            | 说明         | 需要认证 |
|--------|---------------------------------|--------------|----------|
| GET    | `/community/posts`              | 帖子列表     | ❌       |
| POST   | `/community/posts`              | 发布帖子     | ✅       |
| GET    | `/community/posts/<id>`         | 帖子详情     | ❌       |
| DELETE | `/community/posts/<id>`         | 删除帖子     | ✅       |
| POST   | `/community/posts/<id>/like`    | 点赞帖子     | ✅       |
| GET    | `/community/posts/<id>/comments`| 帖子评论     | ❌       |
| POST   | `/community/posts/<id>/comments`| 发表评论     | ✅       |
| GET    | `/community/wanted`             | 热门求购列表 | ❌       |
| GET    | `/community/hot-tags`           | 热门标签     | ❌       |

**post_type 枚举：** `news`（资讯）/ `wanted`（求购）/ `tip`（经验）

---

### 👤 用户模块 `/users`

| 方法   | 路径                         | 说明         | 需要认证 |
|--------|------------------------------|--------------|----------|
| GET    | `/users/<id>`                | 用户公开主页 | ❌       |
| GET    | `/users/<id>/products`       | 用户发布商品 | ❌       |
| GET    | `/users/<id>/favorites`      | 用户收藏列表 | ✅(自己) |
| POST   | `/users/<id>/avatar`         | 上传头像     | ✅       |
| GET    | `/users/<id>/reviews`        | 获取评价     | ❌       |
| POST   | `/users/<id>/reviews`        | 发表评价     | ✅       |
| GET    | `/users/notifications`       | 通知列表     | ✅       |
| POST   | `/users/notifications/read-all` | 全部已读  | ✅       |

---

### 🔧 通用接口

| 方法  | 路径                        | 说明       |
|-------|-----------------------------|------------|
| GET   | `/stats`                    | 平台数据统计 |
| GET   | `/categories`               | 商品分类统计 |
| POST  | `/upload`                   | 通用图片上传 |
| GET   | `/search/suggestions?q=xxx` | 搜索建议 |
| GET   | `/uploads/<filename>`       | 获取上传文件 |

---

## 🗃️ 数据库设计

| 表名              | 说明         |
|-------------------|--------------|
| `users`           | 用户账号     |
| `products`        | 商品信息     |
| `product_images`  | 商品图片     |
| `product_comments`| 商品留言     |
| `comment_likes`   | 留言点赞     |
| `favorites`       | 商品收藏     |
| `conversations`   | 聊天会话     |
| `messages`        | 聊天消息     |
| `posts`           | 社区帖子     |
| `post_images`     | 帖子配图     |
| `post_comments`   | 帖子评论     |
| `post_likes`      | 帖子点赞     |
| `reviews`         | 交易评价     |
| `notifications`   | 系统通知     |

---

## 🚀 生产部署建议

1. **换用生产服务器**：`gunicorn app:app -w 4`
2. **使用 PostgreSQL**：替换 SQLite 以支持高并发
3. **CDN 加速图片**：将 uploads 目录接入 OSS/CDN
4. **HTTPS**：通过 Nginx 反向代理配置 SSL
5. **WebSocket**：升级消息模块为实时推送（Flask-SocketIO）
6. **Redis 缓存**：对热门商品列表、统计数据添加缓存

---

## 📋 功能清单

- ✅ 用户注册 / 登录 / JWT 认证
- ✅ 个人资料编辑 / 头像上传
- ✅ 商品发布（含图片上传，多张）
- ✅ 商品列表（分类、筛选、排序、分页、关键词搜索）
- ✅ 商品详情 + 卖家信息
- ✅ 商品收藏 / 取消收藏
- ✅ 商品留言 + 回复 + 点赞
- ✅ 搜索建议（实时 autocomplete）
- ✅ 站内聊天（买家↔卖家）
- ✅ 社区帖子（资讯 / 求购 / 经验）
- ✅ 帖子点赞 / 评论
- ✅ 用户信用评分 / 交易评价
- ✅ 通知系统（收藏/留言/消息提醒）
- ✅ 数据统计 API
