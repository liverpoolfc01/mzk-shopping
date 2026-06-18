# 🛒 MZK 电商系统

Python Flask + MySQL 全栈电商系统，包含用户端 Web/H5、商家后台管理、六大营销功能。

## 功能特性

### 用户端 (Web + H5 响应式)
- 商品浏览/搜索/分类筛选，支持价格销量排序
- 用户注册登录、收货地址管理
- 购物车 AJAX 增删改
- 订单流程：结算 → 收银台 → 模拟支付
- 订单管理：取消、确认收货、申请退款

### 后台管理 (商家)
- 仪表盘：商品/订单/用户/营收统计
- 商品管理：添加/编辑/上下架（支持图片上传）
- 订单管理：发货、退款处理
- 用户管理：启用/禁用

### 营销功能
- 🎫 **优惠券** — 固定金额/百分比折扣，满减门槛
- 👥 **拼团** — 发起/加入拼团队伍，成团判定，24h倒计时
- ⚡ **秒杀** — 限时抢购，悲观锁防超卖，限购
- 🎰 **抽奖** — 加权随机算法，每日限制，动画效果
- 🔪 **砍价** — 随机帮砍金额，分享邀请，低价购买
- 🎁 **盲盒福袋** — 加权随机开盒，开箱动画

## 技术栈

- **后端**: Python Flask + Jinja2 服务端渲染
- **数据库**: MySQL (SQLAlchemy ORM)
- **前端**: 移动优先响应式 CSS + Vanilla JS
- **认证**: Flask-Login + Werkzeug 密码哈希

## 快速开始

### 1. 环境准备

```bash
git clone <repo-url>
cd mzk_shopping
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置数据库

复制并编辑环境变量文件：
```bash
cp .env.example .env
# 编辑 .env 填入你的数据库连接信息
```

### 3. 初始化数据库

```bash
python scripts/init_db.py    # 创建所有表
python scripts/seed.py        # 导入种子数据
```

### 4. 启动服务

```bash
python run.py
# 访问 http://localhost:5001
```

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `test1234` |
| 测试用户 | `test` | `test1234` |

## 项目结构

```
mzk_shopping/
├── app/
│   ├── __init__.py          # Flask 工厂
│   ├── config.py            # 配置（从环境变量读取）
│   ├── models.py            # 22个数据模型
│   ├── decorators.py        # 登录/管理员装饰器
│   ├── helpers.py           # 工具函数
│   ├── routes/              # 路由模块
│   │   ├── auth.py          # 认证
│   │   ├── main.py          # 首页/商品
│   │   ├── cart.py          # 购物车
│   │   ├── order.py         # 订单/支付
│   │   ├── user.py          # 用户中心
│   │   ├── marketing.py     # 营销功能
│   │   └── admin.py         # 后台管理
│   └── templates/           # Jinja2 模板 (~45个)
├── static/
│   ├── css/style.css        # 移动优先响应式样式
│   ├── js/                  # 前端 JS
│   └── uploads/             # 商品图片
├── scripts/
│   ├── init_db.py           # 建表脚本
│   └── seed.py              # 种子数据
├── requirements.txt
└── run.py
```

## 数据库

22张表覆盖：用户、地址、分类、商品、购物车、订单、优惠券、拼团、抽奖、秒杀、砍价、盲盒

## License

MIT
