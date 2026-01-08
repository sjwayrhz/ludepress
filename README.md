# 路德社网站爬虫项目

这是一个用于爬取 ludepress.com 网站内容并存入 MySQL 数据库的 Python 爬虫项目。

## 功能特点

- ✅ **完整覆盖**：基于sitemap发现所有3643篇文章
- ✅ **混合爬取策略**：优先使用RSS Feed批量获取，补充sitemap缺失文章
- ✅ 自动提取文章分类并存储
- ✅ 数据库自动去重（基于GUID）
- ✅ 支持MySQL SSL加密连接
- ✅ 支持增量更新
- ✅ 详细的日志记录
- ✅ 环境变量配置管理
- ✅ Python 3.12 支持


## 数据库结构

项目包含以下数据表：

1. **creators** - 作者表
2. **categories** - 分类表
3. **articles** - 文章表
4. **article_categories** - 文章分类关联表

## 安装步骤

### 1. 克隆项目

```bash
cd ludepress
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置数据库连接

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

```bash
# MySQL数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=ludepress_db

# MySQL SSL配置（可选）
# 如果您的MySQL服务器需要SSL加密连接，请取消注释并配置以下选项
# DB_SSL_ENABLED=true
# DB_SSL_CA=/path/to/ca-cert.pem
# DB_SSL_CERT=/path/to/client-cert.pem
# DB_SSL_KEY=/path/to/client-key.pem
```

**注意**：爬虫配置（如BASE_URL、FEED_URL等）已硬编码在 `config.py` 中，无需在 `.env` 文件中配置。

### 5. 创建数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE ludepress_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 使用方法

### 运行爬虫

```bash
python scraper.py
```

爬虫将：
1. 自动创建数据库表结构
2. **步骤1**：从RSS Feed批量爬取文章（高效获取元数据和内容）
3. **步骤2**：从sitemap发现所有3643篇文章URL
4. **步骤3**：检查并补充爬取RSS中缺失的文章
5. 自动保存到MySQL数据库（自动去重）
6. 输出统计信息和分类统计

### 配置爬取范围

在 `.env` 文件中可以设置最大爬取的feed页数：

```bash
# 爬虫配置（可选）
MAX_FEED_PAGES=0  # 0表示无限制（爬取所有页面），设为5则爬取5页约50篇文章
```

### 查看日志

运行日志会同时输出到控制台和 `scraper.log` 文件。

## GitHub Actions 自动化部署

本项目支持使用GitHub Actions实现每日自动爬取，无需手动运行。

### 配置步骤

#### 1. 设置GitHub Secrets

在GitHub仓库页面，进入 `Settings` → `Secrets and variables` → `Actions` → `New repository secret`，添加以下密钥:

**必需配置**:
- `DB_HOST` - MySQL数据库主机地址
- `DB_USER` - 数据库用户名
- `DB_PASSWORD` - 数据库密码
- `DB_NAME` - 数据库名称 (如: `ludepress_db`)

**可选配置**:
- `DB_PORT` - 数据库端口 (默认: `3306`)
- `DB_SSL_ENABLED` - 是否启用SSL连接 (默认: `false`)
- `DB_SSL_CA` - SSL CA证书路径
- `DB_SSL_CERT` - SSL客户端证书路径
- `DB_SSL_KEY` - SSL客户端密钥路径

#### 2. 自动执行

工作流配置文件: `.github/workflows/scraper.yml`

- **定时执行**: 每天UTC 0点自动运行 (北京时间上午8点)
- **手动执行**: 在GitHub仓库的 `Actions` 标签页，选择 `Daily Article Scraper`，点击 `Run workflow` 按钮
- **默认爬取**: 每次爬取最多5页feed (约50篇最新文章)

#### 3. 查看运行结果

1. 进入仓库的 `Actions` 标签
2. 点击工作流运行记录查看执行日志
3. 下载 `scraper-log-xxx` 附件查看完整日志

### 注意事项

- 确保GitHub Actions能够访问您的MySQL数据库
- 如使用云数据库，需在安全组中开放允许GitHub Actions IP访问
- 建议使用SSL加密连接以提高安全性
- 首次运行建议手动触发并设置 `MAX_FEED_PAGES=0` 爬取所有历史文章

## 数据库操作指南

### 连接数据库

使用 MySQL 客户端连接到数据库：

```bash
# 命令行方式
mysql -h localhost -u your_username -p ludepress_db

# 或使用GUI工具（如 MySQL Workbench、phpMyAdmin、DBeaver等）
```

### 基础统计查询

#### 1. 查询文章总数

```sql
SELECT COUNT(*) AS total_articles FROM articles;
```

#### 2. 查询最近新增的文章（按插入时间）

```sql
-- 查询最近10篇新增的文章
SELECT id, title, pub_date, created_at 
FROM articles 
ORDER BY created_at DESC 
LIMIT 10;
```

#### 3. 查询今天新增的文章

```sql
SELECT COUNT(*) AS today_new_articles 
FROM articles 
WHERE DATE(created_at) = CURDATE();
```

#### 4. 查询最近7天新增的文章

```sql
SELECT COUNT(*) AS week_new_articles 
FROM articles 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY);
```

#### 5. 按日期统计新增文章数

```sql
SELECT 
    DATE(created_at) AS date,
    COUNT(*) AS article_count
FROM articles 
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 30;
```

### 文章查询

#### 1. 搜索标题包含关键词的文章

```sql
SELECT id, title, link, pub_date 
FROM articles 
WHERE title LIKE '%川普%'
ORDER BY pub_date DESC;
```

#### 2. 查询文章详情

```sql
SELECT 
    a.id,
    a.title,
    a.link,
    a.pub_date,
    a.description,
    c.name AS creator_name
FROM articles a
LEFT JOIN creators c ON a.creator_id = c.id
WHERE a.id = 1;  -- 替换为具体的文章ID
```

#### 3. 查询最新发布的文章

```sql
SELECT id, title, link, pub_date 
FROM articles 
ORDER BY pub_date DESC 
LIMIT 20;
```

### 分类查询

#### 1. 查询所有分类及文章数量

```sql
SELECT 
    c.id,
    c.name AS category_name,
    COUNT(ac.article_id) AS article_count
FROM categories c
LEFT JOIN article_categories ac ON c.id = ac.category_id
GROUP BY c.id, c.name
ORDER BY article_count DESC;
```

#### 2. 查询特定分类的所有文章

```sql
SELECT 
    a.id,
    a.title,
    a.link,
    a.pub_date
FROM articles a
JOIN article_categories ac ON a.id = ac.article_id
JOIN categories c ON ac.category_id = c.id
WHERE c.name = '路德时评'  -- 替换为具体的分类名称
ORDER BY a.pub_date DESC;
```

#### 3. 查询某篇文章的所有分类

```sql
SELECT 
    c.name AS category_name
FROM categories c
JOIN article_categories ac ON c.id = ac.category_id
WHERE ac.article_id = 1;  -- 替换为具体的文章ID
```

### 作者查询

#### 1. 查询所有作者及文章数量

```sql
SELECT 
    c.id,
    c.name AS creator_name,
    COUNT(a.id) AS article_count
FROM creators c
LEFT JOIN articles a ON c.id = a.creator_id
GROUP BY c.id, c.name
ORDER BY article_count DESC;
```

#### 2. 查询特定作者的所有文章

```sql
SELECT 
    a.id,
    a.title,
    a.link,
    a.pub_date
FROM articles a
JOIN creators c ON a.creator_id = c.id
WHERE c.name = '路德社编辑'  -- 替换为具体的作者名称
ORDER BY a.pub_date DESC;
```

### 高级查询

#### 1. 查询每个分类的最新文章

```sql
SELECT 
    c.name AS category_name,
    a.title,
    a.pub_date
FROM categories c
JOIN article_categories ac ON c.id = ac.category_id
JOIN articles a ON ac.article_id = a.id
WHERE (c.id, a.pub_date) IN (
    SELECT 
        c2.id,
        MAX(a2.pub_date)
    FROM categories c2
    JOIN article_categories ac2 ON c2.id = ac2.category_id
    JOIN articles a2 ON ac2.article_id = a2.id
    GROUP BY c2.id
)
ORDER BY c.name;
```

#### 2. 查询多分类文章（同时属于多个分类的文章）

```sql
SELECT 
    a.title,
    COUNT(DISTINCT ac.category_id) AS category_count,
    GROUP_CONCAT(c.name SEPARATOR ', ') AS categories
FROM articles a
JOIN article_categories ac ON a.id = ac.article_id
JOIN categories c ON ac.category_id = c.id
GROUP BY a.id, a.title
HAVING category_count > 1
ORDER BY category_count DESC;
```

#### 3. 查询按月份统计的文章发布量

```sql
SELECT 
    DATE_FORMAT(pub_date, '%Y-%m') AS month,
    COUNT(*) AS article_count
FROM articles
GROUP BY DATE_FORMAT(pub_date, '%Y-%m')
ORDER BY month DESC;
```

### 数据维护

#### 1. 删除重复文章（保留最早的）

```sql
DELETE a1 FROM articles a1
INNER JOIN articles a2 
WHERE a1.id > a2.id 
AND a1.guid = a2.guid;
```

#### 2. 更新文章分类

```sql
-- 为文章添加新分类
INSERT INTO article_categories (article_id, category_id)
SELECT 1, id FROM categories WHERE name = '要闻';  -- 文章ID=1，分类='要闻'
```

#### 3. 查找没有分类的文章

```sql
SELECT 
    a.id,
    a.title,
    a.link
FROM articles a
LEFT JOIN article_categories ac ON a.id = ac.article_id
WHERE ac.id IS NULL;
```

### 导出数据

#### 导出为CSV文件

```sql
-- 导出所有文章
SELECT 
    a.title,
    a.link,
    a.pub_date,
    c.name AS creator,
    GROUP_CONCAT(cat.name SEPARATOR ', ') AS categories
FROM articles a
LEFT JOIN creators c ON a.creator_id = c.id
LEFT JOIN article_categories ac ON a.id = ac.article_id
LEFT JOIN categories cat ON ac.category_id = cat.id
GROUP BY a.id
INTO OUTFILE '/tmp/articles.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

**注意**：需要 MySQL 有文件写入权限，路径需根据系统调整。

## 文件说明

- `scraper.py` - 主爬虫脚本
- `db_utils.py` - 数据库操作工具
- `config.py` - 配置管理模块
- `.env` - 环境变量配置（需自行创建）
- `.env.example` - 环境变量配置模板
- `requirements.txt` - Python 依赖包
- `.gitignore` - Git 忽略文件配置

## 分类说明

系统使用主分类白名单机制，只保存以下15个主分类（其他标签会被自动过滤）：

- **Featured** - 精选内容
- **专栏评论** - 评论文章
- **中共情资** - 中共情报资讯
- **军事** - 军事新闻
- **国会** - 国会相关
- **国际** - 国际新闻
- **地缘** - 地缘政治
- **墨文** - 墨文专栏
- **报道** - 一般报道
- **简讯** - 简短新闻
- **糯贴** - 糯贴专栏
- **美国** - 美国新闻
- **要闻** - 重要新闻
- **路德时评** - 路德时评专栏
- **闫博士说** - 闫博士专栏

> 注：每篇文章可以属于多个分类，平均每篇文章约2-3个分类。

## 注意事项

1. **数据库权限**：确保 MySQL 用户有足够的权限创建表和插入数据
2. **网络连接**：爬虫需要稳定的网络连接访问 ludepress.com
3. **爬取频率**：代码中已设置请求间隔，避免对服务器造成压力
4. **数据去重**：系统会自动检测重复文章（基于 GUID），避免重复插入

## 故障排除

### 1. 数据库连接失败

检查 `.env` 文件中的数据库配置是否正确，确保 MySQL 服务已启动。

### 2. 编码问题

确保数据库和表使用 `utf8mb4` 字符集，以正确存储中文内容。

### 3. 依赖安装失败

尝试升级 pip：

```bash
python -m pip install --upgrade pip
```

然后重新安装依赖。

## 开发信息

- **Python 版本**：3.12
- **数据库**：MySQL 5.7+
- **字符编码**：UTF-8

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request。